"""
ComfyUI 镜语马分镜节点 - 入口文件
"""

from .jingyuma_node import (
    JingyumaStoryboardNode,
    JingyumaSplitShotsNode,
    JingyumaRefreshShotNode,
)

NODE_CLASS_MAPPINGS = {
    "JingyumaStoryboard": JingyumaStoryboardNode,
    "JingyumaSplitShots": JingyumaSplitShotsNode,
    "JingyumaRefreshShot": JingyumaRefreshShotNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "JingyumaStoryboard": "镜语马 · 生成分镜",
    "JingyumaSplitShots": "镜语马 · 拆分镜头",
    "JingyumaRefreshShot": "镜语马 · 刷新单镜头",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]