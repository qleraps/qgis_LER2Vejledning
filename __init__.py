# -*- coding: utf-8 -*-
"""LER 2-Vejledning - look up the LER 2 data model from within QGIS."""


def classFactory(iface):
    from .ler2_vejledning import LER2Vejledning
    return LER2Vejledning(iface)
