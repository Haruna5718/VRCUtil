from __future__ import annotations

from pathlib import Path

import pywebwinui3.core
from pywebwinui3.util import DEFAULT_ACCENT_PALETTE, SyncDict

from . import osc


class _NoGuiAccent:
    def __init__(self):
        self.palette = DEFAULT_ACCENT_PALETTE.copy()
        self.event = pywebwinui3.core.Event()

    def start(self):
        return


class NoGuiRuntime:
    def __init__(self):
        self._on_top = False
        self._minimum_size = (100, 100)
        self._window_size = (900, 600)
        self.destroy = lambda: None
        self.hide = lambda: None
        self.show = lambda: None
        self.restore = lambda: None
        self.minimize = lambda: None

    def queue_sync_value(self, *_):
        return

    def set_on_top(self, state: bool):
        self._on_top = bool(state)

    def get_window_size(self):
        return self._window_size

    def start(
        self,
        *_,
        hidden: bool = False,
        on_top: bool | None = None,
        width: int | None = None,
        height: int | None = None,
        min_width: int | None = None,
        min_height: int | None = None,
        **__,
    ):
        if on_top is not None:
            self._on_top = bool(on_top)
        if min_width is not None and min_height is not None:
            self._minimum_size = (min_width, min_height)
        if width is not None and height is not None:
            self._window_size = (width, height)
        return


def create_nogui_app(title: str, icon: str | None, root_path: Path):
    from . import core as vrcore

    class NoGuiVRCUtil(vrcore.VRCUtil):
        def __init__(self, title: str, icon: str | None, root_path: Path):
            self.rootPath = Path(root_path).resolve()
            self.packagePath = Path(pywebwinui3.core.__file__).parent.resolve() / "web"

            self.accent = _NoGuiAccent()
            self.events = pywebwinui3.core.WindowEvents()
            self.api = NoGuiRuntime()

            self.values = SyncDict(
                {
                    "system_title": title,
                    "system_icon": icon,
                    "system_theme": "system",
                    "system_accent": self.accent.palette,
                    "system_pages": None,
                    "system_settings": None,
                    "system_nofication": [],
                    "system_pin": False,
                }
            )
            self.values.sync = self.api.queue_sync_value

            self.events.accentColorChange = self.accent.event
            self.events.valueChange = self.values.event
            self.events.accentColorChange += lambda palette: self.values.set("system_accent", palette)

            self.process_state = vrcore.RuntimeProcessStateManager(self)
            self._opengl = None
            self._page_lock = vrcore.threading.RLock()
            self._module_lock = vrcore.threading.RLock()
            self._page_sync_depth = 0
            self._page_sync_dirty = False
            self._module_sync_depth = 0
            self._module_sync_dirty = False
            self._module_infos: dict[str, list] = {}
            self._dashboard_widget_sort_keys: dict[int, tuple[str, str]] = {}
            self._steamvr_overlay_lock = vrcore.threading.Lock()
            self._steamvr_overlay_pending: bool | None = None
            self._steamvr_overlay_worker: vrcore.threading.Thread | None = None

            self.osc = osc.EasyOSC(title, init=False)
            self.__initVRCUtil__()

        def start(
            self,
            debug=False,
            *,
            hidden=False,
            onTop=None,
            width=None,
            height=None,
            min_width=800,
            min_height=500,
        ):
            if onTop is not None:
                self.values.set("system_pin", bool(onTop), False)

            self.api.start(
                debug=debug,
                hidden=hidden,
                on_top=bool(self.values.get("system_pin", False)),
                width=width,
                height=height,
                min_width=min_width,
                min_height=min_height,
            )

    return NoGuiVRCUtil(title, icon, root_path)
