import rclpy
from cv_bridge import CvBridge
import cv2
from rclpy.node import Node
import numpy as np
from sensor_msgs.msg import CameraInfo, Image
from rclpy.qos_overriding_options import QoSOverridingOptions
from rclpy.qos import qos_profile_sensor_data
from message_filters import ApproximateTimeSynchronizer, Subscriber

class CamerasNode(Node):
    def __init__(self):
        super().__init__("CamerasNode")
        self.cv_bridge = CvBridge()
        self.initialize_sync_subscribers()
        self.depth_image_pub = self.create_publisher(Image, "stereo_depth_image", 1)
        self.left_camera_info_sub = self.create_subscription(
            CameraInfo, '/left_camera/camera_info', self.store_left_camera_info, 10)
        self.right_camera_info_sub = self.create_subscription(
            CameraInfo, '/right_camera/camera_info', self.store_right_camera_info, 10)
        self.cam = self.create_subscription(
            Image, '/left_camera/image_raw', self.img_callback, 10)
        self.left_camera_info: CameraInfo = None
        self.right_camera_info: CameraInfo = None

    def img_callback(self, img):
        pass

    def store_left_camera_info(self, camera_info_msg: CameraInfo):
        self.left_camera_info = camera_info_msg

    def store_right_camera_info(self, camera_info_msg: CameraInfo):
        self.right_camera_info = camera_info_msg

    def initialize_sync_subscribers(self):
        sync_topics = [
            Subscriber(
                self,
                Image,
                "/left_camera/image_raw",
                qos_profile=qos_profile_sensor_data,
                qos_overriding_options=QoSOverridingOptions.with_default_policies(),
            ),
            Subscriber(
                self,
                Image,
                "/right_camera/image_raw",
                qos_profile=qos_profile_sensor_data,
                qos_overriding_options=QoSOverridingOptions.with_default_policies(),
            ),
        ]

        self.image_approx_time_sync = ApproximateTimeSynchronizer(
            sync_topics,
            queue_size=15,
            slop=0.1,
        )
        self.image_approx_time_sync.registerCallback(self.on_image_data)


    def on_image_data(self, left_image: Image, right_image: Image) -> None:
        if self.right_camera_info is None or self.left_camera_info is None:
            return

        left_image = cv2.cvtColor(self.cv_bridge.imgmsg_to_cv2(left_image), cv2.COLOR_BGR2GRAY)
        right_image = cv2.cvtColor(self.cv_bridge.imgmsg_to_cv2(right_image), cv2.COLOR_BGR2GRAY)

        disparity = self.calculate_disparity(left_image, right_image)

        k_left, _, t_left = self.decompose_projection_matrix(self.left_camera_info.p)

        depth_image = self.calc_depth_map(disparity, k_left, t_left, np.array([0.3, 0, 0]))
        ros_img = self.cv_bridge.cv2_to_imgmsg(disparity)


        self.get_logger().info("XXX")
        self.depth_image_pub.publish(ros_img)


    def calculate_disparity(self, left_image, right_image):
        sad_window = 6
        num_disparities = sad_window*16
        block_size = 11

        matcher = cv2.StereoSGBM_create(numDisparities=num_disparities,
                                        minDisparity=0,
                                        blockSize=block_size,
                                        P1 = 8 * 1 * block_size ** 2,
                                        P2 = 32 * 1 * block_size ** 2,
                                        mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY)

        disparity_left = matcher.compute(left_image, right_image).astype(np.float32)

        return disparity_left


    def decompose_projection_matrix(self, projection_matrix):
        k, r, t, _, _, _, _ = cv2.decomposeProjectionMatrix(np.array(projection_matrix, dtype=np.float64).reshape(3, 4))
        t = (t / t[3])[:3]
        return k, r, t


    def calc_depth_map(self, disparity_left, k_left, t_left, t_right, rectified=True):
        f = k_left[0][0]

        if rectified:
            b = t_right[0] - t_left[0]
        else:
            b = t_left[0] - t_right[0]

        disparity_left[disparity_left == 0.0] = 0.1
        disparity_left[disparity_left == -1.0] = 0.1


        depth_map = np.ones(disparity_left.shape)
        depth_map = f * b / disparity_left
        return depth_map

def main(args=None):
    rclpy.init(args=args)
    cameras_node = CamerasNode()
    rclpy.spin(cameras_node)
    rclpy.shutdown()


if __name__ == "__main__":
    main()