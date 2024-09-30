from tracked_vehicle_interfaces.srv import ChainedTracksCommand
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64

class TracksController(Node):
    def __init__(self):
        super().__init__('')
        self.front_tracks_control_service = \
            self.create_service(ChainedTracksCommand, 'front_tracks_controller', self.front_tracks_control_callback)
        self.front_right_track_control_publisher = self.create_publisher(Float64, 'front_right_flipper_cmd', 10)
        self.front_left_track_control_publisher = self.create_publisher(Float64, 'front_left_flipper_cmd', 10)


    def front_tracks_control_callback(self, request: ChainedTracksCommand.Request, response: ChainedTracksCommand.Response):
        data: Float64 = request.data
        self.front_right_track_control_publisher.publish(data)
        self.front_left_track_control_publisher.publish(data)

        response.result = True
        return response


def main():
    rclpy.init()
    service = TracksController()
    rclpy.spin(service)
    rclpy.shutdown()

if __name__ == '__main__':
    main()