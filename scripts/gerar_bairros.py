import requests
import json
import geopandas as gpd

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

query = """
[out:json][timeout:60];
area["name"="Luanda"]["boundary"="administrative"]->.searchArea;
(
  node["place"="suburb"](area.searchArea);
  node["place"="neighbourhood"](area.searchArea);
  way["place"="suburb"](area.searchArea);
  way["place"="neighbourhood"](area.searchArea);
  relation["place"="suburb"](area.searchArea);
  relation["place"="neighbourhood"](area.searchArea);
);
out center;
"""

response = requests.get(OVERPASS_URL, params={'data': query})
data = response.json()

features = []

for el in data["elements"]:
    tags = el.get("tags", {})
    name = tags.get("name")

    if not name:
        continue

    lat = el.get("lat") or el.get("center", {}).get("lat")
    lon = el.get("lon") or el.get("center", {}).get("lon")

    if not lat or not lon:
        continue

    feature = {
        "type": "Feature",
        "properties": {
            "name": name,
            "municipio": "Luanda"
        },
        "geometry": {
            "type": "Point",
            "coordinates": [lon, lat]
        }
    }

    features.append(feature)

geojson = {
    "type": "FeatureCollection",
    "features": features
}

with open("../data/bairros.geojson", "w", encoding="utf-8") as f:
    json.dump(geojson, f, ensure_ascii=False, indent=2)

print(f"OK: {len(features)} bairros extraídos")