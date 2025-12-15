from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import random

class echo(object):
    ABC = """<b><u>POSTER SCRAPPER BOT</u></b>
<blockquote expandable>
<b>This bot scrapes posters from various OTT platforms and bypasses direct links from cloud sites.</b>
</blockquote>
<b>✺ Commands</b>
<blockquote expandable>
/poster - Scrape any movie/show poster
/overlap - Overlay a logo on a poster
/imdb - Search movie/series on IMDb
/anime - Search Anime on Anilist
/gdflix - Bypass GDFlix links
/hubcloud - Bypass HubCloud links
/hubdrive - Bypass Hubdrive links
/transfer_it - Bypass Transfer.it links
/prime - Prime Video poster
/zee5 - ZEE5 poster
/appletv - Apple TV+ poster
/airtel - Airtel Xstream poster
/sunnxt - Sun NXT poster
/aha - Aha Video poster
/iqiyi - iQIYI poster
/wetv - WeTV poster
/shemaroo - ShemarooMe poster
/bms - BookMyShow poster
/plex - Plex TV poster
/adda - Addatimes poster
/stage - Stage poster
/netflix - Netflix poster
/mxplayer - MX Player poster
/hotstar - Disney+ Hotstar poster
/sonyliv - SonyLIV poster
/voot - Voot poster
/jiocinema - JioCinema poster
/youtube - YouTube thumbnail
/instagram - Instagram thumbnail
/facebook - Facebook thumbnail
/tiktok - TikTok thumbnail
</blockquote>
<blockquote expandable>
<b>Examples</b>
<code>/poster Avatar</code>
<code>/poster Avatar 2022</code>
<code>/poster Avatar: The Way of Water</code>
</blockquote>
<blockquote expandable>
<b>NOTE:</b> Bot can filter results by keywords and release year.
</blockquote>
<blockquote expandable>
<b>Bot By</b> @tellycloudbots   
</blockquote>
"""
    IMG = "https://ibb.co/4ZmgW54D"
    
    # Telegram Message Effects - All popular effects
    EFFECTS = {
        "fire": 5104841245755180586,           # 🔥 Fire
        "like": 5107584321108051014,           # 👍 Like/Heart
        "dislike": 5104858069142078462,        # 👎 Dislike
        "love": 5159385139981059251,           # ❤️ Love/Hearts
        "celebrate": 5046509860389126442,      # 🎉 Celebrate/Party
        "fireworks": 5046589136895476101,      # 🎆 Fireworks
        "poop": 5046446160663208973,           # 💩 Poop
        "mindblown": 5159385139981059251,      # 🤯 Mind Blown
    }
    
    # For backward compatibility
    EFCT = EFFECTS["fire"]  # Default to fire effect
    
    @classmethod
    def get_random_effect(cls):
        """Get a random Telegram message effect ID."""
        return random.choice(list(cls.EFFECTS.values()))
    
    ST_BTN = "Repo"
    REPO = "https://t.me/tellycloudbots"
    UP_BTN = "Updates"
    UPDTE = "https://t.me/tellycloudbots"
    SP_BTN = "Support Group"
    SP_GR = "https://t.me/tellybypassgrp"

