# OSM Polygon Exporter for SUMO

This project allows you to select a custom area on an OpenStreetMap (OSM) map, export it as an OSM file, and convert it to a SUMO network (`.net.xml`). It automatically handles large areas by splitting them into smaller chunks for Overpass queries, then merges the results.  

---

## Features

- Interactive map with polygon drawing.
- Export selected area as OSM file.
- Automatic handling of large areas (splits and merges).
- Escapes special XML characters to ensure SUMO compatibility.
- Optional: Direct conversion to SUMO network using `netconvert`.

---

## Requirements

- Python 3.8+
- Flask
- Overpy
- Shapely
- Geopandas (optional)
- SUMO (for `netconvert`)

Install Python dependencies via pip:

```bash
pip install flask overpy shapely geopandas
