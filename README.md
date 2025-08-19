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
```
## Usage

1- Run the Flask app:
```bash
python osm.py
```
2- Open the generated map in your browser (usually at http://127.0.0.1:5000).

3- Draw a polygon over the area you want to export.

4 -Click Export — this will save the polygon as selected_area.geojson and produce an OSM file (exported_area.osm).

5 -Optional: Convert the OSM file to SUMO network:
```bash
netconvert --osm-files exported_area.osm -o itineraire.net.xml
```
## Notes

-The script automatically escapes XML special characters (<, >, &, ") to prevent netconvert errors.

-Large areas are split into smaller queries for Overpass API and merged seamlessly.

-Ensure netconvert is installed and in your system path if you want automatic SUMO network generation.


