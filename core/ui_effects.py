"""Small UI visual effect helpers: image swapping on hover and related utilities.

Keep hover/swapping behavior centralized so callers only bind a widget and
provide images. These helpers intentionally avoid side-effects except the
Tkinter binding side-effects on the provided widget.
"""
from typing import Callable, Optional
import logging
from PIL import Image, ImageTk


def load_small_icon(path: str, scale_divisor: int = 6) -> Optional[ImageTk.PhotoImage]:
    try:
        pil_img = Image.open(path).convert('RGBA')
        pil_img = pil_img.resize((max(12, pil_img.width // scale_divisor), max(12, pil_img.height // scale_divisor)), Image.LANCZOS)
        bg_color = (37, 37, 38, 255)
        background = Image.new('RGBA', pil_img.size, bg_color)
        pil_img = Image.alpha_composite(background, pil_img)
        return ImageTk.PhotoImage(pil_img)
    except Exception as e:
        logging.error(f"ui_effects: failed to load small icon '{path}': {e}")
        return None


def bind_image_hover(widget, default_img, hover_img, on_enter: Optional[Callable]=None, on_leave: Optional[Callable]=None):
    """Bind a pair of enter/leave events to swap a widget's image.

    widget: tk.Label or similar with .configure(image=...)
    default_img, hover_img: ImageTk.PhotoImage or None
    on_enter/on_leave: optional callbacks executed after the swap
    """
    try:
        if hover_img is None or default_img is None:
            return

        def _enter(ev):
            try:
                widget.configure(image=hover_img)
                if on_enter:
                    on_enter(ev)
            except Exception:
                pass

        def _leave(ev):
            try:
                widget.configure(image=default_img)
                if on_leave:
                    on_leave(ev)
            except Exception:
                pass

        widget.bind('<Enter>', _enter)
        widget.bind('<Leave>', _leave)
    except Exception as e:
        logging.error(f"ui_effects: failed to bind hover for widget: {e}")
