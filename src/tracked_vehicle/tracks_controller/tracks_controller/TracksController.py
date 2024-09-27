import rclpy.publisher
from tracked_vehicle_interfaces.srv import ChainedTracksCommand
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64

class TracksController(Node):
    def __init__(self):
        super().__init__('')
        self.front_track_control_publishers = [
            self.create_publisher(Float64, 'front_right_flipper_cmd', 10),
            self.create_publisher(Float64, 'front_left_flipper_cmd', 10)
        ]
        self.rear_track_control_publishers = [
            self.create_publisher(Float64, 'rear_right_flipper_cmd', 10),
            self.create_publisher(Float64, 'rear_left_flipper_cmd', 10)
        ]

        self.front_tracks_control_service = self.create_service(
            ChainedTracksCommand,
            'front_tracks_controller',
            lambda request, response:
                self.tracks_control_callback(request, response, self.front_track_control_publishers))
        self.rear_tracks_control_service = self.create_service(
            ChainedTracksCommand,
            'rear_tracks_controller',
            lambda request, response:
                self.tracks_control_callback(request, response, self.front_track_control_publishers))

    def tracks_control_callback(
            self,
            request: ChainedTracksCommand.Request,
            response: ChainedTracksCommand.Response,
            publishers: list[rclpy.publisher.Publisher]):
        data: Float64 = request.data
        for publisher in publishers:
            publisher.publish(data)

        response.result = True
        return response


def main():
    rclpy.init()
    service = TracksController()
    rclpy.spin(service)
    rclpy.shutdown()

if __name__ == '__main__':
    main()