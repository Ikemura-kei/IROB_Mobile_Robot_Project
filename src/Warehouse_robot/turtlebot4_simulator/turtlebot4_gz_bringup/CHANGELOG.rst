^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Changelog for package turtlebot4_gz_bringup
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

2.0.2 (2024-10-29)
------------------
* Add -r flag to Gazebo arguments (see https://github.com/turtlebot/turtlebot4_simulator/issues/81)
* Add missing dependency on create3_gz_plugins
* Contributors: Chris Iverach-Brereton

2.0.1 (2024-09-25)
------------------

2.0.0 (2024-09-03)
------------------
* Ignition/ign rename to gz
* Update launch files to remove deprecations
* Use new `view_navigation` launch for the `rviz` argument
* Update dependencies for Gazebo Harmonic
* Enable OSRF testing packages for Github CI
* Initial Jazzy implementation (`#80 <https://github.com/turtlebot/turtlebot4_simulator/issues/80>`_)
* Linting & formatting fixes
* Contributors: Chris Iverach-Brereton

1.0.2 (2024-04-15)
------------------
* Update deprecated links (`#70 <https://github.com/turtlebot/turtlebot4_simulator/issues/70>`_)
  * Update deprecated links
  * Commented out models that are currently broken on the fuel server
* Contributors: Hilary Luo

1.0.1 (2023-11-08)
------------------
* Merge pull request <https://github.com/turtlebot/turtlebot4_simulator/issues/57>
* Merge pull request <https://github.com/turtlebot/turtlebot4_simulator/issues/58>
* Remove outdated world
* Don't push namespace to nav, it is handled in the nav launch files
* Contributors: Hilary Luo

1.0.0 (2023-05-16)
------------------
* Multiple robot support
* Spawn robot slightly lower to reduce the drop and rollback, ensuring the robot starts properly docked
* Add default model type for HMI plugin
* Make warehouse the default world
* Fixed model spawning in wall, improved visuals and made locations less ambiguous for slam
* Fixed world name and set max step size for better performance
* Added namespace support
* Contributors: Hilary Luo, Roni Kreinin, roni-kreinin

0.1.1 (2022-05-09)
------------------
* Added irobot_create_nodes dependency
* Contributors: Roni Kreinin

0.1.0 (2022-05-04)
------------------
* First Galactic release
* Contributors: Katherine Scott, Roni Kreinin
