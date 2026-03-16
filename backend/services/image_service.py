import os
from typing import List, Dict, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont
from bidi.algorithm import get_display

from models.schemas import TextConfig

# Directories searched for font files (ordered by priority)
SYSTEM_FONT_DIRS: List[str] = [
    "C:\\Windows\\Fonts",
    os.path.expanduser("~/AppData/Local/Microsoft/Windows/Fonts"),
    "/usr/share/fonts",
    "/usr/local/share/fonts",
    os.path.expanduser("~/Library/Fonts"),
    "/System/Library/Fonts",
    "/Library/Fonts",
]

# Hebrew-capable fonts to surface first in the font list
PREFERRED_FONTS = [
    "Alef",
    "Rubik",
    "Assistant",
    "Frank",
    "David",
    "Miriam",
    "Tahoma",
    "Arial",
    "Calibri",
    "Segoe UI",
    "Times New Roman",
]


class ImageService:
    def __init__(self, fonts_dir: str):
        self.fonts_dir = fonts_dir
        os.makedirs(fonts_dir, exist_ok=True)
        self._font_cache: Dict[str, ImageFont.FreeTypeFont] = {}
        self._available_fonts: Optional[List[Dict]] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def get_available_fonts(self) -> List[Dict]:
        """Return all font files found, custom fonts first."""
        if self._available_fonts is not None:
            return self._available_fonts

        found: Dict[str, Dict] = {}

        # Custom fonts bundled in backend/fonts/
        for fname in os.listdir(self.fonts_dir):
            if fname.lower().endswith((".ttf", ".otf")):
                name = os.path.splitext(fname)[0]
                path = os.path.join(self.fonts_dir, fname)
                found[name.lower()] = {
                    "name": name,
                    "path": path,
                    "source": "custom",
                }

        # System fonts
        for sys_dir in SYSTEM_FONT_DIRS:
            if not os.path.isdir(sys_dir):
                continue
            for root, _, files in os.walk(sys_dir):
                for file in files:
                    if file.lower().endswith((".ttf", ".otf")):
                        key = os.path.splitext(file)[0].lower()
                        if key not in found:
                            found[key] = {
                                "name": os.path.splitext(file)[0],
                                "path": os.path.join(root, file),
                                "source": "system",
                            }

        def sort_key(f: Dict) -> Tuple:
            if f["source"] == "custom":
                return (0, "")
            name_lower = f["name"].lower()
            for i, pref in enumerate(PREFERRED_FONTS):
                if pref.lower() in name_lower:
                    return (1, str(i).zfill(3))
            return (2, f["name"].lower())

        self._available_fonts = sorted(found.values(), key=sort_key)
        return self._available_fonts

    def generate_image(
        self,
        template_path: str,
        name: str,
        output_path: str,
        text_config: TextConfig,
    ) -> None:
        """Render *name* onto *template_path* and save to *output_path*."""
        img = Image.open(template_path).convert("RGBA")
        img_w, img_h = img.size

        # Text layer (transparent background)
        txt_layer = Image.new("RGBA", (img_w, img_h), (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)

        display_text = self._prepare_hebrew(name)
        font = self._get_font(text_config.font_name, text_config.font_size)
        fill = self._hex_to_rgba(text_config.font_color)

        # Resolve position (prefer percent-based)
        if text_config.x_percent is not None and text_config.y_percent is not None:
            x = int(text_config.x_percent * img_w)
            y = int(text_config.y_percent * img_h)
        else:
            x, y = text_config.x, text_config.y

        # Adjust x for alignment
        bbox = draw.textbbox((0, 0), display_text, font=font)
        text_w = bbox[2] - bbox[0]
        if text_config.align == "center":
            x -= text_w // 2
        elif text_config.align == "right":
            x -= text_w

        # Draw with optional stroke
        stroke = text_config.stroke_width or 0
        if stroke > 0:
            stroke_fill = self._hex_to_rgba(text_config.stroke_color or "#000000")
            draw.text(
                (x, y),
                display_text,
                font=font,
                fill=fill,
                stroke_width=stroke,
                stroke_fill=stroke_fill,
            )
        else:
            draw.text((x, y), display_text, font=font, fill=fill)

        result = Image.alpha_composite(img, txt_layer)

        if output_path.lower().endswith((".jpg", ".jpeg")):
            result.convert("RGB").save(output_path, "JPEG", quality=95)
        else:
            result.save(output_path, "PNG")

    def get_image_dimensions(self, path: str) -> Tuple[int, int]:
        with Image.open(path) as img:
            return img.size

    # ── Internals ─────────────────────────────────────────────────────────────

    def _prepare_hebrew(self, text: str) -> str:
        """Apply BiDi algorithm so Pillow renders Hebrew RTL correctly."""
        try:
            return get_display(text)
        except Exception:
            return text

    def _get_font(self, font_name: str, size: int) -> ImageFont.FreeTypeFont:
        cache_key = f"{font_name}|{size}"
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        fonts = self.get_available_fonts()

        # Exact match
        for info in fonts:
            if info["name"].lower() == font_name.lower():
                f = self._load_font(info["path"], size)
                if f:
                    self._font_cache[cache_key] = f
                    return f

        # Partial match
        for info in fonts:
            if font_name.lower() in info["name"].lower():
                f = self._load_font(info["path"], size)
                if f:
                    self._font_cache[cache_key] = f
                    return f

        # Fall back to any available font
        for info in fonts:
            f = self._load_font(info["path"], size)
            if f:
                self._font_cache[cache_key] = f
                return f

        return ImageFont.load_default()

    @staticmethod
    def _load_font(path: str, size: int) -> Optional[ImageFont.FreeTypeFont]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            return None

    @staticmethod
    def _hex_to_rgba(hex_color: str) -> Tuple[int, int, int, int]:
        h = hex_color.lstrip("#")
        if len(h) == 6:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return (r, g, b, 255)
        if len(h) == 8:
            r, g, b, a = (int(h[i : i + 2], 16) for i in (0, 2, 4, 6))
            return (r, g, b, a)
        return (0, 0, 0, 255)
