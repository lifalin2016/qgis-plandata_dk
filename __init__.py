# -*- coding: utf-8 -*-
"""Plandata DK QGIS plugin package entry point."""


def classFactory(iface):  # pylint: disable=invalid-name
    """QGIS plugin entry point, called by QGIS when the plugin is loaded.

    :param iface: A QGIS QgisInterface instance.
    :type iface: qgis.gui.QgisInterface
    """
    from .plandata_dk import PlandataDkPlugin

    return PlandataDkPlugin(iface)
