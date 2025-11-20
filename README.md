# webots_hw

ROS 2와 Behaviour Tree를 활용한 로봇 제어 시스템


## Webots + Nav2 시나리오 (Lab Webots Control)

이 시나리오는 Webots 시뮬레이터와 Nav2를 사용하여 TurtleBot3를 자율 주행시키고, 목표 지점에서 카메라 이미지를 캡처하는 기능을 제공합니다.

### 1. Webots 시뮬레이션 환경 실행

Webots 워크스페이스에서 다음 명령어를 실행하여 시뮬레이션 환경과 Nav2를 시작합니다:

```bash
cd webots_hw/
source install/local_setup.bash
ros2 launch webots_ros2_turtlebot robot_launch.py nav:=true
```

이 명령어는 다음을 실행합니다:
- Webots 시뮬레이터 (TurtleBot3 환경)
- TurtleBot3 카메라 활성화
- Nav2 네비게이션 스택
- RViz2 시각화 도구


만약 Webots 시뮬레이터에서 카메라 창이 나왔지만 카메라 화면이 안뜬다면

```bash
ros2 topic echo /TurtleBot3Burger/front_camera/image_color
```

### 2. RViz2에서 2D Goal Pose 설정

RViz2에서 목표 위치 설정을 위한 도구를 구성합니다:

1. RViz2 상단 툴바에서 **"2D Goal Pose"** 도구를 선택
2. 왼쪽 패널의 **Tool Properties**에서 발행 토픽 이름을 `/bt/goal_pose`로 설정

### 3. Behaviour Tree 컨트롤러 실행

`webots_hw` 디렉토리에서 다음 명령어를 실행합니다:

```bash
python3 main.py
```
- 이후 RViz2에서 **"2D Goal Pose"** 도구를 통해서 목표 위치를 전달

### 동작 흐름

Behaviour Tree는 다음 순서로 작동합니다:

1. **초기 위치 저장** (`SaveInitialPosition`): 현재 로봇의 위치를 `/odom` 토픽에서 읽어 저장
2. **목표 위치로 이동** (`MoveToGoal`): `/bt/goal_pose` 토픽에서 수신한 목표 위치로 Nav2를 통해 이동
3. **이미지 캡처** (`CaptureImage`): 목표 지점 도착 후 카메라로 이미지 캡처
4. **초기 위치로 복귀** (`ReturnToInitial`): 저장된 초기 위치로 자동 복귀

### 캡처된 이미지 저장 위치

캡처된 이미지는 다음 경로에 저장됩니다:

```
~/webots_hw/scenarios/lab_webots_control/captured_images/
```

파일명 형식: `captured_YYYYMMDD_HHMMSS.jpg` (예: `captured_20251119_143052.jpg`)

### 주요 토픽 및 서비스

- **구독 토픽**:
  - `/odom`: 로봇의 현재 위치 (Odometry)
  - `/bt/goal_pose`: 목표 위치 (PoseStamped)
  - `/TurtleBot3Burger/front_camera/image_color`: 카메라 이미지

- **액션 클라이언트**:
  - `/navigate_to_pose`: Nav2 네비게이션 액션

- **서비스**:
  - `/capture_image`: 이미지 캡처 요청
  - `/save_images`: 캡처된 이미지 파일 저장



