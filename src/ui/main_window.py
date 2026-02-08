from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QSpinBox,
)

from src.ui.app_state import AppMode, SourceMode, ViewLayer
from src.ui.viewmodels.app_controller import AppController
from src.ui.widgets.params_panel import ParamsPanel
from src.ui.widgets.point_cloud_view import PointCloudView
from src.ui.widgets.results_panel import ResultsPanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Measurement GUI")
        self.resize(1200, 800)

        self._controller = AppController()
        self._defaults = self._controller.get_defaults()
        self._status_text = "Starting..."
        self._fps_value: float | None = None

        self._build_ui()
        self._wire()
        self._controller.bootstrap()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self._build_controls())
        self.point_view = PointCloudView()
        left_layout.addWidget(self.point_view, 1)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.params_panel = ParamsPanel(self._defaults)
        self.results_panel = ResultsPanel()
        right_layout.addWidget(self.params_panel)
        right_layout.addWidget(self.results_panel)
        right_layout.addStretch(1)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        self.setCentralWidget(central)
        self._update_statusbar()

        self._set_combo_to_value(self.mode_combo, self._controller.state.mode)
        self._set_combo_to_value(self.source_combo, self._controller.state.source)
        self._set_combo_to_value(self.layer_combo, self._controller.state.layer)
        self._apply_mode(self._controller.state.mode)
        self._apply_source(self._controller.state.source)

    def _build_controls(self) -> QGroupBox:
        group = QGroupBox("Controls")
        layout = QGridLayout(group)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Debug", AppMode.DEBUG)
        self.mode_combo.addItem("Use", AppMode.USE)

        self.source_combo = QComboBox()
        self.source_combo.addItem("Camera", SourceMode.CAMERA)
        self.source_combo.addItem("File (.npz)", SourceMode.FILE)

        self.layer_combo = QComboBox()
        self.layer_combo.addItem("Raw", ViewLayer.RAW)
        self.layer_combo.addItem("Downsampled", ViewLayer.DOWNSAMPLED)
        self.layer_combo.addItem("Table", ViewLayer.TABLE)
        self.layer_combo.addItem("Object", ViewLayer.OBJECT)
        self.layer_combo.addItem("Filtered", ViewLayer.FILTERED)

        self.connect_btn = QPushButton("Connect Camera")
        self.load_btn = QPushButton("Load .npz")
        self.measure_btn = QPushButton("Measure")
        self.measure_count = QSpinBox()
        self.measure_count.setRange(1, 100)
        self.measure_count.setValue(self._controller.get_measure_target())
        self.measure_count.setSingleStep(1)

        layout.addWidget(QLabel("Mode"), 0, 0)
        layout.addWidget(self.mode_combo, 0, 1)
        layout.addWidget(QLabel("Source"), 1, 0)
        layout.addWidget(self.source_combo, 1, 1)
        layout.addWidget(QLabel("Layer"), 2, 0)
        layout.addWidget(self.layer_combo, 2, 1)
        layout.addWidget(self.connect_btn, 3, 0, 1, 2)
        layout.addWidget(self.load_btn, 4, 0, 1, 2)
        layout.addWidget(QLabel("Avg frames"), 5, 0)
        layout.addWidget(self.measure_count, 5, 1)
        layout.addWidget(self.measure_btn, 6, 0, 1, 2)

        return group

    def _wire(self) -> None:
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
        self.layer_combo.currentIndexChanged.connect(self._on_layer_changed)

        self.connect_btn.clicked.connect(lambda _=False: self._controller.connect_camera())
        self.load_btn.clicked.connect(lambda _=False: self._on_load_clicked())
        self.measure_btn.clicked.connect(lambda _=False: self._controller.measure())
        self.measure_count.valueChanged.connect(self._controller.set_measure_target)

        self.params_panel.param_changed.connect(self._controller.set_param)
        self.params_panel.reset_clicked.connect(self._on_reset_params)
        self.params_panel.save_clicked.connect(self._on_save_params)

        self._controller.status_changed.connect(self._on_status_changed)
        self._controller.fps_changed.connect(self._on_fps_changed)
        self._controller.points_changed.connect(self.point_view.set_points)
        self._controller.result_changed.connect(self.results_panel.set_results)

    def _on_status_changed(self, text: str) -> None:
        self._status_text = text
        self._update_statusbar()

    def _on_fps_changed(self, fps: float) -> None:
        self._fps_value = fps
        self._update_statusbar()

    def _update_statusbar(self) -> None:
        if self._fps_value is None:
            msg = self._status_text
        else:
            msg = f"{self._status_text} | FPS: {self._fps_value:.1f}"
        self.statusBar().showMessage(msg)

    def _set_combo_to_value(self, combo: QComboBox, value: object) -> None:
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return

    def _apply_mode(self, mode: AppMode) -> None:
        self.measure_btn.setEnabled(mode == AppMode.USE)

    def _apply_source(self, source: SourceMode) -> None:
        if source == SourceMode.CAMERA:
            self.connect_btn.setEnabled(True)
            self.load_btn.setEnabled(False)
        else:
            self.connect_btn.setEnabled(False)
            self.load_btn.setEnabled(True)

    def _on_mode_changed(self, _index: int | None = None) -> None:
        mode = self.mode_combo.currentData()
        if mode is None:
            return
        self._apply_mode(mode)
        self._controller.set_mode(mode)

    def _on_source_changed(self, _index: int | None = None) -> None:
        source = self.source_combo.currentData()
        if source is None:
            return
        self._apply_source(source)
        self._controller.set_source(source)

    def _on_layer_changed(self, _index: int | None = None) -> None:
        layer = self.layer_combo.currentData()
        if layer is None:
            return
        self._controller.set_layer(layer)

    def _on_load_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open .npz",
            "",
            "NPZ Files (*.npz);;All Files (*)",
        )
        if path:
            self._controller.load_file(path)

    def _on_reset_params(self) -> None:
        self.params_panel.set_values(self._defaults)
        self._controller.reset_params()

    def _on_save_params(self) -> None:
        ok = self._controller.save_params()
        if ok:
            self._defaults = self._controller.get_defaults()

    def closeEvent(self, event) -> None:
        self._controller.shutdown()
        event.accept()
