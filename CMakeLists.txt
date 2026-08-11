cmake_minimum_required(VERSION 3.5)

project(toio_rmf_bringup)

find_package(ament_cmake REQUIRED)

install(DIRECTORY
  launch
  rviz
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/mock_workcells.py
  DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # ament_copyright also requires CONTRIBUTING.md and a LICENSE file in a
  # layout it recognizes; skip it (the copyright test is skipped in
  # toio_ros2 and toio_description as well)
  set(ament_cmake_copyright_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
