FROM althack/ros2:iron-cuda-full
ARG ROS_DISTRO=iron
ARG USERNAME=ros
ARG USER_UID=1000
ARG USER_GID=$USER_UID

ENV SHELL /bin/bash
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y sudo \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y python3-pip lsb-release wget gnupg

RUN sudo wget https://packages.osrfoundation.org/gazebo.gpg -O /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null && \
    apt-get update --fix-missing && \
    apt-get -y install \
    git-core \
    bash-completion \
    ros-$ROS_DISTRO-rmw-cyclonedds-cpp \
    ros-$ROS_DISTRO-xacro \
    ros-$ROS_DISTRO-ros2-control \
    ros-$ROS_DISTRO-robot-localization \
    ros-$ROS_DISTRO-ros-gzharmonic \
    ros-$ROS_DISTRO-ros-gzharmonic-bridge \
    ros-$ROS_DISTRO-ros2-controllers \
    ros-$ROS_DISTRO-libg2o \
    ros-$ROS_DISTRO-sdformat-urdf &&\
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV OptiX_INSTALL_DIR=/optix
ENV NVIDIA_DRIVER_CAPABILITIES=all
ENV GZ_VERSION=harmonic
RUN . /opt/ros/${ROS_DISTRO}/setup.sh && \
    mkdir -p /gz_ros2_control_ws/src && \
    cd /gz_ros2_control_ws/src && \
    git clone --branch $ROS_DISTRO https://github.com/ros-controls/gz_ros2_control && \
    cd /gz_ros2_control_ws && \
    colcon build
ENV DEBIAN_FRONTEND=dialog

ARG WORKSPACE
RUN echo "if [ -f /opt/ros/${ROS_DISTRO}/setup.bash ]; then source /opt/ros/${ROS_DISTRO}/setup.bash; fi" >> /home/$USERNAME/.bashrc \
    && echo "if [ -f /usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash ]; then source /usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash; fi" >> /home/$USERNAME/.bashrc \
    && echo "if [ -f ${WORKSPACE}/install/setup.bash ]; then source ${WORKSPACE}/install/setup.bash; fi" >> //home/$USERNAME/.bashrc \
    && echo "if [ -f /gz_ros2_control_ws/install/setup.bash ]; then source /gz_ros2_control_ws/install/setup.bash; fi" >> //home/$USERNAME/.bashrc
