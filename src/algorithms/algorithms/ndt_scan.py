import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import TransformStamped
import numpy as np
import tf2_ros
from tf_transformations import quaternion_from_euler


class NDTScanMatcher(Node):
    def __init__(self):
        super().__init__("ndt_scan_matcher")
        self.subscription = self.create_subscription(
            LaserScan, "/scan", self.scan_callback, 10
        )
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)
        self.previous_cloud = None

        self.voxel_size = 0.5
        self.grid_cells = {}

        self.max_iterations = 30
        self.epsilon = 1e-6

        self.get_logger().info("NDT Scan Matcher initialized")

    def scan_callback(self, msg):
        self.get_logger().info("Received scan")
        current_cloud = self.laser_scan_to_point_cloud(msg)

        if self.previous_cloud is None:
            self.previous_cloud = current_cloud
            self.initialize_ndt_grid(current_cloud)
            return

        transformation, converged = self.ndt_registration(
            self.previous_cloud, current_cloud
        )

        if converged:
            self.publish_transform(transformation)
            self.previous_cloud = current_cloud
            self.initialize_ndt_grid(current_cloud)
        else:
            self.get_logger().warn("NDT registration did not converge")

    def laser_scan_to_point_cloud(self, scan_msg):
        angles = np.linspace(
            scan_msg.angle_min, scan_msg.angle_max, len(scan_msg.ranges)
        )
        ranges = np.array(scan_msg.ranges)
        valid_indices = (
            np.isfinite(ranges)
            & (ranges > scan_msg.range_min)
            & (ranges < scan_msg.range_max)
        )
        points = np.zeros((np.count_nonzero(valid_indices), 2))
        points[:, 0] = ranges[valid_indices] * np.cos(angles[valid_indices])
        points[:, 1] = ranges[valid_indices] * np.sin(angles[valid_indices])
        return points

    def initialize_ndt_grid(self, points):
        self.grid_cells = {}
        for point in points:
            cell_idx = (
                int(point[0] / self.voxel_size),
                int(point[1] / self.voxel_size),
            )
            if cell_idx not in self.grid_cells:
                self.grid_cells[cell_idx] = []
            self.grid_cells[cell_idx].append(point)

        for cell_idx in list(self.grid_cells.keys()):
            cell_points = np.array(self.grid_cells[cell_idx])
            if len(cell_points) < 3:
                del self.grid_cells[cell_idx]
                continue

            mean = np.mean(cell_points, axis=0)
            cov = np.cov(cell_points, rowvar=False)
            cov += np.eye(2) * 1e-3

            try:
                inv_cov = np.linalg.inv(cov)
                det_cov = np.linalg.det(cov)

                if det_cov > 0:
                    self.grid_cells[cell_idx] = {
                        "mean": mean,
                        "cov": cov,
                        "inv_cov": inv_cov,
                        "det_cov": det_cov,
                    }
                else:
                    del self.grid_cells[cell_idx]
            except np.linalg.LinAlgError:
                del self.grid_cells[cell_idx]

    def ndt_registration(self, target, source, max_iterations=None, epsilon=None):
        if max_iterations is None:
            max_iterations = self.max_iterations
        if epsilon is None:
            epsilon = self.epsilon

        x, y, theta = 0.0, 0.0, 0.0
        converged = False

        for _ in range(max_iterations):
            transformation = np.array(
                [
                    [np.cos(theta), -np.sin(theta), x],
                    [np.sin(theta), np.cos(theta), y],
                    [0, 0, 1],
                ]
            )

            transformed_source = self.apply_transformation(source, transformation)

            score, gradient, hessian = self.compute_ndt_score_and_derivatives(
                transformed_source
            )

            if np.linalg.norm(gradient) < epsilon:
                converged = True

            try:
                delta = np.linalg.solve(hessian, -gradient)
                x += delta[0]
                y += delta[1]
                theta += delta[2]
            except np.linalg.LinAlgError:
                self.get_logger().warn("Hessian is singular, using gradient descent")
                step_size = 0.1
                delta = -step_size * gradient
                x += delta[0]
                y += delta[1]
                theta += delta[2]

        transformation = np.array(
            [
                [np.cos(theta), -np.sin(theta), x],
                [np.sin(theta), np.cos(theta), y],
                [0, 0, 1],
            ]
        )

        return transformation, converged

    def compute_ndt_score_and_derivatives(self, points):
        score = 0.0
        gradient = np.zeros(3)
        hessian = np.zeros((3, 3))

        for point in points:
            cell_idx = (
                int(point[0] / self.voxel_size),
                int(point[1] / self.voxel_size),
            )
            if cell_idx not in self.grid_cells:
                continue

            cell = self.grid_cells[cell_idx]
            diff = point - cell["mean"]
            exponent = -0.5 * diff.dot(cell["inv_cov"]).dot(diff)
            point_score = np.exp(exponent)
            score += point_score

            if point_score > 1e-6:
                grad_point = point_score * cell["inv_cov"].dot(diff)
                gradient[0] += grad_point[0]
                gradient[1] += grad_point[1]
                p_rot = np.array([-point[1], point[0]])
                gradient[2] += grad_point.dot(p_rot)

                H_point = point_score * (
                    cell["inv_cov"] - np.outer(grad_point, grad_point) / point_score
                )

                hessian[:2, :2] += H_point
                hessian[0, 2] += H_point[0, 0] * p_rot[0] + H_point[0, 1] * p_rot[1]
                hessian[1, 2] += H_point[1, 0] * p_rot[0] + H_point[1, 1] * p_rot[1]
                hessian[2, 2] += p_rot.dot(H_point).dot(p_rot)

        hessian[2, 0] = hessian[0, 2]
        hessian[2, 1] = hessian[1, 2]

        hessian += np.eye(3) * 1e-3

        return score, gradient, hessian

    def apply_transformation(self, points, transformation):
        """Zastosowanie transformacji do punktów"""
        homogeneous = np.ones((points.shape[0], 3))
        homogeneous[:, :2] = points
        transformed = homogeneous @ transformation.T
        return transformed[:, :2]

    def publish_transform(self, transformation):
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = "map_scan"
        t.child_frame_id = "odom"

        x = transformation[0, 2]
        y = transformation[1, 2]

        theta = np.arctan2(transformation[1, 0], transformation[0, 0])

        q = quaternion_from_euler(0, 0, theta)

        t.transform.translation.x = x
        t.transform.translation.y = y
        t.transform.translation.z = 0.0

        t.transform.rotation.x = q[0]
        t.transform.rotation.y = q[1]
        t.transform.rotation.z = q[2]
        t.transform.rotation.w = q[3]

        self.tf_broadcaster.sendTransform(t)


def main(args=None):
    rclpy.init(args=args)
    node = NDTScanMatcher()
    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == "__main__":
    main()
