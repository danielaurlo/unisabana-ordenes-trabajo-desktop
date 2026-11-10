"""Native desktop interface for Gestor de Contratos."""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QDate, QObject, Qt, QThread, Signal, Slot
from PySide6.QtGui import QAction, QColor, QPalette
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import (
    QApplication,
    QDateEdit,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from gestor_contratos.models.orden_trabajo import OrdenTrabajoData
from gestor_contratos.services.combined_pdf_generator import (
    CombinedPDFGenerationError,
    CombinedPDFGenerator,
)
from gestor_contratos.services.excel_generator import (
    ExcelGenerationError,
    ExcelGenerator,
)
from gestor_contratos.services.excel_preview import ExcelPreviewError
from gestor_contratos.services.order_extractor import OrdenTrabajoExtractor
from gestor_contratos.services.pdf_extractor import PDFExtractionError


class ProcessingResult:
    def __init__(
        self,
        pdf: bytes,
        data: OrdenTrabajoData,
        excel: bytes | None,
        acta: bytes | None,
        combined: bytes | None,
        warning: str | None = None,
    ):
        self.pdf, self.data, self.excel = pdf, data, excel
        self.acta, self.combined = acta, combined
        self.warning = warning


class Processor(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, pdf: bytes):
        super().__init__()
        self.pdf = pdf

    @Slot()
    def run(self) -> None:
        try:
            data = OrdenTrabajoExtractor().extract(self.pdf)
            excel = acta = combined = None
            warning = None
            if not data.campos_ambiguos:
                excel = ExcelGenerator().generate(data)
                try:
                    result = CombinedPDFGenerator().generate(self.pdf, excel)
                except (ExcelPreviewError, CombinedPDFGenerationError) as exc:
                    warning = str(exc)
                else:
                    acta, combined = result.acta_pdf_bytes, result.combined_pdf_bytes
            self.finished.emit(
                ProcessingResult(self.pdf, data, excel, acta, combined, warning)
            )
        except (
            PDFExtractionError,
            ExcelGenerationError,
            CombinedPDFGenerationError,
        ) as exc:
            self.failed.emit(str(exc))


EMPTY_DATE = QDate(1900, 1, 1)


def qdate(value):
    return QDate(value.year, value.month, value.day) if value else EMPTY_DATE


def date_value(widget: QDateEdit):
    value = widget.date()
    return None if value == EMPTY_DATE else value.toPython()


class PdfPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.document = QPdfDocument(self)
        self._temporary_path: Path | None = None
        self._pending_paths: set[Path] = set()
        self.document.statusChanged.connect(self._handle_document_status)
        self.viewer = QPdfView(self)
        self.viewer.setDocument(self.document)
        self.viewer.setPageMode(QPdfView.PageMode.MultiPage)
        self.viewer.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self.viewer.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.viewer)

    @Slot(object)
    def _handle_document_status(self, status) -> None:
        """Remove old files after QPdfDocument releases them.

        ``close()`` can leave the document in ``Unloading`` temporarily. This
        matters on Windows, where deleting the file during that state raises
        ``PermissionError`` because the PDF engine still has an open handle.
        """
        if status == QPdfDocument.Status.Null:
            self._cleanup_pending_paths()

    def _cleanup_pending_paths(self) -> None:
        for path in tuple(self._pending_paths):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                # Qt may still be releasing the handle even after notifying
                # the status change. Keep the path for the next notification
                # rather than allowing a UI update to fail.
                continue
            self._pending_paths.discard(path)

    def show_bytes(self, content: bytes | None):
        self.document.close()
        if self._temporary_path is not None:
            self._pending_paths.add(self._temporary_path)
            self._temporary_path = None
        if self.document.status() == QPdfDocument.Status.Null:
            self._cleanup_pending_paths()
        if content is None:
            return
        handle = tempfile.NamedTemporaryFile(
            prefix="gestor_contratos_", suffix=".pdf", delete=False
        )
        handle.write(content)
        handle.close()
        self._temporary_path = Path(handle.name)
        self.document.load(handle.name)

    def closeEvent(self, event):
        self.show_bytes(None)
        super().closeEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestor de órdenes de trabajo")
        self.resize(980, 640)
        self.setMinimumSize(820, 540)
        self.source_pdf: bytes | None = None
        self.source_name = ""
        self.data: OrdenTrabajoData | None = None
        self.excel: bytes | None = None
        self.combined: bytes | None = None
        self.acta_view = PdfPanel()
        self.document_view = PdfPanel()
        self._build_ui()

    def _build_ui(self):
        open_action = QAction("Abrir PDF", self)
        open_action.triggered.connect(self.open_pdf)
        self.menuBar().addMenu("Archivo").addAction(open_action)

        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        splitter = QSplitter(Qt.Horizontal)
        outer.addWidget(splitter)

        left = QWidget()
        left.setMinimumWidth(280)
        left.setMaximumWidth(360)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 12, 12, 12)
        group = QGroupBox("Documento fuente")
        group_layout = QVBoxLayout(group)
        self.file_label = QLabel("Ningún PDF seleccionado")
        self.file_label.setWordWrap(True)
        choose = QPushButton("Seleccionar orden PDF")
        choose.setObjectName("secondaryButton")
        choose.clicked.connect(self.open_pdf)
        self.process_button = QPushButton("Procesar documento")
        self.process_button.setObjectName("primaryButton")
        self.process_button.setEnabled(False)
        self.process_button.clicked.connect(self.process)
        group_layout.addWidget(self.file_label)
        group_layout.addWidget(choose)
        group_layout.addWidget(self.process_button)
        left_layout.addWidget(group)
        self.form = self._build_form()
        left_layout.addStretch()
        splitter.addWidget(left)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.document_view, "Documento")
        self.tabs.addTab(self.form, "Revisar datos")
        acta_tab = QWidget()
        acta_layout = QVBoxLayout(acta_tab)
        acta_layout.setContentsMargins(12, 12, 12, 12)
        acta_layout.addWidget(self.acta_view, 1)
        acta_actions = QHBoxLayout()
        acta_actions.setSpacing(12)
        self.save_excel = QPushButton("Guardar Excel")
        self.save_pdf = QPushButton("Guardar orden y acta PDF")
        self.save_excel.setObjectName("secondaryButton")
        self.save_pdf.setObjectName("primaryButton")
        self.save_excel.clicked.connect(self.save_excel_file)
        self.save_pdf.clicked.connect(self.save_pdf_file)
        self.save_excel.setEnabled(False)
        self.save_pdf.setEnabled(False)
        acta_actions.addWidget(self.save_excel)
        acta_actions.addWidget(self.save_pdf)
        acta_layout.addLayout(acta_actions)
        self.tabs.addTab(acta_tab, "Acta")
        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([320, 960])
        self.tabs.setDocumentMode(True)
        self.setStyleSheet(
            """
            QMainWindow { background: #f7f8fa; }
            QGroupBox {
                border: 1px solid #d9dee5;
                border-radius: 5px;
                margin-top: 10px;
                padding: 12px 8px 8px 8px;
                color: #344451;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                background: #f7f8fa;
            }
            QPushButton {
                min-height: 38px;
                padding: 0 12px;
                border: 1px solid #cbd3db;
                border-radius: 4px;
                background: #ffffff;
                color: #344451;
            }
            QPushButton:hover { background: #f0f4f7; }
            QPushButton:disabled { color: #9aa5af; background: #edf0f2; }
            QPushButton#primaryButton {
                border-color: #176b87;
                background: #176b87;
                color: white;
            }
            QPushButton#primaryButton:hover { background: #12566d; }
            QPushButton#secondaryButton { color: #176b87; }
            QLineEdit, QDateEdit {
                min-height: 38px;
                min-width: 170px;
                padding: 0 7px;
                border: 1px solid #cbd3db;
                border-radius: 4px;
                background: white;
            }
            QLineEdit:focus, QDateEdit:focus { border: 1px solid #176b87; }
            QTabWidget::pane { border: 1px solid #d9dee5; background: white; }
            QTabBar::tab {
                min-width: 110px;
                min-height: 32px;
                padding: 0 12px;
                color: #65727d;
            }
            QTabBar::tab:selected { color: #176b87; font-weight: 600; }
            QStatusBar {
                min-height: 30px;
                padding-left: 8px;
                color: #344451;
                background: #e9eef2;
                font-size: 13px;
            }
            """
        )
        self.statusBar().setSizeGripEnabled(False)

    def _build_form(self):
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(16)
        self.fields = {}
        text_fields = (
            ("nombre", "Nombre del proveedor"),
            ("nit", "NIT"),
            ("direccion", "Dirección"),
            ("telefono", "Teléfono"),
            ("numero_orden", "Número de orden"),
        )
        for index, (key, label) in enumerate(text_fields):
            field = QLineEdit()
            field.setEnabled(False)
            self.fields[key] = field
            row, column = divmod(index, 2)
            label_widget = QLabel(label)
            label_widget.setStyleSheet("font-weight: 600; color: #405261;")
            layout.addWidget(label_widget, row * 2, column * 2)
            layout.addWidget(field, row * 2, column * 2 + 1)
        date_fields = (
            ("fecha_orden", "Fecha de orden"),
            ("fecha_vencimiento", "Fecha de entrega"),
            ("fecha_acta", "Fecha del acta"),
        )
        for index, (key, label) in enumerate(date_fields):
            field = QDateEdit()
            field.setMinimumWidth(170)
            field.setCalendarPopup(True)
            field.setMinimumDate(EMPTY_DATE)
            field.setSpecialValueText("Sin fecha")
            field.setDate(EMPTY_DATE)
            field.setEnabled(False)
            self.fields[key] = field
            row, column = divmod(index, 2)
            row += 6
            label_widget = QLabel(label)
            label_widget.setStyleSheet("font-weight: 600; color: #405261;")
            layout.addWidget(label_widget, row, column * 2)
            layout.addWidget(field, row, column * 2 + 1)
        self.update_button = QPushButton("Guardar cambios y actualizar acta")
        self.update_button.clicked.connect(self.update_data)
        self.update_button.setEnabled(False)
        self.update_button.setObjectName("primaryButton")
        layout.addWidget(self.update_button, 9, 0, 1, 4)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)
        layout.setRowStretch(10, 1)
        return widget

    def open_pdf(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar orden de trabajo", "", "Documentos PDF (*.pdf)"
        )
        if not path:
            return
        try:
            source_pdf = Path(path).read_bytes()
        except OSError as exc:
            QMessageBox.critical(self, "No fue posible abrir el PDF", str(exc))
            return
        self.source_pdf = source_pdf
        self.source_name = Path(path).name
        self.data = None
        self.excel = None
        self.combined = None
        self.acta_view.show_bytes(None)
        self.update_button.setEnabled(False)
        for field in self.fields.values():
            if isinstance(field, QDateEdit):
                field.setDate(EMPTY_DATE)
            else:
                field.clear()
            field.setEnabled(False)
        self.save_excel.setEnabled(False)
        self.save_pdf.setEnabled(False)
        self.file_label.setText(self.source_name)
        self.process_button.setEnabled(True)
        self.document_view.show_bytes(self.source_pdf)
        self.tabs.setCurrentIndex(0)
        self.statusBar().showMessage("PDF cargado")

    def process(self):
        if not self.source_pdf:
            return
        self.process_button.setEnabled(False)
        self.statusBar().showMessage("Procesando documento…")
        self.thread = QThread(self)
        self.worker = Processor(self.source_pdf)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.process_finished)
        self.worker.failed.connect(self.process_failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    @Slot(object)
    def process_finished(self, result):
        self.data, self.excel, self.combined = (
            result.data,
            result.excel,
            result.combined,
        )
        self.acta_view.show_bytes(result.acta)
        self.fill_form()
        self.tabs.setCurrentIndex(1)
        self.process_button.setEnabled(True)
        self.update_button.setEnabled(True)
        self.save_excel.setEnabled(result.excel is not None)
        self.save_pdf.setEnabled(result.combined is not None)
        self.statusBar().showMessage("Documento procesado")
        if result.warning:
            QMessageBox.warning(self, "PDF no generado", result.warning)
        if self.data.campos_ambiguos:
            QMessageBox.warning(
                self,
                "Revisión necesaria",
                "Hay datos ambiguos. Revise y guarde los campos antes de "
                "generar el acta.",
            )

    def process_failed(self, message):
        self.process_button.setEnabled(True)
        QMessageBox.critical(self, "No fue posible procesar", message)

    def fill_form(self):
        p = self.data.proveedor
        for field in self.fields.values():
            field.setEnabled(True)
        values = {
            "nombre": p.nombre,
            "nit": p.nit,
            "direccion": p.direccion,
            "telefono": p.telefono,
            "numero_orden": self.data.numero_orden,
        }
        for key, value in values.items():
            self.fields[key].setText(value or "")
        for key in ("fecha_orden", "fecha_vencimiento", "fecha_acta"):
            self.fields[key].setDate(qdate(getattr(self.data, key)))

    def update_data(self):
        if not self.data:
            return
        p = self.data.proveedor.model_copy(
            update={
                k: self.fields[k].text().strip() or None
                for k in ("nombre", "nit", "direccion", "telefono")
            }
        )
        values = {
            "proveedor": p,
            "numero_orden": self.fields["numero_orden"].text().strip() or None,
            "fecha_orden": date_value(self.fields["fecha_orden"]),
            "fecha_vencimiento": date_value(self.fields["fecha_vencimiento"]),
            "fecha_acta": date_value(self.fields["fecha_acta"]),
            "campos_ambiguos": [],
        }
        required = {
            "proveedor.nombre": p.nombre,
            "proveedor.nit": p.nit,
            "proveedor.direccion": p.direccion,
            "proveedor.telefono": p.telefono,
            "numero_orden": values["numero_orden"],
            "fecha_orden": values["fecha_orden"],
            "fecha_vencimiento": values["fecha_vencimiento"],
            "fecha_acta": values["fecha_acta"],
        }
        if (
            values["fecha_acta"]
            and values["fecha_orden"]
            and values["fecha_acta"] < values["fecha_orden"]
        ):
            QMessageBox.warning(
                self,
                "Fecha inválida",
                "La fecha del acta no puede ser anterior a la fecha de la orden.",
            )
            return
        values["campos_faltantes"] = [
            key for key, value in required.items() if not value
        ]
        try:
            updated_data = OrdenTrabajoData.model_validate(
                self.data.model_dump() | values
            )
            excel = ExcelGenerator().generate(updated_data)
        except (ValueError, ExcelGenerationError) as exc:
            QMessageBox.critical(self, "No fue posible guardar", str(exc))
            return
        self.data = updated_data
        self.excel = excel
        try:
            result = CombinedPDFGenerator().generate(self.source_pdf, excel)
        except (ExcelPreviewError, CombinedPDFGenerationError) as exc:
            self.combined = None
            self.acta_view.show_bytes(None)
            self.save_excel.setEnabled(True)
            self.save_pdf.setEnabled(False)
            self.statusBar().showMessage("Excel actualizado; PDF pendiente")
            QMessageBox.warning(self, "PDF no generado", str(exc))
            return
        self.combined, acta = result.combined_pdf_bytes, result.acta_pdf_bytes
        self.acta_view.show_bytes(acta)
        self.save_excel.setEnabled(True)
        self.save_pdf.setEnabled(True)
        self.tabs.setCurrentIndex(2)
        self.statusBar().showMessage("Cambios guardados y acta actualizada")

    def save_excel_file(self):
        if not self.excel:
            return
        number = re.sub(r"[^A-Za-z0-9_-]", "", self.data.numero_orden or "")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Excel",
            f"OT_{number or 'Acta'}_Acta_Entrega.xlsx",
            "Excel (*.xlsx)",
        )
        if path:
            try:
                Path(path).write_bytes(self.excel)
            except OSError as exc:
                QMessageBox.critical(self, "No fue posible guardar el Excel", str(exc))

    def save_pdf_file(self):
        if not self.combined:
            return
        number = re.sub(r"[^A-Za-z0-9_-]", "", self.data.numero_orden or "")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar PDF",
            f"OT_{number or 'Orden'}_Orden_y_Acta.pdf",
            "PDF (*.pdf)",
        )
        if path:
            try:
                Path(path).write_bytes(self.combined)
            except OSError as exc:
                QMessageBox.critical(self, "No fue posible guardar el PDF", str(exc))


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Gestor de órdenes de trabajo")
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#f7f8fa"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#344451"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#f2f4f6"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#344451"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#344451"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#176b87"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)
    window = MainWindow()
    screen = app.primaryScreen()
    if screen is not None:
        available = screen.availableGeometry()
        frame = window.frameGeometry()
        frame.moveCenter(available.center())
        window.move(frame.topLeft())
    window.show()
    sys.exit(app.exec())
