# -*- coding: utf-8 -*-
"""Plandata DK QGIS plugin.

Adds a "Plandata DK" menu to the QGIS menu bar. The menu contains one
submenu per layer group found in the Plandata.dk WFS capabilities
document; choosing a leaf item loads the corresponding WFS layer into
the current project.

Grouping rule
--------------
Each WFS layer name (e.g. ``pdk:theme_pdk_lokalplan_vedtaget`` or
``knz:theme-knz-kystnaerhedszone-linje``) is first stripped of its
namespace prefix (the part before the colon, if any). The remaining
local name is then split on dashes and underscores, and the first
three resulting parts are re-joined with underscores to form the
group key (e.g. ``theme_pdk_lokalplan`` or ``theme_knz_kystnaerhedszone``).
That group key is used both to bucket layers together and as the
submenu's displayed title. Names with fewer than three parts are
placed in their own group named after the full local name.
"""

import re

from .defusedxml import ElementTree as DefusedET

from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.PyQt.QtWidgets import QAction, QMenu, QMessageBox
from qgis.core import (
    Qgis,
    QgsBlockingNetworkRequest,
    QgsMessageLog,
    QgsProject,
    QgsVectorLayer,
)

WFS_BASE_URL = "https://geoserver.plandata.dk/geoserver/wfs"
CAPABILITIES_URL = f"{WFS_BASE_URL}?service=WFS&request=GetCapabilities"

# ETRS89 / UTM zone 32N - the standard grid used by Danish national data
# (including Plandata.dk). Change this if you need a different CRS.
DEFAULT_SRS = "EPSG:25832"

LOG_TAG = "Plandata DK"
HELP_MENU_OBJECT_NAME = "mQgisAppHelpMenu"


class PlandataDkPlugin:
    """Main plugin object implementing the standard QGIS plugin interface."""

    def __init__(self, iface):
        self.iface = iface
        self.menu = None
        self.refresh_action = None
        self._loaded = False

    # ------------------------------------------------------------------
    # QGIS plugin interface
    # ------------------------------------------------------------------
    def initGui(self):  # pylint: disable=invalid-name
        menu_bar = self.iface.mainWindow().menuBar()

        self.menu = QMenu("Plandata DK", menu_bar)
        self.menu.aboutToShow.connect(self._ensure_loaded)

        self.refresh_action = QAction("Refresh layer list", self.iface.mainWindow())
        self.refresh_action.triggered.connect(self.refresh_menu)

        self._show_placeholder("Loading layer list...")
        self._insert_menu(menu_bar)

    def unload(self):  # pylint: disable=invalid-name
        if self.menu is not None:
            self.menu.deleteLater()
            self.menu = None
        self.refresh_action = None

    def _insert_menu(self, menu_bar):
        """Insert self.menu just before the Help menu, if it can be found,
        otherwise append it at the end of the menu bar."""
        for action in menu_bar.actions():
            submenu = action.menu()
            if submenu is not None and submenu.objectName() == HELP_MENU_OBJECT_NAME:
                menu_bar.insertMenu(action, self.menu)
                return
        menu_bar.addMenu(self.menu)

    # ------------------------------------------------------------------
    # Menu building
    # ------------------------------------------------------------------
    def _show_placeholder(self, text):
        self.menu.clear()
        self.menu.addAction(self.refresh_action)
        self.menu.addSeparator()
        placeholder = self.menu.addAction(text)
        placeholder.setEnabled(False)

    def _ensure_loaded(self):
        if not self._loaded:
            self.refresh_menu()

    def refresh_menu(self):
        """(Re-)fetch the WFS capabilities document and rebuild the menu."""
        self._show_placeholder("Loading layer list...")

        try:
            layer_names = self._fetch_layer_names()
        except Exception as exc:  # noqa: BLE001 - surface any failure to the user
            self._loaded = False
            QgsMessageLog.logMessage(str(exc), LOG_TAG, level=Qgis.Critical)
            self._show_placeholder("Failed to load layer list - click Refresh to retry")
            self.iface.messageBar().pushWarning(
                LOG_TAG,
                "Could not load the Plandata.dk WFS layer list. See the "
                "'Plandata DK' tab in the Log Messages panel for details.",
            )
            return

        groups = self._group_layer_names(layer_names)

        self.menu.clear()
        self.menu.addAction(self.refresh_action)
        self.menu.addSeparator()

        if not groups:
            empty_action = self.menu.addAction("No layers found")
            empty_action.setEnabled(False)
            self._loaded = True
            return

        for group_name in sorted(groups, key=str.lower):
            submenu = self.menu.addMenu(group_name)
            for display_name, typename in sorted(
                groups[group_name], key=lambda item: item[0].lower()
            ):
                action = submenu.addAction(display_name)
                action.setToolTip(typename)
                action.triggered.connect(
                    lambda checked=False, tn=typename, dn=display_name: self._add_layer(
                        tn, dn
                    )
                )

        self._loaded = True

    # ------------------------------------------------------------------
    # WFS capabilities handling
    # ------------------------------------------------------------------
    def _fetch_layer_names(self):
        request = QNetworkRequest(QUrl(CAPABILITIES_URL))
        blocking_request = QgsBlockingNetworkRequest()
        error = blocking_request.get(request, forceRefresh=True)
        if error != QgsBlockingNetworkRequest.NoError:
            raise RuntimeError(
                f"Network request failed: {blocking_request.errorMessage()}"
            )

        reply = blocking_request.reply()
        content = bytes(reply.content())
        if not content:
            raise RuntimeError("The WFS server returned an empty response.")

        return self._parse_feature_type_names(content)

    @staticmethod
    def _parse_feature_type_names(xml_bytes):
        """Return every <FeatureType><Name> value in a GetCapabilities
        document, regardless of the XML namespace prefixes used.

        Parsing uses the vendored ``defusedxml`` package rather than the
        standard library's ``xml.etree.ElementTree`` directly, since the
        stdlib parser is vulnerable to entity-expansion and external
        entity ("XXE") attacks when fed untrusted XML - and a remote WFS
        server's response is untrusted input.
        """
        root = DefusedET.fromstring(xml_bytes)
        names = []
        for elem in root.iter():
            tag = elem.tag.rsplit("}", 1)[-1]
            if tag != "FeatureType":
                continue
            for child in elem:
                child_tag = child.tag.rsplit("}", 1)[-1]
                if child_tag == "Name" and child.text:
                    names.append(child.text.strip())
                    break
        return names

    @staticmethod
    def _group_layer_names(layer_names):
        """Group layer names by the first three dash/underscore separated
        parts of their local (unprefixed) name.

        :returns: dict mapping group label -> list of (display_name, typename)
        """
        groups = {}
        for typename in layer_names:
            local_name = typename.split(":", 1)[-1] if ":" in typename else typename
            parts = [p for p in re.split(r"[-_]", local_name) if p]
            if len(parts) >= 3:
                group_label = "_".join(parts[:3])
            else:
                group_label = local_name
            groups.setdefault(group_label, []).append((local_name, typename))
        return groups

    # ------------------------------------------------------------------
    # Adding a layer to the map
    # ------------------------------------------------------------------
    def _add_layer(self, typename, display_name):
        uri = (
            "pagingEnabled='true' "
            "restrictToRequestBBOX='1' "
            f"srsname='{DEFAULT_SRS}' "
            f"typename='{typename}' "
            f"url='{WFS_BASE_URL}' "
            "version='auto'"
        )
        layer = QgsVectorLayer(uri, display_name, "WFS")
        if not layer.isValid():
            QMessageBox.warning(
                self.iface.mainWindow(),
                LOG_TAG,
                f"Could not load layer '{typename}' from the WFS service.",
            )
            return

        QgsProject.instance().addMapLayer(layer)
        self.iface.messageBar().pushSuccess(LOG_TAG, f"Added layer '{display_name}'.")
