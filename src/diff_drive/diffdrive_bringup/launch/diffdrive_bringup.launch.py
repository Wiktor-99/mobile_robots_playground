from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler
from launch.substitutions import (
    LaunchConfiguration,
    Command,
    PathJoinSubstitution,
)
from launch.event_handlers import OnProcessExit
from launch.conditions import IfCondition, UnlessCondition
from ament_index_python.packages import get_package_share_directory
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
import os
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    diffdrive_bringup_path = get_package_share_directory("diffdrive_bringup")
    declared_arguments = [
        DeclareLaunchArgument(
            "world",
            default_value=os.path.join(diffdrive_bringup_path, "worlds", "default_world.sdf"),
            description="Robot controller to start.",
        ),
        DeclareLaunchArgument(
            "use_lidar_slam",
            default_value="False",
            description="Use or not lidar slam",
        ),
    ]

    use_lidar_slam = LaunchConfiguration("use_lidar_slam")
    lidar_slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([diffdrive_bringup_path, "/launch/lidar_slam.launch.py"]),
        condition=IfCondition(use_lidar_slam),
    )

    gazebo = IncludeLaunchDescription(
        os.path.join(get_package_share_directory("ros_gz_sim"), "launch", "gz_sim.launch.py"),
        launch_arguments=[("gz_args", ["-r -v 4 ", LaunchConfiguration("world")])],
    )

    ign_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="ign_bridge",
        ros_arguments=["-p", f"config_file:={os.path.join(diffdrive_bringup_path, 'config', 'ign_bridge.yaml')}"],
        output="screen",
    )

    rviz2_lidar_slam = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        arguments=["-d", os.path.join(diffdrive_bringup_path, "rviz", "localization.rviz")],
        output="screen",
        condition=IfCondition(use_lidar_slam),
    )

    rviz2_nav = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        arguments=["-d", os.path.join(diffdrive_bringup_path, "rviz", "nav2.rviz")],
        output="screen",
        condition=UnlessCondition(use_lidar_slam),
    )

    slam_toolbox = IncludeLaunchDescription(
        os.path.join(get_package_share_directory("slam_toolbox"), "launch", "online_async_launch.py"),
        launch_arguments={
            "use_sim_time": "True",
            "params_file": PathJoinSubstitution(
                [get_package_share_directory("diffdrive_bringup"), "config", "mapper_params_online_async.yaml"]
            ),
        }.items(),
        condition=UnlessCondition(use_lidar_slam),
    )

    nav2_bring_up = IncludeLaunchDescription(
        os.path.join(get_package_share_directory("nav2_bringup"), "launch", "navigation_launch.py"),
        launch_arguments={
            "use_sim_time": "True",
            "params_file": PathJoinSubstitution(
                [get_package_share_directory("diffdrive_bringup"), "config", "nav2_params.yaml"]
            ),
        }.items(),
        condition=UnlessCondition(use_lidar_slam),
    )

    gazebo_spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        name="spawn_diffdrive_robot",
        arguments=["-name", "diffdrive_robot", "-topic", "robot_description"],
        output="screen",
    )

    xacro_file = os.path.join(get_package_share_directory("diffdrive_description"), "urdf", "robot.urdf.xacro")
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="both",
        parameters=[
            {"robot_description": Command(["xacro ", xacro_file, " use_3d_lidar:=", use_lidar_slam])},
            {"use_sim_time": True},
        ],
    )

    robot_localization_node = Node(
        package="robot_localization",
        executable="ekf_node",
        name="ekf_filter_node",
        output="screen",
        parameters=[os.path.join(diffdrive_bringup_path, "config", "ekf.yaml"), {"use_sim_time": True}],
    )

    robot_controllers = PathJoinSubstitution(
        [
            FindPackageShare("diffdrive_bringup"),
            "config",
            "controllers.yaml",
        ]
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--switch-timeout", "30", "--param-file", robot_controllers],
    )

    diff_drive_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["diff_drive_controller", "--param-file", robot_controllers],
    )

    return LaunchDescription(
        declared_arguments
        + [
            ign_bridge,
            gazebo,
            robot_state_publisher,
            robot_localization_node,
            RegisterEventHandler(
                event_handler=OnProcessExit(
                    target_action=gazebo_spawn_robot,
                    on_exit=[joint_state_broadcaster_spawner],
                )
            ),
            RegisterEventHandler(
                event_handler=OnProcessExit(
                    target_action=joint_state_broadcaster_spawner,
                    on_exit=[diff_drive_controller_spawner],
                )
            ),
            gazebo_spawn_robot,
            lidar_slam,
            slam_toolbox,
            nav2_bring_up,
            rviz2_lidar_slam,
            rviz2_nav,
        ]
    )
