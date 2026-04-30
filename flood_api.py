import os
os.system("pip install -r requirements.txt")
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime
import logging
import requests
import geopandas as gpd
from zipfile import ZipFile
from io import BytesIO
import numpy as np
import math
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)
CORS(app)

# ==================== DADOS ESTÁTICOS (NOVA DIVISÃO GEOGRÁFICA) ====================
PROVINCES = [
    {'id': 1, 'name': 'Luanda', 'risk': 'Muito Alto', 'population': 8329517, 'area': 2417},
]

MUNICIPALITIES = {
    'Luanda': [
        {'id': 1,  'name': 'Belas',         'population': 600000,  'area': 500,  'risk': 'Alto'},
        {'id': 2,  'name': 'Cacuaco',        'population': 850000,  'area': 450,  'risk': 'Muito Alto'},
        {'id': 3,  'name': 'Cazenga',        'population': 980000,  'area': 32,   'risk': 'Muito Alto'},
        {'id': 4,  'name': 'Viana',          'population': 800000,  'area': 800,  'risk': 'Alto'},
        {'id': 5,  'name': 'Kilamba Kiaxi',  'population': 1120000, 'area': 52,   'risk': 'Muito Alto'},
        {'id': 6,  'name': 'Talatona',       'population': 500000,  'area': 160,  'risk': 'Médio'},
        {'id': 7,  'name': 'Maianga',        'population': 500000,  'area': 50,   'risk': 'Alto'},
        {'id': 8,  'name': 'Rangel',         'population': 261000,  'area': 10,   'risk': 'Muito Alto'},
        {'id': 9,  'name': 'Ingombota',      'population': 370000,  'area': 8,    'risk': 'Médio'},
        {'id': 10, 'name': 'Samba',          'population': 400000,  'area': 140,  'risk': 'Alto'},
        {'id': 11, 'name': 'Sambizanga',     'population': 300000,  'area': 12,   'risk': 'Muito Alto'},
        {'id': 12, 'name': 'Hoji Ya Henda',  'population': 700000,  'area': 30,   'risk': 'Muito Alto'},
        {'id': 13, 'name': 'Kilamba',        'population': 250000,  'area': 55,   'risk': 'Médio'},
        {'id': 14, 'name': 'Camama',         'population': 320000,  'area': 45,   'risk': 'Alto'},
        {'id': 15, 'name': 'Mulenvos',       'population': 180000,  'area': 20,   'risk': 'Alto'},
    ],
}

BAIRROS = {
    'Kilamba Kiaxi': [
        {'id': 1,  'name': 'Golfe',         'population': 120000, 'type': 'Residencial', 'risk': 'Alto',      'lat': -8.8780, 'lon': 13.2490},
        {'id': 2,  'name': 'Golfe II',      'population': 100000, 'type': 'Residencial', 'risk': 'Alto',      'lat': -8.8850, 'lon': 13.2550},
        {'id': 3,  'name': 'Palanca',       'population': 150000, 'type': 'Residencial', 'risk': 'Alto',      'lat': -8.8950, 'lon': 13.2620},
        {'id': 4,  'name': 'Vila Estoril',  'population': 90000,  'type': 'Residencial', 'risk': 'Médio',     'lat': -8.8900, 'lon': 13.2440},
        {'id': 5,  'name': 'Sapú',          'population': 130000, 'type': 'Residencial', 'risk': 'Alto',      'lat': -8.8820, 'lon': 13.2700},
    ],
    'Cazenga': [
        {'id': 10, 'name': 'Cazenga Sede',   'population': 250000, 'type': 'Residencial', 'risk': 'Muito Alto', 'lat': -8.8195, 'lon': 13.2880},
        {'id': 11, 'name': 'Tala Hady',      'population': 180000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8270, 'lon': 13.3030},
        {'id': 12, 'name': 'Sapú (Cazenga)', 'population': 120000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8340, 'lon': 13.2850},
        {'id': 13, 'name': 'Kikolo',         'population': 160000, 'type': 'Residencial', 'risk': 'Muito Alto', 'lat': -8.8120, 'lon': 13.3020},
    ],
    'Cacuaco': [
        {'id': 20, 'name': 'Cacuaco Sede', 'population': 200000, 'type': 'Residencial', 'risk': 'Muito Alto', 'lat': -8.7870, 'lon': 13.3670},
        {'id': 21, 'name': 'Sequele',      'population': 140000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8030, 'lon': 13.3260},
        {'id': 22, 'name': 'Funda',        'population': 160000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.7700, 'lon': 13.3720},
        {'id': 23, 'name': 'Quiage',       'population': 95000,  'type': 'Residencial', 'risk': 'Médio',      'lat': -8.7560, 'lon': 13.3550},
        {'id': 24, 'name': 'Cabolombo',    'population': 110000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.7780, 'lon': 13.3440},
    ],
    'Viana': [
        {'id': 30, 'name': 'Viana Sede', 'population': 250000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.9040, 'lon': 13.3740},
        {'id': 31, 'name': 'Zango',      'population': 350000, 'type': 'Residencial', 'risk': 'Muito Alto', 'lat': -8.9520, 'lon': 13.4030},
        {'id': 32, 'name': 'Kikuxi',     'population': 200000, 'type': 'Industrial',  'risk': 'Alto',       'lat': -8.9180, 'lon': 13.3390},
        {'id': 33, 'name': 'Calumbo',    'population': 120000, 'type': 'Residencial', 'risk': 'Médio',      'lat': -8.8670, 'lon': 13.4290},
    ],
    'Belas': [
        {'id': 40, 'name': 'Belas Sede',      'population': 180000, 'type': 'Residencial', 'risk': 'Médio',  'lat': -9.0860, 'lon': 13.2010},
        {'id': 41, 'name': 'Benfica (Belas)', 'population': 140000, 'type': 'Residencial', 'risk': 'Alto',   'lat': -8.9700, 'lon': 13.1880},
        {'id': 42, 'name': 'Ramiros',         'population': 95000,  'type': 'Residencial', 'risk': 'Baixo',  'lat': -9.0200, 'lon': 13.2200},
        {'id': 43, 'name': 'Futungo de Belas','population': 110000, 'type': 'Residencial', 'risk': 'Alto',   'lat': -9.0020, 'lon': 13.1700},
    ],
    'Talatona': [
        {'id': 50, 'name': 'Talatona Sede',    'population': 120000, 'type': 'Residencial', 'risk': 'Baixo',  'lat': -8.9600, 'lon': 13.1900},
        {'id': 51, 'name': 'Nova Vida',        'population': 200000, 'type': 'Residencial', 'risk': 'Médio',  'lat': -8.9620, 'lon': 13.2220},
        {'id': 52, 'name': 'Projecto Nova Vida','population': 150000, 'type': 'Residencial', 'risk': 'Baixo',  'lat': -8.9480, 'lon': 13.2310},
        {'id': 53, 'name': 'Morro Bento II',   'population': 100000, 'type': 'Residencial', 'risk': 'Médio',  'lat': -8.9390, 'lon': 13.2200},
    ],
    'Maianga': [
        {'id': 60, 'name': 'Alvalade',               'population': 120000, 'type': 'Residencial', 'risk': 'Médio',      'lat': -8.8375, 'lon': 13.2295},
        {'id': 61, 'name': 'Bairro Popular',         'population': 250000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8440, 'lon': 13.2400},
        {'id': 62, 'name': 'Prenda',                 'population': 200000, 'type': 'Residencial', 'risk': 'Muito Alto', 'lat': -8.8570, 'lon': 13.2560},
        {'id': 63, 'name': 'Rocha Pinto',            'population': 180000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8490, 'lon': 13.2500},
        {'id': 64, 'name': 'Cassequel',              'population': 100000, 'type': 'Residencial', 'risk': 'Médio',      'lat': -8.8460, 'lon': 13.2360},
        {'id': 65, 'name': 'Mártires do Kifangondo', 'population': 80000,  'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8540, 'lon': 13.2480},
        {'id': 66, 'name': 'Calemba',                'population': 70000,  'type': 'Residencial', 'risk': 'Baixo',      'lat': -8.8560, 'lon': 13.2350},
    ],
    'Rangel': [
        {'id': 70, 'name': 'Terra Nova',         'population': 100000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8215, 'lon': 13.2640},
        {'id': 71, 'name': 'Precol',             'population': 80000,  'type': 'Residencial', 'risk': 'Muito Alto', 'lat': -8.8170, 'lon': 13.2590},
        {'id': 72, 'name': 'Combatentes',        'population': 120000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8245, 'lon': 13.2600},
        {'id': 73, 'name': 'Valódia',            'population': 90000,  'type': 'Residencial', 'risk': 'Médio',      'lat': -8.8290, 'lon': 13.2615},
        {'id': 74, 'name': 'Mabor',              'population': 70000,  'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8250, 'lon': 13.2690},
        {'id': 75, 'name': 'Cuca',               'population': 60000,  'type': 'Residencial', 'risk': 'Médio',      'lat': -8.8200, 'lon': 13.2710},
        {'id': 76, 'name': 'Comandante Valódia', 'population': 110000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8310, 'lon': 13.2660},
        {'id': 77, 'name': 'Lixeira (Rangel)',   'population': 95000,  'type': 'Residencial', 'risk': 'Muito Alto', 'lat': -8.8165, 'lon': 13.2625},
    ],
    'Ingombota': [
        {'id': 80, 'name': 'Cidade Alta',     'population': 90000,  'type': 'Comercial',   'risk': 'Baixo',  'lat': -8.8170, 'lon': 13.2240},
        {'id': 81, 'name': 'Coqueiros',       'population': 120000, 'type': 'Residencial', 'risk': 'Médio',  'lat': -8.8145, 'lon': 13.2195},
        {'id': 82, 'name': 'Cruzeiro',        'population': 85000,  'type': 'Comercial',   'risk': 'Médio',  'lat': -8.8155, 'lon': 13.2300},
        {'id': 83, 'name': 'Patrice Lumumba', 'population': 110000, 'type': 'Residencial', 'risk': 'Alto',   'lat': -8.8215, 'lon': 13.2345},
        {'id': 84, 'name': 'Chicala',         'population': 80000,  'type': 'Residencial', 'risk': 'Alto',   'lat': -8.8030, 'lon': 13.2430},
        {'id': 85, 'name': 'Boa Vista',       'population': 60000,  'type': 'Residencial', 'risk': 'Baixo',  'lat': -8.8070, 'lon': 13.2220},
    ],
    'Samba': [
        {'id': 90, 'name': 'Rocha Pinto (Samba)', 'population': 150000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8640, 'lon': 13.2530},
        {'id': 91, 'name': 'Gamek',               'population': 180000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8710, 'lon': 13.2470},
        {'id': 92, 'name': 'Corimba',             'population': 120000, 'type': 'Residencial', 'risk': 'Muito Alto', 'lat': -8.8590, 'lon': 13.2280},
        {'id': 93, 'name': 'Mabunda',             'population': 90000,  'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8680, 'lon': 13.2370},
        {'id': 94, 'name': 'Morro Bento',         'population': 220000, 'type': 'Residencial', 'risk': 'Médio',      'lat': -8.8760, 'lon': 13.2420},
        {'id': 95, 'name': 'Samba Pequena',       'population': 80000,  'type': 'Residencial', 'risk': 'Baixo',      'lat': -8.8820, 'lon': 13.2340},
    ],
    'Sambizanga': [
        {'id': 100, 'name': 'Bairro Operário',  'population': 150000, 'type': 'Residencial', 'risk': 'Muito Alto', 'lat': -8.7980, 'lon': 13.2490},
        {'id': 101, 'name': 'Ngola Kiluanje',   'population': 120000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8015, 'lon': 13.2530},
        {'id': 102, 'name': 'Petrangol',        'population': 110000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8100, 'lon': 13.2590},
        {'id': 103, 'name': 'Miramar',          'population': 80000,  'type': 'Residencial', 'risk': 'Médio',      'lat': -8.7940, 'lon': 13.2420},
        {'id': 104, 'name': 'Boavista',         'population': 60000,  'type': 'Residencial', 'risk': 'Baixo',      'lat': -8.7910, 'lon': 13.2380},
        {'id': 105, 'name': 'EMCIB',            'population': 85000,  'type': 'Residencial', 'risk': 'Médio',      'lat': -8.8000, 'lon': 13.2460},
    ],
    'Hoji Ya Henda': [
        {'id': 110, 'name': 'Hoji Ya Henda Sede', 'population': 220000, 'type': 'Residencial', 'risk': 'Muito Alto', 'lat': -8.8080, 'lon': 13.2945},
        {'id': 111, 'name': 'Calemba II',         'population': 160000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8010, 'lon': 13.3080},
        {'id': 112, 'name': 'Palanca (HYH)',      'population': 130000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.7940, 'lon': 13.3200},
    ],
    'Kilamba': [
        {'id': 120, 'name': 'Kilamba A',   'population': 80000,  'type': 'Residencial', 'risk': 'Médio', 'lat': -8.9295, 'lon': 13.2905},
        {'id': 121, 'name': 'Kilamba B',   'population': 80000,  'type': 'Residencial', 'risk': 'Médio', 'lat': -8.9380, 'lon': 13.2850},
        {'id': 122, 'name': 'Kilamba C',   'population': 90000,  'type': 'Residencial', 'risk': 'Baixo', 'lat': -8.9350, 'lon': 13.3010},
    ],
    'Camama': [
        {'id': 130, 'name': 'Camama Sede', 'population': 150000, 'type': 'Residencial', 'risk': 'Alto',  'lat': -8.9450, 'lon': 13.2680},
        {'id': 131, 'name': 'Benfica',     'population': 120000, 'type': 'Residencial', 'risk': 'Alto',  'lat': -8.9540, 'lon': 13.2530},
        {'id': 132, 'name': 'Cassoneca',   'population': 90000,  'type': 'Residencial', 'risk': 'Médio', 'lat': -8.9350, 'lon': 13.2800},
    ],
    'Mulenvos': [
        {'id': 140, 'name': 'Mulenvos de Baixo', 'population': 100000, 'type': 'Residencial', 'risk': 'Muito Alto', 'lat': -8.7850, 'lon': 13.2650},
        {'id': 141, 'name': 'Mulenvos de Cima',  'population': 80000,  'type': 'Residencial', 'risk': 'Alto',       'lat': -8.7770, 'lon': 13.2720},
    ],
}

# ==================== FUNÇÃO PARA CRIAR POLÍGONO A PARTIR DE BAIRROS ====================
def create_municipio_polygon_from_bairros(municipio_name, bairros_list):
    """Cria um polígono que engloba todos os bairros do município"""
    import math
    
    # Coletar todas as coordenadas dos bairros
    coords = []
    for bairro in bairros_list:
        if 'lat' in bairro and 'lon' in bairro:
            coords.append((bairro['lon'], bairro['lat']))
    
    if len(coords) < 3:
        return None
    
    # Calcular centróide
    center_lon = sum(c[0] for c in coords) / len(coords)
    center_lat = sum(c[1] for c in coords) / len(coords)
    
    # Calcular distâncias máximas para definir o raio do círculo que engloba todos
    max_dist = 0
    for lon, lat in coords:
        dx = (lon - center_lon) * 111.32 * math.cos(center_lat * math.pi / 180)
        dy = (lat - center_lat) * 110.574
        dist = math.sqrt(dx*dx + dy*dy)
        max_dist = max(max_dist, dist)
    
    # Adicionar 20% de margem
    radius_km = (max_dist / 1000) * 1.2
    radius_km = max(0.8, min(radius_km, 3.5))
    
    # Criar polígono circular
    coords_poly = []
    earth_radius = 6371
    points = 48
    
    for i in range(points + 1):
        angle = (i * 2 * math.pi) / points
        d_lat = (radius_km / earth_radius) * math.cos(angle) * (180 / math.pi)
        d_lon = (radius_km / earth_radius) * math.sin(angle) * (180 / math.pi) / math.cos(center_lat * math.pi / 180)
        coords_poly.append([center_lon + d_lon, center_lat + d_lat])
    
    return {
        "type": "Polygon",
        "coordinates": [coords_poly]
    }

# ==================== CACHES ====================
GADM_CACHE = {}
ELEVATION_CACHE = {}

# ==================== FUNÇÕES DE ELEVAÇÃO ====================
def get_elevation_batch(coordinates):
    try:
        if len(coordinates) > 100:
            coordinates = coordinates[:100]
        locations = '|'.join([f"{lat},{lon}" for lat, lon in coordinates])
        url = f"https://api.open-elevation.com/api/v1/lookup?locations={locations}"
        logger.info(f"Buscando elevação para {len(coordinates)} pontos...")
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            elevations = [result['elevation'] for result in data['results']]
            return elevations
        else:
            logger.warning(f"Erro ao obter elevações: Status {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Erro ao obter elevações: {e}")
        return None

def get_point_elevation(lat, lon):
    cache_key = f"pt_{lat:.4f}_{lon:.4f}"
    if cache_key in ELEVATION_CACHE:
        return ELEVATION_CACHE[cache_key]

    elevations = get_elevation_batch([(lat, lon)])
    if elevations and len(elevations) > 0 and elevations[0] is not None and elevations[0] >= 0:
        result = {
            'avg': float(elevations[0]),
            'min': float(elevations[0]),
            'max': float(elevations[0]),
            'range': 0.0,
            'points_sampled': 1
        }
    else:
        result = {
            'avg': 70.0,
            'min': 50.0,
            'max': 90.0,
            'range': 40.0,
            'points_sampled': 0
        }

    ELEVATION_CACHE[cache_key] = result
    return result

def get_region_elevation_stats(geometry):
    try:
        cache_key = f"{geometry.centroid.y:.4f},{geometry.centroid.x:.4f}"
        if cache_key in ELEVATION_CACHE:
            return ELEVATION_CACHE[cache_key]

        bounds = geometry.bounds
        centroid = geometry.centroid
        area = geometry.area

        num_points = 9 if area > 1.0 else (5 if area > 0.1 else 3)

        points = [(centroid.y, centroid.x)]
        if num_points >= 5:
            points.extend([
                (bounds[1], bounds[0]),
                (bounds[3], bounds[2]),
                (bounds[1], bounds[2]),
                (bounds[3], bounds[0]),
            ])
        if num_points >= 9:
            mid_lat = (bounds[1] + bounds[3]) / 2
            mid_lon = (bounds[0] + bounds[2]) / 2
            points.extend([
                (mid_lat, bounds[0]),
                (mid_lat, bounds[2]),
                (bounds[1], mid_lon),
                (bounds[3], mid_lon),
            ])

        elevations = get_elevation_batch(points)
        if elevations and len(elevations) > 0:
            valid_elevations = [e for e in elevations if e is not None and e >= 0]
            if valid_elevations:
                avg = np.mean(valid_elevations)
                min_elev = np.min(valid_elevations)
                max_elev = np.max(valid_elevations)
                result = {
                    'avg': float(avg),
                    'min': float(min_elev),
                    'max': float(max_elev),
                    'range': float(max_elev - min_elev),
                    'points_sampled': len(valid_elevations)
                }
                ELEVATION_CACHE[cache_key] = result
                return result

        result = {'avg': 70.0, 'min': 40.0, 'max': 120.0, 'range': 80.0, 'points_sampled': 0}
        ELEVATION_CACHE[cache_key] = result
        return result

    except Exception as e:
        logger.error(f"Erro ao calcular elevação: {e}")
        return {'avg': 70.0, 'min': 40.0, 'max': 120.0, 'range': 80.0, 'points_sampled': 0}

# ==================== GADM ====================
def download_and_read_gadm_json(country_code, level):
    cache_key = f"{country_code}_{level}"
    if cache_key in GADM_CACHE:
        return GADM_CACHE[cache_key]

    json_url = f'https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_{country_code}_{level}.json.zip'
    logger.info(f"Baixando GeoJSON: {json_url}...")
    try:
        response = requests.get(json_url, timeout=60)
        response.raise_for_status()
        with ZipFile(BytesIO(response.content)) as zip_file:
            json_filename = zip_file.namelist()[0]
            with zip_file.open(json_filename) as json_file:
                gdf = gpd.read_file(json_file, driver='GeoJSON')
        GADM_CACHE[cache_key] = gdf
        logger.info(f"GADM Level {level} em cache ({len(gdf)} features)")
        return gdf
    except Exception as e:
        logger.error(f"Erro ao baixar/processar GeoJSON: {e}")
        return None

def normalize_name(name):
    import unicodedata
    name = unicodedata.normalize('NFD', name)
    name = ''.join(char for char in name if unicodedata.category(char) != 'Mn')
    name = name.replace(' ', '').replace('-', '').replace('_', '').lower()
    return name

# ==================== CÁLCULO DE INUNDAÇÃO ====================
def calculate_flood_risk(risk_level, flood_rate, water_level_input, area_elevation=0, elevation_stats=None):
    risk_factors    = {'Muito Alto': 0.35, 'Alto': 0.20, 'Médio': 0.05, 'Baixo': -0.10}
    drainage_factor = {'Muito Alto': 0.9,  'Alto': 0.7,  'Médio': 0.5,  'Baixo': 0.3}

    risk_modifier = risk_factors.get(risk_level, 0)
    drainage = drainage_factor.get(risk_level, 0.5)

    avg_elevation = elevation_stats['avg'] if elevation_stats else area_elevation
    elevation_range = elevation_stats.get('range', 0) if elevation_stats else 0
    min_elevation = elevation_stats['min'] if elevation_stats else area_elevation

    if avg_elevation < 50:
        elevation_risk = 0.40
    elif avg_elevation < 200:
        elevation_risk = 0.30
    elif avg_elevation < 500:
        elevation_risk = 0.15
    elif avg_elevation < 1000:
        elevation_risk = 0.05
    else:
        elevation_risk = -0.10

    if elevation_range > 300:
        terrain_risk = 0.25
    elif elevation_range > 150:
        terrain_risk = 0.15
    elif elevation_range > 50:
        terrain_risk = 0.08
    else:
        terrain_risk = 0.0

    adjusted_probability = flood_rate + risk_modifier + elevation_risk + terrain_risk
    adjusted_probability = max(0, min(1, adjusted_probability))

    if water_level_input and water_level_input > 0:
        base_water = water_level_input
        elevation_multiplier = max(0.5, (1000 - avg_elevation) / 1000)
        effective_water_level = base_water * drainage * elevation_multiplier
    else:
        if adjusted_probability > 0.5:
            base_water = 10.0 * (adjusted_probability - 0.5) / 0.5
        else:
            base_water = 5.0 * adjusted_probability / 0.5
        elevation_multiplier = max(0.5, (1000 - avg_elevation) / 1000)
        effective_water_level = base_water * drainage * adjusted_probability * elevation_multiplier

    flood_threshold = max(2.0, min_elevation / 100)
    is_flooded = effective_water_level > flood_threshold

    if is_flooded:
        water_level_val = effective_water_level
        if water_level_val < 8.0 and avg_elevation > 100:
            severity = 'Leve'
            recovery_days = int(7 + water_level_val * 0.5)
        elif water_level_val < 15.0:
            severity = 'Moderada'
            recovery_days = int(15 + water_level_val * 1.0)
        elif water_level_val < 25.0:
            severity = 'Grave'
            recovery_days = int(30 + water_level_val * 1.5)
        else:
            severity = 'Crítica'
            recovery_days = int(60 + water_level_val * 2.0)

        if avg_elevation < 50:
            recovery_days = int(recovery_days * 1.5)

        return True, water_level_val, severity, recovery_days
    else:
        return False, 0, 'Nenhuma', 0

# ==================== ROTAS ====================
@app.route('/')
def home():
    return render_template('teste_api.html')

@app.route('/api', methods=['GET'])
def api_home():
    return jsonify({
        'message': 'API de Simulação de Inundações - Angola',
        'version': '4.2.0',
        'status': 'online',
        'features': ['Dados GADM', 'Elevação Real por Ponto', 'Nova Divisão Geográfica de Angola (Lei 14/24)', 'Polígonos para todos os municípios'],
        'endpoints': {
            'health':         '/api/health',
            'info':           '/api/info',
            'provinces':      '/api/provinces',
            'municipalities': '/api/municipalities?province=X',
            'bairros':        '/api/bairros?municipality=X',
            'simulate':       '/api/simulate (POST)',
            'elevation':      '/api/elevation?lat=X&lon=Y',
        }
    })

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'message': 'API activa — Todos os municípios têm polígonos',
        'timestamp': datetime.now().isoformat(),
        'cache_status': {
            'gadm_cached': len(GADM_CACHE),
            'elevation_cached': len(ELEVATION_CACHE),
        }
    })

@app.route('/api/info', methods=['GET'])
def api_info():
    return jsonify({
        'name': 'API de Simulação de Inundações - Angola',
        'version': '4.2.0',
        'description': 'API com coordenadas reais por bairro, elevação pontual e nova divisão geográfica',
        'data_available': {
            'provinces':     len(PROVINCES),
            'municipalities': sum(len(m) for m in MUNICIPALITIES.values()),
            'bairros':       sum(len(b) for b in BAIRROS.values()),
        },
        'elevation_service': 'Open-Elevation API (SRTM 90m)',
    })

@app.route('/api/provinces', methods=['GET'])
def get_provinces():
    gdf = download_and_read_gadm_json('AGO', 1)
    if gdf is None:
        return jsonify({'success': False, 'error': 'Erro ao carregar dados do GADM'}), 500

    provinces = []
    for _, row in gdf.iterrows():
        name = row['NAME_1']
        static = next((p for p in PROVINCES if p['name'] == name), None)
        if static:
            centroid = row['geometry'].centroid
            provinces.append({
                'id': static['id'], 'name': name,
                'risk': static['risk'], 'population': static['population'],
                'area': static['area'], 'lat': centroid.y, 'lon': centroid.x,
            })

    return jsonify({'success': True, 'data': provinces, 'count': len(provinces), 'timestamp': datetime.now().isoformat()})

@app.route('/api/municipalities', methods=['GET'])
def get_municipalities():
    province = request.args.get('province', 'Luanda')
    if province != 'Luanda':
        return jsonify({'success': True, 'data': [], 'count': 0})

    static_muns = MUNICIPALITIES.get('Luanda', [])
    gdf = download_and_read_gadm_json('AGO', 2)

    municipalities = []

    if gdf is not None:
        gdf = gdf[gdf['NAME_1'] == 'Luanda']
        gadm_to_static = {
            'Belas': 'Belas', 'Cacuaco': 'Cacuaco', 'Cazenga': 'Cazenga',
            'Viana': 'Viana', 'Kilamba-Kiaxi': 'Kilamba Kiaxi', 'Talatona': 'Talatona',
            'Maianga': 'Maianga', 'Rangel': 'Rangel', 'Ingombota': 'Ingombota',
            'Samba': 'Samba', 'Sambizanga': 'Sambizanga',
        }

        for _, row in gdf.iterrows():
            gadm_name = row['NAME_2']
            static_name = gadm_to_static.get(gadm_name)
            if static_name:
                static_mun = next((m for m in static_muns if m['name'] == static_name), None)
                if static_mun:
                    centroid = row['geometry'].centroid
                    municipalities.append({
                        'id': static_mun['id'], 'name': static_name, 'province': 'Luanda',
                        'risk': static_mun['risk'], 'population': static_mun['population'],
                        'area': static_mun['area'], 'lat': centroid.y, 'lon': centroid.x,
                        'geometry': row['geometry'].__geo_interface__
                    })

    # Adicionar municípios novos (não estão no GADM) com polígonos criados a partir dos bairros
    novos_municipios = ['Hoji Ya Henda', 'Kilamba', 'Camama', 'Mulenvos']
    for mun_name in novos_municipios:
        if not any(m['name'] == mun_name for m in municipalities):
            static_mun = next((m for m in static_muns if m['name'] == mun_name), None)
            if static_mun:
                bairros_do_municipio = BAIRROS.get(mun_name, [])
                polygon_geo = create_municipio_polygon_from_bairros(mun_name, bairros_do_municipio)
                
                municipality_data = {
                    'id': static_mun['id'], 'name': mun_name, 'province': 'Luanda',
                    'risk': static_mun['risk'], 'population': static_mun['population'],
                    'area': static_mun['area'], 'lat': -8.9, 'lon': 13.3,
                }
                
                if polygon_geo:
                    municipality_data['geometry'] = polygon_geo
                
                municipalities.append(municipality_data)

    # Também adicionar Kilamba Kiaxi se não estiver
    if not any(m['name'] == 'Kilamba Kiaxi' for m in municipalities):
        municipalities.append({
            'id': 5, 'name': 'Kilamba Kiaxi', 'province': 'Luanda',
            'risk': 'Muito Alto', 'population': 1120000, 'area': 52,
            'lat': -8.886, 'lon': 13.258,
        })

    return jsonify({'success': True, 'data': municipalities, 'count': len(municipalities), 'timestamp': datetime.now().isoformat()})

@app.route('/api/bairros', methods=['GET'])
def get_bairros():
    municipality = request.args.get('municipality', None)
    province = request.args.get('province', None)

    if not municipality or municipality == 'all':
        all_bairros = []
        for munic_name, bairros_list in BAIRROS.items():
            for b in bairros_list:
                all_bairros.append({**b, 'municipality': munic_name})
        return jsonify({'success': True, 'data': all_bairros, 'count': len(all_bairros), 'timestamp': datetime.now().isoformat()})

    normalized_municipality = normalize_name(municipality)
    matching_key = next((k for k in BAIRROS if normalize_name(k) == normalized_municipality), None)

    if not matching_key:
        return jsonify({'success': True, 'data': [], 'count': 0,
                        'message': f'Nenhum bairro cadastrado para {municipality}',
                        'timestamp': datetime.now().isoformat()})

    bairros_list = list(BAIRROS[matching_key])

    bairro_filter = request.args.get('bairro', 'all')
    if bairro_filter and bairro_filter != 'all':
        bairros_list = [b for b in bairros_list if b['name'] == bairro_filter]
        if not bairros_list:
            return jsonify({'success': False, 'error': f'Bairro {bairro_filter} não encontrado em {municipality}'}), 404

    result = []
    for b in bairros_list:
        entry = {**b, 'municipality': municipality}
        if province:
            entry['province'] = province
        result.append(entry)

    return jsonify({'success': True, 'data': result, 'count': len(result),
                    'filter': {'municipality': municipality, 'province': province},
                    'timestamp': datetime.now().isoformat()})

@app.route('/api/elevation', methods=['GET'])
def get_elevation():
    try:
        lat = float(request.args.get('lat'))
        lon = float(request.args.get('lon'))
        elevations = get_elevation_batch([(lat, lon)])
        if elevations:
            return jsonify({'success': True, 'latitude': lat, 'longitude': lon, 'elevation': elevations[0], 'unit': 'meters'})
        return jsonify({'success': False, 'error': 'Não foi possível obter elevação'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# ==================== SIMULAÇÃO ====================
@app.route('/api/simulate', methods=['POST'])
def simulate_flood():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400

        level = data.get('level', 'province')
        flood_rate = float(data.get('floodRate', 50)) / 100
        water_level_raw = data.get('waterLevel')
        water_level_input = float(water_level_raw) if water_level_raw is not None else None

        province_param = data.get('province', 'all')
        municipality_param = data.get('municipality', 'all')
        bairro_sel = data.get('bairro', 'all')

        logger.info(f"Simulação — level={level} province={province_param} municipality={municipality_param} bairro={bairro_sel}")

        # ============================================================
        # SIMULAÇÃO DE BAIRROS
        # ============================================================
        if level == 'bairro':
            if not municipality_param or municipality_param == 'all':
                return jsonify({'success': False, 'error': 'Seleccione um município específico para simular bairros'}), 400

            normalized_municipality = normalize_name(municipality_param)
            matching_key = next((k for k in BAIRROS if normalize_name(k) == normalized_municipality), None)

            if not matching_key:
                return jsonify({'success': False, 'error': f'Nenhum bairro cadastrado para o município {municipality_param}'}), 404

            bairros_list = list(BAIRROS[matching_key])

            if bairro_sel and bairro_sel != 'all':
                bairros_list = [b for b in bairros_list if b['name'] == bairro_sel]
                if not bairros_list:
                    return jsonify({'success': False, 'error': f'Bairro "{bairro_sel}" não encontrado em {municipality_param}'}), 404

            results = []
            features = []

            for bairro_data in bairros_list:
                bairro_name = bairro_data['name']
                risk = bairro_data['risk']
                pop = bairro_data['population']
                b_lat = bairro_data['lat']
                b_lon = bairro_data['lon']
                
                elevation_stats = get_point_elevation(b_lat, b_lon)
                avg_elevation = elevation_stats['avg']

                is_flooded, wl, severity, recovery_days = calculate_flood_risk(
                    risk, flood_rate, water_level_input, avg_elevation, elevation_stats
                )

                affected_population = 0
                if is_flooded:
                    impact_factor = min(wl / 20.0, 0.7)
                    affected_population = int(pop * impact_factor)

                result_data = {
                    'name': bairro_name,
                    'municipality': municipality_param,
                    'province': province_param if province_param != 'all' else 'Luanda',
                    'type': bairro_data.get('type', 'Residencial'),
                    'flooded': is_flooded,
                    'waterLevel': wl,
                    'severity': severity,
                    'recoveryDays': recovery_days,
                    'affectedPopulation': affected_population,
                    'totalPopulation': pop,
                    'risk': risk,
                    'elevation': round(avg_elevation, 1),
                    'elevation_min': round(elevation_stats['min'], 1),
                    'elevation_max': round(elevation_stats['max'], 1),
                    'lat': b_lat,
                    'lon': b_lon,
                }
                results.append(result_data)

                # Criar polígono circular para o bairro
                radius_km = max(0.4, min(0.8, pop / 300000))
                polygon_geo = create_circular_polygon(b_lat, b_lon, radius_km)
                
                features.append({
                    'type': 'Feature',
                    'geometry': polygon_geo,
                    'properties': result_data,
                })

            flooded_count = sum(1 for r in results if r['flooded'])
            total_affected = sum(r['affectedPopulation'] for r in results)

            geojson = json.dumps({'type': 'FeatureCollection', 'features': features})

            return jsonify({
                'success': True,
                'data': results,
                'geojson': geojson,
                'statistics': {
                    'floodedCount': flooded_count,
                    'totalAffected': total_affected,
                    'totalBairros': len(results),
                    'avgRisk': (flooded_count / len(results) * 100) if results else 0,
                },
                'parameters': {
                    'level': 'bairro',
                    'floodRate': flood_rate * 100,
                    'province': province_param,
                    'municipality': municipality_param,
                    'bairro': bairro_sel,
                    'elevation_used': True,
                },
                'timestamp': datetime.now().isoformat(),
            })

        # ============================================================
        # SIMULAÇÃO DE MUNICÍPIOS
        # ============================================================
        elif level == 'municipality':
            static_muns = MUNICIPALITIES.get('Luanda', [])
            
            if municipality_param == 'all':
                muns_to_simulate = static_muns
            else:
                muns_to_simulate = [m for m in static_muns if m['name'] == municipality_param]
                if not muns_to_simulate:
                    return jsonify({'success': False, 'error': f'Município {municipality_param} não encontrado'}), 404

            results = []
            features = []

            for mun in muns_to_simulate:
                mun_name = mun['name']
                risk = mun['risk']
                pop = mun['population']
                
                # Obter geometria: primeiro tentar do GADM, senão criar a partir dos bairros
                geometry = None
                
                # Tentar obter do GADM
                gdf = download_and_read_gadm_json('AGO', 2)
                if gdf is not None:
                    gdf_luanda = gdf[gdf['NAME_1'] == 'Luanda']
                    gadm_row = gdf_luanda[gdf_luanda['NAME_2'] == mun_name]
                    if not gadm_row.empty:
                        geometry = gadm_row.iloc[0]['geometry'].__geo_interface__
                
                # Se não encontrou no GADM, criar polígono a partir dos bairros
                if geometry is None and mun_name in BAIRROS:
                    bairros_do_mun = BAIRROS[mun_name]
                    geometry = create_municipio_polygon_from_bairros(mun_name, bairros_do_mun)
                
                # Fallback: usar ponto central
                if geometry is None:
                    if 'lat' in mun and 'lon' in mun:
                        geometry = {
                            "type": "Point",
                            "coordinates": [mun['lon'], mun['lat']]
                        }
                    else:
                        geometry = {
                            "type": "Point",
                            "coordinates": [13.2344, -8.8383]
                        }
                
                elevation_stats = get_region_elevation_stats_for_geometry(geometry)
                avg_elevation = elevation_stats['avg']

                is_flooded, wl, severity, recovery_days = calculate_flood_risk(
                    risk, flood_rate, water_level_input, avg_elevation, elevation_stats
                )

                affected_population = 0
                if is_flooded:
                    impact_factor = min(wl / 20.0, 0.5)
                    affected_population = int(pop * impact_factor)

                result_data = {
                    'name': mun_name,
                    'province': 'Luanda',
                    'flooded': is_flooded,
                    'waterLevel': wl,
                    'severity': severity,
                    'recoveryDays': recovery_days,
                    'affectedPopulation': affected_population,
                    'totalPopulation': pop,
                    'risk': risk,
                    'elevation': round(avg_elevation, 1),
                }
                results.append(result_data)

                features.append({
                    'type': 'Feature',
                    'geometry': geometry,
                    'properties': result_data,
                })

            flooded_count = sum(1 for r in results if r['flooded'])
            total_affected = sum(r['affectedPopulation'] for r in results)
            geojson = json.dumps({'type': 'FeatureCollection', 'features': features})

            return jsonify({
                'success': True,
                'data': results,
                'geojson': geojson,
                'statistics': {
                    'floodedCount': flooded_count,
                    'totalAffected': total_affected,
                    'totalItems': len(results),
                    'avgRisk': (flooded_count / len(results) * 100) if results else 0,
                },
                'parameters': {
                    'level': 'municipality',
                    'floodRate': flood_rate * 100,
                    'province': province_param,
                    'municipality': municipality_param,
                    'elevation_used': True,
                },
                'timestamp': datetime.now().isoformat(),
            })

        # ============================================================
        # SIMULAÇÃO DE PROVÍNCIAS
        # ============================================================
        else:
            return jsonify({'success': False, 'error': 'Nível inválido. Use: municipality ou bairro'}), 400

    except Exception as e:
        logger.error(f"Erro na simulação: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

def create_circular_polygon(lat, lon, radius_km, points=48):
    """Cria um polígono circular"""
    import math
    coords = []
    earth_radius = 6371
    
    for i in range(points + 1):
        angle = (i * 2 * math.pi) / points
        d_lat = (radius_km / earth_radius) * math.cos(angle) * (180 / math.pi)
        d_lon = (radius_km / earth_radius) * math.sin(angle) * (180 / math.pi) / math.cos(lat * math.pi / 180)
        coords.append([lon + d_lon, lat + d_lat])
    
    return {"type": "Polygon", "coordinates": [coords]}

def get_region_elevation_stats_for_geometry(geometry):
    """Calcula estatísticas de elevação para uma geometria"""
    try:
        from shapely.geometry import shape
        
        geom = shape(geometry)
        bounds = geom.bounds
        centroid = geom.centroid
        
        points = [(centroid.y, centroid.x)]
        points.extend([
            (bounds[1], bounds[0]),
            (bounds[3], bounds[2]),
            (bounds[1], bounds[2]),
            (bounds[3], bounds[0]),
        ])
        
        elevations = get_elevation_batch(points)
        if elevations and len(elevations) > 0:
            valid_elevations = [e for e in elevations if e is not None and e >= 0]
            if valid_elevations:
                return {
                    'avg': float(np.mean(valid_elevations)),
                    'min': float(np.min(valid_elevations)),
                    'max': float(np.max(valid_elevations)),
                    'range': float(np.max(valid_elevations) - np.min(valid_elevations)),
                    'points_sampled': len(valid_elevations)
                }
        
        return {'avg': 70.0, 'min': 40.0, 'max': 120.0, 'range': 80.0, 'points_sampled': 0}
    except Exception as e:
        logger.error(f"Erro ao calcular elevação para geometria: {e}")
        return {'avg': 70.0, 'min': 40.0, 'max': 120.0, 'range': 80.0, 'points_sampled': 0}

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)