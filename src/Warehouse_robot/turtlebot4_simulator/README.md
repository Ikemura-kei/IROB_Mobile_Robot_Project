# Turtlebot4 Simulator

Turtlebot4 Simulation using Harmonic Gazebo for ROS 2 Jazzy.

Visit the [TurtleBot 4 User Manual](https://turtlebot.github.io/turtlebot4-user-manual/software/turtlebot4_simulator.html) for details.

## Installation
```bash
sudo apt-get update && sudo apt-get install wget
sudo sh -c 'echo "deb http://packages.osrfoundation.org/gazebo/ubuntu-stable `lsb_release -cs` main" > /etc/apt/sources.list.d/gazebo-stable.list'
wget http://packages.osrfoundation.org/gazebo.key -O - | sudo apt-key add -
sudo apt-get update
sudo apt-get install gz-harmonic ros-jazzy-turtlebot4-simulator
```
