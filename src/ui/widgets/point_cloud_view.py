from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QOffscreenSurface, QOpenGLContext, QSurfaceFormat
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

pg = None
gl = None
np = None
_HAS_PG = False
_PG_IMPORT_ERROR: Exception | None = None
_GL_WARMUP: tuple[QOffscreenSurface, QOpenGLContext] | None = None


def _prime_glx() -> bool:
    """Initialize GLX via Qt before PyOpenGL loads libGL.* (avoids GLX init crash)."""
    global _GL_WARMUP
    if _GL_WARMUP is not None:
        return True
    if QGuiApplication.instance() is None:
        return False

    fmt = QSurfaceFormat.defaultFormat()
    if fmt.renderableType() == QSurfaceFormat.DefaultRenderableType:
        fmt.setRenderableType(QSurfaceFormat.OpenGL)

    surface = QOffscreenSurface()
    surface.setFormat(fmt)
    surface.create()
    if not surface.isValid():
        return False

    ctx = QOpenGLContext()
    ctx.setFormat(fmt)
    if not ctx.create():
        return False
    if not ctx.makeCurrent(surface):
        return False
    ctx.doneCurrent()

    _GL_WARMUP = (surface, ctx)
    return True


def _ensure_pyqtgraph() -> bool:
    global pg, gl, np, _HAS_PG, _PG_IMPORT_ERROR
    if _HAS_PG:
        return True
    if _PG_IMPORT_ERROR is not None:
        return False
    try:
        _prime_glx()
        import pyqtgraph as pg_mod
        import pyqtgraph.opengl as gl_mod
        import numpy as np_mod

        pg = pg_mod
        gl = gl_mod
        np = np_mod
        _HAS_PG = True
    except Exception as exc:
        _PG_IMPORT_ERROR = exc
        _HAS_PG = False
        print(f"PointCloudView: failed to init OpenGL: {exc}")
    return _HAS_PG


class PointCloudView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if _ensure_pyqtgraph():
            self._view = gl.GLViewWidget()
            self._view.setBackgroundColor("k")
            self._view.opts["distance"] = 600

            grid = gl.GLGridItem()
            grid.scale(50, 50, 1)
            self._view.addItem(grid)

            axis = gl.GLAxisItem()
            axis.setSize(100, 100, 100)
            self._view.addItem(axis)

            self._scatter = gl.GLScatterPlotItem(
                pos=np.zeros((1, 3), dtype=np.float32),
                size=3,
                color=(0.2, 0.8, 1.0, 1.0),
            )
            self._view.addItem(self._scatter)
            layout.addWidget(self._view)
        else:
            self._view = None
            self._scatter = None
            placeholder_lines = ["3D view placeholder", "OpenGL init failed."]
            placeholder = QLabel("\n".join(placeholder_lines))
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet(
                "QLabel { border: 1px solid #444; color: #bbb; padding: 16px; }"
            )
            layout.addWidget(placeholder)

    def set_points(self, points) -> None:
        if not _ensure_pyqtgraph() or self._scatter is None:
            return
        if points is None or len(points) == 0:
            points = np.zeros((1, 3), dtype=np.float32)
        self._scatter.setData(pos=points)
