import os
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

__all__ = ["generate_helldiver_banner"]


def generate_helldiver_banner(
    name: str = "Helldiver",
    title: str = "",
    level: int | str = 0,
    shipname1: str = "SES Adjudicator",
    shipname2: str = "of Allegiance",
    profile: Optional[str] = None,
    base_dir: Optional[str] = None,
    font_path: Optional[str] = None,
    size: Tuple[int, int] = (640, 180),
    save_to: Optional[str] = None,
) -> Image.Image:
    def _load_font(fp: Optional[str], size_px: int) -> ImageFont.FreeTypeFont:
        try:
            if fp and os.path.isfile(fp):
                return ImageFont.truetype(fp, size_px)
        except Exception:
            pass
        try:
            base = os.path.dirname(os.path.abspath(__file__))
            default_font = os.path.join(base, "MiscItems", "Fonts", "Insignia.ttf")
            if os.path.isfile(default_font):
                return ImageFont.truetype(default_font, size_px)
        except Exception:
            pass
        return ImageFont.load_default()

    def _resolve_profile_path(profile_in: Optional[str], base: Optional[str]) -> Optional[str]:
        if not profile_in:
            return None
        profile_str = str(profile_in).strip()
        if os.path.isfile(profile_str):
            return profile_str
        search_dirs = []
        if base:
            search_dirs.append(os.path.join(base, "media", "profile_pictures"))
        script_dir = os.path.dirname(os.path.abspath(__file__))
        search_dirs.append(os.path.join(script_dir, "media", "profile_pictures"))
        for d in search_dirs:
            p = os.path.join(d, f"{profile_str}.png")
            if os.path.isfile(p):
                return p
        return None

    W, H = size
    img = Image.new("RGBA", (W, H), (37, 37, 38, 0))
    draw = ImageDraw.Draw(img)

    # Gradient background
    for y in range(H):
        shade = 37 + int((y / max(1, H - 1)) * 18)
        draw.line([(0, y), (W, y)], fill=(shade, shade, shade, 255))

    # Profile picture on the left
    try:
        p_path = _resolve_profile_path(profile, base_dir)
        if p_path:
            p_img = Image.open(p_path).convert("RGBA")
            side = min(140, H - 20)
            p_img = p_img.resize((side, side), Image.LANCZOS)
            img.paste(p_img, (20, (H - side) // 2), p_img)
    except Exception:
        pass

    # Fonts
    font_big = _load_font(font_path, 36)
    font_small = _load_font(font_path, 24)

    # Text
    try:
        level_val = int(level)
    except Exception:
        level_val = 0

    ship = f"{shipname1} {shipname2}".strip()

    # Text positions (to the right of profile area)
    text_x = 180
    draw.text((text_x, 48), str(name), fill=(255, 255, 255, 230), font=font_big)
    draw.text((text_x, 90), f"Level {level_val} | {title}".strip(), fill=(220, 220, 220, 230), font=font_small)
    draw.text((text_x, 122), ship, fill=(200, 200, 200, 210), font=font_small)

    if save_to:
        os.makedirs(os.path.dirname(os.path.abspath(save_to)), exist_ok=True)
        img.save(save_to, format="PNG")

    return img
