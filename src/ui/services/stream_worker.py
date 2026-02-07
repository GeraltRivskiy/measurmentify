from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Signal, Slot


class StreamWorker(QObject):
    processed = Signal(object, object)  # DimsResult, dict[ViewLayer, np.ndarray]
    status = Signal(str)
    error = Signal(str)
    finished = Signal()

    def __init__(self, source, pipeline, cfg_lock: threading.Lock) -> None:
        super().__init__()
        self._source = source
        self._pipeline = pipeline
        self._cfg_lock = cfg_lock
        self._running = False

    @Slot()
    def run(self) -> None:
        self._running = True
        while self._running:
            try:
                frame = self._source.read()
            except StopIteration:
                self.status.emit("No more frames.")
                break
            except Exception as exc:
                self.error.emit(f"Read error: {exc}")
                break

            try:
                with self._cfg_lock:
                    dims, clouds = self._pipeline.process(frame)
            except Exception as exc:
                self.error.emit(f"Processing error: {exc}")
                continue

            self.processed.emit(dims, clouds)

        self.finished.emit()

    def stop(self) -> None:
        self._running = False
