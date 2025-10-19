#Centralized UI sound system for click and hover effects.
from __future__ import annotations

import os
import time
import threading
import logging
import platform
from typing import Optional, Callable

__all__ = [
    "init_ui_sounds",
    "play_button_click",
    "play_button_hover",
    "set_ui_sounds_enabled",
    "register_global_click_binding",
]

# Timing / throttle constants
_BTN_MIN_INTERVAL = 0.08
_HOVER_MIN_INTERVAL = 0.15

# Internal state
_btn_last_play: float = 0.0
_hover_last_play: float = 0.0
_button_player: Optional[Callable[[], object]] = None
_hover_player: Optional[Callable[[], object]] = None
_button_init_attempted = False
_hover_init_attempted = False
_enabled = True  # Disabled by default; use set_ui_sounds_enabled(True)
_lock = threading.Lock()
_preload_started = False


def _asset_path(filename: str) -> Optional[str]:
    # Resolve via app_path so development checkout (repo-root media/) is used
    try:
        from core.runtime_paths import app_path
        path = app_path('media', 'SyInt', filename)
    except Exception:
        base = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base, "media", "SyInt", filename)
    return path if os.path.isfile(path) else None


def _init_player(kind: str) -> None:
    global _button_player, _button_init_attempted, _hover_player, _hover_init_attempted
    if kind == "click":
        if _button_player is not None or _button_init_attempted:
            return
    else:
        if _hover_player is not None or _hover_init_attempted:
            return
    with _lock:
        if kind == "click":
            if _button_player is not None or _button_init_attempted:
                return
            _button_init_attempted = True
            wav_path = _asset_path("ButtonClick.wav")
            if not wav_path:
                return
            try:
                # Prefer a very low-latency native backend on Windows
                if platform.system() == "Windows":
                    try:
                        import winsound  # type: ignore

                        def _win_click():
                            try:
                                winsound.PlaySound(wav_path, winsound.SND_ASYNC | winsound.SND_FILENAME | winsound.SND_NODEFAULT)
                            except Exception:
                                # Fallback to simpleaudio below if winsound fails
                                raise

                        _button_player = _win_click
                    except Exception:
                        # Fall through to simpleaudio fallback
                        pass
                if _button_player is None:
                    import simpleaudio as sa  # type: ignore
                    wave_obj = sa.WaveObject.from_wave_file(wav_path)
                    # Capture wave_obj locally to avoid lookup cost at play time
                    def _sa_click():
                        try:
                            wave_obj.play()
                        except Exception:
                            pass

                    _button_player = _sa_click
            except Exception as e:
                logging.debug(f"UI sound: failed to init click sound: {e}")
        else:
            if _hover_player is not None or _hover_init_attempted:
                return
            _hover_init_attempted = True
            wav_path = _asset_path("ButtonHover.wav")
            if not wav_path:
                return
            try:
                # Windows winsound fast-path
                if platform.system() == "Windows":
                    try:
                        import winsound  # type: ignore

                        def _win_hover():
                            try:
                                winsound.PlaySound(wav_path, winsound.SND_ASYNC | winsound.SND_FILENAME | winsound.SND_NODEFAULT)
                            except Exception:
                                raise

                        _hover_player = _win_hover
                    except Exception:
                        pass
                if _hover_player is None:
                    import simpleaudio as sa  # type: ignore
                    wave_obj = sa.WaveObject.from_wave_file(wav_path)

                    def _sa_hover():
                        try:
                            wave_obj.play()
                        except Exception:
                            pass

                    _hover_player = _sa_hover
            except Exception as e:
                logging.debug(f"UI sound: failed to init hover sound: {e}")


def _preload():
    # Preload both players in background to avoid initial latency
    try:
        _init_player("click")
        _init_player("hover")
    except Exception:
        pass


def init_ui_sounds(preload: bool = True) -> None:
    # Optionally kick off background preload of both sounds.
    global _preload_started
    if not preload or _preload_started:
        return
    _preload_started = True
    t = threading.Thread(target=_preload, name="UI-Sound-Preload", daemon=True)
    t.start()


def set_ui_sounds_enabled(enabled: bool) -> None:
    global _enabled
    _enabled = bool(enabled)


def play_button_click() -> None:
    global _btn_last_play
    if not _enabled:
        return
    # Use monotonic clock for robust interval checks
    now = time.monotonic()
    if now - _btn_last_play < _BTN_MIN_INTERVAL:
        return
    if _button_player is None:
        _init_player("click")
    player = _button_player
    if player is None:
        return
    _btn_last_play = now
    try:
        # Call the prepared player callable directly (very cheap)
        player()
    except Exception:
        pass


def play_button_hover() -> None:
    global _hover_last_play
    if not _enabled:
        return
    now = time.monotonic()
    if now - _hover_last_play < _HOVER_MIN_INTERVAL:
        return
    if _hover_player is None:
        _init_player("hover")
    player = _hover_player
    if player is None:
        return
    _hover_last_play = now
    try:
        player()
    except Exception:
        pass


def register_global_click_binding(root, filter_text_widgets: bool = True) -> None:
    #Bind a global click-release handler that plays the click sound.
    try:
        import tkinter as tk  # local import to avoid circulars
    except Exception:
        return

    def _maybe(ev):
        try:
            # Filter typical text-entry widgets so typing/caret clicks don't trigger sounds
            if filter_text_widgets and isinstance(ev.widget, (tk.Text, tk.Entry, tk.Spinbox)):
                return
            play_button_click()
        except Exception:
            pass
    try:
        root.bind_all('<ButtonRelease-1>', _maybe, add=True)
    except Exception:
        pass
