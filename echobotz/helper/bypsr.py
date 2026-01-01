import re
import json
from urllib.parse import urlparse, quote_plus
import requests

from .. import LOGGER
from .utils.xtra import _sync_to_async

class EchoBypass:
    def __init__(self, key, endpoint, method="GET", norm=None):
        self.key = key
        self.endpoint = endpoint
        self.method = method
        self.norm = norm or self._norm

    async def fetch(self, url):
        api_url = self.endpoint if self.method == "POST" else f"{self.endpoint}{quote_plus(url)}"
        LOGGER.info(f"[{self.key}] API URL: {api_url}")

        try:
            if self.method == "POST":
                resp = await _sync_to_async(
                    requests.post,
                    api_url,
                    json={"url": url},
                    timeout=30
                )
            else:
                resp = await _sync_to_async(
                    requests.get,
                    api_url,
                    timeout=30
                )
            LOGGER.info(f"[{self.key}] Status Code: {resp.status_code}")
        except Exception as e:
            LOGGER.error(f"[{self.key}] HTTP error: {e}", exc_info=True)
            return None, "Failed to reach bypass service."

        if resp.status_code != 200:
            LOGGER.error(
                f"[{self.key}] API error {resp.status_code}: {resp.text[:200]}"
            )
            return None, "Bypass service error."

        try:
            data = resp.json()
            LOGGER.info(f"[{self.key}] JSON parsed successfully")
        except Exception as e:
            LOGGER.error(f"[{self.key}] JSON parse error: {e}")
            return None, "Invalid response from bypass service."

        data = self._unwrap(data)
        LOGGER.info(f"[{self.key}] Data unwrapped: {type(data).__name__}")

        if not isinstance(data, dict):
            LOGGER.error(f"[{self.key}] Invalid JSON structure")
            return None, "Unexpected response from bypass service."

        if data.get("success") is False:
            LOGGER.error(f"[{self.key}] API failure: {data.get('message')}")
            return None, data.get("message") or "Bypass failed."

        LOGGER.info(f"[{self.key}] Normalizing response")
        return self.norm(data)

    def _unwrap(self, data):
        if isinstance(data, dict):
            return data

        if isinstance(data, list):
            if not data:
                return {}
            if len(data) == 1 and isinstance(data[0], dict):
                return data[0]
            return {"results": data}

        return {}

    def _norm(self, data):
        results = data.get("results")

        if isinstance(results, list) and results:
            first = results[0]
            if isinstance(first, dict) and (
                "file_name" in first
                or "links" in first
                or "quality" in first
                or "link" in first
            ):
                return {
                    "hc_pack": True,
                    "hc_pack_results": results,
                    "total_files": len(results),
                    "service": self.key
                }, None

        root = data.get("final") or data

        direct = root.get("url")
        if isinstance(direct, str) and direct.startswith(("http://", "https://")):
            return {
                "title": root.get("file_name") or "N/A",
                "filesize": root.get("file_size") or "N/A",
                "format": "N/A",
                "links": {"Direct Link": direct},
                "service": self.key
            }, None

        title = (
            root.get("title")
            or root.get("file_name")
            or root.get("fileName")
            or "N/A"
        )
        filesize = root.get("filesize") or root.get("file_size") or "N/A"
        file_format = root.get("format") or root.get("file_format") or "N/A"

        links = _xlnk(root)

        if not links:
            LOGGER.error(f"[{self.key}] No direct links found after normalization")
            return None, "No direct links found."

        return {
            "title": str(title),
            "filesize": str(filesize),
            "format": str(file_format),
            "links": links,
            "service": self.key
        }, None

class TeraboxBypass(EchoBypass):
    async def fetch(self, url):
        domains = [
            "1024terabox.com", "teraboxapp.com", "terabox.app", 
            "nephobox.com", "4funbox.com", "mirrobox.com", 
            "momerybox.com", "terabox.fun"
        ]
        for dom in domains:
            if dom in url:
                url = url.replace(dom, "terabox.com")
                break
        return await super().fetch(url)
    
    def _norm(self, data):
        root = data
        links_clean = {}
        
        # Logic from user's provided code for Terabox/Bypass
        if root.get("url") and isinstance(root["url"], str):
             links_clean["Direct Link"] = root["url"]
        
        for k, v in root.items():
            if k.startswith("api") and isinstance(v, dict):
                for subk, subv in v.items():
                    if isinstance(subv, str) and subv.startswith(("http", "https")):
                         label = f"{k.upper()} - {subk.upper()}"
                         links_clean[label] = subv
        
        if "streamapi" in root and isinstance(root["streamapi"], dict):
             v = root["streamapi"]
             for subk, subv in v.items():
                    if isinstance(subv, str) and subv.startswith(("http", "https")):
                         label = f"StreamAPI - {subk.upper()}"
                         links_clean[label] = subv

        # Fallback to standard parsing if specific logic yields nothing
        if not links_clean:
             # Standard "links" or "files" checking
             raw_links = root.get("links") or root.get("files")
             if isinstance(raw_links, dict):
                 for k, v in raw_links.items():
                     if isinstance(v, str) and v.startswith(("http", "https")):
                         links_clean[str(k).title()] = v
             elif isinstance(raw_links, list):
                  for item in raw_links:
                      if isinstance(item, dict):
                           lbl = item.get("type") or item.get("tag") or "Link"
                           url = item.get("url") or item.get("link")
                           if url: links_clean[str(lbl)] = url

        meta = root.get("metadata", {}) if isinstance(root.get("metadata"), dict) else {}
        title = root.get("title") or root.get("filename") or meta.get("file_name") or meta.get("title") or "N/A"
        filesize = root.get("filesize") or root.get("size") or meta.get("size") or meta.get("filesize") or "N/A"
        
        # Always use Pack Mode (Buttons) for Terabox as requested
        if len(links_clean) > 0:
            pack_results = []
            for k, v in links_clean.items():
                pack_results.append({
                    "file_name": str(k),
                    "link": str(v),
                    "file_size": "N/A"
                })
            
            return {
                "hc_pack": True,
                "hc_pack_results": pack_results,
                "total_files": len(pack_results),
                "service": self.key,
                "title": str(title)
            }, None

        return {
            "title": str(title),
            "filesize": str(filesize),
            "format": "N/A",
            "links": links_clean,
            "service": self.key
        }, None

class GofileBypass(EchoBypass):
    async def fetch(self, url):
        match = re.search(r"gofile\.io/d/([a-zA-Z0-9_-]+)", url)
        if not match:
             return None, "Invalid Gofile URL. Expected gofile.io/d/ID"
        gid = match.group(1)
        
        # User confirmed base + ID
        api_url = f"{self.endpoint}/{gid}"
        LOGGER.info(f"[{self.key}] API URL: {api_url}")
        
        try:
             resp = await _sync_to_async(
                requests.get,
                api_url,
                timeout=30
            )
             LOGGER.info(f"[{self.key}] Status Code: {resp.status_code}")
        except Exception as e:
            LOGGER.error(f"[{self.key}] HTTP error: {e}", exc_info=True)
            return None, "Failed to reach bypass service."

        if resp.status_code != 200:
             return None, f"Bypass service error {resp.status_code}"

        try:
            data = resp.json()
        except:
            return None, "Invalid JSON response."
            
        return self._norm(data)

    def _norm(self, data):
        # Handle Gofile Worker Response
        if isinstance(data, dict):
            # Log keys for debugging
            LOGGER.info(f"[{self.key}] Response Keys: {list(data.keys())}")
            
            # 1. Check for 'files' list (Priority as per user sample)
            files_list = data.get("files")
            # Fallback: check nested 'data' or 'result' for 'files'
            if not files_list:
                nested = data.get("data") or data.get("result")
                if isinstance(nested, dict):
                    files_list = nested.get("files")
            
            if files_list and isinstance(files_list, list) and len(files_list) > 0:
                first_file = files_list[0]
                if isinstance(first_file, dict):
                    return {
                        "title": first_file.get("name") or "Gofile",
                        "filesize": "N/A",
                        "format": "N/A",
                        "links": {"Direct Link": first_file.get("link")},
                        "service": self.key
                    }, None

            # 2. Check for generic 'url' or 'download_url'
            direct_url = data.get("url") or data.get("download_url") or data.get("directLink")
            if not direct_url:
                 # Check nested
                 nested = data.get("data") or data.get("result")
                 if isinstance(nested, dict):
                     direct_url = nested.get("url") or nested.get("link") or nested.get("downloadPage") or nested.get("directLink")
            
            if direct_url:
                 return {
                    "title": data.get("filename") or "Gofile",
                    "filesize": "N/A",
                    "format": "N/A",
                    "links": {"Direct Link": direct_url},
                    "service": self.key
                }, None

        # Fallback to parent normalization
        return super()._norm(data)
        
def _xlnk(root):
    out = {}

    for k, v in root.items():
        if not isinstance(v, dict):
            continue

        url = v.get("link") or v.get("url")
        name = v.get("name") or k

        if isinstance(url, str) and url.startswith(("http://", "https://")):
            out[_clean(name)] = url

        g = v.get("google_final")
        if isinstance(g, str) and g.startswith(("http://", "https://")):
            out[_clean("Google Drive")] = g

    raw = root.get("links")

    if isinstance(raw, dict):
        for k, v in raw.items():
            if isinstance(v, str) and v.startswith(("http://", "https://")):
                out[_clean(k)] = v
            elif isinstance(v, dict):
                u = v.get("url") or v.get("link")
                if isinstance(u, str) and u.startswith(("http://", "https://")):
                    out[_clean(k)] = u

    elif isinstance(raw, list):
        for i in raw:
            if not isinstance(i, dict):
                continue
            u = i.get("url") or i.get("link")
            n = i.get("type") or i.get("name") or "Link"
            if isinstance(u, str) and u.startswith(("http://", "https://")):
                out[_clean(n)] = u

    return out

def _clean(s):
    return str(s).replace("_", " ").replace("Link", "").strip().title() or "Link"

EchoByRegistry = {
    # By: HgBots
    "gdflix": EchoBypass("gdflix", "https://hgbots.vercel.app/bypaas/gd.php?url="),
    "hubdrive": EchoBypass("hubdrive", "https://hgbots.vercel.app/bypaas/hubdrive.php?url="),
    # By: PBX1 
    "extraflix": EchoBypass("extraflix", "https://pbx1botapi.vercel.app/api/extraflix?url="),
    "hubcloud": EchoBypass("hubcloud", "https://pbx1botapi.vercel.app/api/hubcloud?url="),
    "vcloud": EchoBypass("vcloud", "https://pbx1botapi.vercel.app/api/vcloud?url="),
    "hubcdn": EchoBypass("hubcdn", "https://pbx1botapi.vercel.app/api/hubcdn?url="),
    "driveleech": EchoBypass("driveleech", "https://pbx1botapi.vercel.app/api/driveleech?url="),
    "neo": EchoBypass("neo", "https://pbx1botapi.vercel.app/api/neo?url="),
    "gdrex": EchoBypass("gdrex", "https://pbx1botapi.vercel.app/api/gdrex?url="),
    "pixelcdn": EchoBypass("pixelcdn", "https://pbx1botapi.vercel.app/api/pixelcdn?url="),
    "extralink": EchoBypass("extralink", "https://pbx1botapi.vercel.app/api/extralink?url="),
    "luxdrive": EchoBypass("luxdrive", "https://pbx1botapi.vercel.app/api/luxdrive?url="),
    "nexdrive": EchoBypass("nexdrive", "https://pbx1botsapi2.vercel.app/api/nexdrive?url="),
    "hblinks": EchoBypass("hblinks", "https://pbx1botsapi2.vercel.app/api/hblinks?url="),
    "vegamovies": EchoBypass("vegamovies", "https://pbx1botsapi2.vercel.app/api/vega?url="),
    # By: NickUpdates
    "transfer_it": EchoBypass("transfer_it", "https://transfer-it-henna.vercel.app/post", method="POST"),
    # New additions
    "terabox": TeraboxBypass("terabox", "https://true-link-vercel-api.vercel.app/api/terabox/api?url="),
    "gofile": GofileBypass("gofile", "https://gofile.dd-bypassed.workers.dev/api"), # Updated logic
    "bypass": TeraboxBypass("bypass", "https://true-link-vercel-api.vercel.app/api/bypass?url="), # Reusing Terabox logic for generic bypass
}

CMD_TO_KEY = {
    a: k
    for k, v in {
        "gdflix": ["gdflix", "gd"],
        "hubdrive": ["hubdrive", "hd"],
        "extraflix": ["extraflix", "exf"],
        "hubcloud": ["hubcloud", "hc"],
        "vcloud": ["vcloud", "vc"],
        "hubcdn": ["hubcdn", "hcdn"],
        "driveleech": ["driveleech", "dleech"],
        "neo": ["neo", "neolinks"],
        "gdrex": ["gdrex", "gdex"],
        "pixelcdn": ["pixelcdn", "pcdn"],
        "extralink": ["extralink"],
        "luxdrive": ["luxdrive", "lxd"],
        "nexdrive": ["nexdrive", "nex"],
        "transfer_it": ["transfer_it", "ti"],
        "hblinks": ["hblinks", "hbl"],
        "vegamovies": ["vegamovies", "vega"],
        "terabox": ["terabox", "tb", "tf"],
        "gofile": ["gofile", "go", "gf"],
        "bypass": ["bypass", "bp"],
    }.items()
    for a in v
}

def _bysrv(cmd):
    return EchoByRegistry.get(CMD_TO_KEY.get(str(cmd).lower().lstrip("/")))

async def _bpinfo(cmd_name, target_url):
    # Smart Routing: if generic 'bypass' command is used, detect specific domains
    # and route to their optimized workers if available.
    if cmd_name in ["bypass", "bp"]:
        if "gofile.io" in target_url:
            cmd_name = "gofile"
            LOGGER.info("Smart Routing: /bypass detected Gofile link -> switching to gofile worker")
        elif "terabox" in target_url or "nephobox" in target_url or "4funbox" in target_url:
            cmd_name = "terabox"
            LOGGER.info("Smart Routing: /bypass detected Terabox link -> switching to terabox worker")

    srv = _bysrv(cmd_name)
    if not srv:
        return None, "Unknown platform."
    try:
        p = urlparse(target_url)
        if not p.scheme or not p.netloc:
            return None, "Invalid URL."
    except Exception:
        return None, "Invalid URL."
    return await srv.fetch(target_url)

def _bylinks(links):
    if not isinstance(links, dict) or not links:
        return "╰╴ No direct links found."

    grouped = any("|" in str(k) for k in links)
    out = []

    if not grouped:
        items = [
            (str(k).strip() or "Link", v.strip())
            for k, v in links.items()
            if isinstance(v, str) and v.strip().startswith(("http://", "https://"))
        ]
        for i, (k, v) in enumerate(items):
            out.append(
                f'{"╰╴" if i == len(items)-1 else "╞╴"} <b>{k}:</b> <a href="{v}">Click Here</a>'
            )
        return "\n".join(out) if out else "╰╴ No direct links found."

    groups = {}
    for k, v in links.items():
        if not isinstance(v, str):
            continue
        u = v.strip()
        if not u.startswith(("http://", "https://")):
            continue
        a, b = str(k).split("|", 1)
        groups.setdefault(a.strip(), []).append((b.strip(), u))

    for g, items in groups.items():
        out.append(f"\n<b>{g}</b>")
        for i, (k, v) in enumerate(items):
            out.append(
                f'{"╰╴" if i == len(items)-1 else "╞╴"} <b>{k}:</b> <a href="{v}">Click Here</a>'
            )

    return "\n".join(out).strip()

def _pack_html(results, page=1, per_page=10):
    total = len(results)
    max_page = (total - 1) // per_page + 1
    page = max(1, min(page, max_page))

    start = (page - 1) * per_page
    end = min(total, page * per_page)

    out = []
    for i, item in enumerate(results[start:end], start=1 + start):
        name = (
            item.get("file_name")
            or item.get("quality")
            or item.get("name")
            or "File"
        )

        size = item.get("file_size") or "N/A"

        if size != "N/A":
            out.append(f"<b>{i}. {name}</b> <code>({size})</code>")
        else:
            out.append(f"<b>{i}. {name}</b>")

        if "links" in item and isinstance(item["links"], list):
            for li in item["links"]:
                typ = li.get("type") or li.get("tag") or "Link"
                url = li.get("url")
                if isinstance(url, str) and url.startswith(("http://", "https://")):
                    out.append(f'   ╞ <b>{typ}</b>: <a href="{url}">Click Here</a>')

        elif "link" in item and isinstance(item["link"], str):
            url = item["link"]
            if url.startswith(("http://", "https://")):
                out.append(f'   ╰╴ <b>Open Link</b>: <a href="{url}">Click Here</a>')

        out.append("")

    txt = "\n".join(out).strip()
    nav = f"<b>Page: {page}/{max_page}</b> | <b>Total Files: {total}</b>"
    return txt, nav, page, max_page
