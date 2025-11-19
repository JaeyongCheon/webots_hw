#!/usr/bin/env python3
"""
Publish Goal Pose Utility
Rviz를 사용하지 않고 터미널에서 직접 목표 위치를 발행하는 유틸리티
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
import argparse


class GoalPosePublisher(Node):
    def __init__(self, x, y, z=0.0, yaw=0.0):
        super().__init__('goal_pose_publisher')
        
        self.publisher = self.create_publisher(PoseStamped, '/bt/goal_pose', 10)
        
        # PoseStamped 메시지 생성
        msg = PoseStamped()
        msg.header.frame_id = 'map'
        msg.header.stamp = self.get_clock().now().to_msg()
        
        msg.pose.position.x = x
        msg.pose.position.y = y
        msg.pose.position.z = z
        
        # Yaw를 quaternion으로 변환
        import math
        msg.pose.orientation.z = math.sin(yaw / 2.0)
        msg.pose.orientation.w = math.cos(yaw / 2.0)
        
        # 발행
        self.get_logger().info(f"목표 위치 발행: x={x}, y={y}, z={z}, yaw={yaw}")
        self.publisher.publish(msg)
        
        # 잠시 대기 후 종료
        import time
        time.sleep(0.5)


def main(args=None):
    parser = argparse.ArgumentParser(description='목표 위치를 /bt/goal_pose 토픽으로 발행')
    parser.add_argument('--x', type=float, required=True, help='X 좌표')
    parser.add_argument('--y', type=float, required=True, help='Y 좌표')
    parser.add_argument('--z', type=float, default=0.0, help='Z 좌표 (기본값: 0.0)')
    parser.add_argument('--yaw', type=float, default=0.0, help='Yaw 각도 (라디안, 기본값: 0.0)')
    
    parsed_args = parser.parse_args()
    
    rclpy.init(args=args)
    node = GoalPosePublisher(parsed_args.x, parsed_args.y, parsed_args.z, parsed_args.yaw)
    rclpy.shutdown()


if __name__ == '__main__':
    main()
