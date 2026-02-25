"""Small UI visual effect helpers: image swapping on hover and related utilities.

Keep hover/swapping behavior centralized so callers only bind a widget and
provide images. These helpers intentionally avoid side-effects except the
Tkinter binding side-effects on the provided widget.
"""

import logging
from typing import Callable, Optional

from PIL import Image, ImageTk

from core.image_utils import load_photo_image_cached


# Loads and scales a small icon with app background; affects small button icons
def load_small_icon(path: str, scale_divisor: int = 6) -> Optional[ImageTk.PhotoImage]:
    try:
        src = Image.open(path)
        size = (max(12, src.width // scale_divisor), max(12, src.height // scale_divisor))
        src.close()
        return load_photo_image_cached(path, size=size, convert_mode="RGBA", composite_bg=True)
    except Exception as e:
        logging.error(f"ui_effects: failed to load small icon '{path}': {e}")
        return None


# Binds hover enter/leave to swap widget image; affects interactive button visuals
def bind_image_hover(
    widget, default_img, hover_img, on_enter: Optional[Callable] = None, on_leave: Optional[Callable] = None
):
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

        widget.bind("<Enter>", _enter)
        widget.bind("<Leave>", _leave)
    except Exception as e:
        logging.error(f"ui_effects: failed to bind hover for widget: {e}")
