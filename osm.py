# -------------------------------
######### "AdnaneYacheur"########
# -------------------------------

import json
from shapely.geometry import shape, box
import overpy
from flask import Flask, render_template_string, request
import html
import time

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
  <style>
    #overlay {
      position: fixed;
      top: 0; left: 0;
      width: 100%; height: 100%;
      background: rgba(0,0,0,0.7);
      color: white;
      display: none;
      justify-content: center;
      align-items: center;
      flex-direction: column;
      font-size: 18px;
      z-index: 9999;
    }
    .progress-bar {
      width: 80%; height: 25px;
      background: #444; border-radius: 8px;
      margin-top: 15px;
      overflow: hidden;
    }
    .progress-fill {
      height: 100%; width: 0%;
      background: limegreen;
      transition: width 0.3s;
    }
  </style>
</head>
<body>
  <h3>Draw your area and click "Export"</h3>
  <div id="map" style="width: 100%; height: 600px;"></div>
  <button onclick="exportPolygon()">Export</button>

  <div id="overlay">
    <div id="status">Starting export...</div>
    <div class="progress-bar"><div class="progress-fill" id="progress"></div></div>
  </div>

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

    function showOverlay(text, percent) {
      document.getElementById("overlay").style.display = "flex";
      document.getElementById("status").innerText = text;
      document.getElementById("progress").style.width = percent + "%";
    }

    function hideOverlay() {
      document.getElementById("overlay").style.display = "none";
    }

    function exportPolygon() {
      var data = drawnItems.toGeoJSON();
      if (data.features.length === 0) {
        alert("Draw a polygon first!");
        return;
      }
      showOverlay("Sending polygon...", 10);

      fetch("/upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
      })
      .then(r => r.json())
      .then(resp => {
        if (resp.status === "ok") {
          showOverlay("Finished! File exported_area.osm created", 100);
          setTimeout(hideOverlay, 3000);
        } else {
          hideOverlay();
          alert("❌ Failed. Check server logs.");
        }
      })
      .catch(err => {
        hideOverlay();
        alert("❌ Error: " + err);
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

def merge_results(results, output_file):
    """
    Merge multiple Overpy results into one OSM XML file.
    Supports nodes, ways, and relations safely.
    """
    seen_nodes = set()
    seen_ways = set()
    seen_rels = set()

    with open(output_file, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<osm version="0.6" generator="overpy">\n')

        for result in results:
            # Nodes
            for node in result.nodes:
                if node.id in seen_nodes:
                    continue
                seen_nodes.add(node.id)
                f.write(f'  <node id="{node.id}" lat="{node.lat}" lon="{node.lon}">\n')
                for k, v in node.tags.items():
                    f.write(f'    <tag k="{html.escape(str(k))}" v="{html.escape(str(v))}"/>\n')
                f.write('  </node>\n')

            # Ways
            for way in result.ways:
                if way.id in seen_ways:
                    continue
                seen_ways.add(way.id)
                f.write(f'  <way id="{way.id}">\n')
                for n in way.nodes:
                    f.write(f'    <nd ref="{n.id}"/>\n')
                for k, v in way.tags.items():
                    f.write(f'    <tag k="{html.escape(str(k))}" v="{html.escape(str(v))}"/>\n')
                f.write('  </way>\n')

            # Relations
            for rel in result.relations:
                if rel.id in seen_rels:
                    continue
                seen_rels.add(rel.id)
                f.write(f'  <relation id="{rel.id}">\n')
                for m in rel.members:
                    if isinstance(m, overpy.RelationNode):
                        f.write(f'    <member type="node" ref="{m.ref}" role="{m.role}"/>\n')
                    elif isinstance(m, overpy.RelationWay):
                        f.write(f'    <member type="way" ref="{m.ref}" role="{m.role}"/>\n')
                    elif isinstance(m, overpy.RelationRelation):
                        f.write(f'    <member type="relation" ref="{m.ref}" role="{m.role}"/>\n')
                for k, v in rel.tags.items():
                    f.write(f'    <tag k="{html.escape(str(k))}" v="{html.escape(str(v))}"/>\n')
                f.write('  </relation>\n')

        f.write('</osm>\n')


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/upload", methods=["POST"])
def upload():
    data = request.json
    with open("selected_area.geojson", "w", encoding="utf-8") as f:
        json.dump(data, f)
    print("✅ Polygon saved as selected_area.geojson")

    # Get the polygon and bounds
    polygon = shape(data["features"][0]["geometry"])
    print("Polygon bounds:", polygon.bounds)

    # Split if too large
    polygons = split_polygon(polygon)
    total_parts = len(polygons)
    print(f"🔎 Splitting polygon into {total_parts} sub-areas...")

    api = overpy.Overpass()
    results = []

    for idx, poly in enumerate(polygons, start=1):
        # Use bbox filter instead of poly for better performance
        minx, miny, maxx, maxy = poly.bounds
        query = f"""
        [out:xml][timeout:300];
        (
          node({miny},{minx},{maxy},{maxx});
          way({miny},{minx},{maxy},{maxx});
          relation({miny},{minx},{maxy},{maxx});
        );
        out body;
        >;
        out skel qt;
        """
        print(f"🔎 Querying Overpass for sub-area {idx}/{total_parts}...")
        try:
            res = api.query(query)
            results.append(res)
        except Exception as e:
            print(f"⚠️ Error querying Overpass for part {idx}: {e}")
            # Consider adding a retry mechanism here with a delay
            time.sleep(5)  # Wait for 5 seconds before retrying
            try:
                res = api.query(query)
                results.append(res)
            except Exception as retry_e:
                print(f"❌ Failed to query part {idx} after retry: {retry_e}")
                # You can choose to skip or raise an error here
                pass

    # Merge everything into one file
    merge_results(results, "exported_area.osm")

    return {"status": "ok", "parts": total_parts}


# -------------------------------
# Run Flask App
# -------------------------------
if __name__ == "__main__":
    print("🌍 Open http://127.0.0.1:5000 ")
    app.run(debug=True)
