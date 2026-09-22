from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'warehouse_inventory_robot'

# 1. Define the standard flat directories
data_files = [
    ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
    ('share/' + package_name, ['package.xml']),
    (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    (os.path.join('share', package_name, 'maps'), glob('maps/*')),
    (os.path.join('share', package_name, 'urdf'), glob('urdf/*')),
    (os.path.join('share', package_name, 'worlds'), glob('worlds/*.sdf')), # Ensure worlds are installed!
    (os.path.join('share', package_name, 'rviz'), glob('rviz/*.rviz')),
]

# 2. Recursively add the 'models' directory to preserve nested folders (like materials/textures)
for root, dirs, files in os.walk('models'):
    for file in files:
        # Destination path inside the install folder
        dest_dir = os.path.join('share', package_name, root)
        # Source file path
        source_file = os.path.join(root, file)
        data_files.append((dest_dir, [source_file]))

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=data_files, # <-- Use the list we built above
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Instructor',
    description='Warehouse Inventory Robot — ROS2 Jazzy final project base package',
    license='MIT',
    entry_points={
        'console_scripts': [
            'mission_node = warehouse_inventory_robot.mission_node:main',
            'wait_for_ready = warehouse_inventory_robot.utils.wait_for_ready:main',
            # Examiner tool for A-grade runs; not part of the mission.
            'relocate_robot = warehouse_inventory_robot.utils.relocate_robot:main',
        ],
    },
)