# KTH DD2410 (IROB) Assignment 5

## 1. 🖥️ Usage for Lab PC

The lab machines run everything inside a `pixi shell` rather than through
`pixi run`. The shell activates the same environment the tasks use, so ROS 2,
Gazebo and the `GZ_*` variables the simulator needs are all in place once you
are inside it.

ROS 2 itself comes from the `dd2410` module, not from pixi: the default pixi
environment deliberately declares no packages, so `pixi shell` here downloads
and installs **nothing**. Run `module add dd2410` *before* `pixi shell`, so the
shell inherits it.

### 1.1 Pre-requisites
Make sure you have enough disk quota left on the lab machine. A fully-used quota can even create login issues.

We provide a simple utility to check both the disk quota used and the storage distribution. Just run

```bash
bash scripts/check_disk_usage.sh 
```

A window should pop-up with the information on disk quota usage percentage and storage distribution. It will refresh periodically so you can see your real-time disk usage. An interesting observation would be open `Chrome` and you might see disk usage slowly rises, since `Chrome` puts cache and stuff. Cleaning the cache directory is recommended once in a while.

### 1.2 Installation

```bash
git clone https://github.com/Ikemura-kei/IROB_Mobile_Robot_Project.git
cd IROB_Mobile_Robot_Project

source /etc/profile.d/modules.sh # This line by now should be in your .bashrc, if not, either add it now or accept the fact that you need to run this everytime.
module add dd2410 # This line by now should be in your .bashrc, if not, either add it now or accept the fact that you need to run this everytime.

pixi shell
```

Then build:

```bash
MAKEFLAGS=-j2 CMAKE_BUILD_PARALLEL_LEVEL=2 colcon build --base-paths src/Warehouse_robot --parallel-workers 4
```

> ⚠️ **Keep those two variables.** They cap how many compilers run at once.
> `colcon` builds four packages in parallel and each package's `make` then uses
> every core by itself, so without the cap you get four times as many concurrent
> compilers as the machine has cores, which is enough to exhaust its RAM and
> freeze it.

### 1.3 Running the project codebase

Open two terminals. **Each needs its own `pixi shell` and its own
`source install/setup.bash`** — the environment does not carry between
terminals, and `setup.bash` is what puts the packages you just built onto the
ROS path.

Terminal-1:
```bash
pixi shell
source install/setup.bash
export ROS_LOCALHOST_ONLY=1
GRADE=e ros2 launch warehouse_inventory_robot mission.launch.py
```

Terminal-2:
```bash
pixi shell
source install/setup.bash
export ROS_LOCALHOST_ONLY=1
GRADE=e ros2 run warehouse_inventory_robot mission_node --ros-args -p use_sim_time:=true
```

Use the same grade in both — `GRADE` is what selects it, exactly as in
section 2. Change it to `c` or `a` for those grades. If you would rather not
repeat it, `export GRADE=c` once per terminal does the same thing.

Upon killing the simulation, run the cleaning utility — Gazebo and its helper
nodes are sometimes left orphaned, and they interfere with the next run:
```bash
bash scripts/sim_clean.sh
```

In case changes are made to `mission_node.py`, rebuild only that package:
```bash
colcon build --base-paths src/Warehouse_robot --packages-select warehouse_inventory_robot
```

Leave the pixi shell environment with the command `exit`.

## 2. 💻 Usage on your own devices

### 2.1 Installation

Please clone the repo:
```bash
git clone https://github.com/Ikemura-kei/IROB_Mobile_Robot_Project.git
```

Then please run the following to install:
```bash
cd IROB_Mobile_Robot_Project
pixi install -e own-device
pixi run -e own-device build
```

> ℹ️ **Why `-e own-device`.** The default environment is the one the lab PCs
> use, and it installs no packages because the lab machines already provide ROS
> 2. On your own machine you want pixi to supply the whole ROS 2 stack instead,
> which is what the `own-device` environment is for. Pass `-e own-device` to
> every `pixi install` and `pixi run` below, or the commands will run against
> the empty default environment and fail to find `ros2`.

### 2.2 Running the project codebase

Open two terminals and run the following commands.

Terminal-1:
```bash
export ROS_LOCALHOST_ONLY=1
GRADE=e pixi run -e own-device mission
```

Terminal-2:
```bash
export ROS_LOCALHOST_ONLY=1
GRADE=e pixi run -e own-device mission-node
```

Upon killing the simulation, it is recommended to run a cleaning utility, since the Gazebo server is sometimes left orphaned and interferes with the next run:
```bash
pixi run -e own-device sim-clean
```

In case changes are made to `mission_node.py`, you only need to recompile that specific package. Feel free to use the provided utility `pixi run -e own-device build-mission`, which builds only the package you modified.

## 3. 💡 Hints and tips
> You will need to have configuration files for at least `nav2` and `amcl` packages. Those configuration files can be placed at `src/Warehouse_robot/warehouse_inventory_robot/config`!

> We provide the map of the environment at `src/Warehouse_robot/warehouse_inventory_robot/maps`, so you do not need to generate one yourself.

> ⚠️ Feel free to add your own files (configuration files, utilities, and so on), but unless you have a very good justification, these are the only two files you should edit:
> * `src/Warehouse_robot/warehouse_inventory_robot/launch/mission.launch.py`
> * `src/Warehouse_robot/warehouse_inventory_robot/warehouse_inventory_robot/mission_node.py`
