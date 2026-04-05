# 预置图片资源

## v2（.pbm 格式，OLED 显示）

图片位于 `face/` 和 `dog/` 目录，`.pbm` 格式，可直接用 `oled.bitmap` 显示。

```python
# 读取 .pbm 文件并显示
with open('/face/Smile.pbm', 'rb') as f:
    f.read(2)           # 跳过 P4 header
    w, h = 16, 16       # 根据实际尺寸
    data = f.read()

oled.bitmap(56, 24, data, w, h, 1)
oled.show()
```

目录结构：
- `face/Expressions/`（13张表情）
- `face/Eyes/`（26张眼睛）
- `face/Information/`（13张信息图标）
- `face/Objects/`（12张物体）
- `face/Progress/`（20张进度指示）
- `dog/`（4帧动画）

## v3（PNG 格式，LVGL 显示）

图片位于 `images/` 目录，PNG 格式，通过 LVGL `lv.img` 显示。

```python
import lvgl as lv

img = lv.img(lv.scr_act())
img.set_src("/images/Color/Expression-happy.png")
img.align(lv.ALIGN.CENTER, 0, 0)
```

目录结构：
- `images/B&W/`（54张黑白图，对应 v2 face/ 内容）
- `images/Color/`（56张彩色图，含表情/眼睛/箭头/物体等）
- `images/magnetic/`（2张磁力计校准图）
