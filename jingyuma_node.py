"""
ComfyUI Jingyuma Storyboard Nodes
Calls https://shotstory.cn/api/v1/generate to convert novel text into storyboard prompts.

Author: Jingyuma
Version: 1.0.2
"""

import json
import time
import hashlib
import requests
from typing import Tuple, List

# ==================== Constants ====================
API_BASE_URL = "https://shotstory.cn"
GENERATE_ENDPOINT = "/api/v1/generate"
ROTATE_ENDPOINT = "/api/v1/rotate_variant"
TIMEOUT = 120  # seconds

# ==================== Dropdown options ====================
# Display label (English) -> API value (Chinese, used by the server)

# Mood mode options
MOOD_OPTIONS = [
    "(not set)",
    "Healing / Warm",
    "Lazy / Relaxed",
    "Passionate / Fiery",
    "Calm / Detached",
    "Despair / Breakdown",
    "Tense / Fearful",
    "Lonely / Melancholic",
    "Angry / Irritable",
    "Sad / Depressed",
    "Ambiguous / Romantic",
]

MOOD_MAP = {
    "(not set)": "",
    "Healing / Warm": "治愈温暖",
    "Lazy / Relaxed": "慵懒松弛",
    "Passionate / Fiery": "热血激昂",
    "Calm / Detached": "平静淡漠",
    "Despair / Breakdown": "绝望崩溃",
    "Tense / Fearful": "紧张恐惧",
    "Lonely / Melancholic": "孤独落寞",
    "Angry / Irritable": "愤怒暴躁",
    "Sad / Depressed": "悲伤压抑",
    "Ambiguous / Romantic": "暧昧心动",
}

# Theme mode options
THEME_OPTIONS = [
    "(auto detect)",
    "Transmigration System",
    "Tomb Raiding Adventure",
    "Urban Romance",
    "Ancient Xianxia",
    "Military War",
    "Sci-Fi Cyberpunk",
    "Historical Political Intrigue",
    "Post-Apocalyptic Wasteland",
    "Apocalypse Awakening System",
    "Apocalypse Zombie",
    "Hot-Blooded Fantasy",
    "Pastoral Rural",
    "Infinite Flow Dungeon",
    "Wuxia Jianghu",
    "Western Fantasy",
    "Campus Youth",
    "Interstellar Sci-Fi",
    "Suspense Thriller",
    "Game Transmigration",
    "Political Campus",
    "Urban Rebirth System",
]

THEME_MAP = {
    "(auto detect)": "",
    "Transmigration System": "穿越系统",
    "Tomb Raiding Adventure": "盗墓探险",
    "Urban Romance": "都市言情",
    "Ancient Xianxia": "古风仙侠",
    "Military War": "军事战争",
    "Sci-Fi Cyberpunk": "科幻赛博",
    "Historical Political Intrigue": "历史权谋",
    "Post-Apocalyptic Wasteland": "末日废土",
    "Apocalypse Awakening System": "末世觉醒系统",
    "Apocalypse Zombie": "末世丧尸",
    "Hot-Blooded Fantasy": "热血玄幻",
    "Pastoral Rural": "田园乡土",
    "Infinite Flow Dungeon": "无限流副本",
    "Wuxia Jianghu": "武侠江湖",
    "Western Fantasy": "西方奇幻",
    "Campus Youth": "校园青春",
    "Interstellar Sci-Fi": "星际科幻",
    "Suspense Thriller": "悬疑惊悚",
    "Game Transmigration": "游戏穿越",
    "Political Campus": "政务校园",
    "Urban Rebirth System": "都市重生系统",
}

# Refresh node options (must pick a specific value, no "not set")
MOOD_OPTIONS_REQUIRED = [m for m in MOOD_OPTIONS if m != "(not set)"]
THEME_OPTIONS_REQUIRED = [t for t in THEME_OPTIONS if t != "(auto detect)"]

# Simple in-memory cache (avoid duplicate API calls for same text)
# Format: {cache_key: (timestamp, result)}
_CACHE = {}
_CACHE_TTL = 600  # 10 minutes


def _make_cache_key(text: str, mode: str, mood: str, theme: str) -> str:
    """Build cache key."""
    raw = f"{text}|{mode}|{mood}|{theme}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _get_from_cache(key: str):
    """Read from cache."""
    if key in _CACHE:
        ts, result = _CACHE[key]
        if time.time() - ts < _CACHE_TTL:
            return result
        else:
            del _CACHE[key]
    return None


def _save_to_cache(key: str, result):
    """Write to cache."""
    _CACHE[key] = (time.time(), result)


def _call_generate_api(api_key: str, text: str, mode: str = "basic",
                       mood: str = "", theme: str = "") -> dict:
    """
    Call Jingyuma /api/v1/generate endpoint.
    Returns parsed dict containing 'shots' array.
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
        raise RuntimeError(f"Request to Jingyuma API failed: {e}")

    # Handle HTTP status codes
    if resp.status_code == 401:
        raise RuntimeError("Invalid or missing API Key. Get yours at https://shotstory.cn")
    elif resp.status_code == 402:
        raise RuntimeError("Insufficient credits. Top up or upgrade your plan at https://shotstory.cn")
    elif resp.status_code == 403:
        try:
            err = resp.json().get("error", "Forbidden")
        except Exception:
            err = "Forbidden"
        raise RuntimeError(f"Permission denied: {err}")
    elif resp.status_code == 429:
        raise RuntimeError("Too many requests. Please try again later.")
    elif resp.status_code != 200:
        raise RuntimeError(f"API error {resp.status_code}: {resp.text[:200]}")

    # Parse JSON body
    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(f"Response is not valid JSON: {resp.text[:200]}")

    if not data.get("success"):
        error = data.get("error", "Unknown error")
        code = data.get("code", "")
        raise RuntimeError(f"Jingyuma API error[{code}]: {error}")

    return data


def _format_shots(shots: List[dict]) -> Tuple[str, str, str, str]:
    """
    Format shots array into 4 output strings.
    Returns: (image_prompts, video_prompts, dialogues, raw_json)
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
            image_prompts.append(f"[Shot {idx:03d}] Content blocked (violation)")
            video_prompts.append(f"[Shot {idx:03d}] Content blocked (violation)")
            dialogues.append(f"[Shot {idx:03d}] (violation)")
        else:
            image_prompts.append(f"[Shot {idx:03d}] {visual}")
            video_prompts.append(f"[Shot {idx:03d}] {visual}")
            dialogues.append(f"[Shot {idx:03d}] {dialogue if dialogue and dialogue != '无' else '(no dialogue)'}")

        shot_info.append({
            "index": idx,
            "original_text": original,
            "dialogue": dialogue,
            "duration": duration,
            "visual_description": visual,
            "is_violation": is_violation,
            "review_token": shot.get("review_token", ""),
        })

    return (
        "\n".join(image_prompts),
        "\n".join(video_prompts),
        "\n".join(dialogues),
        json.dumps(shot_info, ensure_ascii=False, indent=2),
    )


# ==================== Node 1: Generate Storyboard ====================
class JingyumaStoryboardNode:
    """
    Jingyuma Storyboard Generation Node.
    Input: novel text + API key.
    Output: image prompts, video prompts, dialogues, raw JSON.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "Paste novel chapter or script (max 10000 characters)",
                }),
                "api_key": ("STRING", {
                    "default": "",
                    "tooltip": "Get your API key at https://shotstory.cn",
                }),
            },
            "optional": {
                "mode": (["basic", "mood", "theme"], {
                    "default": "basic",
                    "tooltip": "basic = fast (free tier) / mood = emotion (Standard+) / theme = genre (Pro)",
                }),
                "mood": (MOOD_OPTIONS, {
                    "default": "(not set)",
                    "tooltip": "Only used when mode = mood",
                }),
                "theme": (THEME_OPTIONS, {
                    "default": "(auto detect)",
                    "tooltip": "Only used when mode = theme. '(auto detect)' lets the server detect the genre.",
                }),
                "use_cache": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Cache results for 10 minutes to avoid duplicate API charges",
                }),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("image_prompts", "video_prompts", "dialogues", "raw_json")
    FUNCTION = "generate_storyboard"
    CATEGORY = "Jingyuma"

    def generate_storyboard(self, text, api_key, mode="basic",
                            mood="(not set)", theme="(auto detect)", use_cache=True):
        text = text.strip()
        api_key = api_key.strip()

        # Map dropdown labels back to API values (Chinese)
        mood = MOOD_MAP.get(mood, "")
        theme = THEME_MAP.get(theme, "")

        if not text:
            raise RuntimeError("Input text is empty")
        if not api_key:
            raise RuntimeError("API key is missing. Get yours at https://shotstory.cn")
        if len(text) > 10000:
            raise RuntimeError(f"Text too long ({len(text)} chars). Max 10000 chars.")

        # Cache check
        cache_key = _make_cache_key(text, mode, mood, theme)
        if use_cache:
            cached = _get_from_cache(cache_key)
            if cached is not None:
                print("[Jingyuma] Cache hit, skipping API call")
                return _format_shots(cached)

        # Call API
        print(f"[Jingyuma] Calling API: mode={mode}, mood={mood}, theme={theme}, text_len={len(text)}")
        data = _call_generate_api(api_key, text, mode, mood, theme)

        shots = data.get("data", {}).get("shots", [])
        tokens_used = data.get("data", {}).get("tokens_used", 0)
        tokens_remaining = data.get("data", {}).get("tokens_remaining", 0)
        print(f"[Jingyuma] Success: {len(shots)} shots, used {tokens_used} credits, {tokens_remaining} remaining")

        # Save to cache
        if use_cache:
            _save_to_cache(cache_key, shots)

        return _format_shots(shots)


# ==================== Node 2: Split Shots ====================
class JingyumaSplitShotsNode:
    """
    Extract the Nth shot's prompt from the generated shots string.
    Useful for per-shot fine-grained generation.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompts": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "forceInput": True,
                    "tooltip": "Connect to the 'image_prompts' output of 'Jingyuma Storyboard'",
                }),
                "shot_index": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 9999,
                    "tooltip": "Which shot to extract",
                }),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    FUNCTION = "extract_shot"
    CATEGORY = "Jingyuma"

    def extract_shot(self, prompts, shot_index):
        if not prompts:
            return ("",)

        # Find the line starting with "[Shot NNN]"
        target_prefix = f"[Shot {shot_index:03d}]"
        for line in prompts.split("\n"):
            if line.startswith(target_prefix):
                return (line[len(target_prefix):].strip(),)

        # Fallback: index by line number
        lines = [l for l in prompts.split("\n") if l.strip()]
        if 0 <= shot_index - 1 < len(lines):
            line = lines[shot_index - 1]
            # Strip prefix
            if line.startswith("[Shot"):
                idx = line.find("]")
                if idx != -1:
                    return (line[idx + 1:].strip(),)
            return (line,)

        return ("",)


# ==================== Node 3: Refresh Single Shot ====================
class JingyumaRefreshShotNode:
    """
    Refresh a single shot's description with a different variant.
    Available for Standard / Pro plans only.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "shot_text": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "Shot's original text (copy from the 'original_text' field in raw_json)",
                }),
                "api_key": ("STRING", {
                    "default": "",
                    "tooltip": "Jingyuma API key",
                }),
                "mode": (["mood", "theme"], {
                    "default": "mood",
                    "tooltip": "Refresh requires 'mood' or 'theme'. Fast mode (basic) has no refresh.",
                }),
                "mood": (MOOD_OPTIONS_REQUIRED, {
                    "default": MOOD_OPTIONS_REQUIRED[0],
                    "tooltip": "Only used when mode = mood",
                }),
                "theme": (THEME_OPTIONS_REQUIRED, {
                    "default": THEME_OPTIONS_REQUIRED[0],
                    "tooltip": "Only used when mode = theme",
                }),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("new_prompt",)
    FUNCTION = "refresh_shot"
    CATEGORY = "Jingyuma"

    def refresh_shot(self, shot_text, api_key, mode="mood",
                     mood=MOOD_OPTIONS_REQUIRED[0], theme=THEME_OPTIONS_REQUIRED[0]):
        shot_text = shot_text.strip()
        api_key = api_key.strip()

        if not shot_text:
            raise RuntimeError("Shot text is empty")
        if not api_key:
            raise RuntimeError("API key is missing")

        url = API_BASE_URL + ROTATE_ENDPOINT
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key,
            "User-Agent": "ComfyUI-JingyumaNode/1.0",
        }

        # Map dropdown labels back to API values
        payload = {"shot_text": shot_text, "mode": mode}
        if mode == "mood":
            payload["mood"] = MOOD_MAP.get(mood, "")
        if mode == "theme":
            payload["theme"] = THEME_MAP.get(theme, "")

        print(f"[Jingyuma] Refreshing shot: mode={mode}")
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Request failed: {e}")

        if resp.status_code != 200:
            try:
                err = resp.json().get("error", resp.text[:200])
            except Exception:
                err = resp.text[:200]
            raise RuntimeError(f"Refresh failed {resp.status_code}: {err}")

        data = resp.json()
        if not data.get("success"):
            code = data.get("code", "")
            raise RuntimeError(f"Refresh failed[{code}]: {data.get('error', 'Unknown error')}")

        visual = data.get("data", {}).get("visual", "")
        print(f"[Jingyuma] Refresh success: {visual[:50]}...")
        return (visual,)
