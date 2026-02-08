from __future__ import annotations

import numbers
import re
import threading
import time
from dataclasses import asdict
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from src.config import DimsAlgoConfig
from src.core.pipeline import Pipeline
from src.ui.app_state import AppMode, AppState, SourceMode, ViewLayer
from src.ui.services.stream_worker import StreamWorker


class AppController(QObject):
    status_changed = Signal(str)
    fps_changed = Signal(float)
    result_changed = Signal(float, float, float)
    points_changed = Signal(object)
    mode_changed = Signal(AppMode)
    source_changed = Signal(SourceMode)
    layer_changed = Signal(ViewLayer)

    def __init__(self) -> None:
        super().__init__()
        self.state = AppState()
        self._config = DimsAlgoConfig()
        self._defaults = asdict(self._config)
        self._pipeline = Pipeline(self._config)
        self._source = None
        self._thread: QThread | None = None
        self._worker: StreamWorker | None = None
        self._cfg_lock = threading.Lock()
        self._latest_clouds: dict[ViewLayer, object] | None = None
        self._latest_dims = None
        self._measure_active = False
        self._measure_target = 5
        self._measure_count = 0
        self._measure_sum = [0.0, 0.0, 0.0]
        self._fps_last = time.monotonic()
        self._fps_count = 0
        self._fps_value = 0.0

    def bootstrap(self) -> None:
        self.status_changed.emit("Ready.")

    def set_mode(self, mode: AppMode) -> None:
        mode = self._coerce_enum(AppMode, mode)
        if mode is None:
            self.status_changed.emit("Invalid mode value.")
            return
        if self.state.mode == mode:
            return
        self.state.mode = mode
        self._measure_active = False
        self.mode_changed.emit(mode)
        self.status_changed.emit(f"Mode set to: {mode.value}")

    def set_source(self, source: SourceMode) -> None:
        source = self._coerce_enum(SourceMode, source)
        if source is None:
            self.status_changed.emit("Invalid source value.")
            return
        if self.state.source == source:
            return
        self._stop_stream()
        self.state.source = source
        self.source_changed.emit(source)
        self.status_changed.emit(f"Source set to: {source.value}")

    def set_layer(self, layer: ViewLayer) -> None:
        layer = self._coerce_enum(ViewLayer, layer)
        if layer is None:
            self.status_changed.emit("Invalid layer value.")
            return
        if self.state.layer == layer:
            return
        self.state.layer = layer
        self.layer_changed.emit(layer)
        self.status_changed.emit(f"Layer set to: {layer.value}")
        self._emit_current_layer()

    def connect_camera(self) -> None:
        self._stop_stream()
        try:
            from src.acquisition.orbbec import OrbbecSource
        except Exception as exc:
            self.status_changed.emit(f"Failed to import camera source: {exc}")
            return
        try:
            self._source = OrbbecSource()
        except Exception as exc:
            self.status_changed.emit(f"Camera init failed: {exc}")
            return
        self.state.camera_connected = True
        self.status_changed.emit("Camera connected.")
        self._start_stream()

    def load_file(self, path: str) -> None:
        self._stop_stream()
        try:
            from src.acquisition.replay import ReplaySource
        except Exception as exc:
            self.status_changed.emit(f"Failed to import replay source: {exc}")
            return
        try:
            self._source = ReplaySource(data_dir=path, loop=True, config_path="configs/config.yaml")
        except Exception as exc:
            self.status_changed.emit(f"Failed to open file: {exc}")
            return
        self.state.last_file = path
        self.status_changed.emit(f"Loaded file: {path}")
        self._start_stream()

    def measure(self) -> None:
        if self.state.mode != AppMode.USE:
            self.status_changed.emit("Measurement is available in USE mode.")
            return
        self._measure_active = True
        self._measure_count = 0
        self._measure_sum = [0.0, 0.0, 0.0]
        self.status_changed.emit(
            f"Measurement started. Collecting {self._measure_target} frames."
        )

    def set_measure_target(self, count: int) -> None:
        try:
            value = int(count)
        except (TypeError, ValueError):
            self.status_changed.emit("Invalid measurement count.")
            return
        if value < 1:
            value = 1
        if value == self._measure_target:
            return
        self._measure_target = value
        if self._measure_active:
            self._measure_count = 0
            self._measure_sum = [0.0, 0.0, 0.0]
            self.status_changed.emit(
                f"Measurement count updated to {value}. Restarting measurement."
            )
        else:
            self.status_changed.emit(f"Measurement count set to {value}.")

    def get_measure_target(self) -> int:
        return int(self._measure_target)

    def set_param(self, name: str, value: str) -> None:
        if not hasattr(self._config, name):
            self.status_changed.emit(f"Unknown parameter: {name}")
            return
        current = getattr(self._config, name)
        try:
            parsed = self._parse_value(current, value)
        except ValueError as exc:
            self.status_changed.emit(f"Invalid value for {name}: {exc}")
            return
        with self._cfg_lock:
            setattr(self._config, name, parsed)
            self._pipeline.cfg = self._config
        self.status_changed.emit(f"Param updated: {name}={parsed}")

    def reset_params(self) -> None:
        with self._cfg_lock:
            for key, value in self._defaults.items():
                setattr(self._config, key, value)
            self._pipeline.cfg = self._config
        self.status_changed.emit("Parameters reset to defaults.")

    def save_params(self) -> bool:
        with self._cfg_lock:
            values = asdict(self._config)
        try:
            self._write_config_values(values)
        except Exception as exc:
            self.status_changed.emit(f"Failed to save config.py: {exc}")
            return False
        self._defaults = dict(values)
        self.status_changed.emit("Parameters saved to config.py.")
        return True

    def get_defaults(self) -> dict[str, object]:
        return dict(self._defaults)

    def shutdown(self) -> None:
        self._stop_stream()

    def _parse_value(self, current: object, text: str):
        if isinstance(current, bool):
            return text.strip().lower() in {"1", "true", "yes", "y", "on"}
        if isinstance(current, numbers.Integral):
            return int(float(text))
        return float(text)

    def _coerce_enum(self, enum_cls, value):
        if isinstance(value, enum_cls):
            return value
        if isinstance(value, str):
            raw = value.strip()
            try:
                return enum_cls(raw)
            except Exception:
                pass
            lowered = raw.lower()
            for item in enum_cls:
                if item.value == lowered or item.name.lower() == lowered:
                    return item
        return None

    def _start_stream(self) -> None:
        if self._source is None:
            self.status_changed.emit("No source selected.")
            return
        self._fps_last = time.monotonic()
        self._fps_count = 0
        self._thread = QThread()
        self._worker = StreamWorker(self._source, self._pipeline, self._cfg_lock)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.processed.connect(self._on_processed)
        self._worker.status.connect(self.status_changed)
        self._worker.error.connect(self.status_changed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _stop_stream(self) -> None:
        if self._worker is not None:
            self._worker.stop()
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(1000)
        self._thread = None
        self._worker = None

    def _on_processed(self, dims, clouds: dict[ViewLayer, object]) -> None:
        self._latest_dims = dims
        self._latest_clouds = clouds
        self._emit_current_layer()
        self._update_fps()

        if self.state.mode == AppMode.DEBUG:
            self._emit_result(dims)
            return
        if self._measure_active:
            self._measure_sum[0] += dims.length
            self._measure_sum[1] += dims.width
            self._measure_sum[2] += dims.height
            self._measure_count += 1
            if self._measure_count >= self._measure_target:
                avg = [
                    self._measure_sum[0] / self._measure_count,
                    self._measure_sum[1] / self._measure_count,
                    self._measure_sum[2] / self._measure_count,
                ]
                self._measure_active = False
                self.result_changed.emit(avg[0], avg[1], avg[2])
                self.status_changed.emit(
                    f"Measurement captured (avg of {self._measure_count} frames)."
                )
            else:
                self.status_changed.emit(
                    f"Measuring... {self._measure_count}/{self._measure_target}"
                )

    def _emit_current_layer(self) -> None:
        if not self._latest_clouds:
            return
        layer = self.state.layer
        if layer in self._latest_clouds:
            self.points_changed.emit(self._latest_clouds[layer])

    def _emit_result(self, dims) -> None:
        self.result_changed.emit(dims.length, dims.width, dims.height)

    def _update_fps(self) -> None:
        self._fps_count += 1
        now = time.monotonic()
        dt = now - self._fps_last
        if dt >= 0.5:
            fps = self._fps_count / dt
            self._fps_count = 0
            self._fps_last = now
            self._fps_value = fps
            self.fps_changed.emit(fps)

    def _config_file_path(self) -> Path:
        return Path(__file__).resolve().parents[3] / "src" / "config.py"

    def _to_literal(self, value: object) -> str:
        if isinstance(value, bool):
            return "True" if value else "False"
        if isinstance(value, numbers.Integral):
            return str(int(value))
        if isinstance(value, numbers.Real):
            return repr(float(value))
        return repr(value)

    def _write_config_values(self, values: dict[str, object]) -> None:
        path = self._config_file_path()
        if not path.exists():
            raise FileNotFoundError(f"config.py not found at {path}")
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

        annotated_re = re.compile(r"^(\s*)(\w+)\s*:\s*([^=]+?)\s*=\s*(.+?)(\s+#.*)?$")
        simple_re = re.compile(r"^(\s*)(\w+)\s*=\s*(.+?)(\s+#.*)?$")

        in_class = False
        class_indent = 0
        for idx, line in enumerate(lines):
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            if not in_class:
                if stripped.startswith("class DimsAlgoConfig"):
                    in_class = True
                    class_indent = indent
                continue

            if stripped and indent <= class_indent:
                in_class = False
                continue

            if not stripped.strip() or stripped.lstrip().startswith("#"):
                continue

            m = annotated_re.match(line)
            if m:
                name = m.group(2)
                if name in values:
                    annotation = m.group(3).strip()
                    comment = m.group(5) or ""
                    new_val = self._to_literal(values[name])
                    new_line = f"{m.group(1)}{name}: {annotation} = {new_val}{comment}"
                    if line.endswith("\n"):
                        new_line += "\n"
                    lines[idx] = new_line
                continue

            m = simple_re.match(line)
            if m:
                name = m.group(2)
                if name in values:
                    comment = m.group(4) or ""
                    new_val = self._to_literal(values[name])
                    new_line = f"{m.group(1)}{name} = {new_val}{comment}"
                    if line.endswith("\n"):
                        new_line += "\n"
                    lines[idx] = new_line

        path.write_text("".join(lines), encoding="utf-8")
