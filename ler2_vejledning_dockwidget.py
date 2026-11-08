# -*- coding: utf-8 -*-
"""Dock panel: look up the LER 2 data model (attributes and code lists) and
compare the active layer to it."""

import re

from qgis.core import Qgis, QgsProject, QgsSettings, QgsVectorLayer
from qgis.PyQt.QtCore import Qt, QUrl, pyqtSignal
from qgis.PyQt.QtGui import QBrush, QColor, QDesktopServices, QFont
from qgis.PyQt.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDockWidget, QFrame,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton, QSplitter, QTableWidget,
    QTableWidgetItem, QTabWidget, QTextEdit, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)

from .datamodel import DataLoader, truthy
from .i18n import tr

GUIDE_URL = "https://valideringsportalen.dk/vejledning.php"
ROLE = Qt.ItemDataRole.UserRole

RED = QBrush(QColor(192, 40, 40))
ORANGE = QBrush(QColor(200, 110, 10))
GREEN = QBrush(QColor(40, 140, 70))
GREY = QBrush(QColor(130, 130, 130))

AUTO_MATCH_KEY = "LER2Vejledning/auto_match"

Z_EXCEPTION_TYPES = {"elledning", "telekommunikationsledning", "føringsrør"}

# Raw values published by the data model -> translation keys, for display only.
OCCURRENCE_KEYS = {"Obligatorisk": "occ_mandatory", "Betinget": "occ_conditional", "Frivillig": "occ_optional"}
YES_NO_KEYS = {"ja": "yes", "nej": "no"}


def _occurrence_label(value):
    key = OCCURRENCE_KEYS.get(value)
    return tr(key) if key else value


def _yes_no_label(value):
    key = YES_NO_KEYS.get(str(value).strip().lower())
    return tr(key) if key else value


def _format_condition(text):
    text = re.sub(r"(?<=[:;])\*\s*", "\n• ", text)
    return re.sub(r"\.(?=[A-ZÆØÅ])", ".\n", text)


def _make_values_table(columns):
    table = QTableWidget(0, len(columns))
    table.setHorizontalHeaderLabels(columns)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setStretchLastSection(True)
    table.verticalHeader().setVisible(False)
    table.setWordWrap(True)
    return table


class LER2VejledningDockWidget(QDockWidget):
    closingPlugin = pyqtSignal()
    PLUGIN_NAME = "LER 2-Vejledning"

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.model = None
        self.layer_id = None

        self._build_ui()

        self.loader = DataLoader(self)
        self.loader.updated.connect(self.on_data_updated)
        self.loader.failed.connect(self.on_data_failed)

        cached = self.loader.load_cache()
        if cached is not None:
            self.set_model(cached)
            self.set_status(tr("status_cache"))
        else:
            self.set_status(tr("status_fetching"))
        self.loader.refresh()

        self.iface.currentLayerChanged.connect(self.on_active_layer_changed)
        self.on_active_layer_changed(self.iface.activeLayer())

    def shutdown(self):
        try:
            self.iface.currentLayerChanged.disconnect(self.on_active_layer_changed)
        except (TypeError, RuntimeError):
            pass

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        self.setWindowTitle(self.PLUGIN_NAME)
        container = QWidget(self)
        self.setWidget(container)
        layout = QVBoxLayout(container)

        howto = QLabel(tr("howto"))
        howto.setWordWrap(True)
        howto.setTextFormat(Qt.TextFormat.RichText)
        howto.setFrameShape(QFrame.Shape.StyledPanel)
        howto.setStyleSheet("QLabel { background: #fff4e0; color: #222222; padding: 6px; }")
        layout.addWidget(howto)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_attributes_tab(), tr("tab_attributes"))
        self.tabs.addTab(self._build_codes_tab(), tr("tab_codelists"))
        layout.addWidget(self.tabs, 1)

        footer = QHBoxLayout()
        self.lbl_status = QLabel("")
        self.lbl_status.setWordWrap(True)
        footer.addWidget(self.lbl_status, 1)
        self.btn_web = QPushButton(tr("open_web"))
        footer.addWidget(self.btn_web)
        layout.addLayout(footer)

        disclaimer = QLabel(tr("disclaimer"))
        disclaimer.setWordWrap(True)
        disclaimer.setStyleSheet("QLabel { color: #666; font-style: italic; }")
        layout.addWidget(disclaimer)

        self._show_values(None)
        self._update_z_note()
        self.btn_web.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GUIDE_URL)))

    def _build_attributes_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        type_row = QHBoxLayout()
        type_row.addWidget(QLabel(tr("object_type_label")))
        self.cbo_type = QComboBox()
        self.cbo_type.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.cbo_type.setMinimumContentsLength(12)
        type_row.addWidget(self.cbo_type, 1)
        self.btn_match = QPushButton(tr("match_layer"))
        self.btn_match.setToolTip(tr("match_layer_tip"))
        type_row.addWidget(self.btn_match)
        layout.addLayout(type_row)

        self.chk_auto_match = QCheckBox(tr("auto_match"))
        self.chk_auto_match.setToolTip(tr("auto_match_tip"))
        self.chk_auto_match.setChecked(QgsSettings().value(AUTO_MATCH_KEY, True, type=bool))
        layout.addWidget(self.chk_auto_match)

        z_row = QHBoxLayout()
        self.lbl_z_note = QLabel("")
        self.lbl_z_note.setWordWrap(True)
        self.lbl_z_note.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_z_note.setStyleSheet("QLabel { background: #fdecc8; color: #222222; padding: 4px; }")
        z_row.addWidget(self.lbl_z_note, 1)
        self.btn_z_info = QPushButton("ⓘ")
        self.btn_z_info.setFixedWidth(32)
        self.btn_z_info.setToolTip(tr("z_info_tip"))
        z_row.addWidget(self.btn_z_info, 0, Qt.AlignmentFlag.AlignTop)
        self.z_widgets = (self.lbl_z_note, self.btn_z_info)
        layout.addLayout(z_row)

        self.lbl_layer = QLabel("")
        self.lbl_layer.setWordWrap(True)
        layout.addWidget(self.lbl_layer)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText(tr("search_attributes_placeholder"))
        self.txt_search.setClearButtonEnabled(True)
        layout.addWidget(self.txt_search)

        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter, 1)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels([
            tr("col_object_type"), tr("col_attribute"), tr("col_requirement"), tr("col_layer_field"),
        ])
        self.tree.setRootIsDecorated(False)
        self.tree.setUniformRowHeights(True)
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self.tree.header()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(False)
        splitter.addWidget(self.tree)

        bottom = QWidget()
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        self.txt_detail = QTextEdit()
        self.txt_detail.setReadOnly(True)
        self.txt_detail.setAcceptRichText(False)
        bottom_layout.addWidget(self.txt_detail)
        self.tbl_values = _make_values_table([tr("col_value"), tr("col_description")])
        bottom_layout.addWidget(self.tbl_values)
        self.btn_copy = QPushButton(tr("copy_value"))
        self.btn_copy.setToolTip(tr("copy_value_tip"))
        bottom_layout.addWidget(self.btn_copy)
        splitter.addWidget(bottom)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        self.cbo_type.currentIndexChanged.connect(self.populate)
        self.btn_match.clicked.connect(
            lambda: self.on_active_layer_changed(self.iface.activeLayer(), force=True))
        self.chk_auto_match.toggled.connect(
            lambda on: QgsSettings().setValue(AUTO_MATCH_KEY, on))
        self.btn_z_info.clicked.connect(self.show_z_help)
        self.txt_search.textChanged.connect(self.populate)
        self.tree.currentItemChanged.connect(self.on_item_selected)
        self.btn_copy.clicked.connect(lambda: self.copy_value(self.tbl_values, 0))
        self.tbl_values.cellDoubleClicked.connect(lambda *_: self.copy_value(self.tbl_values, 0))
        return tab

    def _build_codes_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        list_row = QHBoxLayout()
        list_row.addWidget(QLabel(tr("code_list_label")))
        self.cbo_list = QComboBox()
        self.cbo_list.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.cbo_list.setMinimumContentsLength(12)
        list_row.addWidget(self.cbo_list, 1)
        layout.addLayout(list_row)

        self.lbl_list_note = QLabel("")
        self.lbl_list_note.setWordWrap(True)
        layout.addWidget(self.lbl_list_note)

        self.txt_code_search = QLineEdit()
        self.txt_code_search.setPlaceholderText(tr("search_values_placeholder"))
        self.txt_code_search.setClearButtonEnabled(True)
        layout.addWidget(self.txt_code_search)

        self.tbl_codes = _make_values_table([tr("col_code_list"), tr("col_value"), tr("col_description")])
        layout.addWidget(self.tbl_codes, 1)

        self.btn_copy_code = QPushButton(tr("copy_value"))
        self.btn_copy_code.setToolTip(tr("copy_value_tip"))
        layout.addWidget(self.btn_copy_code)

        self.cbo_list.currentIndexChanged.connect(self.populate_codes)
        self.txt_code_search.textChanged.connect(self.populate_codes)
        self.btn_copy_code.clicked.connect(lambda: self.copy_value(self.tbl_codes, 1))
        self.tbl_codes.cellDoubleClicked.connect(lambda *_: self.copy_value(self.tbl_codes, 1))
        return tab

    def set_status(self, text):
        self.lbl_status.setText(text)

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------
    def on_data_updated(self, model):
        self.set_model(model)
        self.set_status(tr("status_updated"))

    def on_data_failed(self, message):
        if self.model is None:
            self.set_status(tr("status_fetch_failed", message))
        else:
            self.set_status(tr("status_offline", message))

    def set_model(self, model):
        previous_type = self.cbo_type.currentData()
        previous_list = self.cbo_list.currentData()
        self.model = model

        self.cbo_type.blockSignals(True)
        self.cbo_type.clear()
        self.cbo_type.addItem(tr("select_type"), None)
        for name in model.type_names():
            self.cbo_type.addItem(name, name)
        self.cbo_type.setCurrentIndex(max(self.cbo_type.findData(previous_type), 0))
        self.cbo_type.blockSignals(False)

        self.cbo_list.blockSignals(True)
        self.cbo_list.clear()
        self.cbo_list.addItem(tr("all_lists"), None)
        for name in sorted(model.kodelister, key=str.lower):
            self.cbo_list.addItem(name, name)
        self.cbo_list.setCurrentIndex(max(self.cbo_list.findData(previous_list), 0))
        self.cbo_list.blockSignals(False)

        self.on_active_layer_changed(self.iface.activeLayer())
        self.populate_codes()

    # ------------------------------------------------------------------
    # Layer link
    # ------------------------------------------------------------------
    def _layer(self):
        layer = QgsProject.instance().mapLayer(self.layer_id) if self.layer_id else None
        return layer if isinstance(layer, QgsVectorLayer) else None

    def _layer_field_names(self):
        layer = self._layer()
        return {f.name().lower() for f in layer.fields()} if layer else None

    def on_active_layer_changed(self, layer, force=False):
        if self.model is None:
            return
        if not isinstance(layer, QgsVectorLayer):
            self.layer_id = None
            self.populate()
            return

        self.layer_id = layer.id()
        if not force and not self.chk_auto_match.isChecked():
            self.populate()
            return
        matched = self.model.match_layer_name(layer.name())
        if matched:
            self.cbo_type.setCurrentIndex(self.cbo_type.findData(matched))
        elif force:
            self.set_status(tr("status_no_type_match"))
        self.populate()

    def _update_layer_label(self):
        layer = self._layer()
        names = self._layer_field_names()
        self.lbl_layer.setToolTip("")
        if layer is None:
            self.lbl_layer.setText(tr("layer_none"))
            return
        type_name = self.cbo_type.currentData()
        if not type_name:
            self.lbl_layer.setText(tr("layer_pick_type", layer.name()))
            return
        attrs = self.model.attributes(type_name)
        model_names = {a["navn"].lower() for a in attrs}
        missing_mand = [a["navn"] for a in attrs
                        if a.get("forekomst") == "Obligatorisk" and a["navn"].lower() not in names]
        extra = sorted(n for n in names if n not in model_names)
        text = tr("layer_summary", layer.name(), type_name, len(missing_mand))
        if extra:
            text += tr("layer_extra", len(extra))
        self.lbl_layer.setText(text)
        tip = []
        if missing_mand:
            tip.append(tr("tip_missing") + ", ".join(missing_mand))
        if extra:
            tip.append(tr("tip_not_in_model") + ", ".join(extra))
        self.lbl_layer.setToolTip("\n".join(tip))

    # ------------------------------------------------------------------
    # Attributes tab
    # ------------------------------------------------------------------
    def _update_z_note(self):
        name = (self.cbo_type.currentData() or "").lower()
        is_line = name.endswith("ledning") or name == "føringsrør"
        for widget in self.z_widgets:
            widget.setVisible(is_line)
        if not is_line:
            return
        text = tr("z_note")
        if name in Z_EXCEPTION_TYPES:
            text += tr("z_note_exception")
        self.lbl_z_note.setText(text + tr("z_note_unrelated"))

    def show_z_help(self):
        box = QMessageBox(self)
        box.setWindowTitle(tr("z_help_title"))
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.setText(tr("z_help"))
        box.exec()

    def populate(self, *_):
        self.tree.clear()
        if self.model is None:
            return
        self._update_layer_label()
        self._update_z_note()

        query = self.txt_search.text().strip()
        type_name = self.cbo_type.currentData()
        field_names = self._layer_field_names()
        compare = field_names is not None and type_name is not None

        if query:
            rows = self.model.search_attributes(query)
        elif type_name:
            rows = [(type_name, a) for a in self.model.attributes(type_name)]
        else:
            rows = []

        bold = QFont()
        bold.setBold(True)
        italic = QFont()
        italic.setItalic(True)
        for group, attr in rows:
            occurrence = attr.get("forekomst") or ""
            item = QTreeWidgetItem([group, attr["navn"], _occurrence_label(occurrence), ""])
            if occurrence == "Obligatorisk":
                item.setFont(2, bold)
            elif occurrence == "Betinget":
                item.setFont(2, italic)
                item.setToolTip(2, tr("occ_conditional_tip"))
            else:
                item.setForeground(2, GREY)
            if compare and group == type_name:
                if attr["navn"].lower() in field_names:
                    item.setText(3, tr("compare_yes"))
                    item.setForeground(3, GREEN)
                elif occurrence == "Obligatorisk":
                    item.setText(3, tr("compare_missing"))
                    item.setForeground(3, RED)
                elif occurrence == "Betinget":
                    item.setText(3, tr("compare_missing"))
                    item.setForeground(3, ORANGE)
                    item.setToolTip(3, tr("compare_conditional_tip"))
                else:
                    item.setText(3, "–")
                    item.setForeground(3, GREY)
            item.setData(0, ROLE, (group, attr))
            self.tree.addTopLevelItem(item)

        if not rows:
            hint = tr("no_results") if query else tr("pick_or_search")
            self.tree.addTopLevelItem(QTreeWidgetItem(["", hint, "", ""]))
        self.txt_detail.clear()
        self._show_values(None)

    def on_item_selected(self, current, _previous):
        data = current.data(0, ROLE) if current else None
        if not data:
            return
        type_name, attr = data
        occurrence = attr.get("forekomst")
        lines = [attr["navn"], "", tr("detail_definition", attr.get("definition") or "-")]
        lines.append(tr("detail_object_type", type_name))
        lines.append(tr("detail_occurrence", _occurrence_label(occurrence) if occurrence else "-"))
        # The model's own condition for this attribute links it to the geometry,
        # which does not match how LER actually validates z - so it is hidden.
        if attr.get("betingelse") and attr["navn"] != "noejagtighedsklasseVertikal":
            lines.append(tr("detail_condition", _format_condition(attr["betingelse"])))
        voidable = attr.get("voidable")
        lines.append(tr("detail_multiplicity", attr.get("multiplicitet") or "-",
                        _yes_no_label(voidable) if voidable else "-"))
        if attr.get("defineret_paa"):
            lines.append(tr("detail_defined_on", attr["defineret_paa"]))
        if attr.get("datatype"):
            lines.append(tr("detail_datatype", attr["datatype"]))
        if attr.get("kodeliste"):
            lines.append(tr("detail_code_list", attr["kodeliste"]))
        self.txt_detail.setPlainText("\n".join(lines))
        self._show_values(attr.get("kodeliste"))

    def _show_values(self, list_name):
        kl = self.model.kodeliste(list_name) if (self.model and list_name) else None
        self.tbl_values.setVisible(kl is not None)
        self.btn_copy.setVisible(kl is not None)
        self.tbl_values.setRowCount(0)
        if kl is None:
            return
        values = kl["vaerdier"]
        self.tbl_values.setRowCount(len(values))
        for row, value in enumerate(values):
            self.tbl_values.setItem(row, 0, QTableWidgetItem(str(value["vaerdi"])))
            self.tbl_values.setItem(row, 1, QTableWidgetItem(str(value.get("definition") or "")))
        free = truthy(kl.get("tillader_andet"))
        self.tbl_values.setHorizontalHeaderLabels(
            [tr("col_value_free") if free else tr("col_value"), tr("col_description")])
        self.tbl_values.resizeRowsToContents()

    # ------------------------------------------------------------------
    # Code lists tab
    # ------------------------------------------------------------------
    def populate_codes(self, *_):
        self.tbl_codes.setRowCount(0)
        if self.model is None:
            return
        list_name = self.cbo_list.currentData()
        query = self.txt_code_search.text().strip()

        if list_name:
            kl = self.model.kodeliste(list_name)
            note = (tr("list_note_free") if truthy(kl.get("tillader_andet"))
                    else tr("list_note_closed"))
            rows = (self.model.search_values(query, list_name) if query
                    else [(list_name, v) for v in kl["vaerdier"]])
        else:
            note = tr("list_note_pick")
            rows = self.model.search_values(query) if query else []
        self.lbl_list_note.setText(note)

        self.tbl_codes.setRowCount(len(rows))
        for row, (group, value) in enumerate(rows):
            self.tbl_codes.setItem(row, 0, QTableWidgetItem(group))
            self.tbl_codes.setItem(row, 1, QTableWidgetItem(str(value["vaerdi"])))
            self.tbl_codes.setItem(row, 2, QTableWidgetItem(str(value.get("definition") or "")))
        self.tbl_codes.resizeRowsToContents()

    # ------------------------------------------------------------------
    def copy_value(self, table, column):
        row = table.currentRow()
        item = table.item(row, column) if row >= 0 else None
        if item is None:
            return
        QApplication.clipboard().setText(item.text())
        self.iface.messageBar().pushMessage(
            self.PLUGIN_NAME, tr("copied", item.text()), Qgis.MessageLevel.Info, 2
        )

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()
