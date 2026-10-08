"""
ComfyUI Jingyuma Storyboard Nodes - entry file
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
    "JingyumaStoryboard": "Jingyuma Storyboard",
    "JingyumaSplitShots": "Jingyuma Split Shots",
    "JingyumaRefreshShot": "Jingyuma Refresh Shot",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
