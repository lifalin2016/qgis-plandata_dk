# Plandata DK

A QGIS plugin that adds a **"Plandata DK"** menu to the QGIS menu bar,
listing every layer published by the Danish Plandata.dk WFS service
(`https://geoserver.plandata.dk/geoserver/wfs`), organized into
submenus, with one click to add any layer to the map.

## Installation

1. In QGIS, go to **Plugins -> Manage and Install Plugins... -> Install from ZIP**.
2. Select `plandata_dk.zip`.
3. Click **Install Plugin**, then enable it if it isn't enabled automatically.

No dependencies beyond QGIS itself are required.

## Usage

- Open the **Plandata DK** menu (near the right end of the QGIS menu bar,
  just before **Help**).
- The first time you open it, the plugin fetches the WFS
  `GetCapabilities` document and builds the submenu list. This takes a
  few seconds depending on your connection.
- Each submenu groups related layers together; click a leaf item to add
  that WFS layer to your current project.
- Use **Refresh layer list** (at the top of the menu) at any time to
  re-fetch the layer list from the server, e.g. if Plandata.dk has
  published new datasets.

## How layers are grouped

Each WFS layer name (for example `pdk:theme_pdk_lokalplan_vedtaget` or
`knz:theme-knz-kystnaerhedszone-linje`) is stripped of its namespace
prefix (the part before the colon). The remaining name is split on
dashes and underscores, and the first three parts are rejoined with
underscores to make the group key - e.g. `theme_pdk_lokalplan` or
`theme_knz_kystnaerhedszone`. That key is used both to group layers and
as the submenu's title. Names with fewer than three parts get their own
group named after the full local name (e.g. `regionplaner`).

## Coordinate reference system

Layers are requested in **EPSG:25832** (ETRS89 / UTM zone 32N), the
standard grid for Danish national data, including Plandata.dk. To
change this, edit the `DEFAULT_SRS` constant near the top of
`plandata_dk.py` and reinstall the plugin.

## Notes / assumptions

- The plugin talks to the WFS service via QGIS's own network stack
  (`QgsBlockingNetworkRequest`), so it automatically respects QGIS's
  configured proxy settings.
- The WFS capabilities XML (untrusted input from a remote server) is
  parsed with a bundled copy of [`defusedxml`](https://github.com/tiran/defusedxml)
  (`plandata_dk/defusedxml/`, PSF-licensed, see the `LICENSE` file in
  that folder) instead of `xml.etree.ElementTree` directly, to avoid
  entity-expansion / XXE style XML attacks. It's vendored as a
  subpackage so no extra installation step is required.
- Tested against QGIS 3.16+; requires no extra Python packages.
