from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ParamsPanel(QGroupBox):
    param_changed = Signal(str, str)
    reset_clicked = Signal()
    save_clicked = Signal()

    def __init__(self, defaults: dict[str, object], parent: QWidget | None = None) -> None:
        super().__init__("Parameters", parent=parent)
        self._inputs: dict[str, QLineEdit] = {}

        root = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        root.addLayout(form)

        for name, value in defaults.items():
            label = QLabel(name)
            edit = QLineEdit(str(value))
            edit.editingFinished.connect(lambda n=name, e=edit: self.param_changed.emit(n, e.text()))
            self._inputs[name] = edit
            form.addRow(label, edit)

        buttons = QHBoxLayout()
        self.reset_btn = QPushButton("Reset")
        self.save_btn = QPushButton("Save")
        self.reset_btn.clicked.connect(lambda _=False: self.reset_clicked.emit())
        self.save_btn.clicked.connect(lambda _=False: self.save_clicked.emit())
        buttons.addWidget(self.reset_btn)
        buttons.addWidget(self.save_btn)
        root.addLayout(buttons)

    def set_values(self, values: dict[str, object]) -> None:
        for name, value in values.items():
            if name in self._inputs:
                self._inputs[name].setText(str(value))

    def values(self) -> dict[str, str]:
        return {name: edit.text() for name, edit in self._inputs.items()}
