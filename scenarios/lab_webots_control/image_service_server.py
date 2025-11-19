#!/usr/bin/env python3
"""
Image Service Server
이미지 캡처 및 저장 서비스 제공
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_srvs.srv import Trigger
from cv_bridge import CvBridge
import cv2
import os
from datetime import datetime


class ImageServiceServer(Node):
    def __init__(self, camera_topic="/TurtleBot3Burger/front_camera/image_color", save_dir="./captured_images"):
        super().__init__('image_service_server')
        
        self.camera_topic = camera_topic
        self.save_dir = save_dir
        self.bridge = CvBridge()
        self.latest_image = None
        self.saved_images = []
        self.image_counter = 0
        
        os.makedirs(self.save_dir, exist_ok=True)
        
        self.subscription = self.create_subscription(
            Image,
            self.camera_topic,
            self.image_callback,
            10
        )
        
        self.service = self.create_service(
            Trigger,
            '/capture_image',
            self.capture_image_callback
        )
        
        self.save_service = self.create_service(
            Trigger,
            '/save_images',
            self.save_images_callback
        )

    def image_callback(self, msg):
        self.latest_image = msg

    def capture_image_callback(self, request, response):
        try:
            if self.latest_image is None:
                response.success = False
                response.message = "카메라 이미지를 받지 못했습니다."
                return response
            
            cv_image = self.bridge.imgmsg_to_cv2(self.latest_image, desired_encoding='bgr8')
            self.saved_images = [cv_image]
            self.image_counter += 1
            
            response.success = True
            response.message = f"이미지 캡처 완료 (Total: {self.image_counter})"
            
        except Exception as e:
            response.success = False
            response.message = f"캡처 실패: {str(e)}"
        
        return response

    def save_images_callback(self, request, response):
        try:
            if not self.saved_images:
                response.success = False
                response.message = "저장할 이미지가 없습니다."
                return response
            
            cv_image = self.saved_images[-1]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.save_dir, f"captured_{timestamp}.jpg")
            
            cv2.imwrite(filename, cv_image)
            
            response.success = True
            response.message = f"파일 저장 완료: {filename}"
            
            self.saved_images = []
            
        except Exception as e:
            response.success = False
            response.message = f"저장 실패: {str(e)}"
        
        return response


def main(args=None):
    rclpy.init(args=args)
    
    import sys
    camera_topic = "/TurtleBot3Burger/front_camera/image_color"
    save_dir = "./captured_images"
    
    if "--camera-topic" in sys.argv:
        idx = sys.argv.index("--camera-topic")
        if idx + 1 < len(sys.argv):
            camera_topic = sys.argv[idx + 1]
    
    if "--save-dir" in sys.argv:
        idx = sys.argv.index("--save-dir")
        if idx + 1 < len(sys.argv):
            save_dir = sys.argv[idx + 1]
    
    node = ImageServiceServer(camera_topic=camera_topic, save_dir=save_dir)
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
