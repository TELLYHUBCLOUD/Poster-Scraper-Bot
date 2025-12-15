import json
import re
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse, quote_plus

import requests

from .. import LOGGER
from .utils.xtra import _sync_to_async

# Constants for timeouts
BYPASS_TIMEOUT = 120
BYPASS_SHORT_TIMEOUT = 30

_BYPASS_CMD_TO_SERVICE = {
    "gdflix": "gdflix",
    "gdf": "gdflix",
    "hubcloud": "hubcloud",
    "hc": "hubcloud",
    "hubdrive": "hubdrive",
    "hd": "hubdrive",
    "transfer_it": "transfer_it",
    "ti": "transfer_it",
    "terabox": "terabox",
    "tb": "terabox",
    "bypass": "bypass",
    "bp": "bypass",
    "vega": "custom_vega",
    "vg": "custom_vega",
    "nexdrive": "custom_nexdrive",
    "nd": "custom_nexdrive",
    "pixelcdn": "custom_pixelcdn",
    "pc": "custom_pixelcdn",
    "vcloud": "custom_vcloud",
    "vc": "custom_vcloud",
    "hblinks": "custom_hblinks",
    "hb": "custom_hblinks",
    "gdrex": "custom_gdrex",
    "gr": "custom_gdrex",
    "extraflix": "custom_extraflix",
    "ef": "custom_extraflix",
    "neo": "custom_neo",
    "no": "custom_neo",
    "gofile": "custom_gofile",
    "go": "custom_gofile",
}
_BYPASS_ENDPOINTS = {
    "gdflix": "https://pbx1botapi.vercel.app/api/gdflix?url=",
    "hubcloud": "https://pbx1botapi.vercel.app/api/hubcloud?url=",
    "hubdrive": "https://pbx1botapi.vercel.app/api/hubdrive?url=", 
    "transfer_it": "https://transfer-it-henna.vercel.app/post",
    "terabox": "https://true-link-vercel-api.vercel.app/api/terabox/api?url=",
    "bypass": "https://true-link-vercel-api.vercel.app/api/bypass?url=",
    "bypass_bulk": "https://true-link-vercel-api.vercel.app/api/bypass-bulk",
    "custom_vega": "https://pbx1botsapi2.vercel.app/api/vega?url=",
    "custom_nexdrive": "https://pbx1botsapi2.vercel.app/api/nexdrive?url=",
    "custom_pixelcdn": "https://pbx1botapi.vercel.app/api/pixelcdn?url=",
    "custom_vcloud": "https://pbx1botapi.vercel.app/api/vcloud?url=",
    "custom_hblinks": "https://pbx1botsapi2.vercel.app/api/hblinks?url=",
    "custom_gdrex": "https://pbx1botapi.vercel.app/api/gdrex?url=",
    "custom_extraflix": "https://pbx1botapi.vercel.app/api/extraflix?url=",
    "custom_neo": "https://pbx1botapi.vercel.app/api/neo?url=",
    "custom_gofile": "https://gofile.dd-bypassed.workers.dev/api", 
}
"""
Credits:
@Nick_Updates for transfer.it
HgBot (Harshit) for Gdflix, Hubcloud, Hubdrive
"""

def _bp_srv(cmd):
    if not cmd:
        return None
    cmd = cmd.lower().lstrip("/")
    return _BYPASS_CMD_TO_SERVICE.get(cmd)


def _bp_label_from_key(key):
    mapping = {
        "instant_final": "Instant",
        "cloud_r2": "Cloud R2",
        "zip_final": "ZIP",
        "pixeldrain": "Pixeldrain",
        "telegram_file": "Telegram",
        "gofile_final": "Gofile",
    }
    if key in mapping:
        return mapping[key]
    return key.replace("_", " ").title()


def _bp_label_from_name(name):
    s = str(name).strip()
    low = s.lower()
    if "[" in s and "]" in s and "download" in low:
        i1 = s.find("[")
        i2 = s.rfind("]")
        if i1 != -1 and i2 != -1 and i2 > i1:
            inner = s[i1 + 1 : i2].strip()
            if inner:
                return inner
    if low.startswith("download "):
        return s[8:].strip() or s
    return s


def _bp_links(links):
    if not isinstance(links, dict) or not links:
        return "• No direct links found."
    lines = []
    for label, url in links.items():
        if not isinstance(url, str):
            continue
        u = url.strip()
        if not u.startswith(("http://", "https://")):
            continue
        lbl = str(label).strip()
        if not lbl:
            lbl = "Link"
        lines.append(f"• <b>{lbl}:</b> <a href=\"{u}\">Click Here</a>")
    if not lines:
        return "• No direct links found."
    return "\n".join(lines)


def _bp_norm(data, service):
    # Handle list of results (Vega, ExtraFlix)
    if isinstance(data, dict) and "results" in data and isinstance(data["results"], list):
        norm_list = []
        for item in data["results"]:
             norm_list.append(_bp_norm(item, service))
        return norm_list
        
    root = data
    if isinstance(data, dict) and isinstance(data.get("final"), dict):
        root = data["final"]
    title = root.get("title") or root.get("file_name") or data.get("title") or "N/A"
    filesize = root.get("filesize") or root.get("file_size") or data.get("filesize") or "N/A"
    file_format = (
        root.get("format")
        or root.get("file_format")
        or data.get("format")
        or data.get("file_format")
        or "N/A"
    )
    links_clean = {}
    raw_links = root.get("links") or root.get("files")
    
    # Check metadata for title/size (Terabox/Bypass API)
    if "metadata" in root and isinstance(root["metadata"], dict):
        meta = root["metadata"]
        if title == "N/A":
            title = meta.get("file_name") or meta.get("title") or "N/A"
        if filesize == "N/A":
            filesize = meta.get("size") or meta.get("filesize") or "N/A"

    # Handle single logic url (HBLinks)
    if not raw_links and root.get("url") and isinstance(root["url"], str):
        links_clean["Direct Link"] = root["url"]

    # Handle 'links' as list of dicts (NexDrive, PixelCDN, HubCloud, GDFlix, etc)
    if isinstance(raw_links, list):
         for item in raw_links:
             if isinstance(item, dict):
                 # Try to find label and url
                 # Common keys: type, tag, text | url, link
                 lbl = item.get("type") or item.get("tag") or item.get("text") or item.get("quality") or "Link"
                 url = item.get("url") or item.get("link")
                 if url:
                      links_clean[str(lbl)] = url

    elif isinstance(raw_links, dict):
        for k, v in raw_links.items():
            url = None
            lbl = _bp_label_from_key(k)
            if isinstance(v, str):
                url = v.strip()
            elif isinstance(v, dict):
                url = (
                    v.get("link")
                    or v.get("url")
                    or v.get("google_final")
                    or v.get("edited")
                    or v.get("telegram_file")
                    or v.get("gofile_final")
                )
                if v.get("name"):
                    lbl = _bp_label_from_name(v["name"])
            if not url:
                continue
            url = str(url).strip()
            if not url.startswith(("http://", "https://")):
                continue
            links_clean[lbl] = url
    
    # Special handling for Terabox/Bypass new API structure
    if not links_clean and service in ["terabox", "bypass"]:
        # Check for direct 'url' in root (bypass api)
        if root.get("url") and isinstance(root["url"], str):
             links_clean["Direct Link"] = root["url"]
        
        # Check for 'api' keys (terabox api)
        # e.g. api1: { dl1: ..., dl2: ..., stream: ... }
        for k, v in root.items():
            if k.startswith("api") and isinstance(v, dict):
                # Extract dl1, dl2, stream
                for subk, subv in v.items():
                    if isinstance(subv, str) and subv.startswith(("http", "https")):
                         label = f"{k.upper()} - {subk.upper()}"
                         links_clean[label] = subv
        
        # Check for 'streamapi' (terabox api)
        if "streamapi" in root and isinstance(root["streamapi"], dict):
             v = root["streamapi"]
             for subk, subv in v.items():
                    if isinstance(subv, str) and subv.startswith(("http", "https")):
                         label = f"StreamAPI - {subk.upper()}"
                         links_clean[label] = subv

    if not links_clean:
        skip = {"title", "filesize", "format", "file_format", "success", "links"}
        for k, v in root.items():
            if k in skip:
                continue
            url = None
            lbl = str(k)
            if isinstance(v, dict):
                url = (
                    v.get("link")
                    or v.get("url")
                    or v.get("google_final")
                    or v.get("edited")
                    or v.get("telegram_file")
                    or v.get("gofile_final")
                )
                if v.get("name"):
                    lbl = _bp_label_from_name(v["name"])
            elif isinstance(v, str) and v.startswith(("http://", "https://")):
                url = v
                lbl = _bp_label_from_key(k)
            if not url:
                continue
            url = str(url).strip()
            if not url.startswith(("http://", "https://")):
                continue
            links_clean[lbl] = url
    return {
        "title": str(title),
        "filesize": str(filesize),
        "format": str(file_format),
        "links": links_clean,
        "service": service,
    }


def _validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """Validate URL format and structure.
    
    Args:
        url: URL string to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url or not isinstance(url, str):
        return False, "Invalid URL format."
    
    url = url.strip()
    
    # Basic validation using urlparse
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False, "URL missing scheme or domain."
        if parsed.scheme not in ['http', 'https']:
            return False, "Only HTTP/HTTPS URLs are supported."
    except Exception as e:
        return False, f"URL validation error: {str(e)}"
    
    return True, None

async def _bp_info(cmd_name: str, target_url: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Fetch bypass information for a given URL.
    
    Args:
        cmd_name: Command name (e.g., 'gdflix', 'terabox')
        target_url: URL to bypass
        
    Returns:
        Tuple of (normalized_data, error_message)
    """
    service = _bp_srv(cmd_name)
    if not service:
        return None, "Unknown platform for this command."
    
    base = _BYPASS_ENDPOINTS.get(service)
    if not base:
        return None, "Bypass endpoint not configured for this service."
    
    # Validate URL
    is_valid, error_msg = _validate_url(target_url)
    if not is_valid:
        return None, error_msg
    
    # Check cache first
    cache_key = f"{service}:{target_url}"
    if cache_key in _bypass_cache:
        LOGGER.info(f"Cache hit for {service}")
        return _bypass_cache[cache_key], None
    # Build API URL based on service type
    if service == "transfer_it":
        api_url = base
    else:
        # Fix for Terabox API 400 error on alternate domains
        if service == "terabox":
            # Replace common alternate domains with terabox.com
            # The API expects https://terabox.com/s/xxxx
            terabox_domains = [
                "1024terabox.com", "teraboxapp.com", "terabox.app", 
                "nephobox.com", "4funbox.com", "mirrobox.com", 
                "momerybox.com", "terabox.fun"
            ]
            for dom in terabox_domains:
                if dom in target_url:
                    target_url = target_url.replace(dom, "terabox.com")
                    LOGGER.info(f"Normalized Terabox domain to terabox.com")
                    break
        
        # Gofile Custom Logic: Extract ID and append to base
        if service == "custom_gofile":
            # URL: https://gofile.io/d/B3QPQb -> ID: B3QPQb
            # API: base + ID
            try:
                match = re.search(r"gofile\.io/d/([a-zA-Z0-9_-]+)", target_url)
                if match:
                    gofile_id = match.group(1)
                    api_url = f"{base}/{gofile_id}"
                    LOGGER.info(f"Extracted Gofile ID: {gofile_id}")
                else:
                    return None, "Invalid Gofile URL format. Expected gofile.io/d/ID"
            except Exception as e:
                LOGGER.error(f"Gofile ID extraction error: {e}")
                return None, "Failed to extract Gofile ID."
        else:
            api_url = f"{base}{quote_plus(target_url)}"

    LOGGER.info(f"Bypassing via [{service}] -> {api_url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        resp = await _sync_to_async(
            requests.get, api_url, headers=headers, timeout=BYPASS_TIMEOUT
        )
    except Exception as e:
        LOGGER.error(f"Bypass request failed: {e}", exc_info=True)
        return None, "Failed to reach bypass service."
    
    if resp.status_code != 200:
        LOGGER.error(f"Bypass API returned {resp.status_code}: {resp.text[:200]}")
        return None, f"Bypass service error (HTTP {resp.status_code})."
    try:
        data = resp.json()
    except json.JSONDecodeError as e:
        LOGGER.error(f"Bypass JSON parse error: {e}")
        return None, "Invalid response from bypass service."
    if not isinstance(data, dict):
        return None, "Unexpected response from bypass service."
    if service == "transfer_it":
        direct = data.get("url")
        if not direct:
            return None, "File Expired or File Not Found"
        fake = {
            "title": "N/A",
            "filesize": "N/A",
            "format": "N/A",
            "links": {"Direct Link": str(direct)},
        }
        norm = _bp_norm(fake, service)
        return norm, None
    if "success" in data and not data.get("success"):
        error_msg = data.get("message") or "Bypass failed."
        return None, error_msg
    
    norm = _bp_norm(data, service)
    
    return norm, None

async def _bp_bulk_info(urls: List[str]) -> Tuple[Optional[Any], Optional[str]]:
    api_url = _BYPASS_ENDPOINTS.get("bypass_bulk")
    if not api_url:
        return None, "Bulk bypass endpoint not configured."
    
    """Bulk bypass multiple URLs at once.
    
    Args:
        urls: List of URLs to bypass
        
    Returns:
        Tuple of (results, error_message)
    """
    # Validate all URLs first
    invalid_urls = []
    for url in urls:
        is_valid, error = _validate_url(url)
        if not is_valid:
            invalid_urls.append(url)
    
    if invalid_urls:
        return None, f"Invalid URLs found: {len(invalid_urls)} out of {len(urls)}"
    
    LOGGER.info(f"Bulk bypassing {len(urls)} links via {api_url}")
    try:
        resp = await _sync_to_async(
            requests.post, api_url, json={"urls": urls}, timeout=BYPASS_SHORT_TIMEOUT
        )
    except Exception as e:
        LOGGER.error(f"Bulk bypass error: {e}", exc_info=True)
        return None, "Failed to reach bulk service."
        
    if resp.status_code != 200:
         return None, f"Bulk service returned {resp.status_code}"
         
    try:
        data = resp.json()
    except:
        return None, "Invalid JSON from bulk service."
        
    if isinstance(data, list):
        return data, None
    elif isinstance(data, dict):
        return data, None
        
    return None, "Unexpected bulk response format."
