# KTH DD2410 (IROB) Assignment 5

## 1. 🖥️ Usage for Lab PC

The lab machines get ROS 2, Gazebo and `colcon` from the `dd2410` environment
module, which the administrators have bundled with everything the course needs.
You load the module and enter a `pixi shell`, which picks that bundled
environment up — nothing is downloaded or installed.

For that to work this repository deliberately keeps **no pixi project in its
root**: `pixi.toml` and `pixi.lock` live in `pixi/` instead. pixi searches the
current directory and its parents for a manifest, never its children, so
`pixi shell` here finds the module's bundled environment rather than a manifest
belonging to this repository. The one in `pixi/` is only for students running on
their own machine, and is opted into explicitly (section 2).

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

Open two terminals. **Each needs the `dd2410` module, its own `pixi shell` and
its own `source install/setup.bash`** — the environment does not carry between
terminals, and `setup.bash` is what puts the packages you just built onto the
ROS path.

Terminal-1:
```bash
source /etc/profile.d/modules.sh
module add dd2410
pixi shell
source install/setup.bash
export ROS_LOCALHOST_ONLY=1
export GZ_IP=127.0.0.1
GRADE=e ros2 launch warehouse_inventory_robot mission.launch.py
```

Terminal-2:
```bash
source /etc/profile.d/modules.sh
module add dd2410
pixi shell
source install/setup.bash
export ROS_LOCALHOST_ONLY=1
export GZ_IP=127.0.0.1
GRADE=e ros2 run warehouse_inventory_robot mission_node --ros-args -p use_sim_time:=true
```

> ⚠️ **Keep `GZ_IP=127.0.0.1`.** It pins Gazebo's transport to loopback. Without
> it, gz binds whichever external interface it finds first, which in a lab means
> your simulation and the machine next to you can discover each other and
> interfere.

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
pixi shell --manifest-path pixi
pixi run build
```

The first command downloads the whole ROS 2 stack and drops you in a shell that
has it; the second builds the workspace. Expect the install to take a while and
a few GB the first time. It is cached, so later runs are fast.

> ℹ️ **Why `--manifest-path pixi`.** The pixi project deliberately does not live
> in the repository root — the lab machines get ROS 2 from an environment module
> and must not see a pixi project at all (section 1). So `pixi.toml` and
> `pixi.lock` sit in `pixi/`, and you point pixi at them once with
> `--manifest-path pixi` (`-m pixi` for short). Running plain `pixi shell` in the
> repository root will just report that it found no manifest — that is expected.
>
> You only need the flag to *enter* the shell. Once inside, `pixi run ...` finds
> the project on its own, and the tasks build into the repository root rather
> than into `pixi/`.

### 2.2 Running the project codebase

Open two terminals. **Each needs its own `pixi shell`** — the environment does
not carry between terminals.

Terminal-1:
```bash
pixi shell --manifest-path pixi
export ROS_LOCALHOST_ONLY=1
GRADE=e pixi run mission
```

Terminal-2:
```bash
pixi shell --manifest-path pixi
export ROS_LOCALHOST_ONLY=1
GRADE=e pixi run mission-node
```

Upon killing the simulation, it is recommended to run a cleaning utility, since the Gazebo server is sometimes left orphaned and interferes with the next run:
```bash
pixi run sim-clean
```

In case changes are made to `mission_node.py`, you only need to recompile that specific package. Feel free to use the provided utility `pixi run build-mission`, which builds only the package you modified.

## 3. 💡 Hints and tips
> You will need to have configuration files for at least `nav2` and `amcl` packages. Those configuration files can be placed at `src/Warehouse_robot/warehouse_inventory_robot/config`!

> We provide the map of the environment at `src/Warehouse_robot/warehouse_inventory_robot/maps`, so you do not need to generate one yourself.

> ⚠️ Feel free to add your own files (configuration files, utilities, and so on), but unless you have a very good justification, these are the only two files you should edit:
> * `src/Warehouse_robot/warehouse_inventory_robot/launch/mission.launch.py`
> * `src/Warehouse_robot/warehouse_inventory_robot/warehouse_inventory_robot/mission_node.py`
