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
        {'id': 1,  'name': 'Belas',          'population': 600000,  'area': 500,   'risk': 'Alto'},
        {'id': 2,  'name': 'Cacuaco',         'population': 850000,  'area': 450,   'risk': 'Muito Alto'},
        {'id': 3,  'name': 'Cazenga',         'population': 980000,  'area': 32,    'risk': 'Muito Alto'},
        {'id': 4,  'name': 'Icolo e Bengo',   'population': 150000,  'area': 3600,  'risk': 'Médio'},
        {'id': 5,  'name': 'Luanda',          'population': 2200000, 'area': 116,   'risk': 'Muito Alto'},
        {'id': 6,  'name': 'Quiçama',         'population': 25000,   'area': 13900, 'risk': 'Baixo'},
        {'id': 7,  'name': 'Viana',           'population': 2000000, 'area': 1700,  'risk': 'Alto'},
        {'id': 8,  'name': 'Kilamba Kiaxi',   'population': 1800000, 'area': 189,   'risk': 'Muito Alto'},
        {'id': 9,  'name': 'Talatona',        'population': 500000,  'area': 160,   'risk': 'Médio'},
        {'id': 10, 'name': 'Maianga',         'population': 500000,  'area': 50,    'risk': 'Alto'},
        {'id': 11, 'name': 'Rangel',          'population': 261000,  'area': 62,    'risk': 'Muito Alto'},
        {'id': 12, 'name': 'Ingombota',       'population': 370000,  'area': 30,    'risk': 'Médio'},
        {'id': 13, 'name': 'Samba',           'population': 400000,  'area': 345,   'risk': 'Alto'},
        {'id': 14, 'name': 'Sambizanga',      'population': 300000,  'area': 40,    'risk': 'Muito Alto'},
    ],
}

# ==================== BAIRROS COM COORDENADAS REAIS ====================
BAIRROS = {
    'Kilamba Kiaxi': [
        {'id': 19,  'name': 'Golfe',            'population': 300000, 'type': 'Residencial', 'risk': 'Alto',      'lat': -8.8950, 'lon': 13.2510},
        {'id': 20,  'name': 'Palanca',           'population': 280000, 'type': 'Residencial', 'risk': 'Alto',      'lat': -8.9120, 'lon': 13.2650},
        {'id': 21,  'name': 'Kilamba',           'population': 450000, 'type': 'Residencial', 'risk': 'Médio',     'lat': -8.9300, 'lon': 13.2900},
        {'id': 22,  'name': 'Camama',            'population': 320000, 'type': 'Residencial', 'risk': 'Alto',      'lat': -8.9450, 'lon': 13.2700},
        {'id': 100, 'name': 'Sapu',              'population': 150000, 'type': 'Residencial', 'risk': 'Alto',      'lat': -8.9020, 'lon': 13.2580},
        {'id': 101, 'name': 'Nova Vida',         'population': 200000, 'type': 'Residencial', 'risk': 'Médio',     'lat': -8.9200, 'lon': 13.2450},
        {'id': 102, 'name': 'Bairro Popular',    'population': 250000, 'type': 'Residencial', 'risk': 'Alto',      'lat': -8.8870, 'lon': 13.2600},
        {'id': 103, 'name': 'Benfica',           'population': 180000, 'type': 'Residencial', 'risk': 'Médio',     'lat': -8.9550, 'lon': 13.2550},
        {'id': 104, 'name': 'Morro Bento',       'population': 220000, 'type': 'Residencial', 'risk': 'Alto',      'lat': -8.8820, 'lon': 13.2480},
        {'id': 105, 'name': 'Projecto Nova Vida','population': 150000, 'type': 'Residencial', 'risk': 'Baixo',     'lat': -8.9350, 'lon': 13.2400},
    ],
    'Cazenga': [
        {'id': 23, 'name': 'Hoji-ya-Henda',  'population': 220000, 'type': 'Residencial', 'risk': 'Muito Alto', 'lat': -8.8080, 'lon': 13.2945},
        {'id': 24, 'name': 'Tala Hady',       'population': 180000, 'type': 'Residencial', 'risk': 'Alto',      'lat': -8.8280, 'lon': 13.3050},
        {'id': 25, 'name': 'Cazenga Sede',    'population': 250000, 'type': 'Residencial', 'risk': 'Muito Alto', 'lat': -8.8195, 'lon': 13.2880},
        {'id': 26, 'name': 'Sapu',            'population': 150000, 'type': 'Residencial', 'risk': 'Alto',      'lat': -8.8350, 'lon': 13.2820},
    ],
    'Luanda': [
        {'id': 1, 'name': 'Ingombota',      'population': 150000, 'type': 'Comercial',   'risk': 'Médio',      'lat': -8.8150, 'lon': 13.2320},
        {'id': 2, 'name': 'Maianga',        'population': 180000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8420, 'lon': 13.2450},
        {'id': 3, 'name': 'Rangel',         'population': 220000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8300, 'lon': 13.2550},
        {'id': 4, 'name': 'Sambizanga',     'population': 280000, 'type': 'Residencial', 'risk': 'Muito Alto', 'lat': -8.8050, 'lon': 13.2450},
        {'id': 5, 'name': 'Ilha de Luanda', 'population': 45000,  'type': 'Turístico',   'risk': 'Muito Alto', 'lat': -8.7950, 'lon': 13.2150},
        {'id': 6, 'name': 'Maculusso',      'population': 90000,  'type': 'Residencial', 'risk': 'Baixo',      'lat': -8.8280, 'lon': 13.2350},
        {'id': 7, 'name': 'Alvalade',       'population': 120000, 'type': 'Residencial', 'risk': 'Médio',      'lat': -8.8380, 'lon': 13.2280},
        {'id': 8, 'name': 'Mutamba',        'population': 80000,  'type': 'Comercial',   'risk': 'Alto',       'lat': -8.8220, 'lon': 13.2300},
    ],
    'Cacuaco': [
        {'id': 9,  'name': 'Kikolo',     'population': 180000, 'type': 'Residencial', 'risk': 'Muito Alto', 'lat': -8.7600, 'lon': 13.3200},
        {'id': 10, 'name': 'Sequele',    'population': 140000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.7820, 'lon': 13.3050},
        {'id': 11, 'name': 'Funda',      'population': 160000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.7950, 'lon': 13.3450},
        {'id': 12, 'name': 'Quiage',     'population': 95000,  'type': 'Residencial', 'risk': 'Médio',      'lat': -8.7700, 'lon': 13.3350},
        {'id': 13, 'name': 'Cabolombo',  'population': 110000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.7850, 'lon': 13.3180},
    ],
    'Viana': [
        {'id': 14, 'name': 'Viana Sede', 'population': 250000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.9050, 'lon': 13.3750},
        {'id': 15, 'name': 'Calumbo',    'population': 180000, 'type': 'Residencial', 'risk': 'Médio',      'lat': -8.8800, 'lon': 13.4150},
        {'id': 16, 'name': 'Catete',     'population': 120000, 'type': 'Residencial', 'risk': 'Médio',      'lat': -9.0900, 'lon': 13.7100},
        {'id': 17, 'name': 'Kikuxi',     'population': 200000, 'type': 'Industrial',  'risk': 'Alto',       'lat': -8.9250, 'lon': 13.3500},
        {'id': 18, 'name': 'Zango',      'population': 350000, 'type': 'Residencial', 'risk': 'Muito Alto', 'lat': -8.9550, 'lon': 13.3950},
    ],
    'Belas': [
        {'id': 27, 'name': 'Belas Sede', 'population': 180000, 'type': 'Residencial', 'risk': 'Médio',  'lat': -9.0850, 'lon': 13.2050},
        {'id': 28, 'name': 'Benfica',    'population': 140000, 'type': 'Residencial', 'risk': 'Alto',   'lat': -8.9750, 'lon': 13.1900},
        {'id': 29, 'name': 'Ramiros',    'population': 95000,  'type': 'Residencial', 'risk': 'Baixo',  'lat': -9.0200, 'lon': 13.2150},
    ],
    'Maianga': [
        {'id': 200, 'name': 'Alvalade',                 'population': 120000, 'type': 'Residencial', 'risk': 'Médio',      'lat': -8.8370, 'lon': 13.2290},
        {'id': 201, 'name': 'Bairro Popular',           'population': 250000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8450, 'lon': 13.2380},
        {'id': 202, 'name': 'Cassenda',                 'population': 150000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8510, 'lon': 13.2430},
        {'id': 203, 'name': 'Cassequel',                'population': 100000, 'type': 'Residencial', 'risk': 'Médio',      'lat': -8.8480, 'lon': 13.2360},
        {'id': 204, 'name': 'Mártires do Kifangondo',   'population': 80000,  'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8540, 'lon': 13.2480},
        {'id': 205, 'name': 'Prenda',                   'population': 200000, 'type': 'Residencial', 'risk': 'Muito Alto', 'lat': -8.8580, 'lon': 13.2550},
        {'id': 206, 'name': 'Rocha Pinto',              'population': 180000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8490, 'lon': 13.2500},
        {'id': 207, 'name': 'Catambor',                 'population': 90000,  'type': 'Residencial', 'risk': 'Médio',      'lat': -8.8420, 'lon': 13.2420},
        {'id': 208, 'name': 'Catinton',                 'population': 110000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8460, 'lon': 13.2460},
        {'id': 209, 'name': 'Calemba',                  'population': 70000,  'type': 'Residencial', 'risk': 'Baixo',      'lat': -8.8560, 'lon': 13.2350},
    ],
    'Rangel': [
        {'id': 300, 'name': 'Terra Nova',           'population': 100000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8220, 'lon': 13.2640},
        {'id': 301, 'name': 'Precol',               'population': 80000,  'type': 'Residencial', 'risk': 'Muito Alto', 'lat': -8.8180, 'lon': 13.2580},
        {'id': 302, 'name': 'Combatentes',          'population': 120000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8250, 'lon': 13.2590},
        {'id': 303, 'name': 'Valódia',              'population': 90000,  'type': 'Residencial', 'risk': 'Médio',      'lat': -8.8290, 'lon': 13.2610},
        {'id': 304, 'name': 'Mabor',                'population': 70000,  'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8260, 'lon': 13.2680},
        {'id': 305, 'name': 'Cuca',                 'population': 60000,  'type': 'Residencial', 'risk': 'Médio',      'lat': -8.8200, 'lon': 13.2700},
        {'id': 306, 'name': 'Triangulo',            'population': 50000,  'type': 'Residencial', 'risk': 'Baixo',      'lat': -8.8150, 'lon': 13.2650},
        {'id': 307, 'name': 'Comandante Valódia',   'population': 110000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8310, 'lon': 13.2660},
        {'id': 308, 'name': 'Lixeira',              'population': 95000,  'type': 'Residencial', 'risk': 'Muito Alto', 'lat': -8.8170, 'lon': 13.2620},
        {'id': 309, 'name': 'S. Pedro',             'population': 85000,  'type': 'Residencial', 'risk': 'Médio',      'lat': -8.8330, 'lon': 13.2580},
    ],
    'Ingombota': [
        {'id': 400, 'name': 'Azul',             'population': 80000,  'type': 'Residencial', 'risk': 'Médio',  'lat': -8.8120, 'lon': 13.2280},
        {'id': 401, 'name': 'Boa Vista',        'population': 60000,  'type': 'Residencial', 'risk': 'Baixo',  'lat': -8.8080, 'lon': 13.2230},
        {'id': 402, 'name': 'Bungo',            'population': 70000,  'type': 'Residencial', 'risk': 'Alto',   'lat': -8.8100, 'lon': 13.2350},
        {'id': 403, 'name': 'Chicala I',        'population': 50000,  'type': 'Residencial', 'risk': 'Médio',  'lat': -8.8050, 'lon': 13.2380},
        {'id': 404, 'name': 'Chicala II',       'population': 45000,  'type': 'Residencial', 'risk': 'Alto',   'lat': -8.8020, 'lon': 13.2410},
        {'id': 405, 'name': 'Cidade Alta',      'population': 90000,  'type': 'Comercial',   'risk': 'Baixo',  'lat': -8.8180, 'lon': 13.2250},
        {'id': 406, 'name': 'Coqueiros',        'population': 120000, 'type': 'Residencial', 'risk': 'Médio',  'lat': -8.8150, 'lon': 13.2200},
        {'id': 407, 'name': 'Coreia',           'population': 100000, 'type': 'Residencial', 'risk': 'Alto',   'lat': -8.8200, 'lon': 13.2380},
        {'id': 408, 'name': 'Cruzeiro',         'population': 85000,  'type': 'Comercial',   'risk': 'Médio',  'lat': -8.8160, 'lon': 13.2310},
        {'id': 409, 'name': 'Patrice Lumumba',  'population': 110000, 'type': 'Residencial', 'risk': 'Alto',   'lat': -8.8220, 'lon': 13.2350},
    ],
    'Samba': [
        {'id': 500, 'name': 'Rocha Pinto',  'population': 150000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8600, 'lon': 13.2550},
        {'id': 501, 'name': 'Prenda',       'population': 200000, 'type': 'Residencial', 'risk': 'Muito Alto', 'lat': -8.8650, 'lon': 13.2600},
        {'id': 502, 'name': 'Gamek',        'population': 180000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8700, 'lon': 13.2480},
        {'id': 503, 'name': 'Morro Bento',  'population': 220000, 'type': 'Residencial', 'risk': 'Médio',      'lat': -8.8750, 'lon': 13.2420},
        {'id': 504, 'name': 'Mabunda',      'population': 90000,  'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8680, 'lon': 13.2380},
        {'id': 505, 'name': 'Corimba',      'population': 120000, 'type': 'Residencial', 'risk': 'Muito Alto', 'lat': -8.8580, 'lon': 13.2300},
        {'id': 506, 'name': 'Bairro Azul',  'population': 100000, 'type': 'Residencial', 'risk': 'Médio',      'lat': -8.8720, 'lon': 13.2530},
        {'id': 507, 'name': 'Samba Pequena','population': 80000,  'type': 'Residencial', 'risk': 'Baixo',      'lat': -8.8800, 'lon': 13.2350},
        {'id': 508, 'name': 'Coreia',       'population': 95000,  'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8630, 'lon': 13.2450},
        {'id': 509, 'name': 'Cassenda',     'population': 110000, 'type': 'Residencial', 'risk': 'Médio',      'lat': -8.8760, 'lon': 13.2600},
    ],
    'Sambizanga': [
        {'id': 600, 'name': 'Bairro Operário',      'population': 150000, 'type': 'Residencial', 'risk': 'Muito Alto', 'lat': -8.7980, 'lon': 13.2480},
        {'id': 601, 'name': 'Ngola Kiluanje',        'population': 120000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8020, 'lon': 13.2520},
        {'id': 602, 'name': 'Miramar',               'population': 80000,  'type': 'Residencial', 'risk': 'Médio',      'lat': -8.7950, 'lon': 13.2420},
        {'id': 603, 'name': 'Comandante Valódia',    'population': 100000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8060, 'lon': 13.2560},
        {'id': 604, 'name': 'Lixeira',               'population': 90000,  'type': 'Residencial', 'risk': 'Muito Alto', 'lat': -8.8040, 'lon': 13.2500},
        {'id': 605, 'name': 'S. Pedro',              'population': 70000,  'type': 'Residencial', 'risk': 'Médio',      'lat': -8.8080, 'lon': 13.2440},
        {'id': 606, 'name': 'Petrangol',             'population': 110000, 'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8100, 'lon': 13.2580},
        {'id': 607, 'name': 'Boavista',              'population': 60000,  'type': 'Residencial', 'risk': 'Baixo',      'lat': -8.7920, 'lon': 13.2390},
        {'id': 608, 'name': 'EMCIB',                 'population': 85000,  'type': 'Residencial', 'risk': 'Médio',      'lat': -8.8000, 'lon': 13.2460},
        {'id': 609, 'name': 'Uíge',                  'population': 95000,  'type': 'Residencial', 'risk': 'Alto',       'lat': -8.8090, 'lon': 13.2610},
    ],
}

# ==================== FUNÇÕES AUXILIARES ====================
GADM_CACHE = {}
ELEVATION_CACHE = {}

def normalize_name(name):
    import unicodedata
    name = unicodedata.normalize('NFD', name)
    name = ''.join(char for char in name if unicodedata.category(char) != 'Mn')
    name = name.replace(' ', '').replace('-', '').replace('_', '').lower()
    return name

def get_bairros_by_municipality(municipality_name):
    """Retorna lista de bairros para um determinado município"""
    normalized_municipality = normalize_name(municipality_name)
    matching_key = next((k for k in BAIRROS if normalize_name(k) == normalized_municipality), None)
    
    if not matching_key:
        return []
    
    return list(BAIRROS[matching_key])

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
            logger.info(f"Elevações obtidas: {len(elevations)} pontos")
            return elevations
        else:
            logger.warning(f"Erro ao obter elevações: Status {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Erro ao obter elevações: {e}")
        return None

def get_point_elevation(lat, lon):
    """Obtém elevação de um único ponto (bairro) usando as coordenadas reais dele"""
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
    """Calcula estatísticas de elevação para uma região"""
    try:
        cache_key = f"{geometry.centroid.y:.4f},{geometry.centroid.x:.4f}"
        if cache_key in ELEVATION_CACHE:
            return ELEVATION_CACHE[cache_key]

        bounds = geometry.bounds
        centroid = geometry.centroid
        area = geometry.area

        if area > 1.0:
            num_points = 9
        elif area > 0.1:
            num_points = 5
        else:
            num_points = 3

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
        water_level = effective_water_level
        if water_level < 8.0 and avg_elevation > 100:
            severity = 'Leve'
            recovery_days = int(7 + water_level * 0.5)
        elif water_level < 15.0:
            severity = 'Moderada'
            recovery_days = int(15 + water_level * 1.0)
        elif water_level < 25.0:
            severity = 'Grave'
            recovery_days = int(30 + water_level * 1.5)
        else:
            severity = 'Crítica'
            recovery_days = int(60 + water_level * 2.0)

        if avg_elevation < 50:
            recovery_days = int(recovery_days * 1.5)

        return True, water_level, severity, recovery_days
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
        'version': '5.0.0',
        'status': 'online',
        'features': ['Dados GADM', 'Elevação Real por Ponto', 'Bairros com Coordenadas', 'Detalhamento Hierárquico'],
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
        'message': 'API activa — com suporte a detalhamento hierárquico',
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
        'version': '5.0.0',
        'description': 'API com detalhamento hierárquico: Província → Municípios → Bairros',
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

    if gdf is None:
        municipalities = [
            {'id': m['id'], 'name': m['name'], 'province': 'Luanda',
             'risk': m['risk'], 'population': m['population'], 'area': m['area'],
             'lat': -8.9, 'lon': 13.3}
            for m in static_muns
        ]
        return jsonify({'success': True, 'data': municipalities, 'count': len(municipalities)})

    gdf = gdf[gdf['NAME_1'] == 'Luanda']
    gadm_to_static = {
        'Belas': 'Belas', 'Cacuaco': 'Cacuaco', 'Cazenga': 'Cazenga',
        'Icolo e Bengo': 'Icolo e Bengo', 'Luanda': 'Luanda', 'Quiçama': 'Quiçama',
        'Viana': 'Viana', 'Kilamba-Kiaxi': 'Kilamba Kiaxi', 'Talatona': 'Talatona',
        'Maianga': 'Maianga', 'Rangel': 'Rangel', 'Ingombota': 'Ingombota',
        'Samba': 'Samba', 'Sambizanga': 'Sambizanga',
    }

    municipalities = []
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
                })

    if not any(m['name'] == 'Kilamba Kiaxi' for m in municipalities):
        municipalities.append({
            'id': 8, 'name': 'Kilamba Kiaxi', 'province': 'Luanda',
            'risk': 'Muito Alto', 'population': 1800000, 'area': 189,
            'lat': -8.92, 'lon': 13.28,
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

# ==================== SIMULAÇÃO PRINCIPAL ====================
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

        province = data.get('province', 'all')
        municipality = data.get('municipality', 'all')
        bairro_sel = data.get('bairro', 'all')

        logger.info(f"Simulação — level={level} province={province} municipality={municipality} bairro={bairro_sel}")

        # ============================================================
        # SIMULAÇÃO DE BAIRROS
        # ============================================================
        if level == 'bairro':
            if not municipality or municipality == 'all':
                return jsonify({'success': False,
                                'error': 'Seleccione um município específico para simular bairros'}), 400

            normalized_municipality = normalize_name(municipality)
            matching_key = next((k for k in BAIRROS if normalize_name(k) == normalized_municipality), None)

            if not matching_key:
                return jsonify({'success': False,
                                'error': f'Nenhum bairro cadastrado para o município {municipality}'}), 404

            bairros_list = list(BAIRROS[matching_key])

            if bairro_sel and bairro_sel != 'all':
                bairros_list = [b for b in bairros_list if b['name'] == bairro_sel]
                if not bairros_list:
                    return jsonify({'success': False,
                                    'error': f'Bairro "{bairro_sel}" não encontrado em {municipality}'}), 404
                logger.info(f"Simulando apenas o bairro: {bairro_sel}")
            else:
                logger.info(f"Simulando todos os {len(bairros_list)} bairros de {municipality}")

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

                logger.info(f"Bairro {bairro_name}: lat={b_lat} lon={b_lon} elev={avg_elevation:.1f}m")

                is_flooded, wl, severity, recovery_days = calculate_flood_risk(
                    risk, flood_rate, water_level_input, avg_elevation, elevation_stats
                )

                affected_population = 0
                if is_flooded:
                    impact_factor = min(wl / 20.0, 0.7)
                    affected_population = int(pop * impact_factor)

                result_data = {
                    'name': bairro_name,
                    'municipality': municipality,
                    'province': province if province != 'all' else 'Luanda',
                    'type': bairro_data.get('type', 'Residencial'),
                    'flooded': is_flooded,
                    'waterLevel': round(wl, 2),
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

                features.append({
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [b_lon, b_lat],
                    },
                    'properties': result_data,
                })

            flooded_count = sum(1 for r in results if r['flooded'])
            total_affected = sum(r['affectedPopulation'] for r in results)

            import json
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
                    'province': province,
                    'municipality': municipality,
                    'bairro': bairro_sel,
                    'elevation_used': True,
                },
                'timestamp': datetime.now().isoformat(),
            })

        # ============================================================
        # SIMULAÇÃO DE PROVÍNCIAS / MUNICÍPIOS COM DETALHAMENTO
        # ============================================================
        level_map = {'province': 1, 'municipality': 2}
        level_num = level_map.get(level)
        if level_num is None:
            return jsonify({'success': False, 'error': 'Nível inválido. Use: province, municipality ou bairro'}), 400

        gdf = download_and_read_gadm_json('AGO', level_num)
        if gdf is None:
            return jsonify({'success': False, 'error': 'Erro ao carregar dados do GADM'}), 500

        if province != 'all' and province != 'Luanda':
            return jsonify({'success': True, 'data': [], 'count': 0, 'message': 'Apenas Luanda disponível'})

        if province != 'all':
            gdf = gdf[gdf['NAME_1'] == province]
        if level == 'municipality' and municipality != 'all':
            gdf = gdf[gdf['NAME_2'] == municipality]

        gdf['name'] = gdf[f'NAME_{level_num}']
        gdf['flooded'] = False
        gdf['waterLevel'] = 0.0
        gdf['severity'] = 'Nenhuma'
        gdf['recoveryDays'] = 0
        gdf['affectedPopulation'] = 0
        gdf['elevation'] = 0.0

        results = []
        
        for i, row in gdf.iterrows():
            prov = row['NAME_1']
            name = row[f'NAME_{level_num}']
            elevation_stats = get_region_elevation_stats(row['geometry'])
            avg_elevation = elevation_stats['avg']

            if level == 'province':
                static = next((p for p in PROVINCES if p['name'] == name), None)
            else:
                static = next((m for m in MUNICIPALITIES.get(prov, []) if m['name'] == name), None)

            if not static:
                continue

            is_flooded, wl, severity, recovery_days = calculate_flood_risk(
                static['risk'], flood_rate, water_level_input, avg_elevation, elevation_stats
            )

            affected_population = 0
            if is_flooded:
                impact_factor = min(wl / 20.0, 0.5)
                affected_population = int(static['population'] * impact_factor)

            result_item = {
                'name': name,
                'province': prov,
                'flooded': is_flooded,
                'waterLevel': round(wl, 2),
                'severity': severity,
                'recoveryDays': recovery_days,
                'affectedPopulation': affected_population,
                'totalPopulation': static['population'],
                'risk': static['risk'],
                'elevation': round(avg_elevation, 1),
                'lat': row['geometry'].centroid.y,
                'lon': row['geometry'].centroid.x,
            }
            
            # ====================================================
            # DETALHAMENTO: Para Província, buscar Municípios
            # ====================================================
            if level == 'province':
                municipios_detalhes = []
                municipios_gdf = download_and_read_gadm_json('AGO', 2)
                
                if municipios_gdf is not None:
                    municipios_prov = municipios_gdf[municipios_gdf['NAME_1'] == name]
                    
                    for _, mun_row in municipios_prov.iterrows():
                        mun_name = mun_row['NAME_2']
                        static_mun = next((m for m in MUNICIPALITIES.get(name, []) if m['name'] == mun_name), None)
                        
                        if static_mun:
                            elevation_stats_mun = get_region_elevation_stats(mun_row['geometry'])
                            is_flooded_mun, wl_mun, severity_mun, days_mun = calculate_flood_risk(
                                static_mun['risk'], flood_rate, water_level_input,
                                elevation_stats_mun['avg'], elevation_stats_mun
                            )
                            
                            affected_pop_mun = 0
                            if is_flooded_mun:
                                impact_factor_mun = min(wl_mun / 20.0, 0.5)
                                affected_pop_mun = int(static_mun['population'] * impact_factor_mun)
                            
                            municipios_detalhes.append({
                                'name': mun_name,
                                'flooded': is_flooded_mun,
                                'waterLevel': round(wl_mun, 2),
                                'severity': severity_mun,
                                'recoveryDays': days_mun,
                                'affectedPopulation': affected_pop_mun,
                                'totalPopulation': static_mun['population'],
                                'risk': static_mun['risk'],
                                'elevation': round(elevation_stats_mun['avg'], 1)
                            })
                
                result_item['municipalities'] = municipios_detalhes
                result_item['municipalities_total'] = len(municipios_detalhes)
                result_item['municipalities_flooded'] = sum(1 for m in municipios_detalhes if m['flooded'])
            
            # ====================================================
            # DETALHAMENTO: Para Município, buscar Bairros
            # ====================================================
            elif level == 'municipality':
                bairros_detalhes = []
                bairros_list = get_bairros_by_municipality(name)
                
                for bairro_data in bairros_list:
                    bairro_name = bairro_data['name']
                    b_lat = bairro_data['lat']
                    b_lon = bairro_data['lon']
                    elevation_stats_bairro = get_point_elevation(b_lat, b_lon)
                    
                    is_flooded_b, wl_b, severity_b, days_b = calculate_flood_risk(
                        bairro_data['risk'], flood_rate, water_level_input,
                        elevation_stats_bairro['avg'], elevation_stats_bairro
                    )
                    
                    affected_pop_b = 0
                    if is_flooded_b:
                        impact_factor_b = min(wl_b / 20.0, 0.7)
                        affected_pop_b = int(bairro_data['population'] * impact_factor_b)
                    
                    bairros_detalhes.append({
                        'name': bairro_name,
                        'flooded': is_flooded_b,
                        'waterLevel': round(wl_b, 2),
                        'severity': severity_b,
                        'recoveryDays': days_b,
                        'affectedPopulation': affected_pop_b,
                        'totalPopulation': bairro_data['population'],
                        'risk': bairro_data['risk'],
                        'elevation': round(elevation_stats_bairro['avg'], 1),
                        'lat': b_lat,
                        'lon': b_lon
                    })
                
                result_item['bairros'] = bairros_detalhes
                result_item['bairros_total'] = len(bairros_detalhes)
                result_item['bairros_flooded'] = sum(1 for b in bairros_detalhes if b['flooded'])
            
            results.append(result_item)
            
            # Atualizar gdf para GeoJSON
            gdf.at[i, 'flooded'] = is_flooded
            gdf.at[i, 'waterLevel'] = wl
            gdf.at[i, 'severity'] = severity
            gdf.at[i, 'recoveryDays'] = recovery_days
            gdf.at[i, 'affectedPopulation'] = affected_population
            gdf.at[i, 'elevation'] = round(avg_elevation, 1)

        flooded_count = len([r for r in results if r['flooded']])
        total_affected = sum(r['affectedPopulation'] for r in results)
        geojson = gdf.to_json()

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
                'level': level,
                'floodRate': flood_rate * 100,
                'province': province,
                'municipality': municipality,
                'elevation_used': True,
            },
            'timestamp': datetime.now().isoformat(),
        })

    except Exception as e:
        logger.error(f"Erro na simulação: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Endpoint não encontrado'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("API de Simulação de Inundações — Angola v5.0")
    print("COM SUPORTE A DETALHAMENTO HIERÁRQUICO")
    print("=" * 70)
    print(f"Servidor : http://0.0.0.0:5000")
    print(f"Províncias: {len(PROVINCES)}")
    print(f"Municípios: {sum(len(m) for m in MUNICIPALITIES.values())}")
    print(f"Bairros   : {sum(len(b) for b in BAIRROS.values())} (com coordenadas reais)")
    print("=" * 70)
    print("\n🔹 NOVIDADE: Simulação hierárquica")
    print("   - Província → lista municípios afectados")
    print("   - Município → lista bairros inundados")
    print("=" * 70 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)