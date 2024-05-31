from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'diffdrive_bringup'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join("share", package_name, "rviz"), glob("rviz/*.rviz")),
        (os.path.join("share", package_name, "launch"), glob("launch/*.py")),
        (os.path.join("share", package_name, "config"), glob("config/*.yaml")),
        (os.path.join("share", package_name, "worlds"), glob("worlds/*.sdf"))
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='wiktorbajor1@gmail.com',
    maintainer_email='wiktorbajor1@gmail.com',
    description='Bringup of diffdrive_robot',
    license='Apache License 2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [],
    },
)
