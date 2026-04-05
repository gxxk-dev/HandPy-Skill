# LVGL GUI lv_gui（v3 专属）

`lv_gui.py` 预置于 v3 用户文件系统，封装了 LVGL 的页面路由和资源加载。

```python
from lv_gui import LV_GUI

gui = LV_GUI()
gui.load_assets()                    # 加载图片资源
img_src = gui.get_img_src("Smile")  # 获取图片路径
gui.change_route("main")            # 切换页面
gui.set_key_config({                 # 配置按键
    "A": lambda: print("A pressed"),
    "B": lambda: print("B pressed"),
})
```

底层直接使用 LVGL：

```python
import lvgl as lv
from lv_utils import event_loop

el = event_loop()
scr = lv.scr_act()
img = lv.img(scr)
img.set_src("/images/Color/Expression-happy.png")
img.align(lv.ALIGN.CENTER, 0, 0)
```

官方文档：https://mpython-esp32s3-doc.readthedocs.io/zh-cn/latest/
