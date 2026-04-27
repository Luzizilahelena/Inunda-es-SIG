import os

# ⚠️ MELHORIA: evitar instalar dependências automaticamente em produção
# os.system("pip install -r requirements.txt")

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime
import logging
import requests
import geopandas as gpd
from zipfile import ZipFile
from io import BytesIO
import numpy as np

import json  # ✔️ movido para topo (evita import repetido)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# ==================== DADOS ESTÁTICOS ====================
PROVINCES = [
    {'id': 1, 'name': 'Luanda', 'risk': 'Muito Alto', 'population': 8329517, 'area': 2417},
]

MUNICIPALITIES = {
    'Luanda': [
        {'id': 1, 'name': 'Belas', 'population': 600000, 'area': 500, 'risk': 'Alto'},
        {'id': 2, 'name': 'Cacuaco', 'population': 850000, 'area': 450, 'risk': 'Muito Alto'},
        {'id': 3, 'name': 'Cazenga', 'population': 980000, 'area': 32, 'risk': 'Muito Alto'},
        {'id': 4, 'name': 'Icolo e Bengo', 'population': 150000, 'area': 3600, 'risk': 'Médio'},
        {'id': 5, 'name': 'Luanda', 'population': 2200000, 'area': 116, 'risk': 'Muito Alto'},
        {'id': 6, 'name': 'Quiçama', 'population': 25000, 'area': 13900, 'risk': 'Baixo'},
        {'id': 7, 'name': 'Viana', 'population': 2000000, 'area': 1700, 'risk': 'Alto'},
        {'id': 8, 'name': 'Kilamba Kiaxi', 'population': 1800000, 'area': 189, 'risk': 'Muito Alto'},
        {'id': 9, 'name': 'Talatona', 'population': 500000, 'area': 160, 'risk': 'Médio'},
        {'id': 10, 'name': 'Maianga', 'population': 500000, 'area': 50, 'risk': 'Alto'},
        {'id': 11, 'name': 'Rangel', 'population': 261000, 'area': 62, 'risk': 'Muito Alto'},
        {'id': 12, 'name': 'Ingombota', 'population': 370000, 'area': 30, 'risk': 'Médio'},
        {'id': 13, 'name': 'Samba', 'population': 400000, 'area': 345, 'risk': 'Alto'},
        {'id': 14, 'name': 'Sambizanga', 'population': 300000, 'area': 40, 'risk': 'Muito Alto'},
    ],
}

# ==================== BAIRROS ====================
BAIRROS = {
    'Kilamba Kiaxi': [
        {'id': 19, 'name': 'Golfe', 'population': 300000, 'type': 'Residencial', 'risk': 'Alto', 'lat': -8.8950, 'lon': 13.2510},
    ],
    'Cazenga': [
        {'id': 23, 'name': 'Hoji-ya-Henda', 'population': 220000, 'type': 'Residencial', 'risk': 'Muito Alto', 'lat': -8.8080, 'lon': 13.2945},
    ],
}

# ==================== CACHES ====================
GADM_CACHE = {}
ELEVATION_CACHE = {}

# ==================== ELEVATION ====================
def get_elevation_batch(coordinates):
    try:
        locations = '|'.join([f"{lat},{lon}" for lat, lon in coordinates])
        url = f"https://api.open-elevation.com/api/v1/lookup?locations={locations}"
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            data = response.json()
            return [r['elevation'] for r in data['results']]
    except Exception as e:
        logger.error(f"Elevation error: {e}")
    return None


def get_point_elevation(lat, lon):
    cache_key = f"{lat:.4f}_{lon:.4f}"

    if cache_key in ELEVATION_CACHE:
        return ELEVATION_CACHE[cache_key]

    elevations = get_elevation_batch([(lat, lon)])

    if elevations:
        result = {
            'avg': float(elevations[0]),
            'min': float(elevations[0]),
            'max': float(elevations[0]),
            'range': 0.0
        }
    else:
        result = {'avg': 70.0, 'min': 50.0, 'max': 90.0, 'range': 40.0}

    ELEVATION_CACHE[cache_key] = result
    return result


# ==================== FLOOD LOGIC ====================
def calculate_flood_risk(risk_level, flood_rate, water_level_input, area_elevation=0, elevation_stats=None):
    risk_factors = {'Muito Alto': 0.35, 'Alto': 0.20, 'Médio': 0.05, 'Baixo': -0.10}

    risk_modifier = risk_factors.get(risk_level, 0)

    adjusted_probability = flood_rate + risk_modifier
    adjusted_probability = max(0, min(1, adjusted_probability))

    water_level = adjusted_probability * 10
    is_flooded = water_level > 2

    if is_flooded:
        return True, water_level, 'Moderada', 10

    return False, 0, 'Nenhuma', 0


# ==================== ROUTES ====================
@app.route('/')
def home():
    return render_template('teste_api.html')


@app.route('/api/simulate', methods=['POST'])
def simulate():
    data = request.get_json()

    municipality = data.get('municipality')
    flood_rate = float(data.get('floodRate', 50)) / 100

    bairros = BAIRROS.get(municipality, [])
    results = []

    for b in bairros:
        elev = get_point_elevation(b['lat'], b['lon'])

        flooded, wl, severity, rec = calculate_flood_risk(
            b['risk'], flood_rate, None, elev['avg'], elev
        )

        results.append({
            'name': b['name'],
            'flooded': flooded,
            'waterLevel': wl,
            'severity': severity,
            'elevation': elev['avg']
        })

    return jsonify({'success': True, 'data': results})


# ==================== GADM SIMULATION FIX ====================
@app.route('/api/simulate_full', methods=['POST'])
def simulate_full():
    try:
        data = request.get_json()
        flood_rate = float(data.get('floodRate', 0.5))

        level = data.get('level', 'province')

        gdf = None

        if level == 'province':
            gdf = download_and_read_gadm_json('AGO', 1)
        else:
            gdf = download_and_read_gadm_json('AGO', 2)

        if gdf is None:
            return jsonify({'success': False, 'error': 'GADM error'}), 500

        results = []

        for i, row in gdf.iterrows():

            # ✔️ FIX: garantir nome antes de usar
            name = row.get('NAME_1') if level == 'province' else row.get('NAME_2')
            prov = row.get('NAME_1')

            elevation = get_point_elevation(row.geometry.centroid.y, row.geometry.centroid.x)

            flooded, wl, severity, rec = calculate_flood_risk(
                'Médio', flood_rate, None, elevation['avg'], elevation
            )

            results.append({
                'name': name,
                'province': prov,
                'flooded': flooded,
                'waterLevel': wl,
                'severity': severity,
                'elevation': elevation['avg']
            })

        return jsonify({'success': True, 'data': results})

    except Exception as e:
        logger.error(e)
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== RUN ====================
if __name__ == '__main__':
    app.run(debug=True)