"""
ComfyUI 镜语马分镜节点
调用 https://shotstory.cn/api/v1/generate 将小说文本转换为分镜提示词

作者：镜语马
版本：1.0.0
"""

import json
import time
import hashlib
import requests
from typing import Tuple, List

# ==================== 常量配置 ====================
API_BASE_URL = "https://shotstory.cn"
GENERATE_ENDPOINT = "/api/v1/generate"
ROTATE_ENDPOINT = "/api/v1/rotate_variant"
TIMEOUT = 120  # 秒

# 简单的内存缓存（避免同一文本重复调用扣积分）
# 结构：{cache_key: (timestamp, result)}
_CACHE = {}
_CACHE_TTL = 600  # 10 分钟


def _make_cache_key(text: str, mode: str, mood: str, theme: str) -> str:
    """生成缓存 key"""
    raw = f"{text}|{mode}|{mood}|{theme}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _get_from_cache(key: str):
    """从缓存读取"""
    if key in _CACHE:
        ts, result = _CACHE[key]
        if time.time() - ts < _CACHE_TTL:
            return result
        else:
            del _CACHE[key]
    return None


def _save_to_cache(key: str, result):
    """写入缓存"""
    _CACHE[key] = (time.time(), result)


def _call_generate_api(api_key: str, text: str, mode: str = "basic",
                       mood: str = "", theme: str = "") -> dict:
    """
    调用镜语马 /api/v1/generate 接口
    返回解析后的 dict（含 shots 数组）
    """
    url = API_BASE_URL + GENERATE_ENDPOINT
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key,
        "User-Agent": "ComfyUI-JingyumaNode/1.0",
    }
    payload = {"text": text, "mode": mode}
    if mode == "mood" and mood:
        payload["mood"] = mood
    if mode == "theme" and theme:
        payload["theme"] = theme

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"❌ 请求镜语马 API 失败：{e}")

    # 解析 HTTP 状态码
    if resp.status_code == 401:
        raise RuntimeError("❌ API Key 无效或缺失，请在镜语马官网获取正确的 Key")
    elif resp.status_code == 402:
        raise RuntimeError("❌ 积分不足，请前往 https://shotstory.cn 充值或升级套餐")
    elif resp.status_code == 403:
        try:
            err = resp.json().get("error", "无权限")
        except Exception:
            err = "无权限"
        raise RuntimeError(f"❌ 权限拒绝：{err}")
    elif resp.status_code == 429:
        raise RuntimeError("❌ 请求过于频繁，请稍后重试")
    elif resp.status_code != 200:
        raise RuntimeError(f"❌ API 返回错误 {resp.status_code}：{resp.text[:200]}")

    # 解析业务响应
    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(f"❌ 响应不是合法 JSON：{resp.text[:200]}")

    if not data.get("success"):
        error = data.get("error", "未知错误")
        code = data.get("code", "")
        raise RuntimeError(f"❌ 镜语马 API 业务错误[{code}]：{error}")

    return data


def _format_shots(shots: List[dict]) -> Tuple[str, str, str, str]:
    """
    将 shots 数组格式化为 4 个输出字符串
    返回：(image_prompts, video_prompts, dialogues, raw_json)
    """
    image_prompts = []
    video_prompts = []
    dialogues = []
    shot_info = []

    for shot in shots:
        idx = shot.get("index", 0)
        original = shot.get("original_text", "")
        dialogue = shot.get("dialogue", "")
        duration = shot.get("duration", "")
        visual = shot.get("visual_description", "")
        is_violation = shot.get("is_violation", False)

        if is_violation:
            image_prompts.append(f"[镜头 {idx:03d}] ⚠️ 内容违规，已屏蔽")
            video_prompts.append(f"[镜头 {idx:03d}] ⚠️ 内容违规，已屏蔽")
            dialogues.append(f"[镜头 {idx:03d}] (违规)")
        else:
            image_prompts.append(f"[镜头 {idx:03d}] {visual}")
            video_prompts.append(f"[镜头 {idx:03d}] {visual}")
            dialogues.append(f"[镜头 {idx:03d}] {dialogue if dialogue and dialogue != '无' else '(无台词)'}")

        shot_info.append({
            "index": idx,
            "original_text": original,
            "dialogue": dialogue,
            "duration": duration,
            "visual_description": visual,
            "is_violation": is_violation,
        })

    return (
        "\n".join(image_prompts),
        "\n".join(video_prompts),
        "\n".join(dialogues),
        json.dumps(shot_info, ensure_ascii=False, indent=2),
    )


# ==================== 节点 1：生成分镜 ====================
class JingyumaStoryboardNode:
    """
    镜语马分镜生成节点
    输入：小说文本 + API Key
    输出：图像提示词、视频提示词、台词、原始 JSON
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "输入小说章节或剧本内容（最长 10000 字）",
                }),
                "api_key": ("STRING", {
                    "default": "",
                    "tooltip": "在 https://shotstory.cn 注册后获取的 API Key",
                }),
            },
            "optional": {
                "mode": (["basic", "mood", "theme"], {
                    "default": "basic",
                    "tooltip": "basic=快速 / mood=情绪 / theme=题材",
                }),
                "mood": ("STRING", {
                    "default": "",
                    "tooltip": "情绪模式时填写，如：热血激昂、孤独落寞",
                }),
                "theme": ("STRING", {
                    "default": "",
                    "tooltip": "题材模式时填写，如：古风仙侠、都市言情",
                }),
                "use_cache": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "是否启用 10 分钟缓存（避免同一文本重复扣积分）",
                }),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("image_prompts", "video_prompts", "dialogues", "raw_json")
    FUNCTION = "generate_storyboard"
    CATEGORY = "镜语马"

    def generate_storyboard(self, text, api_key, mode="basic",
                            mood="", theme="", use_cache=True):
        text = text.strip()
        api_key = api_key.strip()

        if not text:
            raise RuntimeError("❌ 输入文本为空")
        if not api_key:
            raise RuntimeError("❌ API Key 未填写，请前往 https://shotstory.cn 注册获取")
        if len(text) > 10000:
            raise RuntimeError(f"❌ 文本过长（{len(text)} 字），上限 10000 字")

        # 缓存检查
        cache_key = _make_cache_key(text, mode, mood, theme)
        if use_cache:
            cached = _get_from_cache(cache_key)
            if cached is not None:
                print(f"✅ [镜语马] 命中缓存，跳过 API 调用")
                return _format_shots(cached)

        # 调用 API
        print(f"🌐 [镜语马] 调用 API：mode={mode}, 文本长度={len(text)}")
        data = _call_generate_api(api_key, text, mode, mood, theme)

        shots = data.get("data", {}).get("shots", [])
        tokens_used = data.get("data", {}).get("tokens_used", 0)
        tokens_remaining = data.get("data", {}).get("tokens_remaining", 0)
        print(f"✅ [镜语马] 生成成功：{len(shots)} 个镜头，消耗 {tokens_used} 积分，剩余 {tokens_remaining} 积分")

        # 缓存结果
        if use_cache:
            _save_to_cache(cache_key, shots)

        return _format_shots(shots)


# ==================== 节点 2：拆分镜头 ====================
class JingyumaSplitShotsNode:
    """
    从生成的镜头字符串中提取第 N 个镜头的提示词
    用于逐镜头精细控制生成
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompts": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "forceInput": True,
                    "tooltip": "连接『镜语马·生成分镜』的 image_prompts 输出",
                }),
                "shot_index": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 9999,
                    "tooltip": "要提取第几个镜头",
                }),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    FUNCTION = "extract_shot"
    CATEGORY = "镜语马"

    def extract_shot(self, prompts, shot_index):
        if not prompts:
            return ("",)

        # 找到以 [镜头 NNN] 开头的行
        target_prefix = f"[镜头 {shot_index:03d}]"
        for line in prompts.split("\n"):
            if line.startswith(target_prefix):
                return (line[len(target_prefix):].strip(),)

        # 兜底：按行索引
        lines = [l for l in prompts.split("\n") if l.strip()]
        if 0 <= shot_index - 1 < len(lines):
            line = lines[shot_index - 1]
            # 去掉前缀
            if line.startswith("[镜头"):
                idx = line.find("]")
                if idx != -1:
                    return (line[idx + 1:].strip(),)
            return (line,)

        return ("",)


# ==================== 节点 3：刷新单镜头 ====================
class JingyumaRefreshShotNode:
    """
    对单个镜头刷新不同版本的分镜描述
    仅标准版/专业版套餐可用
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "shot_text": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "要刷新的镜头原句（从 raw_json 中的 original_text 字段复制）",
                }),
                "api_key": ("STRING", {
                    "default": "",
                    "tooltip": "镜语马 API Key",
                }),
                "mode": (["mood", "theme"], {
                    "default": "mood",
                }),
            },
            "optional": {
                "mood": ("STRING", {"default": "", "tooltip": "情绪模式时必填"}),
                "theme": ("STRING", {"default": "", "tooltip": "题材模式时必填"}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("new_prompt",)
    FUNCTION = "refresh_shot"
    CATEGORY = "镜语马"

    def refresh_shot(self, shot_text, api_key, mode="mood", mood="", theme=""):
        shot_text = shot_text.strip()
        api_key = api_key.strip()

        if not shot_text:
            raise RuntimeError("❌ 镜头原句为空")
        if not api_key:
            raise RuntimeError("❌ API Key 未填写")

        url = API_BASE_URL + ROTATE_ENDPOINT
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key,
            "User-Agent": "ComfyUI-JingyumaNode/1.0",
        }
        payload = {"shot_text": shot_text, "mode": mode}
        if mode == "mood" and mood:
            payload["mood"] = mood
        if mode == "theme" and theme:
            payload["theme"] = theme

        print(f"🌐 [镜语马] 刷新镜头：mode={mode}")
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"❌ 请求失败：{e}")

        if resp.status_code != 200:
            try:
                err = resp.json().get("error", resp.text[:200])
            except Exception:
                err = resp.text[:200]
            raise RuntimeError(f"❌ 刷新失败 {resp.status_code}：{err}")

        data = resp.json()
        if not data.get("success"):
            code = data.get("code", "")
            raise RuntimeError(f"❌ 刷新失败[{code}]：{data.get('error', '未知错误')}")

        visual = data.get("data", {}).get("visual", "")
        print(f"✅ [镜语马] 刷新成功：{visual[:50]}...")
        return (visual,)