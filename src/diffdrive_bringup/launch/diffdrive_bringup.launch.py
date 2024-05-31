from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    ExecuteProcess
)
from launch.substitutions import (
    LaunchConfiguration,
    Command
)
from ament_index_python.packages import get_package_share_directory
from launch_ros.actions import Node
import os


def generate_launch_description():
    diffdrive_bringup_path = get_package_share_directory('diffdrive_bringup')
    declared_arguments = [
        DeclareLaunchArgument(
            "world",
            default_value=os.path.join(diffdrive_bringup_path, "worlds", "default_world.sdf"),
            description="Robot controller to start.",
        )
    ]

    gazebo = IncludeLaunchDescription(
        os.path.join(get_package_share_directory("ros_ign_gazebo"), 'launch', 'ign_gazebo.launch.py'),
         launch_arguments=[('ign_args', [LaunchConfiguration('world'),' -v 4'])]
    )

    ign_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="ign_bridge",
        ros_arguments=["-p", f"config_file:={os.path.join(diffdrive_bringup_path, 'config', 'ign_bridge.yaml')}"],
        output="screen",
    )

    rviz2 = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        arguments=["-d", os.path.join(diffdrive_bringup_path, 'rviz', 'localization.rviz')],
        output="screen",
    )

    gazebo_spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        name="spawn_diffdrive_robot",
        arguments=["-name", "diffdrive_robot", "-topic", "robot_description"],
        output="screen",
    )

    xacro_file = os.path.join(get_package_share_directory('diffdrive_description'), 'urdf', 'robot.urdf.xacro')
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="both",
        parameters=[
            {'robot_description': Command(['xacro ', xacro_file]) },
            {'use_sim_time' : True}

        ],
    )

    robot_localization_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[
            os.path.join(diffdrive_bringup_path, 'config', 'ekf.yaml'),
            {'use_sim_time' : True}
        ]
    )

    load_joint_state_controller = ExecuteProcess(
        name="activate_joint_state_broadcaster",
        cmd=["ros2", "control", "load_controller", "--set-state", "active", "joint_state_broadcaster"],
        shell=False,
        output="screen",
    )

    load_joint_trajectory_controller = ExecuteProcess(
        name="activate_diff_drive_controller",
        cmd=[ "ros2", "control", "load_controller", "--set-state", "active", "diff_drive_controller"],
        shell=False,
        output="screen",
    )

    return LaunchDescription(
        declared_arguments +
        [
            ign_bridge,
            gazebo,
            gazebo_spawn_robot,
            robot_state_publisher,
            robot_localization_node,
            load_joint_state_controller,
            load_joint_trajectory_controller,
            rviz2
        ])