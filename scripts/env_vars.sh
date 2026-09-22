#! /bin/bash

unset ROS_LOCALHOST_ONLY
unset ROS_AUTOMATIC_DISCOVERY_RANGE
export FASTRTPS_DEFAULT_PROFILES_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/fastdds_localhost.xml"
export GZ_IP=127.0.0.1
export GZ_SIM_SYSTEM_PLUGIN_PATH=$CONDA_PREFIX/lib
