cmake_minimum_required(VERSION 3.10.2 FATAL_ERROR)

if(POLICY CMP0100)
  cmake_policy(SET CMP0100 NEW)
endif()

set(CMAKE_AUTOMOC ON)
set(OpenGL_GL_PREFERENCE LEGACY)

# Find Qt5
find_package(Qt5
  COMPONENTS
    Core
    Quick
    QuickControls2
  REQUIRED
)

# Find the Gz gui library
find_package(gz_gui_vendor REQUIRED)
find_package(gz-gui REQUIRED)
find_package(gz_common_vendor REQUIRED)
find_package(gz-common REQUIRED)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${GZ-GUI_CXX_FLAGS}")

qt5_add_resources(resources_rcc Turtlebot4Hmi.qrc)

include_directories(SYSTEM
  ${GZ-COMMON_INCLUDE_DIRS}
  ${GZ-GUI_INCLUDE_DIRS}
  ${Qt5Core_INCLUDE_DIRS}
  ${Qt5Qml_INCLUDE_DIRS}
  ${Qt5Quick_INCLUDE_DIRS}
  ${Qt5QuickControls2_INCLUDE_DIRS}
)

link_directories(
  ${GZ-COMMON_LIBRARY_DIRS}
  ${GZ-GUI_LIBRARY_DIRS}
)

# Generate examples
# MOC parsing is broken on Ionic: https://github.com/gazebosim/gz-msgs/issues/463
add_library(Turtlebot4Hmi SHARED ${headers_MOC}
Turtlebot4Hmi.cc
  ${resources_rcc}
)
target_link_libraries(Turtlebot4Hmi
  ${GZ-GUI_LIBRARIES}
  ${Qt5Core_LIBRARIES}
  ${Qt5Qml_LIBRARIES}
  ${Qt5Quick_LIBRARIES}
  ${Qt5QuickControls2_LIBRARIES}
)

install(
  TARGETS Turtlebot4Hmi
  DESTINATION share/${PROJECT_NAME}/lib
)
