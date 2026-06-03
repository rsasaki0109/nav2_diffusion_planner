cmake_minimum_required(VERSION 3.8)
project(nav2_diffusion_benchmarks)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(nav2_diffusion_core REQUIRED)
find_package(nav2_costmap_2d REQUIRED)
find_package(geometry_msgs REQUIRED)

add_library(${PROJECT_NAME} SHARED
  src/metrics.cpp
  src/collision_metrics.cpp
  src/report.cpp
)
target_compile_features(${PROJECT_NAME} PUBLIC cxx_std_17)
target_include_directories(${PROJECT_NAME} PUBLIC
  "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>"
  "$<INSTALL_INTERFACE:include>"
)
ament_target_dependencies(${PROJECT_NAME} nav2_diffusion_core nav2_costmap_2d geometry_msgs)

install(
  DIRECTORY include/
  DESTINATION include
)
install(
  TARGETS ${PROJECT_NAME}
  EXPORT export_${PROJECT_NAME}
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

ament_export_targets(export_${PROJECT_NAME} HAS_LIBRARY_TARGET)
ament_export_include_directories(include)
ament_export_dependencies(nav2_diffusion_core nav2_costmap_2d geometry_msgs)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()

  find_package(ament_cmake_gtest REQUIRED)
  ament_add_gtest(test_metrics test/test_metrics.cpp)
  target_link_libraries(test_metrics ${PROJECT_NAME})

  ament_add_gtest(test_collision_metrics test/test_collision_metrics.cpp)
  target_link_libraries(test_collision_metrics ${PROJECT_NAME})
  ament_target_dependencies(test_collision_metrics nav2_costmap_2d geometry_msgs)

  ament_add_gtest(test_report test/test_report.cpp)
  target_link_libraries(test_report ${PROJECT_NAME})
endif()

ament_package()
