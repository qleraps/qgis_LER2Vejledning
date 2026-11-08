# -*- coding: utf-8 -*-
"""Main plugin class for LER 2-Vejledning."""

import os

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon

try:
    from qgis.PyQt.QtWidgets import QAction
except ImportError:  # Qt6 / QGIS 4
    from qgis.PyQt.QtGui import QAction

from .ler2_vejledning_dockwidget import LER2VejledningDockWidget


class LER2Vejledning:
    MENU_NAME = "&LER 2-Vejledning"

    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dockwidget = None

    def initGui(self):
        icon = QIcon(os.path.join(os.path.dirname(__file__), "icon.png"))
        self.action = QAction(icon, "LER 2-Vejledning", self.iface.mainWindow())
        self.action.setCheckable(True)
        self.action.triggered.connect(self.toggle)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(self.MENU_NAME, self.action)

    def unload(self):
        self.iface.removePluginMenu(self.MENU_NAME, self.action)
        self.iface.removeToolBarIcon(self.action)
        if self.dockwidget is not None:
            self.dockwidget.shutdown()
            self.iface.removeDockWidget(self.dockwidget)
            self.dockwidget.deleteLater()
            self.dockwidget = None

    def toggle(self, checked):
        if self.dockwidget is None:
            self.dockwidget = LER2VejledningDockWidget(self.iface)
            self.dockwidget.closingPlugin.connect(lambda: self.action.setChecked(False))
            self.iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dockwidget)
        self.dockwidget.setVisible(checked)
