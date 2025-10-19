"""Centralized image and icon loading/manipulation helpers.

This module exposes functions used throughout the UI to load and prepare
images for display. Each function returns an ImageTk.PhotoImage or None
on failure. The functions avoid side-effects other than reading files.
"""
import os
import logging
import random
from datetime import datetime
from typing import Optional, Tuple

from PIL import Image, ImageTk, ImageDraw

from runtime_paths import app_path


def _composite_bg(pil_img: Image.Image, bg_color=(37, 37, 38, 255)) -> Image.Image:
    """Composite the image onto a uniform background to avoid haloing."""
    try:
        background = Image.new('RGBA', pil_img.size, bg_color)
        return Image.alpha_composite(background, pil_img)
    except Exception:
        return pil_img


def pil_to_photo(pil_img: Image.Image) -> ImageTk.PhotoImage:
    pil_img = _composite_bg(pil_img)
    return ImageTk.PhotoImage(pil_img)


def load_gw_icon() -> Optional[ImageTk.PhotoImage]:
    try:
        path = os.path.join('media', 'SyInt', 'gw_icon.png')
        pil = Image.open(path).convert('RGBA')
        pil = pil.resize((max(1, pil.width // 55), max(1, pil.height // 55)), Image.LANCZOS)
        return pil_to_photo(pil)
    except Exception as e:
        logging.error(f"image_utils: failed to load gw icon: {e}")
        return None


def load_profile_preview(profile_name: str, size: Tuple[int, int] = (120, 120)) -> Optional[ImageTk.PhotoImage]:
    try:
        img_path = os.path.join('media', 'profile_pictures', f"{profile_name}.png")
        pil = Image.open(img_path).convert('RGBA')
        pil = pil.resize(size, Image.LANCZOS)
        return pil_to_photo(pil)
    except Exception as e:
        logging.error(f"image_utils: failed to load profile preview '{profile_name}': {e}")
        return None


def load_sector_placeholder(size: Optional[Tuple[int, int]] = None) -> Optional[ImageTk.PhotoImage]:
    try:
        path = 'sector-placeholder.png'
        pil = Image.open(path).convert('RGBA')
        if size:
            pil = pil.resize(size, Image.LANCZOS)
        return pil_to_photo(pil)
    except Exception as e:
        logging.error(f"image_utils: failed to load sector placeholder: {e}")
        return None


def load_planet_preview(biome_name: str) -> Optional[ImageTk.PhotoImage]:
    try:
        img_path = os.path.join('media', 'planets', f"{biome_name}.png")
        pil = Image.open(img_path).convert('RGBA')
        return pil_to_photo(pil)
    except Exception as e:
        logging.error(f"image_utils: failed to load planet preview '{biome_name}': {e}")
        return None


def load_sector_preview(sector_name: str, enemy_type: str) -> Optional[ImageTk.PhotoImage]:
    try:
        img_path = os.path.join('media', 'sectors', f"{sector_name}.png")
        pil = Image.open(img_path).convert('RGBA')

        # Replace near-white pixels with chroma color depending on enemy type
        enemy_colors = {
            "Automatons": "#ff6d6d",
            "Terminids": "#ffc100",
            "Illuminate": "#8960ca",
            "Observing": "#41639C"
        }
        chroma_color = enemy_colors.get(enemy_type, "#ffffff")
        data = pil.getdata()
        new_data = []
        r = int(chroma_color[1:3], 16)
        g = int(chroma_color[3:5], 16)
        b = int(chroma_color[5:7], 16)
        for item in data:
            if item[0] > 240 and item[1] > 240 and item[2] > 240:
                new_data.append((r, g, b, item[3]))
            else:
                new_data.append(item)
        pil.putdata(new_data)
        return pil_to_photo(pil)
    except Exception as e:
        logging.error(f"image_utils: failed to load sector preview '{sector_name}': {e}")
        return None


def load_row_image(img_path: str, size: Tuple[int, int] = (60, 60)) -> Optional[ImageTk.PhotoImage]:
    try:
        if not img_path or not os.path.exists(img_path):
            return None
        pil = Image.open(img_path).convert('RGBA')
        pil = pil.resize(size, Image.LANCZOS)
        return pil_to_photo(pil)
    except Exception as e:
        logging.error(f"image_utils: failed to load row image '{img_path}': {e}")
        return None


def load_settings_button_images() -> Tuple[Optional[ImageTk.PhotoImage], Optional[ImageTk.PhotoImage]]:
    try:
        def _load(path):
            pil = Image.open(path).convert('RGBA')
            pil = pil.resize((max(1, pil.width // 4), max(1, pil.height // 4)), Image.LANCZOS)
            return pil_to_photo(pil)

        default = _load(os.path.join('media', 'SyInt', 'SettingsButton.png'))
        hover = _load(os.path.join('media', 'SyInt', 'SettingsButtonHover.png'))
        return default, hover
    except Exception as e:
        logging.error(f"image_utils: failed to load settings button images: {e}")
        return None, None


def load_biome_banner(app, banner_type_selected: str, planet_name: str) -> Optional[ImageTk.PhotoImage]:
    """Load and produce a biome/subfaction/helldiver banner for a planet.

    This mirrors the original logic in gui_components but packaged here.
    """
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))

        pil_banner = None
        # Subfaction banner
        if banner_type_selected == "Subfaction Banner":
            subfaction = (getattr(app, 'subfaction_type', None) and app.subfaction_type.get()) or "Unknown"
            subf_clean = subfaction.replace(" ", "_")
            candidates = [
                os.path.join(base_dir, 'media', 'subfaction_banner', f"{subfaction}.png"),
                os.path.join(base_dir, 'media', 'subfaction_banner', f"{subf_clean}.png"),
                os.path.join(base_dir, 'media', 'subfactions', f"{subf_clean}.png"),
            ]
            for path in candidates:
                if os.path.isfile(path):
                    img = Image.open(path).convert('RGBA')
                    if 'media/subfactions' in path.replace('\\', '/'):
                        W, H = 640, 180
                        canvas = Image.new('RGBA', (W, H), (37, 37, 38, 0))
                        draw = ImageDraw.Draw(canvas)
                        for y in range(H):
                            shade = 37 + int((y / max(1, H - 1)) * 18)
                            draw.line([(0, y), (W, y)], fill=(shade, shade, shade, 255))
                        target_h = H - 40
                        ratio = target_h / max(1, img.height)
                        icon_img = img.resize((int(img.width * ratio), target_h), Image.LANCZOS)
                        x = (W - icon_img.width) // 2
                        y = (H - icon_img.height) // 2
                        canvas.paste(icon_img, (x, y), icon_img)
                        pil_banner = canvas
                    else:
                        pil_banner = img
                    break

        # Helldiver banner
        elif banner_type_selected == "Helldiver Banner":
            try:
                idx = random.randint(1, 6)
                candidates = [
                    os.path.join(base_dir, 'media', 'helldiver_banner', f'helldiver{idx}.png'),
                    os.path.join(base_dir, 'media', 'helldivers', f'helldiver{idx}.png'),
                    os.path.join(base_dir, f'helldiver{idx}.png'),
                ]
                hld_path = next((p for p in candidates if os.path.isfile(p)), None)
                if hld_path:
                    img = Image.open(hld_path).convert('RGBA')
                    W, H = 460, 148
                    canvas = Image.new('RGBA', (W, H), (37, 37, 38, 0))
                    x = (W - img.width) // 2
                    y = (H - img.height) // 2
                    canvas.paste(img, (x, y), img)
                    pil_banner = canvas
            except Exception:
                pil_banner = None

        # Default biome banner
        if pil_banner is None:
            biome_name = planet_name or 'Mars'
            path = os.path.join(base_dir, 'media', 'biome_banners', f"{biome_name}.png")
            if not os.path.isfile(path):
                path = os.path.join(base_dir, 'media', 'biome_banners', 'Mars.png')
            pil_banner = Image.open(path).convert('RGBA')

        # Overlay HVT if present
        try:
            hvt_name = (getattr(app, 'hvt_type', None) and app.hvt_type.get()) or ""
            if hvt_name and hvt_name != "No HVTs":
                hvt_norm = hvt_name.replace(" ", "")
                hvt_underscored = hvt_name.replace(" ", "_")
                candidates = [
                    os.path.join(base_dir, "media", "overlays", f"{hvt_underscored}_Overlay.png"),
                    os.path.join(base_dir, "media", "overlays", f"{hvt_norm}_Overlay.png"),
                    os.path.join(base_dir, "media", "overlays", f"{hvt_underscored}.png"),
                ]
                if hvt_name == "Hive Lords":
                    candidates.append(os.path.join(base_dir, "media", "overlays", "Hive_Lords_Overlay.png"))
                    candidates.append(os.path.join(base_dir, "Hive_Lords_Overlay.png"))
                overlay_path = next((p for p in candidates if os.path.isfile(p)), None)
                if overlay_path:
                    hvt_img = Image.open(overlay_path).convert('RGBA')
                    if hvt_img.size != pil_banner.size:
                        hvt_img = hvt_img.resize(pil_banner.size, Image.LANCZOS)
                    pil_banner.paste(hvt_img, (0, 0), hvt_img)
        except Exception:
            pass

        pil_banner = _composite_bg(pil_banner)
        return pil_to_photo(pil_banner)
    except Exception as e:
        logging.error(f"image_utils: failed to load biome banner for {planet_name}: {e}")
        return None
