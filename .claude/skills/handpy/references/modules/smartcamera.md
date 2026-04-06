# AI 摄像头 smartcamera

`smartcamera_k230.py`（K230）和 `smartcamera_new.py`（K210）预置于导出的板载用户文件系统，通过 UART 与外接 AI 摄像头模块通信。这里已经合并了常用模式类和结果字段，不需要再依赖外部网页说明。

两套封装都会在构造时自动初始化并启动后台监听，不需要额外手动开线程。

## K230

```python
from smartcamera_k230 import SmartCameraK230
from mpython import Pin

cam = SmartCameraK230(tx=Pin.P1, rx=Pin.P0)
cam.wait_for_ai_init()   # 等待 AI 模块初始化完成
```

默认构造就是 `SmartCameraK230(tx=Pin.P1, rx=Pin.P0)`。

常见入口：

| 方法 | 说明 |
|------|------|
| `switcher_mode(mode)` | 切换到内置模式 |
| `color_obj_count_init(cur_mode)` | 颜色计数 |
| `lab_color_count_init(color)` | LAB 颜色计数 |
| `classify_kmodel_init(param)` | 自定义分类模型 |
| `detect_kmodel_init(param)` | 自定义检测模型 |

K230 常见能力包括：

- `YOLO80`
- `FACE_DETECT`
- `LPR`
- `HandDetect`
- `HandKeypointClass`
- `DG`
- `PersonDetect`
- `PersonKeypointDetct`
- `PersonKeypointDetctPlus`
- `FaceExpressionDetct`
- `FaceLivingBodyDetct`
- `QRCodeRecognization`
- `BarCodeRecognization`
- `FallDetection`
- `FaceRecogization`
- `ColorCount`
- `LABColorCount`
- `ClassifyMODEL`
- `DetectMODEL`

典型结果字段：

| 字段 | 类型 | 范围/约束 | 说明 |
|------|------|-----------|------|
| `cam.yolo_detect.category_name` | `str` | 依模型标签集而定 | 当前识别类别名 |
| `cam.yolo_detect.max_score` | `number` | 待确认 | 当前最高置信度分数 |
| `cam.yolo_detect.objnum` | `int` | `>= 0` | 当前检测到的目标数量 |
| `cam.face_detect.face_num` | `int` | `>= 0` | 当前检测到的人脸数量 |

## K210

```python
from smartcamera_new import SmartCamera
from mpython import Pin

cam = SmartCamera(rx=Pin.P15, tx=Pin.P16)
cam.wait_for_ai_init()
```

默认构造是 `SmartCamera(rx=Pin.P15, tx=Pin.P16)`，不是 `P1/P0`。

常见初始化方法：

| 方法 | 说明 |
|------|------|
| `mnist_init(choice)` | 手写数字识别 |
| `yolo_detect_init(choice)` | 20 类物体识别 |
| `face_detect_init(choice)` | 人脸检测 |
| `face_recognize_init(face_num, accuracy, choice)` | 人脸识别 |
| `asr_init()` | K210 语音识别 |
| `self_learning_classifier_init(class_num, sample_num, threshold, choice)` | 自学习分类 |
| `qrcode_init(choice)` | 二维码识别 |
| `color_init(choice)` | 颜色识别 |
| `guidepost_init(choice)` | 路标识别 |
| `kmodel_init(choice, komodel_path, width, height)` | 自定义模型 |
| `kmodel_yolo_init(choice, komodel_path, width, height, anchors)` | 自定义 YOLO 模型 |
| `track_init(choice)` / `track_set_up(threshold, area_threshold)` | 颜色块跟踪 |
| `color_statistics_init(choice)` | 颜色统计/线性回归 |
| `color_extracto_init(choice)` | 颜色提取 |
| `apriltag_init(choice)` | AprilTag |
| `video_capture(...)` | 录像 |
| `canvas_init()` / `canvas_clear()` / `canvas_txt()` | 画布操作 |
| `rgb(r, g, b)` / `led(mode)` | 控制摄像头侧灯效 |

最小示例：

```python
from smartcamera_new import SmartCamera
import time

cam = SmartCamera()
cam.yolo_detect_init(1)

while True:
    cam.yolo_detect.recognize()
    print(cam.yolo_detect.id, cam.yolo_detect.max_score, cam.yolo_detect.objnum)
    time.sleep_ms(200)
```

K210 语音识别示例：

```python
cam = SmartCamera()
cam.asr_init()
cam.asr.addKeyword('kai deng', 0)
cam.asr.addKeyword('guan deng', 1)
cam.asr.start()

while True:
    cam.asr.recognize()
```

常见结果字段：

| 字段 | 类型 | 范围/约束 | 说明 |
|------|------|-----------|------|
| `cam.yolo_detect.id` | `int` | 依当前模型标签 ID 而定 | 当前识别到的类别 ID |
| `cam.yolo_detect.max_score` | `number` | 待确认 | 当前最高置信度分数 |
| `cam.yolo_detect.objnum` | `int` | `>= 0` | 当前检测到的目标数量 |
| `cam.face_detect.face_num` | `int` | `>= 0` | 当前检测到的人脸数量 |
| `cam.fcr.id` | `int` | 依已录入人脸库而定 | 当前识别到的人脸 ID |
| `cam.fcr.max_score` | `number` | 待确认 | 当前人脸识别匹配分数 |
| `cam.qrcode.info` | `str` | 非空时表示识别到内容 | 当前二维码内容 |
| `cam.track.x` | `number` | 依画面分辨率而定 | 跟踪目标的 X 坐标 |
| `cam.track.y` | `number` | 依画面分辨率而定 | 跟踪目标的 Y 坐标 |
| `cam.track.cx` | `number` | 依画面分辨率而定 | 跟踪目标中心点 X 坐标 |
| `cam.track.cy` | `number` | 依画面分辨率而定 | 跟踪目标中心点 Y 坐标 |

> 两者均需外接对应的 AI 摄像头硬件模块，通过 UART 串口通信。
> 上表只整理高频结果字段的使用级类型与已确认约束；如果任务要用更冷门模式，不要臆测接口。
