#!/usr/bin/env bash
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
#
# Set up a workspace for the toio Open-RMF integration on
# Ubuntu 24.04 + ROS 2 Jazzy.
#
# Usage:
#   ./setup_environment.sh [--ws <path>] [--with-demos] [--with-toio-py]
#                          [--skip-viz-patch]
#
#   --ws <path>       workspace root (default: ~/dev_ws)
#   --with-demos      also set up rmf_demos (Office world) for baseline
#                     verification: source-clone + partial build + Gazebo
#                     model symlinks. Not needed to run the toio fleet.
#   --with-toio-py    install toio.py into a venv (~/toio_venv) for driving
#                     real cubes over BLE. Requires a Bluetooth adapter.
#   --skip-viz-patch  do NOT overlay the small-maps-patched rmf_visualization.
#                     By default the script clones rmf_visualization 2.3.2 and
#                     applies patches/rmf_visualization-small-maps.patch so RViz
#                     renders the tiny toio mats correctly (see docs/SETUP.md).
#                     Skipping keeps the apt rmf_visualization; RViz markers
#                     then bury the mat, but driving/traffic are unaffected.
#
# Prerequisites: ROS 2 Jazzy installed under /opt/ros/jazzy, and the
# `gh` CLI (used for cloning; authentication is only needed while any
# of the toio repositories is still private).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

WS="$HOME/dev_ws"
WITH_DEMOS=0
WITH_TOIO_PY=0
SKIP_VIZ_PATCH=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --ws) WS="$2"; shift 2 ;;
    --with-demos) WITH_DEMOS=1; shift ;;
    --with-toio-py) WITH_TOIO_PY=1; shift ;;
    --skip-viz-patch) SKIP_VIZ_PATCH=1; shift ;;
    *) echo "unknown option: $1"; exit 1 ;;
  esac
done

VIZ_PATCH="${SCRIPT_DIR}/../patches/rmf_visualization-small-maps.patch"
RMF_VIZ_TAG="2.3.2"  # tag the small-maps patch is verified against

echo "=== [1/6] Installing Open-RMF and dependencies (apt) ==="
sudo apt-get update
sudo apt-get install -y \
  ros-jazzy-rmf-dev \
  ros-jazzy-rmf-fleet-adapter-python \
  ros-jazzy-rmf-task-ros2 \
  ros-jazzy-rmf-traffic-editor \
  ros-jazzy-rmf-building-map-tools \
  ros-jazzy-rmf-visualization \
  ros-jazzy-rmf-demos-tasks \
  ros-jazzy-rmf-demos-assets \
  ros-jazzy-rmf-building-sim-gz-plugins \
  ros-jazzy-rmf-robot-sim-gz-plugins \
  ros-jazzy-tf-transformations \
  python3-colcon-common-extensions \
  python3-rosdep \
  python3-pil

if [[ $WITH_DEMOS -eq 1 ]]; then
  # Python dependencies of rmf_demos_fleet_adapter's fleet_manager
  sudo apt-get install -y \
    python3-fastapi python3-uvicorn python3-websockets \
    python3-socketio python3-flask-socketio python3-pyproj
fi

echo "=== [2/6] Cloning repositories into ${WS}/src ==="
mkdir -p "${WS}/src"
cd "${WS}/src"
clone() {  # clone <repo> [branch]
  local repo="$1" branch="${2:-}"
  if [[ -d "${repo##*/}" ]]; then
    echo "  ${repo##*/}: already present, skipping"
    return
  fi
  gh repo clone "$repo" -- ${branch:+-b "$branch"}
}
# toio_msgs carries the LED/sound/pose message types imported by toio_ros2,
# toio_gazebo and toio_fleet_adapter; without it the fleet adapter and the
# Gazebo LED/sound nodes die on `ModuleNotFoundError: No module named
# 'toio_msgs'`. It is not a released package, so rosdep cannot supply it.
clone atinfinity/toio_msgs
clone atinfinity/toio_ros2
clone atinfinity/toio_navigation
clone atinfinity/toio_description
clone atinfinity/toio_gazebo
clone atinfinity/toio_rmf_maps
clone atinfinity/toio_fleet_adapter
clone atinfinity/toio_rmf_bringup

if [[ $SKIP_VIZ_PATCH -eq 0 ]]; then
  # RViz marker sizes assume tens-of-meters buildings and bury a toio mat, so
  # overlay rmf_visualization with the small-maps patch (docs/SETUP.md). Pin to
  # the tag the patch is verified against; only the two patched packages are
  # built from source later (the rest stay from the debs).
  if [[ ! -d rmf_visualization ]]; then
    git clone --branch "$RMF_VIZ_TAG" \
      https://github.com/open-rmf/rmf_visualization.git
  fi
  if git -C rmf_visualization apply --reverse --check "$VIZ_PATCH" 2>/dev/null; then
    echo "  rmf_visualization: small-maps patch already applied, skipping"
  else
    git -C rmf_visualization apply "$VIZ_PATCH"
    echo "  rmf_visualization: applied small-maps patch"
  fi
fi

if [[ $WITH_DEMOS -eq 1 && ! -d rmf_demos ]]; then
  git clone -b jazzy https://github.com/open-rmf/rmf_demos
fi

echo "=== [3/6] Resolving ROS dependencies (rosdep) ==="
if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
  sudo rosdep init
fi
rosdep update
# The ROS setup files dereference unbound vars (e.g. AMENT_TRACE_SETUP_FILES),
# which aborts under `set -u`; relax it just for the source.
set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u
rosdep install --from-paths "${WS}/src" --ignore-src -y \
  --skip-keys "rmf_demos_assets rmf_demos_tasks rmf_demos_bridges" || true

if [[ $WITH_DEMOS -eq 1 ]]; then
  echo "=== [4/6] Gazebo model symlinks for the rmf_demos Office world ==="
  # The generated office.world references model://Open-RMF/TinyRobot and
  # model://TeleportDispenser|Ingestor, which are neither auto-downloaded
  # from Fuel nor exposed under those names by the rmf_demos_assets deb.
  ASSETS=/opt/ros/jazzy/share/rmf_demos_assets/models
  mkdir -p "$HOME/.gazebo/models/Open-RMF"
  ln -sfn "$ASSETS/TinyRobot" "$HOME/.gazebo/models/Open-RMF/TinyRobot"
  ln -sfn "$ASSETS/TinyRobot" "$HOME/.gazebo/models/TinyRobot"
  ln -sfn "$ASSETS/TeleportDispenser" "$HOME/.gazebo/models/TeleportDispenser"
  ln -sfn "$ASSETS/TeleportIngestor" "$HOME/.gazebo/models/TeleportIngestor"
else
  echo "=== [4/6] Skipping rmf_demos setup (enable with --with-demos) ==="
fi

echo "=== [5/6] Building the workspace ==="
cd "${WS}"
# rmf_demos_assets/tasks/bridges come from debs; building them from
# source is unnecessary and they are therefore ignored when the
# rmf_demos sources are present. The rmf_visualization tree is likewise
# skipped here and only its two patched packages are built below, so the
# rest keep coming from the debs.
VIZ_IGNORE=()
if [[ $SKIP_VIZ_PATCH -eq 0 ]]; then
  VIZ_IGNORE=(--packages-ignore-regex 'rmf_visualization.*')
fi
colcon build --symlink-install \
  --packages-ignore rmf_demos_assets rmf_demos_tasks rmf_demos_bridges \
  "${VIZ_IGNORE[@]}"

if [[ $SKIP_VIZ_PATCH -eq 0 ]]; then
  echo "=== [5/6] Building patched rmf_visualization overlay ==="
  # Only the two packages the small-maps patch touches; they link against the
  # apt-installed rmf_visualization_msgs / rmf_traffic and override the debs.
  colcon build --symlink-install \
    --packages-select rmf_visualization_navgraphs rmf_visualization_schedule
fi

if [[ $WITH_TOIO_PY -eq 1 ]]; then
  echo "=== [6/6] Installing toio.py into ~/toio_venv (for real cubes) ==="
  # Ubuntu 24.04 is PEP 668 externally-managed; use a venv that can still
  # see the ROS python packages
  python3 -m venv --system-site-packages "$HOME/toio_venv"
  "$HOME/toio_venv/bin/pip" install toio.py
  echo "  Run real-robot nodes with: source ~/toio_venv/bin/activate"
else
  echo "=== [6/6] Skipping toio.py (enable with --with-toio-py) ==="
fi

echo ""
echo "Done. Verify with:"
echo "  source ${WS}/install/setup.bash"
echo "  python3 ${WS}/src/toio_rmf_maps/scripts/verify_alignment.py"
echo "  ros2 launch toio_rmf_bringup toio_rmf.launch.py mat:=a3 run_sim:=true use_sim_time:=true"
echo "  ros2 run rmf_demos_tasks dispatch_patrol -p patrol_A patrol_D -n 2 --use_sim_time"
