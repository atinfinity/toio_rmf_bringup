#!/usr/bin/env python3
# Copyright 2026
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Dispensers and ingestors that acknowledge requests without moving anything.

RMF's delivery task hands the pickup and dropoff to workcells, not to the
robot: it publishes a DispenserRequest and waits for a DispenserResult with a
matching request_guid. Nothing on a play mat can transfer a payload, and
without something answering, a delivery task stalls at the pickup forever.

These nodes answer. They report themselves IDLE, take a request, wait a
moment so the robot is visibly parked at the waypoint, and report SUCCESS.
A standard delivery task never triggers the robot's own LED / chime
feedback: toio_fleet_adapter implements those as the fleet actions
delivery_pickup / delivery_dropoff, which run only through a separate
perform_action (dispatch_action) task.
"""

import argparse
import sys

import rclpy
from rclpy.node import Node
from rmf_dispenser_msgs.msg import DispenserRequest, DispenserResult, DispenserState
from rmf_ingestor_msgs.msg import IngestorRequest, IngestorResult, IngestorState


class MockWorkcell(Node):
    """One workcell that answers requests addressed to its own guid."""

    def __init__(self, name, guid, prefix, request_type, result_type,
                 state_type, handle_seconds, state_period=1.0):
        super().__init__(name)
        self.guid = guid
        self.result_type = result_type
        self.state_type = state_type
        self.handle_seconds = handle_seconds
        # request_guid -> hold timer. Doubles as the queue reported in the
        # state messages (dict order is arrival order). Do not rename this to
        # _timers: that is an rclpy Node attribute that create_timer appends
        # every timer to, and clobbering it once made "cancel the oldest
        # timer" cancel the state timer instead of the hold timer.
        self._pending = {}

        self._result_pub = self.create_publisher(
            result_type, f'/{prefix}_results', 10)
        self._state_pub = self.create_publisher(
            state_type, f'/{prefix}_states', 10)
        self.create_subscription(
            request_type, f'/{prefix}_requests', self._on_request, 10)
        self.create_timer(state_period, self._publish_state)
        self.get_logger().info(f'{guid} ready')

    def _on_request(self, msg):
        if msg.target_guid != self.guid:
            return
        if msg.request_guid in self._pending:
            # RMF repeats the request until it sees a result, so a repeat is
            # normal rather than a second job
            return
        self.get_logger().info(f'{self.guid}: request {msg.request_guid}')
        # A timer, not a sleep: the state has to keep publishing while the
        # request is being "handled", or RMF sees the workcell go silent
        self._pending[msg.request_guid] = self.create_timer(
            self.handle_seconds, lambda: self._complete(msg.request_guid))
        self._publish_state()

    def _complete(self, request_guid):
        timer = self._pending.pop(request_guid, None)
        if timer is None:
            return
        # create_timer makes periodic timers; destroy this one or it fires
        # again and publishes the result a second time
        self.destroy_timer(timer)
        result = self.result_type()
        result.time = self.get_clock().now().to_msg()
        result.request_guid = request_guid
        result.source_guid = self.guid
        result.status = self.result_type.SUCCESS
        self._result_pub.publish(result)
        self._publish_state()
        self.get_logger().info(f'{self.guid}: {request_guid} done')

    def _publish_state(self):
        state = self.state_type()
        state.time = self.get_clock().now().to_msg()
        state.guid = self.guid
        state.mode = (
            self.state_type.BUSY if self._pending else self.state_type.IDLE)
        state.request_guid_queue = list(self._pending)
        state.seconds_remaining = float(
            self.handle_seconds if self._pending else 0.0)
        self._state_pub.publish(state)


def main(argv=sys.argv):
    rclpy.init(args=argv)
    parser = argparse.ArgumentParser(
        prog='mock_workcells',
        description='Mock RMF dispensers and ingestors for the toio demo')
    parser.add_argument(
        '--dispensers', nargs='*', default=[],
        help='guids to answer DispenserRequests for')
    parser.add_argument(
        '--ingestors', nargs='*', default=[],
        help='guids to answer IngestorRequests for')
    parser.add_argument(
        '--handle-seconds', type=float, default=3.0,
        help='how long a request takes to complete')
    args = parser.parse_args(rclpy.utilities.remove_ros_args(argv)[1:])

    nodes = []
    for guid in args.dispensers:
        nodes.append(MockWorkcell(
            f'mock_dispenser_{guid}', guid, 'dispenser',
            DispenserRequest, DispenserResult, DispenserState,
            args.handle_seconds))
    for guid in args.ingestors:
        nodes.append(MockWorkcell(
            f'mock_ingestor_{guid}', guid, 'ingestor',
            IngestorRequest, IngestorResult, IngestorState,
            args.handle_seconds))
    if not nodes:
        print('no workcells requested; pass --dispensers and/or --ingestors')
        return

    executor = rclpy.executors.SingleThreadedExecutor()
    for node in nodes:
        executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        for node in nodes:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main(sys.argv)
