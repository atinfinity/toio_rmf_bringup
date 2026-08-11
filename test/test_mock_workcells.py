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
Unit tests for the mock workcells.

A MockWorkcell and a probe node run in one executor, so requests, results
and states travel over real ROS 2 topics the same way RMF sees them. The
script is loaded from scripts/ by path because it is installed as a program,
not as a Python package.
"""

import importlib.util
import pathlib
import time

import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rmf_dispenser_msgs.msg import DispenserRequest, DispenserResult, DispenserState
from rmf_ingestor_msgs.msg import IngestorRequest, IngestorResult, IngestorState

_SCRIPT = pathlib.Path(__file__).resolve().parents[1] / 'scripts' / 'mock_workcells.py'
_spec = importlib.util.spec_from_file_location('mock_workcells', _SCRIPT)
mock_workcells = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mock_workcells)

# Short enough to keep the tests fast, long enough that a BUSY state
# (republished every state_period) is reliably observed before completion.
HANDLE_SECONDS = 0.3
STATE_PERIOD = 0.05


@pytest.fixture(scope='module', autouse=True)
def ros_context():
    rclpy.init()
    yield
    rclpy.shutdown()


class Probe(Node):
    """Publishes requests and records the results and states that come back."""

    def __init__(self, name, prefix, request_type, result_type, state_type):
        super().__init__(name)
        self.results = []
        self.states = []
        self.request_pub = self.create_publisher(
            request_type, f'/{prefix}_requests', 10)
        self.create_subscription(
            result_type, f'/{prefix}_results', self.results.append, 10)
        self.create_subscription(
            state_type, f'/{prefix}_states', self.states.append, 10)


class Harness:
    """One MockWorkcell plus a probe, spun together."""

    def __init__(self, name, guid, prefix, request_type, result_type, state_type):
        self.cell = mock_workcells.MockWorkcell(
            name, guid, prefix, request_type, result_type, state_type,
            HANDLE_SECONDS, state_period=STATE_PERIOD)
        self.probe = Probe(f'probe_{name}', prefix,
                           request_type, result_type, state_type)
        self.executor = SingleThreadedExecutor()
        self.executor.add_node(self.cell)
        self.executor.add_node(self.probe)
        # The publisher and subscriptions live in one process, but matching
        # still has to happen before a published request can arrive.
        assert self.spin_until(
            lambda: self.probe.request_pub.get_subscription_count() > 0, 2.0)

    def spin_until(self, predicate, timeout):
        deadline = time.monotonic() + timeout
        while not predicate() and time.monotonic() < deadline:
            self.executor.spin_once(timeout_sec=0.05)
        return predicate()

    def send(self, request_type, target_guid, request_guid):
        request = request_type()
        request.target_guid = target_guid
        request.request_guid = request_guid
        self.probe.request_pub.publish(request)

    def close(self):
        self.executor.remove_node(self.cell)
        self.executor.remove_node(self.probe)
        self.cell.destroy_node()
        self.probe.destroy_node()


@pytest.fixture
def dispenser():
    harness = Harness('cell_dispenser', 'toio_dispenser', 'dispenser',
                      DispenserRequest, DispenserResult, DispenserState)
    yield harness
    harness.close()


@pytest.fixture
def ingestor():
    harness = Harness('cell_ingestor', 'toio_ingestor', 'ingestor',
                      IngestorRequest, IngestorResult, IngestorState)
    yield harness
    harness.close()


def test_request_completes_with_success(dispenser):
    dispenser.send(DispenserRequest, 'toio_dispenser', 'req-1')

    assert dispenser.spin_until(lambda: dispenser.probe.results, 5.0)
    result = dispenser.probe.results[0]
    assert result.status == DispenserResult.SUCCESS
    assert result.request_guid == 'req-1'
    assert result.source_guid == 'toio_dispenser'


def test_state_is_busy_while_handling_and_idle_after(dispenser):
    dispenser.send(DispenserRequest, 'toio_dispenser', 'req-2')

    assert dispenser.spin_until(lambda: dispenser.probe.results, 5.0)
    # The completion also republishes the state; wait for that one.
    assert dispenser.spin_until(
        lambda: dispenser.probe.states
        and dispenser.probe.states[-1].mode == DispenserState.IDLE, 2.0)

    busy = [s for s in dispenser.probe.states
            if s.mode == DispenserState.BUSY]
    assert busy, 'no BUSY state was published while the request was handled'
    assert all('req-2' in s.request_guid_queue for s in busy)
    assert all(s.seconds_remaining > 0.0 for s in busy)
    assert dispenser.probe.states[-1].request_guid_queue == []


def test_request_for_another_guid_is_ignored(dispenser):
    dispenser.send(DispenserRequest, 'someone_else', 'req-3')

    # Bounded wait: nothing should come back, and the cell must stay IDLE.
    dispenser.spin_until(lambda: False, HANDLE_SECONDS + 0.3)
    assert dispenser.probe.results == []
    assert all(s.mode == DispenserState.IDLE for s in dispenser.probe.states)


def test_repeated_request_yields_a_single_result(dispenser):
    # RMF repeats a request until it sees a result; a repeat is the same
    # job, not a second one.
    dispenser.send(DispenserRequest, 'toio_dispenser', 'req-4')
    dispenser.send(DispenserRequest, 'toio_dispenser', 'req-4')

    assert dispenser.spin_until(lambda: dispenser.probe.results, 5.0)
    dispenser.spin_until(lambda: False, HANDLE_SECONDS + 0.3)
    assert len(dispenser.probe.results) == 1


def test_states_keep_publishing_after_completion(dispenser):
    # Regression: the cell once cancelled its own state timer instead of the
    # hold timer, going silent for RMF after the first handled request.
    dispenser.send(DispenserRequest, 'toio_dispenser', 'req-6')
    assert dispenser.spin_until(lambda: dispenser.probe.results, 5.0)

    seen = len(dispenser.probe.states)
    assert dispenser.spin_until(
        lambda: len(dispenser.probe.states) >= seen + 3, 5.0)
    assert dispenser.probe.states[-1].mode == DispenserState.IDLE


def test_ingestor_answers_ingestor_requests(ingestor):
    ingestor.send(IngestorRequest, 'toio_ingestor', 'req-5')

    assert ingestor.spin_until(lambda: ingestor.probe.results, 5.0)
    result = ingestor.probe.results[0]
    assert result.status == IngestorResult.SUCCESS
    assert result.request_guid == 'req-5'
    assert result.source_guid == 'toio_ingestor'
