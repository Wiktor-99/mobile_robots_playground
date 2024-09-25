from setuptools import find_packages, setup

package_name = 'diffdrive_description'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/urdf/', ['urdf/' + 'robot.urdf.xacro']),
        ('share/' + package_name + '/urdf/', ['urdf/' + 'macros.urdf.xacro'])
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='wiktorbajor1@gmail.com',
    maintainer_email='wiktorbajor1@gmail.com',
    description='Description of diffdrive_robot',
    license='Apache License 2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
        ],
    },
)
