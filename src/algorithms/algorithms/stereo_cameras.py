import rclpy
from cv_bridge import CvBridge
import cv2
from rclpy.node import Node
import numpy as np
from sensor_msgs.msg import CameraInfo, Image
from rclpy.qos_overriding_options import QoSOverridingOptions
from rclpy.qos import qos_profile_sensor_data
from message_filters import ApproximateTimeSynchronizer, Subscriber
from geometry_msgs.msg import TransformStamped
import tf2_ros
from tf_transformations import quaternion_from_matrix


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
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)
        self.left_camera_info: CameraInfo = None
        self.right_camera_info: CameraInfo = None
        self.left_image = None
        self.T_tot = np.eye(4)

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

        self.depth_image = self.calc_depth_map(disparity, k_left, t_left, np.array([0.3, 0, 0]))
        self.depth_image_pub.publish(self.cv_bridge.cv2_to_imgmsg(self.depth_image, encoding="32FC1"))

        if self.left_image is not None:
            self.visual_odometry(left_image, k_left)

        self.left_image = left_image.copy()

    def extract_features(self, image, detector='sift', mask=None):
        if detector == 'sift':
            det = cv2.SIFT_create()
        elif detector == 'orb':
            det = cv2.ORB_create()

        kp, des = det.detectAndCompute(image, mask)

        return kp, des

    def match_features(self, des1, des2, matching='BF', detector='sift', sort=True, k=2):
        if matching == 'BF':
            if detector == 'sift':
                matcher = cv2.BFMatcher_create(cv2.NORM_L2, crossCheck=False)
            elif detector == 'orb':
                matcher = cv2.BFMatcher_create(cv2.NORM_HAMMING2, crossCheck=False)
            matches = matcher.knnMatch(des1, des2, k=k)
        elif matching == 'FLANN':
            FLANN_INDEX_KDTREE = 1
            index_params = dict(algorithm = FLANN_INDEX_KDTREE, trees=5)
            search_params = dict(checks=50)
            matcher = cv2.FlannBasedMatcher(index_params, search_params)
            matches = matcher.knnMatch(des1, des2, k=k)

        if sort:
            matches = sorted(matches, key = lambda x:x[0].distance)

        return matches

    def filter_matches_distance(self, matches, dist_threshold):
        filtered_match = []
        for m, n in matches:
            if m.distance <= dist_threshold*n.distance:
                filtered_match.append(m)

        return filtered_match


    def estimate_motion(self, match, kp1, kp2, k, depth, max_depth=3000):
        rmat = np.eye(3)
        tvec = np.zeros((3, 1))

        image1_points = np.float32([kp1[m.queryIdx].pt for m in match])
        image2_points = np.float32([kp2[m.trainIdx].pt for m in match])

        cx = k[0, 2]
        cy = k[1, 2]
        fx = k[0, 0]
        fy = k[1, 1]
        object_points = np.zeros((0, 3))
        delete = []

        for i, (u, v) in enumerate(image1_points):
            z = depth[int(v), int(u)]
            if z > max_depth:
                delete.append(i)
                continue

            x = z*(u-cx)/fx
            y = z*(v-cy)/fy
            object_points = np.vstack([object_points, np.array([x, y, z])])

        image1_points = np.delete(image1_points, delete, 0)
        image2_points = np.delete(image2_points, delete, 0)

        _, rvec, tvec, inliers = cv2.solvePnPRansac(object_points, image2_points, k, None)
        rmat = cv2.Rodrigues(rvec)[0]


        return rmat, tvec, image1_points, image2_points


    def visual_odometry(self, next_image, k_left, detector='sift', matching='BF', mask=None):
        filter_match_distance=0.5
        kp0, des0 = self.extract_features(self.left_image, detector, mask)
        kp1, des1 = self.extract_features(next_image, detector, mask)

        matches_unfilt = self.match_features(des0,
                                        des1,
                                        matching=matching,
                                        detector=detector,
                                        sort=True)

        matches = self.filter_matches_distance(matches_unfilt, filter_match_distance)

        R_convert = np.array([
            [0,  0, 1],
            [1,  0, 0],
            [0, -1, 0]
        ])
        rmat, tvec, img1_points, img2_points = self.estimate_motion(matches, kp0, kp1, k_left, self.depth_image)
        Tmat = np.eye(4)
        Tmat[:3, :3] = rmat
        Tmat[:3, 3] = tvec.T


        R_convert = np.array([
            [0,  0,  1],
            [-1,  0,  0],
            [0, -1,  0]
        ])

        T_convert = np.eye(4)
        T_convert[:3, :3] = R_convert

        T_ros = T_convert @ Tmat @ np.linalg.inv(T_convert)

        self.T_tot =  self.T_tot.dot(np.linalg.inv(T_ros))
        self.publish_transform(self.T_tot)


    def publish_transform(self, transformation):
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = 'odom_vis'
        t.child_frame_id = 'base_link'

        x = transformation[0, 3]
        y = transformation[1, 3]

        q = quaternion_from_matrix(transformation)

        t.transform.translation.x = x
        t.transform.translation.y = y
        t.transform.translation.z = 0.0

        t.transform.rotation.x = q[0]
        t.transform.rotation.y = q[1]
        t.transform.rotation.z = q[2]
        t.transform.rotation.w = q[3]

        self.tf_broadcaster.sendTransform(t)

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

        disparity_left = matcher.compute(left_image, right_image)

        return disparity_left.astype(np.float32) / 16


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

        return depth_map.astype(np.float32)

def main(args=None):
    rclpy.init(args=args)
    cameras_node = CamerasNode()
    rclpy.spin(cameras_node)
    rclpy.shutdown()


if __name__ == "__main__":
    main()