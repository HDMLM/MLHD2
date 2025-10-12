import os
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
import json
import pandas as pd
import unicodedata

__all__ = ["generate_helldiver_banner"]


def generate_helldiver_banner(
    name: str = "Helldiver",
    title: str = "",
    level: int | str = 0,
    shipname1: str = "SES Adjudicator",
    shipname2: str = "of Allegiance",
    profile: Optional[str] = None,
    base_dir: Optional[str] = None,
    size: Tuple[int, int] = (640, 180),
    save_to: Optional[str] = None,
    extra_images: Optional[list[str]] = None,
    # QR: subtle-but-scannable overlay in the bottom-right corner
    qr_data: Optional[str] = "https://hdmlm.github.io/MLHD2",
    qr_opacity: int = 120,
) -> Image.Image:

    def _load_font(size_px: int) -> ImageFont.FreeTypeFont:
        """Load Insignia font if bundled; fallback to default font."""
        try:
            base = os.path.dirname(os.path.abspath(__file__))
            default_font = os.path.join(base, "MiscItems", "Fonts", "Insignia.ttf")
            if os.path.isfile(default_font):
                return ImageFont.truetype(default_font, size_px)
        except Exception:
            pass
        return ImageFont.load_default()

    # --- QR (camouflage) helpers -------------------------------------------
    def _make_qr_modules(data: str):
        """Return a tuple (modules, width, height) of 0/1 modules (1 = black data), or (None,0,0).
        Uses high error correction so it stays scannable with low contrast.
        """
        try:
            import qrcode
            from qrcode.constants import ERROR_CORRECT_H

            qr = qrcode.QRCode(
                version=None,
                error_correction=ERROR_CORRECT_H,
                box_size=1,
                border=4,  # include quiet zone to improve scanning
            )
            qr.add_data(data)
            qr.make(fit=True)
            # Standard black modules on white background for reliable thresholding
            img_qr = qr.make_image(fill_color="black", back_color="white").convert("L")
            w, h = img_qr.size
            px = img_qr.load()
            # 1 = black (data) module, 0 = white background
            modules = [[1 if px[x, y] < 128 else 0 for x in range(w)] for y in range(h)]
            return modules, w, h
        except Exception:
            return None, 0, 0

    def _draw_camouflaged_qr(img_rgba: Image.Image, data: str, box: Tuple[int, int, int, int], opacity: int = 70) -> None:
        """Draw a low-contrast QR into the given box on a transparent overlay.
        - data: text/URL to encode
        - box: (x0,y0,x1,y1) target rectangle; QR will be centered and scaled
        - opacity: alpha (0-255) for dark modules
        The function fails silently if dependencies are missing or box too small.
        """
        modules, qr_w, qr_h = _make_qr_modules(str(data))
        if not modules or qr_w == 0 or qr_h == 0:
            return

        x0, y0, x1, y1 = [int(v) for v in box]
        x0 = max(0, min(x0, img_rgba.width))
        y0 = max(0, min(y0, img_rgba.height))
        x1 = max(x0, min(x1, img_rgba.width))
        y1 = max(y0, min(y1, img_rgba.height))
        w_box = x1 - x0
        h_box = y1 - y0
        if w_box < 40 or h_box < 40:
            return

        # Choose integer module size that fits in the box
        module = max(2, min(w_box // qr_w, h_box // qr_h))
        draw_w = module * qr_w
        draw_h = module * qr_h
        ox = x0 + (w_box - draw_w) // 2
        oy = y0 + (h_box - draw_h) // 2

        # Compute a very faint backdrop to boost contrast a touch
        # Sample average brightness in the target box to pick light/dark blend
        try:
            crop = img_rgba.crop((x0, y0, x1, y1)).convert("L")
            avg = int(sum(crop.getdata()) / (crop.width * crop.height)) if crop.width and crop.height else 128
        except Exception:
            avg = 128

        # Always use black modules; add a faint light plate for stability
        bg_alpha = 20  # make the surrounding rectangle a bit fainter
        # Respect qr_opacity with a gentle clamp allowing fainter modules
        mod_alpha = max(50, min(200, int(opacity)))
        plate = (255, 255, 255, bg_alpha)   # faint light plate behind QR
        module_fill = (0, 0, 0, mod_alpha)  # actual QR data modules in black

        overlay = Image.new("RGBA", img_rgba.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)

        # Rounded plate sized to the drawn QR
        pad = max(2, module // 2)
        od.rounded_rectangle(
            [(ox - pad, oy - pad), (ox + draw_w + pad, oy + draw_h + pad)],
            radius=max(4, module // 2),
            fill=plate,
            outline=None,
        )

        # Draw dark/light modules
        for yy in range(qr_h):
            row = modules[yy]
            for xx in range(qr_w):
                if row[xx]:  # draw "dark" modules
                    xL = ox + xx * module
                    yT = oy + yy * module
                    od.rectangle([xL, yT, xL + module - 1, yT + module - 1], fill=module_fill)

        img_rgba.alpha_composite(overlay)

    # assign pngs to strings for badges
    #list of badge png names
    badge_pngs = ["bcal.png", "bcyb.png", "bdev.png", "bmal.png", "bpla.png", "bpop.png", "bste.png", "bsup.png", "bxbo.png"]

    #reuse code from main to get elegibal badges
    def _get_eligible_badges(level: int) -> list[str]:
        eligible: list[str] = []

        # Platform and dev badges from local JSON settings
        try:

            script_dir = os.path.dirname(os.path.abspath(__file__))
            dcord_path = os.path.join(script_dir, "JSON", "DCord.json")
            dcord = {}
            if os.path.isfile(dcord_path):
                with open(dcord_path, "r", encoding="utf-8") as f:
                    dcord = json.load(f)

            platform = str(dcord.get("platform", "")).strip()
            if platform == "Steam":
                eligible.append("bste.png")
            elif platform == "PlayStation":
                eligible.append("bpla.png")
            elif platform == "Xbox":
                eligible.append("bxbo.png")

            # Special dev badge for known UIDs
            uid = str(dcord.get("discord_uid", "")).strip()
            if uid in {"695767541393653791", "850139032720900116"}:
                eligible.append("bcal.png")
                eligible.append("bdev.png")
            elif uid in {"332209233577771008"}:
                eligible.append("btst.png")
        except Exception:
            pass

        # Planet visit badges and anniversary badge from mission log in %LOCALAPPDATA%/MLHD2
        try:
            app_data = os.path.join(os.getenv("LOCALAPPDATA") or "", "MLHD2")
            prod_log = os.path.join(app_data, "mission_log.xlsx")
            test_log = os.path.join(app_data, "mission_log_test.xlsx")
            xlsx_path = prod_log if os.path.isfile(prod_log) else (test_log if os.path.isfile(test_log) else None)

            if xlsx_path:
                df = pd.read_excel(xlsx_path)
                # Normalize and robustly detect planet column
                def _norm_planet(s: object) -> str:
                    try:
                        t = str(s or "").strip().lower()
                        # collapse spaces
                        t = " ".join(t.split())
                        # strip diacritics
                        t = unicodedata.normalize("NFKD", t)
                        t = "".join(ch for ch in t if not unicodedata.combining(ch))
                        # keep alphanumerics and spaces only
                        t = "".join(ch for ch in t if ch.isalnum() or ch.isspace())
                        return t
                    except Exception:
                        return str(s or "").strip().lower()

                planet_col = None
                for c in df.columns:
                    if str(c).strip().lower() == "planet":
                        planet_col = c
                        break
                if planet_col is None:
                    for c in df.columns:
                        if "planet" in str(c).strip().lower():
                            planet_col = c
                            break

                if planet_col is not None:
                    planets_raw = df[planet_col].tolist()
                else:
                    planets_raw = df.get("Planet", []).tolist() if hasattr(df.get("Planet", []), "tolist") else list(df.get("Planet", []))

                planets = { _norm_planet(p) for p in planets_raw }

                planet_to_badge_norm = {
                    _norm_planet("Calypso"): "bcal.png",
                    _norm_planet("Cyberstan"): "bcyb.png",
                    _norm_planet("Malevelon Creek"): "bmal.png",
                    _norm_planet("Popli IX"): "bpop.png",  # also matches Pöpli IX after normalization
                    _norm_planet("Super Earth"): "bsup.png",
                }
                for planet_norm, badge in planet_to_badge_norm.items():
                    if planet_norm in planets and badge not in eligible:
                        eligible.append(badge)

                # Award 1-year service badge by comparing first deployment to today
                try:
                    since_str = _get_first_mission_date()
                    if since_str:
                        first_dt = pd.to_datetime(since_str, dayfirst=True, errors="coerce")
                        if pd.notna(first_dt) and (pd.Timestamp.now() - first_dt) >= pd.Timedelta(days=365):
                            if "b1ye.png" not in eligible:
                                eligible.append("b1ye.png")
                except Exception:
                    pass
        except Exception:
            pass

        # Stable ordering
        order = ["bcal.png", "btst.png", "b1ye.png", "bcyb.png", "bdev.png", "bmal.png", "bpla.png", "bpop.png", "bste.png", "bsup.png", "bxbo.png"]
        eligible_set = set(eligible)
        return [b for b in order if b in eligible_set]
    # apply badges to banner
    def _apply_badges(
        banner: Image.Image,
        level: int,
        box_right: Optional[int] = None,
        box_top: Optional[int] = None,
        box_bottom: Optional[int] = None,
        text_x: Optional[int] = None,
        name_y: Optional[int] = None,
        profile_side_val: Optional[int] = None,
    ) -> Image.Image:
        """Render eligible badges near the top with their own background rectangle."""
        try:
            # Determine which badges are eligible (colored)
            eligible_list = _get_eligible_badges(level)
            eligible_set = set(eligible_list)

            # Load all badges in a fixed order; mark whether each is eligible
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # Desired left-to-right order:
            # dev, temp, platform (PS/Steam/Xbox), Super Earth, Cyberstan, Malevelon Creek, Calypso, Popli IX
            # "btmp.png" is optional; if not found, it's skipped.
            ordered = [
                "bdev.png",  # dev
                "btst.png",  # tester
                "b1ye.png",  # 1 year badge
                "bpla.png",  # platform
                "bste.png",
                "bxbo.png",
                "bsup.png",  # Super Earth
                "bcyb.png",  # Cyberstan
                "bmal.png",  # Malevelon Creek
                "bcal.png",  # Calypso
                "bpop.png",  # Popli IX
            ]
            badge_imgs: list[tuple[Image.Image, bool]] = []
            for b in ordered:
                b_path = os.path.join(script_dir, "media", "badges", b)
                if os.path.isfile(b_path):
                    try:
                        im = Image.open(b_path).convert("RGBA")
                        is_eligible = b in eligible_set
                        # Hide uneligible variants of the dev, tester, and platform badges
                        if not is_eligible and (b in {"bdev.png", "btst.png", "bpla.png", "bste.png", "bxbo.png"}):
                            continue
                        badge_imgs.append((im, is_eligible))
                    except Exception:
                        pass
            if not badge_imgs:
                return banner

            # Layout parameters with multi-row support
            W, H = banner.size
            max_badge_h = 48
            min_badge_h = 24
            spacing = 8
            row_capacity = 9
            row_spacing = 6

            anchor_left = int(text_x) if text_x is not None else 180
            anchor_right = int(box_right) if box_right is not None else (W - 16)
            avail_w = max(1, anchor_right - anchor_left)

            y_margin = 8
            pad_x = 10
            pad_y = 6

            # Determine rows
            total_badges = len(badge_imgs)
            rows = max(1, (total_badges + row_capacity - 1) // row_capacity)

            def row_slices():
                for r in range(rows):
                    start = r * row_capacity
                    end = min(total_badges, start + row_capacity)
                    yield badge_imgs[start:end]

            def row_total_width(h: int, row_imgs) -> int:
                widths = [ (im.width * h) // max(1, im.height) for (im, _) in row_imgs ]
                if not widths:
                    return 0
                return sum(widths) + spacing * (len(widths) - 1)

            # Scale height to fit width across the widest row
            badge_h = max_badge_h
            if total_badges:
                max_row_w = 0
                for row in row_slices():
                    max_row_w = max(max_row_w, row_total_width(badge_h, row))
                if max_row_w > avail_w:
                    scale = avail_w / max(1, max_row_w)
                    badge_h = max(min_badge_h, min(64, int(badge_h * scale)))

            # Scale height to fit vertically above the main rectangle
            if box_top is not None:
                avail_vert = max(16, int(box_top) - (4 + pad_y))
                needed_vert = rows * badge_h + (rows - 1) * row_spacing
                if needed_vert > avail_vert:
                    # compute the largest badge_h that fits
                    badge_h = max(min_badge_h, (avail_vert - (rows - 1) * row_spacing) // rows)

            # Baseline: bottom row aligned with the main rectangle top
            if box_top is not None:
                bottom_row_y = int(box_top) - badge_h - pad_y
            else:
                bottom_row_y = y_margin

            # Compute top row y
            top_row_y = bottom_row_y - (rows - 1) * (badge_h + row_spacing)

            # Background rectangle covering all rows
            try:
                rect_left = max(4, (anchor_left - 12))
                rect_top = max(4, top_row_y - pad_y)
                rect_right = min(W - 4, anchor_right)
                rect_bottom = min(H - 4, bottom_row_y + badge_h + pad_y)

                overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                ov_draw = ImageDraw.Draw(overlay)
                ov_draw.rounded_rectangle(
                    [(rect_left, rect_top), (rect_right, rect_bottom)],
                    radius=8,
                    fill=(25, 25, 25, 140),
                    outline=None,
                )
                banner.alpha_composite(overlay)
            except Exception:
                pass

            # Paste rows: top to bottom so overlaps (if any) look natural
            y = top_row_y
            start = 0
            for r in range(rows):
                end = min(total_badges, start + row_capacity)
                row_imgs = badge_imgs[start:end]
                x = anchor_left
                for im, is_eligible in row_imgs:
                    bw = im.width * badge_h // max(1, im.height)
                    im_resized = im.resize((bw, badge_h), Image.LANCZOS)
                    if is_eligible:
                        paste_img = im_resized
                    else:
                        rC, gC, bC, aC = im_resized.split()
                        paste_img = Image.new("RGBA", im_resized.size, (0, 0, 0, 255))
                        paste_img.putalpha(aC)
                    banner.paste(paste_img, (x, y), paste_img)
                    x += bw + spacing
                start = end
                y += badge_h + row_spacing

            # Paste decorative placard banner to the LEFT of the badges rectangle, if available.
            # Match its WIDTH to the profile picture width if provided.
            try:
                banner_path = os.path.join(script_dir, "media", "badges", "placardbanner.png")
                if os.path.isfile(banner_path):
                    deco = Image.open(banner_path).convert("RGBA")
                    # If a profile width was provided, force the decorative banner to match that width
                    # and scale height to preserve aspect ratio. Otherwise, fall back to fitting by height.
                    if profile_side_val and deco.width > 0:
                        # Initial target size: match width to profile picture
                        target_w = max(1, int(profile_side_val))
                        target_h = max(1, int(deco.height * (target_w / deco.width)))

                        # Background rectangle clamped to profile width and badges-rect height
                        bg_h = max(1, int(rect_bottom - rect_top))
                        bg_right = min(W - 4, int(rect_left - 6))
                        bg_left = max(4, bg_right - target_w)
                        # Adjust bg width if clamped by canvas
                        bg_w = max(1, bg_right - bg_left)
                        # Ensure banner width matches bg width after clamping
                        if bg_w != target_w:
                            target_w = bg_w
                            target_h = max(1, int(deco.height * (target_w / deco.width)))

                        bg_top = max(4, int(rect_top))
                        # Clamp bottom to stay within canvas and maintain desired height
                        bg_bottom_desired = bg_top + bg_h
                        bg_bottom = min(H - 4, bg_bottom_desired)
                        # If clamped by canvas, recompute height accordingly
                        bg_h = max(1, bg_bottom - bg_top)

                        # If the banner is taller than the background height, scale down to fit
                        if target_h > bg_h and deco.height > 0:
                            scale = bg_h / float(target_h)
                            target_h = max(1, int(target_h * scale))
                            target_w = max(1, int(target_w * scale))

                        deco_resized = deco.resize((target_w, target_h), Image.LANCZOS)

                        # Shift background and banner 3px to the left, clamped to left margin
                        shift = min(3, max(0, bg_left - 4))
                        bg_left = bg_left - shift

                        # Place banner centered vertically within background rectangle
                        paste_x = bg_left
                        paste_y = bg_top + (bg_h - target_h) // 2
                        paste_y = max(4, min(paste_y, H - 4 - target_h))

                        # Draw background rectangle exactly profile-width by badges-rect height
                        try:
                            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                            ovd = ImageDraw.Draw(ov)
                            ovd.rounded_rectangle([(bg_left, bg_top), (bg_left + bg_w, bg_top + bg_h)], radius=8, fill=(25, 25, 25, 140))
                            banner.alpha_composite(ov)
                        except Exception:
                            pass

                        banner.paste(deco_resized, (int(paste_x), int(paste_y)), deco_resized)
                    else:
                        # Fallback: profile width is unknown; still clamp background to badges height.
                        target_h = max(8, int(rect_bottom - rect_top - 2))
                        if target_h > 0 and deco.height > 0:
                            # Background rectangle dimensions (use available space on left of badges)
                            bg_h = max(1, int(rect_bottom - rect_top))
                            bg_top = max(4, int(rect_top))
                            bg_bottom = min(H - 4, bg_top + bg_h)
                            bg_h = max(1, bg_bottom - bg_top)
                            bg_right = min(W - 4, int(rect_left - 6))
                            # Compute banner width by height fit, then clamp to available width
                            target_w = max(1, int(deco.width * (target_h / deco.height)))
                            max_w = max(1, bg_right - 4)
                            if target_w > max_w:
                                scale = max_w / float(target_w)
                                target_w = max(1, int(target_w * scale))
                                target_h = max(1, int(target_h * scale))

                            deco_resized = deco.resize((target_w, target_h), Image.LANCZOS)

                            # Background rectangle width equals the clamped banner width
                            bg_left = max(4, bg_right - target_w)
                            bg_w = max(1, bg_right - bg_left)

                            # Shift background and banner 3px to the left, clamped to left margin
                            shift = min(3, max(0, bg_left - 4))
                            bg_left = bg_left - shift

                            # Position
                            paste_x = bg_left
                            paste_y = bg_top + (bg_h - target_h) // 2
                            paste_y = max(4, min(paste_y, H - 4 - target_h))

                            # Draw strict background rectangle (width aligned to banner, height to badges)
                            try:
                                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                                ovd = ImageDraw.Draw(ov)
                                ovd.rounded_rectangle([(bg_left, bg_top), (bg_left + bg_w, bg_top + bg_h)], radius=8, fill=(25, 25, 25, 140))
                                banner.alpha_composite(ov)
                            except Exception:
                                pass

                            banner.paste(deco_resized, (int(paste_x), int(paste_y)), deco_resized)
            except Exception:
                pass

            return banner
        except Exception:
            return banner

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

    def _resolve_background_path(base: Optional[str]) -> Optional[str]:
        if not base:
            return None
        p = os.path.join(base, "media", "badges", "backing.png")
        return p if os.path.isfile(p) else None

    def _resolve_asset_path(name: str, base: Optional[str]) -> Optional[str]:
        """Resolve an asset by name to an absolute path. Accepts full paths or basenames.
        Searches common media folders in base and script directories.
        """
        if not name:
            return None
        n = str(name).strip()
        if n.startswith('#file:'):
            n = n.split(':', 1)[1]
        if os.path.isfile(n):
            return n
        # ensure .png extension default
        if not os.path.splitext(n)[1]:
            n_png = n + ".png"
        else:
            n_png = n
        search_dirs: list[str] = []
        if base:
            search_dirs.append(os.path.join(base, "media"))
            search_dirs.append(os.path.join(base, "media", "badges"))
            search_dirs.append(os.path.join(base, "media", "profile_pictures"))
            search_dirs.append(os.path.join(base, "media", "SettingsInt"))
        script_dir = os.path.dirname(os.path.abspath(__file__))
        search_dirs.append(os.path.join(script_dir, "media"))
        search_dirs.append(os.path.join(script_dir, "media", "badges"))
        search_dirs.append(os.path.join(script_dir, "media", "profile_pictures"))
        search_dirs.append(os.path.join(script_dir, "media", "SettingsInt"))
        for d in search_dirs:
            p = os.path.join(d, n_png)
            if os.path.isfile(p):
                return p
        return None

    def _get_average_rating_gold_count() -> Optional[int]:
        """Compute average rating across mission logs mapped to gold-star count (0-5).
        Uses a mapping from rating text to star numbers; averages and rounds to nearest int.
        Returns None if logs are missing or no parse possible.
        """
        try:
            app_data = os.path.join(os.getenv("LOCALAPPDATA") or "", "MLHD2")
            prod_log = os.path.join(app_data, "mission_log.xlsx")
            test_log = os.path.join(app_data, "mission_log_test.xlsx")
            xlsx_path = prod_log if os.path.isfile(prod_log) else (test_log if os.path.isfile(test_log) else None)
            if not xlsx_path:
                return None
            df = pd.read_excel(xlsx_path)
            if df is None or df.empty:
                return None

            rating_map = {
                "Outstanding Patriotism": 5,
                "Superior Valour": 4,
                "Costly Failure": 4,
                "Honourable Duty": 3,
                "Unremarkable Performance": 2,
                "Disappointing Service": 1,
                "Disgraceful Conduct": 0,
            }

            # Try likely rating columns
            cols = [c for c in df.columns if str(c).strip().lower() in {"rating", "result", "mission rating"}]
            if not cols:
                # fallback: any column containing rating keywords
                cols = [c for c in df.columns if "rating" in str(c).lower() or "result" in str(c).lower()]
            if not cols:
                return None

            vals = []
            for c in cols:
                series = df[c].astype(str).str.strip()
                mapped = series.map(lambda s: rating_map.get(s))
                mapped = mapped.dropna()
                if not mapped.empty:
                    vals.extend(mapped.tolist())
            if not vals:
                return None
            avg = sum(vals) / len(vals)
            # round to nearest integer
            gold = int(round(avg))
            return max(0, min(5, gold))
        except Exception:
            return None

    def _get_first_mission_date() -> Optional[str]:
        """Return earliest mission date from mission log Excel, formatted for display.
        Looks in %LOCALAPPDATA%/MLHD2 for mission_log.xlsx or mission_log_test.xlsx.
        Dates are stored as dd/mm/yyyy (day-first). Tries to infer robustly.
        """
        try:
            app_data = os.path.join(os.getenv("LOCALAPPDATA") or "", "MLHD2")
            prod_log = os.path.join(app_data, "mission_log.xlsx")
            test_log = os.path.join(app_data, "mission_log_test.xlsx")
            xlsx_path = prod_log if os.path.isfile(prod_log) else (test_log if os.path.isfile(test_log) else None)
            if not xlsx_path:
                return None
            df = pd.read_excel(xlsx_path)
            if df is None or df.empty:
                return None

            # Helper to robustly coerce a Series to datetimes and drop unrealistic dates
            def _coerce_datetimes(series: pd.Series) -> pd.Series:
                try:
                    s = series
                    # Already datetime-like
                    if pd.api.types.is_datetime64_any_dtype(s):
                        dt = pd.to_datetime(s, errors="coerce")
                    # Numeric columns may be unix timestamps (s/ms) or Excel serials
                    elif pd.api.types.is_integer_dtype(s) or pd.api.types.is_float_dtype(s):
                        s_num = pd.to_numeric(s, errors="coerce")
                        dt = pd.to_datetime(s_num, errors="coerce")
                        if s_num.notna().any():
                            maxv = float(s_num.max())
                            minv = float(s_num.min())
                            try:
                                if maxv > 1e12:  # likely milliseconds
                                    dt = pd.to_datetime(s_num, unit="ms", errors="coerce", utc=True).dt.tz_localize(None)
                                elif maxv > 1e9:  # likely seconds
                                    dt = pd.to_datetime(s_num, unit="s", errors="coerce", utc=True).dt.tz_localize(None)
                                elif 20000 < minv < 60000 and 20000 < maxv < 60000:
                                    # Excel serial date (days since 1899-12-30)
                                    dt = pd.to_datetime(s_num, unit="D", origin="1899-12-30", errors="coerce")
                            except Exception:
                                pass
                    else:
                        # Strings or mixed types; try explicit formats first (e.g., 05-09-2025 23:00:10) to avoid per-element parsing warnings
                        s_str = s.astype(str).str.strip()
                        dt = None
                        for fmt in ("%d-%m-%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M", "%d-%m-%Y", "%d/%m/%Y"):
                            try:
                                parsed = pd.to_datetime(s_str, format=fmt, errors="coerce")
                                if parsed.notna().any():
                                    dt = parsed
                                    break
                            except Exception:
                                pass
                        if dt is None:
                            # Fallback to a tolerant parse with day-first assumption
                            dt = pd.to_datetime(s_str, errors="coerce", format="%d/%m/%Y", dayfirst=True)
                except Exception:
                    # Final fallback using explicit string conversion to keep behavior consistent
                    dt = pd.to_datetime(series.astype(str), errors="coerce", dayfirst=True)

                # Filter out clearly invalid dates (e.g., 1970-01-01 from zeros)
                lower_bound = pd.Timestamp("2014-01-01")
                upper_bound = pd.Timestamp("2100-01-01")
                dt = dt.where((dt >= lower_bound) & (dt < upper_bound))
                return dt

            candidate_mins: list[pd.Timestamp] = []
            # Prefer common column names first
            preferred_cols = [
                "Time",
                "time",
                "Date",
                "date",
                "Timestamp",
                "timestamp",
                "DateTime",
                "datetime",
            ]
            for col in df.columns:
                series = df[col]
                dt = _coerce_datetimes(series)
                if dt.notna().any():
                    col_min = dt.min()
                    if pd.notna(col_min):
                        # If column name is preferred, favor it by appending first
                        if col in preferred_cols:
                            candidate_mins.insert(0, col_min)
                        else:
                            candidate_mins.append(col_min)

            if not candidate_mins:
                return None
            first_dt = min([d for d in candidate_mins if pd.notna(d)])
            if pd.isna(first_dt):
                return None
            # Friendly date format, e.g., 02 Jan, 2025 or Jan 02, 2025; keep original style
            return first_dt.strftime("%d/%m/%Y")
        except Exception:
            return None

    def _get_totals_and_homeworld() -> tuple[Optional[int], Optional[int], Optional[str]]:
        """Return (total_kills, total_deployments, homeworld) from mission logs.
        - total_kills: sum of numeric 'Kills' column (best-effort detection)
        - total_deployments: number of rows in the log (non-empty DataFrame)
        - homeworld: planet from the earliest mission by timestamp (best-effort),
          falling back to the first non-empty planet value in file order.
        """
        try:
            app_data = os.path.join(os.getenv("LOCALAPPDATA") or "", "MLHD2")
            prod_log = os.path.join(app_data, "mission_log.xlsx")
            test_log = os.path.join(app_data, "mission_log_test.xlsx")
            xlsx_path = prod_log if os.path.isfile(prod_log) else (test_log if os.path.isfile(test_log) else None)
            if not xlsx_path:
                return None, None, None
            df = pd.read_excel(xlsx_path)
            if df is None or df.empty:
                return 0, 0, None

            # Total deployments = all rows
            deployments = int(len(df))

            # Total kills: find a column named 'kills' (case-insensitive) or containing 'kill'
            kills_col = None
            for c in df.columns:
                cl = str(c).strip().lower()
                if cl == "kills":
                    kills_col = c
                    break
            if kills_col is None:
                for c in df.columns:
                    if "kill" in str(c).lower():
                        kills_col = c
                        break
            kills_total = 0
            if kills_col is not None:
                try:
                    kills_series = pd.to_numeric(df[kills_col], errors="coerce").fillna(0)
                    kills_total = int(kills_series.sum())
                except Exception:
                    kills_total = 0

            # Homeworld: earliest planet by timestamp if possible
            planet_col = None
            for c in df.columns:
                if str(c).strip().lower() == "planet":
                    planet_col = c
                    break
            if planet_col is None:
                for c in df.columns:
                    if "planet" in str(c).lower():
                        planet_col = c
                        break

            homeworld = None
            if planet_col is not None:
                # Attempt to detect a datetime column and pick earliest
                def _try_parse_datetime_column(series: pd.Series) -> Optional[pd.Series]:
                    try:
                        s = series
                        if pd.api.types.is_datetime64_any_dtype(s):
                            dt = pd.to_datetime(s, errors="coerce")
                        elif pd.api.types.is_integer_dtype(s) or pd.api.types.is_float_dtype(s):
                            s_num = pd.to_numeric(s, errors="coerce")
                            dt = pd.to_datetime(s_num, errors="coerce")
                            if s_num.notna().any():
                                maxv = float(s_num.max())
                                minv = float(s_num.min())
                                try:
                                    if maxv > 1e12:
                                        dt = pd.to_datetime(s_num, unit="ms", errors="coerce", utc=True).dt.tz_localize(None)
                                    elif maxv > 1e9:
                                        dt = pd.to_datetime(s_num, unit="s", errors="coerce", utc=True).dt.tz_localize(None)
                                    elif 20000 < minv < 60000 and 20000 < maxv < 60000:
                                        dt = pd.to_datetime(s_num, unit="D", origin="1899-12-30", errors="coerce")
                                except Exception:
                                    pass
                        else:
                            s_str = s.astype(str).str.strip()
                            dt = None
                            for fmt in ("%d-%m-%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M", "%d-%m-%Y", "%d/%m/%Y"):
                                try:
                                    parsed = pd.to_datetime(s_str, format=fmt, errors="coerce")
                                    if parsed.notna().any():
                                        dt = parsed
                                        break
                                except Exception:
                                    pass
                            if dt is None:
                                dt = pd.to_datetime(s_str, errors="coerce", dayfirst=True)
                    except Exception:
                        dt = pd.to_datetime(series.astype(str), errors="coerce", dayfirst=True)
                    lower_bound = pd.Timestamp("2014-01-01")
                    upper_bound = pd.Timestamp("2100-01-01")
                    dt = dt.where((dt >= lower_bound) & (dt < upper_bound))
                    return dt

                # Identify a likely datetime column
                time_cols = []
                for c in df.columns:
                    cl = str(c).strip().lower()
                    if cl in {"time", "date", "timestamp", "datetime"} or "time" in cl or "date" in cl:
                        time_cols.append(c)
                dt_series = None
                for c in time_cols:
                    parsed = _try_parse_datetime_column(df[c])
                    if parsed is not None and parsed.notna().any():
                        dt_series = parsed
                        break
                if dt_series is not None:
                    idx = dt_series.idxmin()
                    try:
                        val = df.loc[idx, planet_col]
                        if pd.notna(val):
                            homeworld = str(val).strip() or None
                    except Exception:
                        homeworld = None

                # Fallback: first non-empty planet value
                if not homeworld:
                    for v in df[planet_col].astype(str):
                        sv = str(v).strip()
                        if sv:
                            homeworld = sv
                            break

            return kills_total, deployments, homeworld
        except Exception:
            return None, None, None

    bg_path = _resolve_background_path(base_dir)
    if bg_path:
        try:
            bg = Image.open(bg_path).convert("RGBA")
            W, H = bg.size
            img = Image.new("RGBA", (W, H), (37, 37, 38, 255))
            # Use native image size; no resize or crop, paste at origin
            img.paste(bg, (0, 0), bg)
        except Exception:
            W, H = size
            img = Image.new("RGBA", (W, H), (37, 37, 38, 255))
            # Fallback: simple vertical gradient
            draw = ImageDraw.Draw(img)
            for y in range(H):
                shade = 37 + int((y / max(1, H - 1)) * 18)
                draw.line([(0, y), (W, y)], fill=(shade, shade, shade, 255))
    else:
        W, H = size
        img = Image.new("RGBA", (W, H), (37, 37, 38, 255))
        # Fallback: simple vertical gradient
        draw = ImageDraw.Draw(img)
        for y in range(H):
            shade = 37 + int((y / max(1, H - 1)) * 18)
            draw.line([(0, y), (W, y)], fill=(shade, shade, shade, 255))

    # Compute profile image placement and render on the left
    profile_side = min(140, H - 20)
    profile_x = 20
    profile_top = (H - profile_side) // 2
    profile_bottom = profile_top + profile_side
    try:
        p_path = _resolve_profile_path(profile, base_dir)
        if p_path:
            p_img = Image.open(p_path).convert("RGBA")
            p_img = p_img.resize((profile_side, profile_side), Image.LANCZOS)
            img.paste(p_img, (profile_x, profile_top), p_img)
    except Exception:
        pass

    # Fonts
    font_big = _load_font(36)
    font_small = _load_font(24)

    # Text
    try:
        level_val = int(level)
    except Exception:
        level_val = 0

    ship = f"{shipname1} {shipname2}".strip()

    # Text positions (to the right of profile area)
    # Ensure we have a drawing context for text
    draw = ImageDraw.Draw(img)
    text_x = 180

    # Name baseline (used for badge placement) — align within the profile-height rectangle
    name_y = profile_top + 12

    # Translucent backdrop for text (over background, under text)
    try:
        pad_x = 12
        box_left = text_x - pad_x
        # Make the overlay rectangle match the profile image height
        box_top = profile_top
        box_right = W - 16
        box_bottom = profile_bottom

        # Pre-compute stats to decide if the main rectangle needs to extend downward
        info_lines_stats: list[str] = []
        heights_stats: list[int] = []
        BASELINE_SPACING = 32
        stats_pad_y = 10
        # Start stats one line below the Serving Since baseline for consistent spacing
        serving_line_y = name_y + 106
        stats_start_y = serving_line_y + BASELINE_SPACING
        try:
            kills_total, deployments, homeworld = _get_totals_and_homeworld()
            if kills_total is not None:
                info_lines_stats.append(f"Kills: {kills_total}")
            if deployments is not None:
                info_lines_stats.append(f"Deployments: {deployments}")
            if homeworld:
                info_lines_stats.append(f"Homeworld: {homeworld}")

            if info_lines_stats:
                tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
                for t in info_lines_stats:
                    bb = tmp.textbbox((0, 0), t, font=font_small)
                    heights_stats.append(max(0, bb[3] - bb[1]))
                # Estimate block height using consistent baseline spacing
                typical_h = max(heights_stats) if heights_stats else 18
                block_h = (len(info_lines_stats) - 1) * BASELINE_SPACING + typical_h
                # Include extra bottom padding for descenders (e.g., y,g,p,q,j)
                try:
                    asc, desc = font_small.getmetrics()
                    desc_margin = max(3, int(desc))
                except Exception:
                    desc_margin = 4
                new_bottom = min(H - 8, stats_start_y + block_h + stats_pad_y + desc_margin)
                # Ensure it still covers the original rectangle
                box_bottom = max(box_bottom, new_bottom)
        except Exception:
            # If stats fail, proceed without extending
            info_lines_stats = []
            heights_stats = []

        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ov_draw = ImageDraw.Draw(overlay)
        ov_draw.rounded_rectangle(
            [(box_left, box_top), (box_right, box_bottom)],
            radius=10,
            fill=(25, 25, 25, 140),  # dark gray with transparency
            outline=None,
        )
        img.alpha_composite(overlay)
    except Exception:
        # Fallback values if overlay computation fails
        box_top = profile_top
        box_right = W - 16
        box_bottom = profile_bottom
    draw.text((text_x, name_y), str(name), fill=(255, 255, 255, 230), font=font_big)
    title_text = f"Level {level_val}" + (f" | {title}" if str(title).strip() else "")
    # Keep spacing relative to the name baseline to stay within the resized rectangle
    draw.text((text_x, name_y + 42), title_text, fill=(220, 220, 220, 230), font=font_small)
    draw.text((text_x, name_y + 74), ship, fill=(200, 200, 200, 210), font=font_small)
    # Serving Since line under ship name, if a log is found
    since = _get_first_mission_date()
    if since:
        draw.text((text_x, name_y + 106), f"Serving Since: {since}", fill=(190, 190, 190, 210), font=font_small)

    # Draw stats lines (if computed earlier) inside the extended main rectangle, no extra overlay
    try:
        if 'info_lines_stats' in locals() and info_lines_stats:
            cur_y = stats_start_y
            for idx, t in enumerate(info_lines_stats):
                bb = draw.textbbox((0, 0), t, font=font_small)
                tw = max(0, bb[2] - bb[0])
                th = max(0, bb[3] - bb[1])
                tx = text_x
                if tx + tw > box_right - 10:
                    tx = max(text_x, box_right - 10 - tw)
                # Clamp Y so the full text height stays inside the rectangle
                y_draw = min(max(cur_y, box_top + 6), max(box_top + 6, box_bottom - 6 - th))
                # Match 'Serving Since' color
                draw.text((tx, y_draw), t, fill=(190, 190, 190, 210), font=font_small)
                cur_y += BASELINE_SPACING
    except Exception:
        pass

    # Apply eligible badges above the rectangle, aligned to the name's left edge
    img = _apply_badges(
        img,
        level_val,
        box_right=box_right,
        box_top=box_top,
        box_bottom=box_bottom,
        text_x=text_x,
        name_y=name_y,
        profile_side_val=profile_side,
    )

    # Under-profile gallery rectangle holding 5 stars based on average rating (fallback to provided extra_images)
    try:
        slots = 5
        gap = 4
        pad = 6
        # Determine icon size to fit within the profile square width
        max_icon_w = (profile_side - 2 * pad - gap * (slots - 1)) // slots
        icon = max(18, min(28, max_icon_w))
        rect_h = pad * 2 + icon

        # Compute gold star count once and derive a rating label for text inside stars area
        gold_count = _get_average_rating_gold_count()
        rating_text = ""
        font_tiny = _load_font(18)
        text_w = text_h = 0
        if gold_count is not None:
            try:
                labels = {
                    5: "Outstanding Patriotism",
                    4: "Superior Valour",
                    3: "Honourable Duty",
                    2: "Unremarkable Performance",
                    1: "Disappointing Service",
                    0: "Disgraceful Conduct",
                }
                rating_text = labels.get(max(0, min(5, int(gold_count))), "")
            except Exception:
                rating_text = ""
        # Determine text layout (1 or 2 lines) to keep inside rectangle width
        lines = []
        line_heights = []
        line_spacing = 2
        max_text_w = profile_side - 2 * pad - 2
        if rating_text:
            try:
                # Single line fits?
                tb = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), rating_text, font=font_tiny)
                w_single = max(0, tb[2] - tb[0])
                h_single = max(0, tb[3] - tb[1])
                if w_single <= max_text_w:
                    lines = [rating_text]
                    line_heights = [h_single]
                else:
                    words = rating_text.split()
                    best = None  # (score, [l1,l2], [h1,h2])
                    tmp_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
                    for i in range(1, len(words)):
                        l1 = " ".join(words[:i])
                        l2 = " ".join(words[i:])
                        b1 = tmp_draw.textbbox((0, 0), l1, font=font_tiny)
                        b2 = tmp_draw.textbbox((0, 0), l2, font=font_tiny)
                        w1 = max(0, b1[2] - b1[0])
                        w2 = max(0, b2[2] - b2[0])
                        h1 = max(0, b1[3] - b1[1])
                        h2 = max(0, b2[3] - b2[1])
                        if w1 <= max_text_w and w2 <= max_text_w:
                            score = max(w1, w2)
                            if best is None or score < best[0]:
                                best = (score, [l1, l2], [h1, h2])
                    if best is not None:
                        lines = best[1]
                        line_heights = best[2]
                    else:
                        # Fallback: force two lines at middle, even if slightly wider
                        mid = len(words) // 2
                        l1 = " ".join(words[:mid])
                        l2 = " ".join(words[mid:])
                        b1 = tmp_draw.textbbox((0, 0), l1, font=font_tiny)
                        b2 = tmp_draw.textbbox((0, 0), l2, font=font_tiny)
                        lines = [l1, l2]
                        line_heights = [max(0, b1[3] - b1[1]), max(0, b2[3] - b2[1])]
            except Exception:
                lines = [rating_text]
                line_heights = [text_h or 14]

        # Increase rectangle height to include text if present
        if lines:
            total_text_h = sum(line_heights) + (len(lines) - 1) * line_spacing
            rect_h += 4 + total_text_h

        rect_top = profile_bottom + 8
        # keep inside canvas, accounting for rectangle height
        rect_top = min(rect_top, H - rect_h - 8)
        rect_left = profile_x
        rect_right = profile_x + profile_side
        rect_bottom = rect_top + rect_h

        # Draw the rectangle
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ov_draw = ImageDraw.Draw(overlay)
        ov_draw.rounded_rectangle(
            [(rect_left, rect_top), (rect_right, rect_bottom)],
            radius=6,
            fill=(25, 25, 25, 140),
            outline=None,
        )
        img.alpha_composite(overlay)

        # Place stars based on average rating
        icons: list[Optional[Image.Image]] = []
        if gold_count is None:
            # Optional fallback: allow manual images if provided
            if extra_images:
                for name in extra_images[:slots]:
                    p = _resolve_asset_path(name, base_dir)
                    if p:
                        try:
                            im = Image.open(p).convert("RGBA")
                            icons.append(im)
                            continue
                        except Exception:
                            pass
                    icons.append(None)
            # pad to slots
            while len(icons) < slots:
                icons.append(None)
        else:
            gold = max(0, min(5, int(gold_count)))
            grey = slots - gold
            gold_path = _resolve_asset_path("goldstar.png", base_dir)
            grey_path = _resolve_asset_path("greystar.png", base_dir)
            gold_img = Image.open(gold_path).convert("RGBA") if gold_path else None
            grey_img = Image.open(grey_path).convert("RGBA") if grey_path else None
            for _ in range(gold):
                icons.append(gold_img)
            for _ in range(grey):
                icons.append(grey_img)

        x = rect_left + pad
        y = rect_top + pad
        for im in icons:
            if im is not None:
                iw = icon
                ih = icon
                im_resized = im.resize((iw, ih), Image.LANCZOS)
                img.paste(im_resized, (x, y), im_resized)
            else:
                # placeholder slot
                ph = Image.new("RGBA", (icon, icon), (0, 0, 0, 0))
                ph_draw = ImageDraw.Draw(ph)
                ph_draw.rounded_rectangle([(1, 1), (icon - 2, icon - 2)], radius=4, outline=(180, 180, 180, 180), width=1)
                # diagonal hint
                ph_draw.line([(3, icon - 3), (icon - 3, 3)], fill=(120, 120, 120, 140), width=1)
                img.paste(ph, (x, y), ph)
            x += icon + gap

        # Draw rating text centered inside the rectangle (under the stars)
        if lines:
            try:
                cur_y = rect_top + pad + icon + 4
                for idx, line in enumerate(lines):
                    tb = draw.textbbox((0, 0), line, font=font_tiny)
                    tw = max(0, tb[2] - tb[0])
                    lh = line_heights[idx] if idx < len(line_heights) else max(0, tb[3] - tb[1])
                    tx = rect_left + (profile_side - tw) // 2
                    # Clamp vertically within rectangle
                    if cur_y + lh > rect_bottom - pad:
                        cur_y = max(rect_top + pad, rect_bottom - pad - lh)
                    draw.text((tx, cur_y), line, fill=(210, 210, 210, 230), font=font_tiny)
                    cur_y += lh + line_spacing
            except Exception:
                pass

    except Exception:
        pass

    # Subtle but scannable QR in the bottom-right corner
    try:
        if qr_data:
            pad = 10
            box_w = box_h = max(84, min(140, min(img.width, img.height) // 3))
            qr_box = (img.width - pad - box_w, img.height - pad - box_h, img.width - pad, img.height - pad)
            _draw_camouflaged_qr(img, str(qr_data), qr_box, opacity=int(qr_opacity))
    except Exception:
        pass

    if save_to:
        os.makedirs(os.path.dirname(os.path.abspath(save_to)), exist_ok=True)
        img.save(save_to, format="PNG")

    return img
