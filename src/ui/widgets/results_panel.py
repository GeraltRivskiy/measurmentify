from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QGroupBox, QLabel, QWidget


class ResultsPanel(QGroupBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Results", parent=parent)
        self._length = QLabel("—")
        self._width = QLabel("—")
        self._height = QLabel("—")

        form = QFormLayout(self)
        form.addRow("Length (mm)", self._length)
        form.addRow("Width (mm)", self._width)
        form.addRow("Height (mm)", self._height)

    def set_results(self, length: float, width: float, height: float) -> None:
        self._length.setText(f"{length:.2f}")
        self._width.setText(f"{width:.2f}")
        self._height.setText(f"{height:.2f}")
