import re
import json
from typing import Dict, Optional, Tuple, Any
from urllib.parse import urlparse, quote_plus

import requests

from .. import LOGGER
from .utils.xtra import _sync_to_async

# Constants for timeouts
OTT_TIMEOUT = 20

def _collect_url_pairs(node, out_list, parent_key=""):
    if isinstance(node, dict):
        for k, v in node.items():
            key = f"{parent_key}.{k}" if parent_key else str(k)
            _collect_url_pairs(v, out_list, key)
    elif isinstance(node, (list, tuple)):
        for idx, v in enumerate(node):
            key = f"{parent_key}[{idx}]" if parent_key else str(idx)
            _collect_url_pairs(v, out_list, key)
    elif isinstance(node, str):
        v = node.strip()
        if v.startswith("http://") or v.startswith("https://"):
            out_list.append((parent_key.lower(), v))


def _looks_like_image(url: str) -> bool:
    url_l = url.lower()
    if any(url_l.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".avif", ".jfif")):
        return True
    if any(x in url_l for x in ["image", "img", "poster", "cover", "banner", "art", "thumb"]):
        return True
    return False

_CMD_TO_PROVIDER = {
    "prime": "primevideo", "pv": "primevideo",
    "zee5": "zee5", "z5": "zee5",
    "appletv": "appletv", "atv": "appletv",
    "airtel": "airtelxstream", "ax": "airtelxstream",
    "sunnxt": "sunnxt", "sn": "sunnxt",
    "aha": "ahavideo", "ah": "ahavideo",
    "iqiyi": "iqiyi", "iq": "iqiyi",
    "wetv": "wetv", "wt": "wetv",
    "shemaroo": "shemaroo", "sm": "shemaroo",
    "bms": "bookmyshow", "bm": "bookmyshow",
    "plex": "plextv", "px": "plextv",
    "adda": "addatimes", "ad": "addatimes",
    "stage": "stage", "stg": "stage",
    "netflix": "netflix", "nf": "netflix",
    "mxplayer": "mxplayer", "mx": "mxplayer",
    "youtube": "ytdl", "yt": "ytdl",
    "instagram": "instagram", "ig": "instagram",
    "facebook": "facebook", "fb": "facebook",
    "tiktok": "tiktok", "tk": "tiktok",
    # New OTT platforms
    "hotstar": "hotstar", "hs": "hotstar",
    "sonyliv": "sonyliv", "sl": "sonyliv",
    "voot": "voot", "vo": "voot",
    "jiocinema": "jiocinema", "jc": "jiocinema",
}

_PROVIDER_NAMES = {
    "primevideo": "Prime Video",
    "zee5": "ZEE5",
    "appletv": "Apple TV+",
    "airtelxstream": "Airtel Xstream",
    "sunnxt": "Sun NXT",
    "ahavideo": "Aha Video",
    "iqiyi": "iQIYI",
    "wetv": "WeTV",
    "shemaroo": "ShemarooMe",
    "bookmyshow": "BookMyShow",
    "plextv": "Plex TV",
    "addatimes": "Addatimes",
    "stage": "Stage",
    "netflix": "Netflix",
    "mxplayer": "MX Player",
    "ytdl": "YouTube",
    "instagram": "Instagram",
    "facebook": "Facebook",
    "tiktok": "TikTok",
    # New platforms
    "hotstar": "Disney+ Hotstar",
    "sonyliv": "SonyLIV",
    "voot": "Voot",
    "jiocinema": "JioCinema",
}

_WORKERS = {
    "primevideo": "https://primevideo.pbx1bots.workers.dev/?url=",
    "zee5": "https://zee5.pbx1bots.workers.dev/?url=",
    "appletv": "https://appletv.pbx1bots.workers.dev/?url=",
    "airtelxstream": "https://airtelxstream.pbx1bots.workers.dev/?url=",
    "sunnxt": "https://sunnxt.pbx1.workers.dev/?url=",
    "ahavideo": "https://ahavideo.the-zake.workers.dev/?url=",
    "iqiyi": "https://iqiyi.the-zake.workers.dev/?url=",
    "wetv": "https://wetv.the-zake.workers.dev/?url=",
    "shemaroo": "https://shemaroo.the-zake.workers.dev/?url=",
    "bookmyshow": "https://bms.pbx1.workers.dev/?url=",
    "plextv": "https://plextv.the-zake.workers.dev/?url=",
    "addatimes": "https://addatimes.the-zake.workers.dev/?url=",
    "stage": "https://stage.pbx1bots.workers.dev/?url=",
    "netflix": "https://netflix.the-zake.workers.dev/?url=",
    "mxplayer": "https://mxplayer.the-zake.workers.dev/?url=",
    "ytdl": "https://youtubedl.the-zake.workers.dev/?url=",
    "instagram": "https://instagramdl.the-zake.workers.dev/?url=",
    "facebook": "https://facebookdl.the-zake.workers.dev/?url=",
    "tiktok": "https://tiktokdl.the-zake.workers.dev/?url=",
    # New platforms - using the-zake.workers.dev pattern
    "hotstar": "https://hotstar.the-zake.workers.dev/?url=",
    "sonyliv": "https://sonyliv.the-zake.workers.dev/?url=",
    "voot": "https://voot.the-zake.workers.dev/?url=",
    "jiocinema": "https://jiocinema.the-zake.workers.dev/?url=",
}
def _extract_url_from_message(message):
    if getattr(message, "command", None) and len(message.command) > 1:
        return message.command[1].strip()

    if message.reply_to_message:
        reply = message.reply_to_message
        text = reply.text or reply.caption or ""
        for part in text.split():
            if part.startswith("http://") or part.startswith("https://"):
                return part.strip()

    text = message.text or ""
    for part in text.split():
        if part.startswith("http://") or part.startswith("https://"):
            return part.strip()

    return None


def _extract_all_urls_from_message(message):
    urls = []
    
    # Check command args (e.g. /bypass url1 url2)
    if getattr(message, "command", None) and len(message.command) > 1:
        for arg in message.command[1:]:
            arg = arg.strip()
            if arg.startswith("http://") or arg.startswith("https://"):
                urls.append(arg)

    # Check reply message
    if message.reply_to_message:
        reply = message.reply_to_message
        text = reply.text or reply.caption or ""
        for part in text.split():
            part = part.strip()
            if part.startswith("http://") or part.startswith("https://"):
                urls.append(part)

    # Check current message text (if mixed with command or just text)
    text = message.text or ""
    # Avoid re-adding command args if we already processed them, but simpler to just regex or split
    # If the command was /bypass url1, message.text is "/bypass url1"
    for part in text.split():
        part = part.strip()
        # skip the command itself if it starts with /
        if part.startswith("/"):
            continue
        if part.startswith("http://") or part.startswith("https://"):
            if part not in urls: # simple dedup
                urls.append(part)
                
    return urls


def _provider_from_cmd(cmd: str) -> Optional[str]:
    """Get provider name from command.
    
    Args:
        cmd: Command string
        
    Returns:
        Provider name or None
    """
    cmd = cmd.lower().lstrip("/")
    return _CMD_TO_PROVIDER.get(cmd)

def _normalize_ott_json(provider: str, data: dict):
    if not isinstance(data, dict):
        return None

    if "data" in data and isinstance(data["data"], dict):
        root = data["data"]
    else:
        root = data

    poster = (
        root.get("portrait")
        or root.get("poster")
        or root.get("poster_url")
        or root.get("thumbnail")
        or root.get("image")
        or root.get("image_url")
        or root.get("cover")
        or root.get("thumb")
    )

    landscape = (
        root.get("landscape")
        or root.get("landscape_url")
        or root.get("backdrop")
        or root.get("banner")
        or root.get("fanart")
    )

    urls = []
    _collect_url_pairs(data, urls)

    image_urls = [(k, v) for k, v in urls if _looks_like_image(v)]
    all_urls = [v for _, v in image_urls] or [v for _, v in urls]

    if (not poster or not _looks_like_image(str(poster))) or (
        not landscape or not _looks_like_image(str(landscape))
    ):
        portrait_candidates = []
        landscape_candidates = []

        for key, url in image_urls:
            key_l = key.lower()
            if any(x in key_l for x in ["portrait", "vertical", "poster", "thumb", "cover", "thumbnail"]):
                portrait_candidates.append(url)
            if any(x in key_l for x in ["landscape", "horizontal", "backdrop", "banner", "hero"]):
                landscape_candidates.append(url)

        if (not poster or not _looks_like_image(str(poster))) and portrait_candidates:
            poster = portrait_candidates[0]

        if (not landscape or not _looks_like_image(str(landscape))) and landscape_candidates:
            landscape = landscape_candidates[0]

        if not poster and all_urls:
            poster = all_urls[0]

        if not landscape and len(all_urls) > 1:
            candidate = all_urls[1]
            landscape = candidate if candidate != poster else None

    title = (
        root.get("title")
        or root.get("name")
        or root.get("show")
        or root.get("movie")
        or "N/A"
    )
    year = (
        root.get("year")
        or root.get("release_year")
        or root.get("release")
        or "N/A"
    )
    otype = root.get("type") or root.get("kind") or "N/A"

    return {
        "title": str(title) if title is not None else "N/A",
        "year": str(year) if year is not None else "N/A",
        "type": str(otype) if otype is not None else "N/A",
        "poster": poster,
        "landscape": landscape,
        "raw": data,
        "source": _PROVIDER_NAMES.get(provider, provider.title()),
    }

async def _fetch_ott_info(cmd_name: str, target_url: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Fetch OTT poster information for a given URL.
    
    Args:
        cmd_name: Command name (e.g., 'prime', 'netflix')
        target_url: URL to fetch poster from
        
    Returns:
        Tuple of (poster_info, error_message)
    """
    provider = _provider_from_cmd(cmd_name)
    if not provider:
        return None, "Unknown platform for this command."

    base = _WORKERS.get(provider)
    if not base:
        return None, "Worker endpoint not configured for this platform."

    # Validate URL
    try:
        parsed = urlparse(target_url)
        if not parsed.scheme or not parsed.netloc:
            return None, "Invalid URL format."
    except Exception:
        return None, "Invalid URL format."

    worker_url = f"{base}{quote_plus(target_url)}"
    LOGGER.info(f"Fetching OTT poster from [{provider}] via {worker_url}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        resp = await _sync_to_async(
            requests.get, worker_url, headers=headers, timeout=OTT_TIMEOUT
        )
    except Exception as e:
        LOGGER.error(f"OTT request failed: {e}", exc_info=True)
        return None, "Failed to reach poster service."

    if resp.status_code != 200:
        LOGGER.error(f"Worker returned status {resp.status_code}: {resp.text[:200]}")
        return None, f"Poster service error (HTTP {resp.status_code})"

    try:
        data = resp.json()
    except json.JSONDecodeError as e:
        LOGGER.error(f"JSON parse error: {e}")
        return None, "Invalid response from poster service."

    info = _normalize_ott_json(provider, data)
    if not info:
        return None, "Could not parse poster info."

    return info, None
