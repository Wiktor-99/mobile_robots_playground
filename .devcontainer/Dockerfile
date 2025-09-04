FROM osrf/ros:jazzy-desktop-full-noble


ENV NVARCH=x86_64

ENV NVIDIA_REQUIRE_CUDA="cuda>=12.9 brand=unknown,driver>=535,driver<536 brand=grid,driver>=535,driver<536 brand=tesla,driver>=535,driver<536 brand=nvidia,driver>=535,driver<536 brand=quadro,driver>=535,driver<536 brand=quadrortx,driver>=535,driver<536 brand=nvidiartx,driver>=535,driver<536 brand=vapps,driver>=535,driver<536 brand=vpc,driver>=535,driver<536 brand=vcs,driver>=535,driver<536 brand=vws,driver>=535,driver<536 brand=cloudgaming,driver>=535,driver<536 brand=unknown,driver>=550,driver<551 brand=grid,driver>=550,driver<551 brand=tesla,driver>=550,driver<551 brand=nvidia,driver>=550,driver<551 brand=quadro,driver>=550,driver<551 brand=quadrortx,driver>=550,driver<551 brand=nvidiartx,driver>=550,driver<551 brand=vapps,driver>=550,driver<551 brand=vpc,driver>=550,driver<551 brand=vcs,driver>=550,driver<551 brand=vws,driver>=550,driver<551 brand=cloudgaming,driver>=550,driver<551 brand=unknown,driver>=560,driver<561 brand=grid,driver>=560,driver<561 brand=tesla,driver>=560,driver<561 brand=nvidia,driver>=560,driver<561 brand=quadro,driver>=560,driver<561 brand=quadrortx,driver>=560,driver<561 brand=nvidiartx,driver>=560,driver<561 brand=vapps,driver>=560,driver<561 brand=vpc,driver>=560,driver<561 brand=vcs,driver>=560,driver<561 brand=vws,driver>=560,driver<561 brand=cloudgaming,driver>=560,driver<561 brand=unknown,driver>=565,driver<566 brand=grid,driver>=565,driver<566 brand=tesla,driver>=565,driver<566 brand=nvidia,driver>=565,driver<566 brand=quadro,driver>=565,driver<566 brand=quadrortx,driver>=565,driver<566 brand=nvidiartx,driver>=565,driver<566 brand=vapps,driver>=565,driver<566 brand=vpc,driver>=565,driver<566 brand=vcs,driver>=565,driver<566 brand=vws,driver>=565,driver<566 brand=cloudgaming,driver>=565,driver<566 brand=unknown,driver>=570,driver<571 brand=grid,driver>=570,driver<571 brand=tesla,driver>=570,driver<571 brand=nvidia,driver>=570,driver<571 brand=quadro,driver>=570,driver<571 brand=quadrortx,driver>=570,driver<571 brand=nvidiartx,driver>=570,driver<571 brand=vapps,driver>=570,driver<571 brand=vpc,driver>=570,driver<571 brand=vcs,driver>=570,driver<571 brand=vws,driver>=570,driver<571 brand=cloudgaming,driver>=570,driver<571"
ENV NV_CUDA_CUDART_VERSION=12.9.79-1
ARG TARGETARCH

RUN apt-get update && apt-get install -y --no-install-recommends \
    gnupg2 curl ca-certificates && \
    curl -fsSL https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/${NVARCH}/3bf863cc.pub | apt-key add - && \
    echo "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/${NVARCH} /" > /etc/apt/sources.list.d/cuda.list && \
    apt-get purge --autoremove -y curl \
    && rm -rf /var/lib/apt/lists/*

ENV CUDA_VERSION=12.9.1

# For libraries in the cuda-compat-* package: https://docs.nvidia.com/cuda/eula/index.html#attachment-a
RUN apt-get update && apt-get install -y --no-install-recommends \
    cuda-cudart-12-9=${NV_CUDA_CUDART_VERSION} \
    cuda-compat-12-9 \
    && rm -rf /var/lib/apt/lists/*

RUN echo "/usr/local/cuda/lib64" >> /etc/ld.so.conf.d/nvidia.conf

ENV PATH=/usr/local/cuda/bin:${PATH}
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64


ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

ARG ROS_DISTRO=jazzy
ARG USERNAME=ros
ARG USER_UID=1000
ARG USER_GID=$USER_UID

ENV SHELL /bin/bash
ENV DEBIAN_FRONTEND=noninteractive

RUN userdel $(getent passwd 1000 | cut -d: -f1)
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && apt-get update \
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
    libg2o-dev \
    libpcl-dev \
    python3-opencv \
    ros-$ROS_DISTRO-cv-bridge \
    ros-$ROS_DISTRO-image-tools \
    ros-$ROS_DISTRO-message-filters \
    ros-$ROS_DISTRO-rmw-cyclonedds-cpp \
    ros-$ROS_DISTRO-xacro \
    ros-$ROS_DISTRO-ros2-control-cmake \
    ros-$ROS_DISTRO-ros2-control \
    ros-$ROS_DISTRO-robot-localization \
    ros-$ROS_DISTRO-ros2-controllers \
    ros-$ROS_DISTRO-libg2o \
    ros-$ROS_DISTRO-slam-toolbox \
    ros-$ROS_DISTRO-navigation2 \
    ros-$ROS_DISTRO-nav2-bringup \
    ros-$ROS_DISTRO-nav2-rviz-plugins \
    ros-$ROS_DISTRO-sdformat-urdf \
    ros-$ROS_DISTRO-pcl-ros \
    ros-$ROS_DISTRO-tf-transformations && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install numpy  --break-system-packages

ENV OptiX_INSTALL_DIR=/optix
ENV NVIDIA_DRIVER_CAPABILITIES=all
ENV GZ_VERSION=harmonic
RUN . /opt/ros/${ROS_DISTRO}/setup.sh && \
    mkdir -p /ros2_deps_ws/src && \
    cd /ros2_deps_ws/src && \
    git clone https://github.com/gazebosim/ros_gz.git -b ros2 && \
    git clone --branch $ROS_DISTRO https://github.com/ros-controls/gz_ros2_control && \
    git clone https://github.com/dfki-ric/pclomp.git && \
    cd /ros2_deps_ws && \
    apt update && rosdep update && \
    rosdep install -r --from-paths src -i -y --rosdistro $ROS_DISTRO && \
    colcon build
ENV DEBIAN_FRONTEND=dialog

ARG WORKSPACE
RUN echo "if [ -f /opt/ros/${ROS_DISTRO}/setup.bash ]; then source /opt/ros/${ROS_DISTRO}/setup.bash; fi" >> /home/$USERNAME/.bashrc \
    && echo "if [ -f /usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash ]; then source /usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash; fi" >> /home/$USERNAME/.bashrc \
    && echo "if [ -f ${WORKSPACE}/install/setup.bash ]; then source ${WORKSPACE}/install/setup.bash; fi" >> //home/$USERNAME/.bashrc \
    && echo "if [ -f /ros2_deps_ws/install/setup.bash ]; then source /ros2_deps_ws/install/setup.bash; fi" >> //home/$USERNAME/.bashrc
