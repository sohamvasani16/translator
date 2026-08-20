import os
import urllib.request
import logging

logger = logging.getLogger("font_manager")
logger.setLevel(logging.INFO)

FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")

# Map target language codes to font filenames and download URLs
FONT_MAP = {
    "hi": {
        "file": "NotoSansDevanagari-Regular.ttf",
        "url": "https://raw.githubusercontent.com/notofonts/noto-fonts/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf",
        "alias": "noto-devanagari"
    },
    "mr": {
        "file": "NotoSansDevanagari-Regular.ttf",
        "url": "https://raw.githubusercontent.com/notofonts/noto-fonts/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf",
        "alias": "noto-devanagari"
    },
    "ne": {
        "file": "NotoSansDevanagari-Regular.ttf",
        "url": "https://raw.githubusercontent.com/notofonts/noto-fonts/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf",
        "alias": "noto-devanagari"
    },
    "gu": {
        "file": "NotoSansGujarati-Regular.ttf",
        "url": "https://raw.githubusercontent.com/notofonts/noto-fonts/main/hinted/ttf/NotoSansGujarati/NotoSansGujarati-Regular.ttf",
        "alias": "noto-gujarati"
    },
    "ar": {
        "file": "NotoSansArabic-Regular.ttf",
        "url": "https://raw.githubusercontent.com/notofonts/noto-fonts/main/hinted/ttf/NotoSansArabic/NotoSansArabic-Regular.ttf",
        "alias": "noto-arabic"
    },
    "bn": {
        "file": "NotoSansBengali-Regular.ttf",
        "url": "https://raw.githubusercontent.com/notofonts/noto-fonts/main/hinted/ttf/NotoSansBengali/NotoSansBengali-Regular.ttf",
        "alias": "noto-bengali"
    },
    "ta": {
        "file": "NotoSansTamil-Regular.ttf",
        "url": "https://raw.githubusercontent.com/notofonts/noto-fonts/main/hinted/ttf/NotoSansTamil/NotoSansTamil-Regular.ttf",
        "alias": "noto-tamil"
    },
    "te": {
        "file": "NotoSansTelugu-Regular.ttf",
        "url": "https://raw.githubusercontent.com/notofonts/noto-fonts/main/hinted/ttf/NotoSansTelugu/NotoSansTelugu-Regular.ttf",
        "alias": "noto-telugu"
    },
    "default": {
        "file": "NotoSans-Regular.ttf",
        "url": "https://raw.githubusercontent.com/notofonts/noto-fonts/main/hinted/ttf/NotoSans/NotoSans-Regular.ttf",
        "alias": "noto-sans"
    }
}

class FontManager:
    def __init__(self, fonts_dir: str = FONTS_DIR):
        self.fonts_dir = fonts_dir
        os.makedirs(self.fonts_dir, exist_ok=True)

    def get_font_for_language(self, lang_code: str):
        """
        Returns (font_path, font_alias) for the given language code.
        Downloads font on-demand if not present locally.
        """
        key = lang_code.lower()
        if key not in FONT_MAP:
            key = "default"

        font_info = FONT_MAP[key]
        font_filename = font_info["file"]
        font_path = os.path.join(self.fonts_dir, font_filename)
        font_alias = font_info["alias"]

        if not os.path.exists(font_path):
            url = font_info["url"]
            logger.info(f"Downloading Unicode font for script '{lang_code}' from {url}...")
            try:
                urllib.request.urlretrieve(url, font_path)
                logger.info(f"Successfully downloaded font: {font_path}")
            except Exception as e:
                logger.error(f"Failed to download font from {url}: {e}")
                # Fall back to default font if available
                default_path = os.path.join(self.fonts_dir, FONT_MAP["default"]["file"])
                if os.path.exists(default_path):
                    return default_path, FONT_MAP["default"]["alias"]
                return None, "helv"

        return font_path, font_alias

font_manager = FontManager()
