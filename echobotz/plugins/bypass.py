from pyrogram.enums import ChatType

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
            
            # Using bulk API
            # Ideally we only use bulk API if the command is /bypass or /bp ??
            # But the user asked for bulk link handling generally.
            # If the user uses specific command like /terabox with multiple links, 
            # we should technically map each one or use bulk if supported?
            # User specifically asked for /bypass bulk logic. 
            # For now, if multiple links, we try bulk API if command is general bypass, 
            # Or we can iterate if it's specific?
            # The prompt says: "and bulk link ho to api post par work karega ... endpoint: /api/bypass-bulk"
            # It seems this endpoint is for generic bulk bypass.
            
            # Let's try _bp_bulk_info for all multiple link cases.
            
            info, err = await _bp_bulk_info(target_urls)
            if err:
                return await edit_message(
                    wait_msg,
                    f"<b>Error:</b> <code>{err}</code>",
                )
            
            # Formatting bulk response
            # Formatting bulk response
            lines = []
            success_count = 0
            fail_count = 0
            total_count = len(target_urls)
            
            # Ensure info is a list and has same length as target_urls to map correctly
            results = info if isinstance(info, list) else [info] * len(target_urls) # Fallback
            
            for i, (orig_url, res) in enumerate(zip(target_urls, results), 1):
                lines.append(f"<b>Link {i}</b>")
                lines.append(f"Original Link: {orig_url}")
                
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
                    lines.append(f"<a href=\"{bypass_url}\">Click Here</a>")
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
        # Update wait message to show the single URL logic if needed, but it's fine.
        
        info, err = await _bp_info(cmd_name, target_url)
        if err:
            return await edit_message(
                wait_msg,
                f"<b>Error:</b> <code>{err}</code>",
            )

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
        links_block = _bp_links(info.get("links") or {})
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
