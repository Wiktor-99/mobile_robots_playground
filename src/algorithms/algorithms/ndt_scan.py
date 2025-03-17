import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import TransformStamped
import numpy as np
import tf2_ros

class NDTScanMatcher(Node):
    def __init__(self):
        super().__init__('ndt_scan_matcher')
        self.subscription = self.create_subscription(
            LaserScan, '/scan', self.scan_callback, 10)
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)
        self.previous_cloud = None

    def scan_callback(self, msg):
        self.get_logger().info("Store scan")
        current_cloud = self.laser_scan_to_point_cloud(msg)

        if self.previous_cloud is None:
            self.previous_cloud = current_cloud
            return

        # Perform NDT scan matching
        transformation = self.ndt_registration(self.previous_cloud, current_cloud)
        self.publish_transform(transformation)
        self.previous_cloud = current_cloud

    def laser_scan_to_point_cloud(self, scan_msg):
        angles = np.linspace(scan_msg.angle_min, scan_msg.angle_max, len(scan_msg.ranges))
        ranges = np.array(scan_msg.ranges)
        valid_indices = np.isfinite(ranges)
        points = np.zeros((np.count_nonzero(valid_indices), 2))
        points[:, 0] = ranges[valid_indices] * np.cos(angles[valid_indices])
        points[:, 1] = ranges[valid_indices] * np.sin(angles[valid_indices])
        return points

    def ndt_registration(self, target, source, max_iterations=10, epsilon=1e-3):
        transformation = np.eye(3)
        for _ in range(max_iterations):
            transformed_source = self.apply_transformation(source, transformation)
            _, hessian, gradient = self.compute_ndt_parameters(target, transformed_source)  # Remove unused variable 'errors'

            if np.linalg.norm(gradient) < epsilon:  # Ensure proper use of numpy.linalg
                break

            delta = np.linalg.solve(hessian, -gradient)  # Ensure proper use of numpy.linalg
            update_matrix = np.eye(3)
            update_matrix[:2, 2] = delta[:2]
            update_matrix[:2, :2] = self.rotation_matrix(delta[2])
            transformation = update_matrix @ transformation

        return transformation

    def apply_transformation(self, points, transformation):
        homogeneous = np.hstack((points, np.ones((points.shape[0], 1))))  # Ensure proper use of numpy.hstack
        transformed = homogeneous @ transformation.T
        return transformed[:, :2]

    def compute_ndt_parameters(self, target, source):
        errors = target - source

        covariance = np.cov(errors, rowvar=False) + np.eye(2) * 1e-6  # Ensure proper use of rowvar in numpy.cov
        inv_cov = np.linalg.inv(covariance)  # Ensure proper use of numpy.linalg

        gradient = np.sum(errors @ inv_cov, axis=0)
        hessian = np.einsum('ni,ij,nj->ij', errors, inv_cov, errors)

        return errors, hessian, gradient


    def rotation_matrix(self, theta):
        return np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])

    def publish_transform(self, transformation):
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = 'map_scan'
        t.child_frame_id = 'odom'
        t.transform.translation.x = transformation[0, 2]
        t.transform.translation.y = transformation[1, 2]
        t.transform.rotation.w = np.cos(transformation[0, 0] / 2)
        t.transform.rotation.z = np.sin(transformation[0, 0] / 2)
        self.tf_broadcaster.sendTransform(t)

def main(args=None):
    rclpy.init(args=args)
    node = NDTScanMatcher()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()