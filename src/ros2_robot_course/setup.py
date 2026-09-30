import os
from glob import glob

from setuptools import setup

package_name = 'ros2_robot_course'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        (os.path.join('share', package_name), ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob(os.path.join(package_name, 'launch', '*.launch.py'))),
        (os.path.join('share', package_name, 'world'),
            glob(os.path.join(package_name, 'world', '*.world')) +
            glob(os.path.join(package_name, 'world', '*.sdf'))),
        (os.path.join('share', package_name, 'urdf'),
            glob(os.path.join(package_name, 'urdf', '*.xacro')) +
            glob(os.path.join(package_name, 'urdf', '*.urdf'))),
        (os.path.join('share', package_name, 'config'),
            glob(os.path.join(package_name, 'config', '*.yaml')) +
            glob(os.path.join(package_name, 'config', '*.rviz'))),
        (os.path.join('share', package_name, 'maps'),
            glob(os.path.join(package_name, 'maps', '*.pgm')) +
            glob(os.path.join(package_name, 'maps', '*.yaml'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='student',
    maintainer_email='student@example.com',
    description='ROS2 Humble Gazebo differential-drive SLAM + AMCL + Nav2 course project',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'send_goal = ros2_robot_course.send_goal:main',
            'verify_nav = ros2_robot_course.verify_nav:main',
            'moving_obstacle = ros2_robot_course.moving_obstacle:main',
        ],
    },
)
