# -------------------------------
######### "AdnaneYacheur"########
# -------------------------------

import json
from shapely.geometry import shape, box
import overpy
from flask import Flask, render_template_string, request
import html

app = Flask(__name__)

# -------------------------------
# HTML with Leaflet + Draw plugin
# -------------------------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>OSM Polygon Export</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css"/>
  <link rel="stylesheet" href="https://unpkg.com/leaflet-draw/dist/leaflet.draw.css"/>
  <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
  <script src="https://unpkg.com/leaflet-draw/dist/leaflet.draw.js"></script>
</head>
<body>
  <h3>Draw your area and click "Export"</h3>
  <div id="map" style="width: 100%; height: 600px;"></div>
  <button onclick="exportPolygon()">Export</button>

  <script>
    var map = L.map('map').setView([40.7128, -74.0060], 14);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    var drawnItems = new L.FeatureGroup();
    map.addLayer(drawnItems);

    var drawControl = new L.Control.Draw({
      edit: { featureGroup: drawnItems }
    });
    map.addControl(drawControl);

    map.on(L.Draw.Event.CREATED, function (e) {
      var layer = e.layer;
      drawnItems.addLayer(layer);
    });

    function exportPolygon() {
      var data = drawnItems.toGeoJSON();
      if (data.features.length === 0) {
        alert("Draw a polygon first!");
        return;
      }
      fetch("/upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
      }).then(r => {
        if (r.ok) { alert("✅ Exported! Check exported_area.osm"); }
        else { alert("❌ Failed. Check console."); }
      });
    }
  </script>
</body>
</html>
"""

# -------------------------------
# Convert Overpy result -> OSM XML (nodes + ways only)
# -------------------------------
def result_to_osm(result):
    parts = ['<?xml version="1.0" encoding="UTF-8"?>', '<osm version="0.6" generator="overpy">']

    # Nodes
    for node in result.nodes:
        parts.append(f'<node id="{node.id}" lat="{node.lat}" lon="{node.lon}">')
        for k, v in node.tags.items():
            safe_k = html.escape(str(k), quote=True)
            safe_v = html.escape(str(v), quote=True)
            parts.append(f'  <tag k="{safe_k}" v="{safe_v}"/>')
        parts.append('</node>')

    # Ways
    for way in result.ways:
        parts.append(f'<way id="{way.id}">')
        for n in way.nodes:
            parts.append(f'  <nd ref="{n.id}"/>')
        for k, v in way.tags.items():
            safe_k = html.escape(str(k), quote=True)
            safe_v = html.escape(str(v), quote=True)
            parts.append(f'  <tag k="{safe_k}" v="{safe_v}"/>')
        parts.append('</way>')

    parts.append('</osm>')
    return "\n".join(parts)

# -------------------------------
# Split polygon if too large
# -------------------------------
def split_polygon(polygon, max_size=0.25):
    minx, miny, maxx, maxy = polygon.bounds
    width = maxx - minx
    height = maxy - miny

    if width <= max_size and height <= max_size:
        return [polygon]

    nx = int(width // max_size) + 1
    ny = int(height // max_size) + 1

    small_polygons = []
    for i in range(nx):
        for j in range(ny):
            sub = box(
                minx + i * max_size,
                miny + j * max_size,
                min(minx + (i + 1) * max_size, maxx),
                min(miny + (j + 1) * max_size, maxy)
            )
            if sub.intersects(polygon):
                small_polygons.append(sub.intersection(polygon))
    return small_polygons


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/upload", methods=["POST"])
def upload():
    data = request.json
    with open("selected_area.geojson", "w", encoding="utf-8") as f:
        json.dump(data, f)
    print("✅ Polygon saved as selected_area.geojson")

    polygon = shape(data["features"][0]["geometry"])
    print("Polygon bounds:", polygon.bounds)

    # Split if too large
    polygons = split_polygon(polygon)

    api = overpy.Overpass()
    merged = []

    for poly in polygons:
        coords = " ".join(f"{y} {x}" for x, y in poly.exterior.coords)
        query = f"""
        [out:xml][timeout:300];
        (
          node(poly:"{coords}");
          way(poly:"{coords}");
        );
        out body;
        >;
        out skel qt;
        """
        print("🔎 Querying Overpass for sub-area...")
        result = api.query(query)
        merged.append(result_to_osm(result))

    
    final_xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<osm version="0.6" generator="overpy">']
    for block in merged:
        
        for line in block.splitlines():
            if not line.startswith("<?xml") and not line.startswith("<osm") and not line.startswith("</osm>"):
                final_xml.append(line)
    final_xml.append("</osm>")

    with open("exported_area.osm", "w", encoding="utf-8") as f:
        f.write("\n".join(final_xml))

    print("✅ Exported full area to exported_area.osm")
    return {"status": "ok"}

# -------------------------------
# Run Flask App
# -------------------------------
if __name__ == "__main__":
    print("🌍 Open http://127.0.0.1:5000 ")
    app.run(debug=True)
