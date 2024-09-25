import os

import launch
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    diffdrive_bringup = get_package_share_directory("diffdrive_bringup")

    main_param_dir = LaunchConfiguration(
        "main_param_dir",
        default=os.path.join(diffdrive_bringup, "config", "lidar_slam.yaml"),
    )

    mapping = Node(
        package="scanmatcher",
        executable="scanmatcher_node",
        parameters=[main_param_dir, {"use_sim_time": True}],
        remappings=[
            ("/input_cloud", "lidar"),
            ("/odom", "/odometry/filtered"),
        ],
        output="screen",
    )

    graph_based_slam = Node(
        package="graph_based_slam",
        executable="graph_based_slam_node",
        parameters=[main_param_dir, {"use_sim_time": True}],
        output="screen",
    )

    return launch.LaunchDescription(
        [
            DeclareLaunchArgument(
                "main_param_dir",
                default_value=main_param_dir,
                description="Full path to main parameter file to load",
            ),
            DeclareLaunchArgument(
                "use_sim",
                default_value="True",
                description="Use /clock as time source.",
            ),
            mapping,
            graph_based_slam
        ]
    )
