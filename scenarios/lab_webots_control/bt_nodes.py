"""
Lab Webots Control Scenario - BT Nodes
목표: 
1. 초기 위치 저장 (odom 토픽 사용)
2. 목표 위치로 이동 (/bt/goal_pose 토픽)
3. 사진 촬영 (서비스 호출)
4. 초기 위치로 복귀
"""

from modules.base_bt_nodes import BTNodeList, Status, Node, Sequence, Fallback, ReactiveSequence, ReactiveFallback
from modules.base_bt_nodes_ros import ConditionWithROSTopics, ActionWithROSAction, ActionWithROSService

from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from nav2_msgs.action import NavigateToPose
from std_srvs.srv import Trigger
from action_msgs.msg import GoalStatus

import subprocess
import os
import sys
import time


# BT Node List
CUSTOM_ACTION_NODES = [
    'SaveInitialPosition',
    'MoveToGoal',
    'CaptureImage',
    'ReturnToInitial'
]

CUSTOM_CONDITION_NODES = []

BTNodeList.ACTION_NODES.extend(CUSTOM_ACTION_NODES)
BTNodeList.CONDITION_NODES.extend(CUSTOM_CONDITION_NODES)


# 이미지 서비스 서버 자동 시작
_image_service_process = None

def start_image_service_server():
    """이미지 서비스 서버를 백그라운드에서 시작"""
    global _image_service_process
    
    if _image_service_process is not None:
        return
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    server_script = os.path.join(script_dir, "image_service_server.py")
    
    if not os.path.exists(server_script):
        return
    
    try:
        _image_service_process = subprocess.Popen(
            [sys.executable, server_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=script_dir
        )
        time.sleep(2)
    except Exception as e:
        print(f"[ERROR] Image Service Server 시작 실패: {e}")

# 모듈 로드 시 서비스 서버 시작
start_image_service_server()


class SaveInitialPosition(ConditionWithROSTopics):
    """
    /odom 토픽에서 현재 위치를 받아 초기 위치로 blackboard에 저장
    """
    def __init__(self, name, agent):
        super().__init__(name, agent, [
            (Odometry, "/odom", 'odom'),
        ])
        self.saved = False

    def _predicate(self, agent, blackboard):
        if self.saved:
            return True
        
        if "odom" not in self._cache:
            return False
        
        odom = self._cache["odom"]
        
        initial_pose = PoseStamped()
        initial_pose.header.frame_id = 'map'
        initial_pose.header.stamp = self.ros.node.get_clock().now().to_msg()
        initial_pose.pose = odom.pose.pose
        
        blackboard["initial_position"] = initial_pose
        self.saved = True
        
        print("[상태] 초기 위치 저장 완료")
        return True


class MoveToGoal(ActionWithROSAction):
    """
    /bt/goal_pose 토픽에서 목표 위치를 받아 이동
    """
    def __init__(self, name, agent):
        ns = agent.ros_namespace or ""
        super().__init__(name, agent, (NavigateToPose, f"{ns}/navigate_to_pose"))
        
        goal_topic = "/bt/goal_pose"
        self.goal_pose = None
        self.current_goal = None
        self.waiting_logged = False
        self.ros.node.create_subscription(
            PoseStamped,
            goal_topic,
            self._goal_pose_callback,
            10
        )

    def _goal_pose_callback(self, msg):
        if self.current_goal is None:
            self.goal_pose = msg
            self.waiting_logged = False
            print(f"[상태] 새로운 목표 수신")

    def _build_goal(self, agent, blackboard):
        if self.goal_pose is None:
            if not self.waiting_logged:
                print("[상태] 목표 위치 대기 중...")
                self.waiting_logged = True
            return None
        
        self.current_goal = self.goal_pose
        
        goal = NavigateToPose.Goal()
        goal.pose = self.goal_pose
        
        blackboard["goal_pose"] = self.goal_pose
        blackboard["mission_cycle_id"] = blackboard.get("mission_cycle_id", 0) + 1
        
        print("[상태] 목표 위치로 이동 중...")
        return goal

    def _interpret_result(self, result, agent, blackboard, status_code=None):
        if status_code == GoalStatus.STATUS_SUCCEEDED:
            blackboard['nav_result'] = 'succeeded'
            print("[상태] 목표 위치 도착 완료")
            self.goal_pose = None
            self.current_goal = None
            self.waiting_logged = False
            return Status.SUCCESS
        elif status_code == GoalStatus.STATUS_CANCELED:
            blackboard['nav_result'] = 'canceled'
            self.current_goal = None
            self.waiting_logged = False
            return Status.FAILURE
        else:
            blackboard['nav_result'] = 'aborted'
            self.current_goal = None
            self.waiting_logged = False
            return Status.FAILURE
    
    def halt(self):
        super().halt()
        self.current_goal = None


class CaptureImage(ActionWithROSService):
    """
    /capture_image 서비스를 호출하여 사진 촬영
    """
    def __init__(self, name, agent):
        super().__init__(name, agent, (Trigger, '/capture_image'))
        self.waiting_logged = False
        self.save_client = agent.ros_bridge.node.create_client(Trigger, '/save_images')

    async def run(self, agent, blackboard):
        if not self.client.wait_for_service(timeout_sec=0.0):
            if not self.waiting_logged:
                self.waiting_logged = True
            self.status = Status.RUNNING
            return self.status
        
        if self.waiting_logged:
            self.waiting_logged = False
        
        return await super().run(agent, blackboard)

    def _build_request(self, agent, blackboard):
        print("[상태] 이미지 캡처 중...")
        return Trigger.Request()

    def _interpret_response(self, response, agent, blackboard):
        blackboard['image_captured'] = response.success
        blackboard['capture_message'] = response.message
        
        if response.success:
            print("[상태] 이미지 캡처 완료")
            self._save_image_to_file()
            return Status.SUCCESS
        else:
            return Status.FAILURE
    
    def _save_image_to_file(self):
        if not self.save_client.wait_for_service(timeout_sec=0.0):
            return
        
        request = Trigger.Request()
        future = self.save_client.call_async(request)



class ReturnToInitial(ActionWithROSAction):
    """
    초기 위치로 복귀
    """
    def __init__(self, name, agent):
        ns = agent.ros_namespace or ""
        super().__init__(name, agent, (NavigateToPose, f"{ns}/navigate_to_pose"))
        self.returning = False

    def _build_goal(self, agent, blackboard):
        initial_position = blackboard.get("initial_position")
        if initial_position is None:
            return None
        
        goal = NavigateToPose.Goal()
        goal.pose = PoseStamped()
        goal.pose.header.frame_id = 'map'
        goal.pose.header.stamp = self.ros.node.get_clock().now().to_msg()
        goal.pose.pose = initial_position.pose
        
        self.returning = True
        print("[상태] 초기 위치로 복귀 중...")
        return goal

    def _interpret_result(self, result, agent, blackboard, status_code=None):
        self.returning = False
        if status_code == GoalStatus.STATUS_SUCCEEDED:
            blackboard['return_result'] = 'succeeded'
            print("[상태] 초기 위치 복귀 완료\n")
            return Status.FAILURE
        elif status_code == GoalStatus.STATUS_CANCELED:
            blackboard['return_result'] = 'canceled'
            return Status.FAILURE
        else:
            blackboard['return_result'] = 'aborted'
            return Status.FAILURE
    
    def halt(self):
        super().halt()
        self.returning = False


# 종료 시 이미지 서비스 서버 정리
import atexit

def cleanup_image_service_server():
    global _image_service_process
    
    if _image_service_process is not None:
        _image_service_process.terminate()
        try:
            _image_service_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _image_service_process.kill()
        _image_service_process = None

atexit.register(cleanup_image_service_server)
