from pyrogram.enums import ChatType
import uuid
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from .. import LOGGER
from ..helper.ott import _extract_url_from_message
from ..helper.bypsr import _bp_info, _bp_links
from ..helper.utils.msg_util import send_message, edit_message
from ..helper.utils.xtra import _task
from config import Config

from echobotz.eco import echo
from ..helper.utils.btns import EchoButtons

def _sexy(name):
    if not name:
        return None
    name = str(name).lower()
    mapping = {
        "gdflix": "GDFlix",
        "hubcloud": "HubCloud",
        "hubdrive": "HubDrive",
        "transfer_it": "Transfer.it",
    }
    return mapping.get(name, name.title())

_BP_CACHE = {}

async def _bp_page_cb(client, callback_query):
    try:
        _, uid, page = callback_query.data.split("_")
        page = int(page)
        
        data = _BP_CACHE.get(uid)
        if not data:
            return await callback_query.answer("Session expired or invalid.", show_alert=True)
            
        header_block = data["header"]
        meta_block = data["meta"]
        links_dict = data["links"]
        original_url = data["url"]
        
        # Pagination logic
        chunk_size = 5  # Reduced to prevent ENTITIES_TOO_LONG
        items = list(links_dict.items())
        total_items = len(items)
        total_pages = (total_items + chunk_size - 1) // chunk_size
        
        if page < 1: page = 1
        if page > total_pages: page = total_pages
        
        start = (page - 1) * chunk_size
        end = start + chunk_size
        current_chunk = dict(items[start:end])
        
        links_block = _bp_links(current_chunk)
        
        text = Config.BYPASS_TEMPLATE.format(
            header_block=header_block,
            meta_block=meta_block,
            links_block=links_block,
            original_url=original_url,
        )
        
        buttons = []
        # Nav buttons
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"bp_page_{uid}_{page-1}"))
        
        nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
        
        if page < total_pages:
            nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"bp_page_{uid}_{page+1}"))
            
        if nav_row:
            buttons.append(nav_row)
            
        # Add Close button or others?
        # Re-add repo buttons?
        btns = EchoButtons()
        btns.url_button(echo.UP_BTN, echo.UPDTE)
        btns.url_button(echo.ST_BTN, echo.REPO)
        repo_btns = btns.build(2)
        if repo_btns and hasattr(repo_btns, "inline_keyboard"):
            for row in repo_btns.inline_keyboard:
                buttons.append(row)

        await callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        LOGGER.error(f"bp_page_cb error: {e}", exc_info=True)
        await callback_query.answer("Error during pagination.", show_alert=True)

# Main command update
@_task
async def _bypass_cmd(client, message):
    try:
        if message.chat.type not in (ChatType.PRIVATE, ChatType.GROUP, ChatType.SUPERGROUP):
            return
        if not getattr(message, "command", None) or not message.command:
            return

        cmd_name = message.command[0].lstrip("/").split("@")[0].lower()
        
        # New: Support multiple URLs
        from ..helper.ott import _extract_all_urls_from_message
        target_urls = _extract_all_urls_from_message(message)

        if not target_urls:
            return await send_message(
                message,
                (
                    "<b>Usage:</b>\n"
                    f"/{cmd_name} &lt;url&gt;  <i>or</i>\n"
                    f"Reply to a URL with <code>/{cmd_name}</code>"
                ),
            )

        wait_msg = await send_message(
            message,
            f"<i>Processing {len(target_urls)} link(s)...</i>",
        )

        if len(target_urls) > 1:
            from ..helper.bypsr import _bp_bulk_info
            
            info, err = await _bp_bulk_info(target_urls)
            if err:
                return await edit_message(
                    wait_msg,
                    f"<b>Error:</b> <code>{err}</code>",
                )
            
            # Formatting bulk response
            lines = []
            success_count = 0
            fail_count = 0
            total_count = len(target_urls)
            
            # Ensure info is a list and has same length as target_urls to map correctly
            results = info if isinstance(info, list) else [info] * len(target_urls) # Fallback
            
            for i, (orig_url, res) in enumerate(zip(target_urls, results), 1):
                # Paginator check: specific character limit to avoid ENTITIES_TOO_LONG
                if len("\n".join(lines)) > 3000:
                    lines.append(f"\n<i>...and {total_count - (i-1)} more links (truncated)</i>")
                    break

                lines.append(f"<b>Link {i}</b>")
                lines.append(f"<a href=\"{orig_url}\">Original Link</a>")
                
                bypass_url = None
                if isinstance(res, dict):
                    if res.get("success"):
                        bypass_url = res.get("url") or res.get("link")
                    else:
                        # Try to find a url anyway if success is missing but url exists
                        bypass_url = res.get("url") or res.get("link")
                elif isinstance(res, str) and res.startswith("http"):
                    bypass_url = res
                
                if bypass_url:
                    lines.append(f"<a href=\"{bypass_url}\">Download Link</a>")
                    success_count += 1
                else:
                    lines.append("<i>Failed to bypass</i>")
                    fail_count += 1
                
                lines.append("") # Empty line between items

            stats = [
                f"Total Link = {total_count}",
                f"Bypass Link = {success_count}",
                f"Failed Link = {fail_count}"
            ]
            
            text = "\n".join(lines) + "\n" + "\n".join(stats)
            
            if len(text) > 4096:
                text = text[:4000] + "\n\n... (truncated)"
            
            await edit_message(wait_msg, text)
            return

        # Single URL case (existing logic)
        target_url = target_urls[0]
        
        info, err = await _bp_info(cmd_name, target_url)
        if err:
            return await edit_message(
                wait_msg,
                f"<b>Error:</b> <code>{err}</code>",
            )

        # NEW: Handle Multi-Result Response (e.g. VegaMovies returning list of qualities)
        if isinstance(info, list):
            # Format similar to bulk, but maybe more detailed with Titles
            lines = []
            for i, item in enumerate(info, 1):
                 # Paginator check
                 if len("\n".join(lines)) > 3000:
                     lines.append(f"\n<i>...and {len(info) - (i-1)} more results (truncated)</i>")
                     break

                 # Item is a normalized dict from _bp_norm
                 title = item.get("title", f"Result {i}")
                 size = item.get("filesize", "N/A")
                 links = item.get("links", {})
                 
                 lines.append(f"<b>{i}. {title}</b> [{size}]")
                 for lbl, url in links.items():
                     lines.append(f"<a href=\"{url}\">{lbl}</a>")
                 lines.append("")
                 
            text = f"<b>Found {len(info)} Results:</b>\n\n" + "\n".join(lines)
            if len(text) > 4096:
                text = text[:4000] + "\n... (truncated)"
            
            await edit_message(wait_msg, text)
            return

        service = _sexy(info.get("service"))
        title = info.get("title")
        filesize = info.get("filesize")
        file_format = info.get("format")

        header_lines = []
        if service:
            header_lines.append(f"<b>✺Source:</b> {service}")
        if title and title != "N/A":
            if header_lines:
                header_lines.append("")
            header_lines.append("<b>File:</b>")
            header_lines.append(f"<blockquote>{title}</blockquote>")
        header_block = "\n".join(header_lines) if header_lines else ""
        meta_lines = []
        if filesize and filesize != "N/A":
            meta_lines.append(f"<b>Size:</b> {filesize}")
        if file_format and file_format != "N/A":
            meta_lines.append(f"<b>Format:</b> {file_format}")
        meta_block = ("\n".join(meta_lines) + "\n\n") if meta_lines else ""
        
        links_dict = info.get("links") or {}
        
        # Determine if we need pagination (limit > 5 links to avoid ENTITIES_TOO_LONG)
        if len(links_dict) > 5:
            uid = str(uuid.uuid4())
            _BP_CACHE[uid] = {
                "header": header_block,
                "meta": meta_block,
                "links": links_dict,
                "url": target_url
            }
            
            # Show first page (5 links max)
            items = list(links_dict.items())
            first_chunk = dict(items[:5])
            links_block = _bp_links(first_chunk)
            
            text = Config.BYPASS_TEMPLATE.format(
                header_block=header_block,
                meta_block=meta_block,
                links_block=links_block,
                original_url=target_url,
            )
            
            buttons = [
                [
                    InlineKeyboardButton("Next ➡️", callback_data=f"bp_page_{uid}_2")
                ]
            ]
            
            # Add repo buttons
            btns = EchoButtons()
            btns.url_button(echo.UP_BTN, echo.UPDTE)
            btns.url_button(echo.ST_BTN, echo.REPO)
            repo_btns = btns.build(2)
            if repo_btns and hasattr(repo_btns, "inline_keyboard"):
                for row in repo_btns.inline_keyboard:
                    buttons.append(row)
                    
            await edit_message(
                wait_msg,
                text,
                buttons=InlineKeyboardMarkup(buttons),
            )
        else:
            links_block = _bp_links(links_dict)
            text = Config.BYPASS_TEMPLATE.format(
                header_block=header_block,
                meta_block=meta_block,
                links_block=links_block,
                original_url=target_url,
            )
            btns = EchoButtons()
            btns.url_button(echo.UP_BTN, echo.UPDTE)
            btns.url_button(echo.ST_BTN, echo.REPO)
            buttons = btns.build(2)
            await edit_message(
                wait_msg,
                text,
                buttons=buttons,
            )
            
    except Exception as e:
        LOGGER.error(f"bypass_cmd error: {e}", exc_info=True)
        try:
            await send_message(
                message,
                "<b>Error:</b> <code>Something went wrong while bypassing the URL.</code>",
            )
        except Exception:
            pass
