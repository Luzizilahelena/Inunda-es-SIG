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

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# ==================== DADOS ESTÁTICOS ====================
PROVINCES = [
    {'id': 1, 'name': 'Bengo', 'risk': 'Alto', 'population': 356641, 'area': 31371},
    {'id': 2, 'name': 'Benguela', 'risk': 'Alto', 'population': 2231385, 'area': 31788},
    {'id': 3, 'name': 'Bié', 'risk': 'Médio', 'population': 1455255, 'area': 70314},
    {'id': 4, 'name': 'Cabinda', 'risk': 'Alto', 'population': 716076, 'area': 7270},
    {'id': 5, 'name': 'Cuando Cubango', 'risk': 'Baixo', 'population': 534002, 'area': 199049},
    {'id': 6, 'name': 'Cuanza Norte', 'risk': 'Alto', 'population': 443386, 'area': 24110},
    {'id': 7, 'name': 'Cuanza Sul', 'risk': 'Médio', 'population': 1881873, 'area': 55660},
    {'id': 8, 'name': 'Cunene', 'risk': 'Médio', 'population': 990087, 'area': 78342},
    {'id': 9, 'name': 'Huambo', 'risk': 'Alto', 'population': 2019555, 'area': 34270},
    {'id': 10, 'name': 'Huíla', 'risk': 'Alto', 'population': 2497422, 'area': 79023},
    {'id': 11, 'name': 'Luanda', 'risk': 'Muito Alto', 'population': 8329517, 'area': 2417},
    {'id': 12, 'name': 'Lunda Norte', 'risk': 'Médio', 'population': 862566, 'area': 103000},
    {'id': 13, 'name': 'Lunda Sul', 'risk': 'Médio', 'population': 537587, 'area': 77637},
    {'id': 14, 'name': 'Malanje', 'risk': 'Alto', 'population': 1108404, 'area': 97602},
    {'id': 15, 'name': 'Moxico', 'risk': 'Baixo', 'population': 758568, 'area': 223023},
    {'id': 16, 'name': 'Namibe', 'risk': 'Médio', 'population': 495326, 'area': 58137},
    {'id': 17, 'name': 'Uíge', 'risk': 'Alto', 'population': 1483118, 'area': 58698},
    {'id': 18, 'name': 'Zaire', 'risk': 'Médio', 'population': 594428, 'area': 40130}
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
        {'id': 9, 'name': 'Talatona', 'population': 500000, 'area': 160, 'risk': 'Médio'}
    ],
    'Benguela': [
        {'id': 10, 'name': 'Balombo', 'population': 35000, 'area': 3000, 'risk': 'Baixo'},
        {'id': 11, 'name': 'Benguela', 'population': 555000, 'area': 2800, 'risk': 'Alto'},
        {'id': 12, 'name': 'Bocoio', 'population': 120000, 'area': 4500, 'risk': 'Médio'},
        {'id': 13, 'name': 'Caimbambo', 'population': 95000, 'area': 2100, 'risk': 'Médio'},
        {'id': 14, 'name': 'Catumbela', 'population': 300000, 'area': 3600, 'risk': 'Alto'},
        {'id': 15, 'name': 'Lobito', 'population': 450000, 'area': 3600, 'risk': 'Alto'},
        {'id': 16, 'name': 'Chongoroi', 'population': 80000, 'area': 2200, 'risk': 'Médio'},
        {'id': 17, 'name': 'Ganda', 'population': 180000, 'area': 4900, 'risk': 'Baixo'}
    ],
    'Huambo': [
        {'id': 18, 'name': 'Bailundo', 'population': 400000, 'area': 5000, 'risk': 'Médio'},
        {'id': 19, 'name': 'Cachiungo', 'population': 75000, 'area': 3200, 'risk': 'Baixo'},
        {'id': 20, 'name': 'Caála', 'population': 180000, 'area': 3400, 'risk': 'Médio'},
        {'id': 21, 'name': 'Huambo', 'population': 650000, 'area': 4200, 'risk': 'Alto'},
        {'id': 22, 'name': 'Londuimbali', 'population': 85000, 'area': 2800, 'risk': 'Baixo'},
        {'id': 23, 'name': 'Longonjo', 'population': 120000, 'area': 4100, 'risk': 'Médio'},
        {'id': 24, 'name': 'Chicala-Choloanga', 'population': 95000, 'area': 2600, 'risk': 'Baixo'}
    ],
    'Huíla': [
        {'id': 25, 'name': 'Lubango', 'population': 914000, 'area': 3700, 'risk': 'Alto'},
        {'id': 26, 'name': 'Caconda', 'population': 150000, 'area': 9700, 'risk': 'Médio'},
        {'id': 27, 'name': 'Chibia', 'population': 180000, 'area': 7900, 'risk': 'Baixo'},
        {'id': 28, 'name': 'Matala', 'population': 160000, 'area': 3700, 'risk': 'Médio'}
    ],
    'Bié': [
        {'id': 29, 'name': 'Kuito', 'population': 355000, 'area': 7700, 'risk': 'Alto'},
        {'id': 30, 'name': 'Andulo', 'population': 120000, 'area': 10100, 'risk': 'Médio'},
        {'id': 31, 'name': 'Camacupa', 'population': 95000, 'area': 11400, 'risk': 'Baixo'}
    ],
    'Malanje': [
        {'id': 32, 'name': 'Malanje', 'population': 455000, 'area': 4800, 'risk': 'Alto'},
        {'id': 33, 'name': 'Cacuso', 'population': 95000, 'area': 7900, 'risk': 'Médio'},
        {'id': 34, 'name': 'Calandula', 'population': 80000, 'area': 5700, 'risk': 'Baixo'}
    ],
    'Uíge': [
        {'id': 35, 'name': 'Uíge', 'population': 519000, 'area': 5200, 'risk': 'Alto'},
        {'id': 36, 'name': 'Negage', 'population': 150000, 'area': 5500, 'risk': 'Médio'},
        {'id': 37, 'name': 'Puri', 'population': 85000, 'area': 4200, 'risk': 'Baixo'}
    ],
    'Cabinda': [
        {'id': 38, 'name': 'Cabinda', 'population': 300000, 'area': 1200, 'risk': 'Alto'},
        {'id': 39, 'name': 'Belize', 'population': 85000, 'area': 1700, 'risk': 'Médio'},
        {'id': 40, 'name': 'Cacongo', 'population': 95000, 'area': 1700, 'risk': 'Médio'}
    ]
}

# BAIRROS organizados por MUNICÍPIO
BAIRROS = {
    'Kilamba Kiaxi': [
        {'id': 19, 'name': 'Golfe', 'population': 300000, 'type': 'Residencial', 'risk': 'Alto'},
        {'id': 20, 'name': 'Palanca', 'population': 280000, 'type': 'Residencial', 'risk': 'Alto'},
        {'id': 21, 'name': 'Kilamba', 'population': 450000, 'type': 'Residencial', 'risk': 'Médio'},
        {'id': 22, 'name': 'Camama', 'population': 320000, 'type': 'Residencial', 'risk': 'Alto'},
        {'id': 100, 'name': 'Sapu', 'population': 150000, 'type': 'Residencial', 'risk': 'Alto'}
    ],
    'Cazenga': [
        {'id': 23, 'name': 'Hoji-ya-Henda', 'population': 220000, 'type': 'Residencial', 'risk': 'Muito Alto'},
        {'id': 24, 'name': 'Tala Hady', 'population': 180000, 'type': 'Residencial', 'risk': 'Alto'},
        {'id': 25, 'name': 'Cazenga Sede', 'population': 250000, 'type': 'Residencial', 'risk': 'Muito Alto'},
        {'id': 26, 'name': 'Sapu', 'population': 150000, 'type': 'Residencial', 'risk': 'Alto'}
    ],
    'Luanda': [
        {'id': 1, 'name': 'Ingombota', 'population': 150000, 'type': 'Comercial', 'risk': 'Médio'},
        {'id': 2, 'name': 'Maianga', 'population': 180000, 'type': 'Residencial', 'risk': 'Alto'},
        {'id': 3, 'name': 'Rangel', 'population': 220000, 'type': 'Residencial', 'risk': 'Alto'},
        {'id': 4, 'name': 'Sambizanga', 'population': 280000, 'type': 'Residencial', 'risk': 'Muito Alto'},
        {'id': 5, 'name': 'Ilha de Luanda', 'population': 45000, 'type': 'Turístico', 'risk': 'Muito Alto'},
        {'id': 6, 'name': 'Maculusso', 'population': 90000, 'type': 'Residencial', 'risk': 'Baixo'},
        {'id': 7, 'name': 'Alvalade', 'population': 120000, 'type': 'Residencial', 'risk': 'Médio'},
        {'id': 8, 'name': 'Mutamba', 'population': 80000, 'type': 'Comercial', 'risk': 'Alto'}
    ],
    'Cacuaco': [
        {'id': 9, 'name': 'Kikolo', 'population': 180000, 'type': 'Residencial', 'risk': 'Muito Alto'},
        {'id': 10, 'name': 'Sequele', 'population': 140000, 'type': 'Residencial', 'risk': 'Alto'},
        {'id': 11, 'name': 'Funda', 'population': 160000, 'type': 'Residencial', 'risk': 'Alto'},
        {'id': 12, 'name': 'Quiage', 'population': 95000, 'type': 'Residencial', 'risk': 'Médio'},
        {'id': 13, 'name': 'Cabolombo', 'population': 110000, 'type': 'Residencial', 'risk': 'Alto'}
    ],
    'Viana': [
        {'id': 14, 'name': 'Viana Sede', 'population': 250000, 'type': 'Residencial', 'risk': 'Alto'},
        {'id': 15, 'name': 'Calumbo', 'population': 180000, 'type': 'Residencial', 'risk': 'Médio'},
        {'id': 16, 'name': 'Catete', 'population': 120000, 'type': 'Residencial', 'risk': 'Médio'},
        {'id': 17, 'name': 'Kikuxi', 'population': 200000, 'type': 'Industrial', 'risk': 'Alto'},
        {'id': 18, 'name': 'Zango', 'population': 350000, 'type': 'Residencial', 'risk': 'Muito Alto'}
    ],
    'Belas': [
        {'id': 27, 'name': 'Belas Sede', 'population': 180000, 'type': 'Residencial', 'risk': 'Médio'},
        {'id': 28, 'name': 'Benfica', 'population': 140000, 'type': 'Residencial', 'risk': 'Alto'},
        {'id': 29, 'name': 'Ramiros', 'population': 95000, 'type': 'Residencial', 'risk': 'Baixo'}
    ],
    'Benguela': [
        {'id': 30, 'name': 'Centro', 'population': 85000, 'type': 'Comercial', 'risk': 'Médio'},
        {'id': 31, 'name': 'Compão', 'population': 70000, 'type': 'Residencial', 'risk': 'Alto'},
        {'id': 32, 'name': 'Calombotão', 'population': 55000, 'type': 'Residencial', 'risk': 'Alto'},
        {'id': 33, 'name': 'Praia Morena', 'population': 40000, 'type': 'Residencial', 'risk': 'Muito Alto'}
    ],
    'Lobito': [
        {'id': 34, 'name': 'Canata', 'population': 90000, 'type': 'Residencial', 'risk': 'Alto'},
        {'id': 35, 'name': 'Caponte', 'population': 75000, 'type': 'Residencial', 'risk': 'Médio'},
        {'id': 36, 'name': 'Compão', 'population': 60000, 'type': 'Residencial', 'risk': 'Alto'},
        {'id': 37, 'name': 'Restinga', 'population': 50000, 'type': 'Portuário', 'risk': 'Muito Alto'}
    ],
    'Huambo': [
        {'id': 38, 'name': 'Centro', 'population': 180000, 'type': 'Comercial', 'risk': 'Alto'},
        {'id': 39, 'name': 'Benfica', 'population': 120000, 'type': 'Residencial', 'risk': 'Médio'},
        {'id': 40, 'name': 'Comala', 'population': 95000, 'type': 'Residencial', 'risk': 'Baixo'}
    ],
    'Lubango': [
        {'id': 41, 'name': 'Centro', 'population': 210000, 'type': 'Comercial', 'risk': 'Alto'},
        {'id': 42, 'name': 'Comandante Cowboy', 'population': 180000, 'type': 'Residencial', 'risk': 'Médio'},
        {'id': 43, 'name': 'Lumumba', 'population': 150000, 'type': 'Residencial', 'risk': 'Alto'}
    ]
}

# ==================== CACHES ====================
GADM_CACHE = {}
ELEVATION_CACHE = {}

# ==================== FUNÇÕES DE ELEVAÇÃO ====================
def get_elevation_batch(coordinates):
    """Obtém elevação de múltiplos pontos"""
    try:
        if len(coordinates) > 100:
            coordinates = coordinates[:100]
        
        locations = '|'.join([f"{lat},{lon}" for lat, lon in coordinates])
        url = f"https://api.open-elevation.com/api/v1/lookup?locations={locations}"
        
        logger.info(f"🗻 Buscando elevação para {len(coordinates)} pontos...")
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            elevations = [result['elevation'] for result in data['results']]
            logger.info(f"✅ Elevações obtidas: {len(elevations)} pontos")
            return elevations
        else:
            logger.warning(f"⚠️ Erro ao obter elevações: Status {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"❌ Erro ao obter elevações: {e}")
        return None

def get_region_elevation_stats(geometry):
    """Calcula estatísticas de elevação para uma região"""
    try:
        cache_key = f"{geometry.centroid.y:.4f},{geometry.centroid.x:.4f}"
        if cache_key in ELEVATION_CACHE:
            logger.info(f"📦 Usando elevação do cache")
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
                elevation_range = max_elev - min_elev
                
                result = {
                    'avg': float(avg),
                    'min': float(min_elev),
                    'max': float(max_elev),
                    'range': float(elevation_range),
                    'points_sampled': len(valid_elevations)
                }
                
                ELEVATION_CACHE[cache_key] = result
                
                logger.info(f"🗻 Elevação - Média: {avg:.1f}m, Min: {min_elev:.1f}m, Max: {max_elev:.1f}m")
                return result
        
        logger.warning(f"⚠️ Usando elevação estimada (fallback)")
        result = {
            'avg': 400.0,
            'min': 200.0,
            'max': 600.0,
            'range': 400.0,
            'points_sampled': 0
        }
        ELEVATION_CACHE[cache_key] = result
        return result
        
    except Exception as e:
        logger.error(f"❌ Erro ao calcular elevação: {e}")
        return {
            'avg': 400.0,
            'min': 200.0,
            'max': 600.0,
            'range': 400.0,
            'points_sampled': 0
        }

# ==================== GADM ====================
def download_and_read_gadm_json(country_code, level):
    cache_key = f"{country_code}_{level}"
    
    if cache_key in GADM_CACHE:
        logger.info(f"📦 Usando dados GADM do cache: Level {level}")
        return GADM_CACHE[cache_key]
    
    json_url = f'https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_{country_code}_{level}.json.zip'
    logger.info(f"⬇️ Baixando GeoJSON: {json_url}...")
    
    try:
        response = requests.get(json_url, timeout=60)
        response.raise_for_status()
        
        with ZipFile(BytesIO(response.content)) as zip_file:
            json_filename = zip_file.namelist()[0]
            with zip_file.open(json_filename) as json_file:
                gdf = gpd.read_file(json_file, driver='GeoJSON')
        
        GADM_CACHE[cache_key] = gdf
        logger.info(f"✅ Dados GADM Level {level} armazenados em cache ({len(gdf)} features)")
        return gdf
        
    except Exception as e:
        logger.error(f"❌ Erro ao baixar/processar GeoJSON: {e}")
        return None

def normalize_name(name):
    """Normaliza nomes para comparação"""
    import unicodedata
    name = unicodedata.normalize('NFD', name)
    name = ''.join(char for char in name if unicodedata.category(char) != 'Mn')
    name = name.replace(' ', '').replace('-', '').replace('_', '').lower()
    return name

# ==================== CÁLCULO ====================
def calculate_flood_risk(risk_level, flood_rate, water_level_input, area_elevation=0, elevation_stats=None):
    """Calcula inundação considerando elevação"""
    risk_factors = {
        'Muito Alto': 0.35,
        'Alto': 0.20,
        'Médio': 0.05,
        'Baixo': -0.10
    }
    
    drainage_factor = {
        'Muito Alto': 0.9,
        'Alto': 0.7,
        'Médio': 0.5,
        'Baixo': 0.3
    }
    
    risk_modifier = risk_factors.get(risk_level, 0)
    drainage = drainage_factor.get(risk_level, 0.5)
    
    if elevation_stats:
        avg_elevation = elevation_stats.get('avg', area_elevation)
        elevation_range = elevation_stats.get('range', 0)
        min_elevation = elevation_stats.get('min', area_elevation)
    else:
        avg_elevation = area_elevation
        elevation_range = 0
        min_elevation = area_elevation
    
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
        'message': 'API de Simulação de Inundações - Angola (Com Bairros)',
        'version': '3.1.0',
        'status': 'online',
        'features': ['Dados GADM', 'Elevação Real', 'Sistema de Bairros Corrigido'],
        'endpoints': {
            'health': '/api/health',
            'info': '/api/info',
            'provinces': '/api/provinces',
            'municipalities': '/api/municipalities?province=X',
            'bairros': '/api/bairros?municipality=X',
            'simulate': '/api/simulate (POST)',
            'elevation': '/api/elevation?lat=X&lon=Y'
        }
    })

@app.route('/api/health', methods=['GET'])
def health():
    logger.info("Health check realizado")
    return jsonify({
        'status': 'ok',
        'message': 'API está ativa com suporte a bairros',
        'timestamp': datetime.now().isoformat(),
        'cache_status': {
            'gadm_cached': len(GADM_CACHE),
            'elevation_cached': len(ELEVATION_CACHE)
        }
    })

@app.route('/api/info', methods=['GET'])
def api_info():
    return jsonify({
        'name': 'API de Simulação de Inundações - Angola',
        'version': '3.1.0',
        'description': 'API completa com análise de elevação e sistema de bairros',
        'author': 'Sistema de Gestão de Desastres Naturais',
        'data_available': {
            'provinces': len(PROVINCES),
            'municipalities': sum(len(m) for m in MUNICIPALITIES.values()),
            'bairros': sum(len(b) for b in BAIRROS.values())
        },
        'elevation_service': 'Open-Elevation API (SRTM 90m)'
    })

@app.route('/api/provinces', methods=['GET'])
def get_provinces():
    logger.info("Listando províncias")
    gdf = download_and_read_gadm_json('AGO', 1)
    
    if gdf is None:
        return jsonify({'success': False, 'error': 'Erro ao carregar dados do GADM'}), 500
    
    provinces = []
    for index, row in gdf.iterrows():
        name = row['NAME_1']
        static = next((p for p in PROVINCES if p['name'] == name), None)
        
        pop = static['population'] if static else 0
        area = static['area'] if static else 0
        risk = static['risk'] if static else 'Médio'
        id_ = static['id'] if static else index + 1
        
        centroid = row['geometry'].centroid
        
        provinces.append({
            'id': id_,
            'name': name,
            'risk': risk,
            'population': pop,
            'area': area,
            'lat': centroid.y,
            'lon': centroid.x
        })
    
    return jsonify({
        'success': True,
        'data': provinces,
        'count': len(provinces),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/municipalities', methods=['GET'])
def get_municipalities():
    province = request.args.get('province', None)
    logger.info(f"Listando municípios - Província: {province}")
    
    gdf = download_and_read_gadm_json('AGO', 2)
    if gdf is None:
        return jsonify({'success': False, 'error': 'Erro ao carregar dados do GADM'}), 500
    
    if province and province != 'all':
        gdf = gdf[gdf['NAME_1'] == province]
    
    municipalities = []
    for index, row in gdf.iterrows():
        prov = row['NAME_1']
        name = row['NAME_2']
        
        static_mun = next((m for m in MUNICIPALITIES.get(prov, []) if m['name'] == name), None)
        
        if static_mun:
            pop = static_mun['population']
            area = static_mun['area']
            risk = static_mun['risk']
            id_ = static_mun['id']
        else:
            static_prov = next((p for p in PROVINCES if p['name'] == prov), None)
            risk = static_prov['risk'] if static_prov else 'Médio'
            pop = 0
            area = 0
            id_ = index + 1
        
        centroid = row['geometry'].centroid
        
        municipalities.append({
            'id': id_,
            'name': name,
            'province': prov,
            'risk': risk,
            'population': pop,
            'area': area,
            'lat': centroid.y,
            'lon': centroid.x
        })
    
    return jsonify({
        'success': True,
        'data': municipalities,
        'count': len(municipalities),
        'filter': {'province': province} if province else None,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/bairros', methods=['GET'])
def get_bairros():
    """ENDPOINT NOVO: Lista bairros de um município específico"""
    municipality = request.args.get('municipality', None)
    province = request.args.get('province', None)
    
    logger.info(f"🏘️ Listando BAIRROS - Município: {municipality}, Província: {province}")
    
    if not municipality or municipality == 'all':
        # Retornar todos os bairros
        all_bairros = []
        for munic_name, bairros_list in BAIRROS.items():
            for bairro in bairros_list:
                bairro_data = {**bairro, 'municipality': munic_name}
                all_bairros.append(bairro_data)
        
        return jsonify({
            'success': True,
            'data': all_bairros,
            'count': len(all_bairros),
            'timestamp': datetime.now().isoformat()
        })
    
    # Buscar bairros do município específico
    bairros_list = BAIRROS.get(municipality, [])
    
    if not bairros_list:
        logger.warning(f"⚠️ Nenhum bairro encontrado para município: {municipality}")
        return jsonify({
            'success': True,
            'data': [],
            'count': 0,
            'message': f'Nenhum bairro cadastrado para o município {municipality}',
            'timestamp': datetime.now().isoformat()
        })
    
    # Adicionar informação do município a cada bairro
    bairros_with_municipality = []
    for bairro in bairros_list:
        bairro_data = {**bairro, 'municipality': municipality}
        if province:
            bairro_data['province'] = province
        bairros_with_municipality.append(bairro_data)
    
    logger.info(f"✅ Encontrados {len(bairros_with_municipality)} bairros em {municipality}")
    
    return jsonify({
        'success': True,
        'data': bairros_with_municipality,
        'count': len(bairros_with_municipality),
        'filter': {
            'municipality': municipality,
            'province': province
        },
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/elevation', methods=['GET'])
def get_elevation():
    """Endpoint para testar elevação"""
    try:
        lat = float(request.args.get('lat'))
        lon = float(request.args.get('lon'))
        
        elevations = get_elevation_batch([(lat, lon)])
        
        if elevations and len(elevations) > 0:
            return jsonify({
                'success': True,
                'latitude': lat,
                'longitude': lon,
                'elevation': elevations[0],
                'unit': 'meters'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Não foi possível obter elevação'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/simulate', methods=['POST'])
def simulate_flood():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400
        
        level = data.get('level', 'province')
        flood_rate = float(data.get('floodRate', 50)) / 100
        water_level = data.get('waterLevel')
        
        if water_level is not None:
            water_level_input = float(data.get('waterLevel', 50))
        else:
            water_level_input = None
        
        province = data.get('province', 'all')
        municipality = data.get('municipality', 'all')
        bairro = data.get('bairro', 'all')
        
        logger.info(f"🌊 Simulação - Level: {level}, Province: {province}, Municipality: {municipality}, Bairro: {bairro}")
        
        # ========== SIMULAÇÃO DE BAIRROS ==========
        if level == 'bairro':
            logger.info(f"🏘️ SIMULAÇÃO DE BAIRROS INICIADA")
            
            if municipality == 'all' or not municipality:
                return jsonify({
                    'success': False,
                    'error': 'Para simular bairros, você deve selecionar um município específico'
                }), 400
            
            # Buscar bairros do município
            bairros_list = BAIRROS.get(municipality, [])
            
            if not bairros_list:
                return jsonify({
                    'success': False,
                    'error': f'Nenhum bairro cadastrado para o município {municipality}'
                }), 404
            
            # Filtrar bairro específico se foi selecionado
            if bairro and bairro != 'all':
                bairros_list = [b for b in bairros_list if b['name'] == bairro]
                if not bairros_list:
                    return jsonify({
                        'success': False,
                        'error': f'Bairro {bairro} não encontrado em {municipality}'
                    }), 404
            
            logger.info(f"✅ Processando {len(bairros_list)} bairros de {municipality}")
            
            # Buscar geometria do município para usar como referência
            gdf_level2 = download_and_read_gadm_json('AGO', 2)
            gdf_level3 = download_and_read_gadm_json('AGO', 3)
            
            results = []
            features = []
            
            for bairro_data in bairros_list:
                risk = bairro_data['risk']
                pop = bairro_data['population']
                bairro_name = bairro_data['name']
                
                logger.info(f"🏘️ Processando bairro: {bairro_name}")
                
                # Buscar geometria no GADM Level 3 (comunas)
                found_geom = None
                elevation_stats = None
                
                if gdf_level3 is not None:
                    municipality_normalized = normalize_name(municipality)
                    bairro_normalized = normalize_name(bairro_name)
                    
                    # Filtrar por município
                    gdf_filtered = gdf_level3[gdf_level3['NAME_2'].apply(normalize_name) == municipality_normalized]
                    
                    # Buscar bairro específico
                    for idx, row in gdf_filtered.iterrows():
                        commune_normalized = normalize_name(row['NAME_3'])
                        
                        if commune_normalized == bairro_normalized or bairro_normalized in commune_normalized:
                            found_geom = row['geometry']
                            elevation_stats = get_region_elevation_stats(found_geom)
                            logger.info(f"✅ Geometria encontrada para {bairro_name} - Elevação: {elevation_stats['avg']:.1f}m")
                            break
                
                # Se não encontrou no Level 3, usar geometria do município
                if found_geom is None and gdf_level2 is not None:
                    logger.warning(f"⚠️ Geometria específica não encontrada para {bairro_name}, usando município")
                    municipality_normalized = normalize_name(municipality)
                    
                    for idx, row in gdf_level2.iterrows():
                        if normalize_name(row['NAME_2']) == municipality_normalized:
                            found_geom = row['geometry']
                            elevation_stats = get_region_elevation_stats(found_geom)
                            logger.info(f"📍 Usando geometria do município - Elevação: {elevation_stats['avg']:.1f}m")
                            break
                
                # Calcular inundação com elevação
                avg_elevation = elevation_stats['avg'] if elevation_stats else 400.0
                
                is_flooded, water_level_calc, severity, recovery_days = calculate_flood_risk(
                    risk, 
                    flood_rate, 
                    water_level_input, 
                    avg_elevation, 
                    elevation_stats
                )
                
                affected_population = 0
                if is_flooded:
                    impact_factor = min(water_level_calc / 20.0, 0.7)
                    affected_population = int(pop * impact_factor)
                
                result_data = {
                    'name': bairro_name,
                    'municipality': municipality,
                    'province': province if province != 'all' else 'Luanda',
                    'type': bairro_data.get('type', 'Residencial'),
                    'flooded': is_flooded,
                    'waterLevel': water_level_calc,
                    'severity': severity,
                    'recoveryDays': recovery_days,
                    'affectedPopulation': affected_population,
                    'totalPopulation': pop,
                    'risk': risk,
                    'elevation': round(avg_elevation, 1) if elevation_stats else None,
                    'elevation_min': round(elevation_stats['min'], 1) if elevation_stats else None,
                    'elevation_max': round(elevation_stats['max'], 1) if elevation_stats else None
                }
                
                results.append(result_data)
                
                # Criar feature GeoJSON
                if found_geom is not None:
                    import json
                    geom_json = json.loads(gpd.GeoSeries([found_geom]).to_json())['features'][0]['geometry']
                    
                    features.append({
                        'type': 'Feature',
                        'geometry': geom_json,
                        'properties': result_data
                    })
                else:
                    # Fallback: usar ponto central do município
                    fallback_coords = [13.2437, -8.8383]
                    
                    features.append({
                        'type': 'Feature',
                        'geometry': {
                            'type': 'Point',
                            'coordinates': fallback_coords
                        },
                        'properties': result_data
                    })
            
            flooded_count = sum(1 for r in results if r['flooded'])
            total_affected = sum(r['affectedPopulation'] for r in results)
            
            geojson_data = {
                'type': 'FeatureCollection',
                'features': features
            }
            
            import json
            geojson = json.dumps(geojson_data)
            
            response = {
                'success': True,
                'data': results,
                'geojson': geojson,
                'statistics': {
                    'floodedCount': flooded_count,
                    'totalAffected': total_affected,
                    'totalBairros': len(results),
                    'avgRisk': (flooded_count / len(results) * 100) if results else 0
                },
                'parameters': {
                    'level': 'bairro',
                    'floodRate': flood_rate * 100,
                    'province': province,
                    'municipality': municipality,
                    'bairro': bairro,
                    'elevation_used': True
                },
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Simulação de bairros concluída - {flooded_count} de {len(results)} bairros inundados")
            return jsonify(response)
        
        # ========== SIMULAÇÃO DE PROVÍNCIAS E MUNICÍPIOS ==========
        level_map = {'province': 1, 'municipality': 2}
        level_num = level_map.get(level)
        
        if level_num is None:
            return jsonify({'success': False, 'error': 'Nível inválido. Use: province, municipality ou bairro'}), 400
        
        gdf = download_and_read_gadm_json('AGO', level_num)
        if gdf is None:
            return jsonify({'success': False, 'error': 'Erro ao carregar dados do GADM'}), 500
        
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
        
        logger.info(f"🔄 Processando {len(gdf)} regiões...")
        
        for i, row in gdf.iterrows():
            prov = row['NAME_1']
            name = row[f'NAME_{level_num}']
            geometry = row['geometry']
            
            elevation_stats = get_region_elevation_stats(geometry)
            avg_elevation = elevation_stats['avg']
            
            if level == 'province':
                static = next((p for p in PROVINCES if p['name'] == name), None)
            else:
                static = next((m for m in MUNICIPALITIES.get(prov, []) if m['name'] == name), None)
            
            if static:
                risk = static['risk']
                pop = static['population']
            else:
                static_prov = next((p for p in PROVINCES if p['name'] == prov), None)
                risk = static_prov['risk'] if static_prov else 'Médio'
                pop = 0
            
            is_flooded, water_level_calc, severity, recovery_days = calculate_flood_risk(
                risk, 
                flood_rate, 
                water_level_input, 
                avg_elevation, 
                elevation_stats
            )
            
            affected_population = 0
            if is_flooded:
                impact_factor = min(water_level_calc / 20.0, 0.5)
                affected_population = int(pop * impact_factor)
            
            gdf.at[i, 'flooded'] = is_flooded
            gdf.at[i, 'waterLevel'] = water_level_calc
            gdf.at[i, 'severity'] = severity
            gdf.at[i, 'recoveryDays'] = recovery_days
            gdf.at[i, 'affectedPopulation'] = affected_population
            gdf.at[i, 'elevation'] = round(avg_elevation, 1)
        
        gdf_copy = gdf.copy()
        gdf_copy['lat'] = gdf.geometry.centroid.y
        gdf_copy['lon'] = gdf.geometry.centroid.x
        results = gdf_copy.drop(columns=['geometry']).to_dict('records')
        
        geojson = gdf.to_json()
        
        flooded_count = len(gdf[gdf['flooded']])
        total_affected = sum(item['affectedPopulation'] for item in results)
        
        response = {
            'success': True,
            'data': results,
            'geojson': geojson,
            'statistics': {
                'floodedCount': flooded_count,
                'totalAffected': total_affected,
                'totalItems': len(results),
                'avgRisk': (flooded_count / len(results) * 100) if results else 0
            },
            'parameters': {
                'level': level,
                'floodRate': flood_rate * 100,
                'province': province,
                'municipality': municipality,
                'elevation_used': True
            },
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"✅ Simulação concluída - {flooded_count} de {len(results)} áreas inundadas")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"❌ Erro na simulação: {str(e)}")
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
    print("\n" + "="*70)
    print("🌊 API de Simulação de Inundações - Angola v3.1")
    print("🏘️ COM SISTEMA DE BAIRROS CORRIGIDO")
    print("="*70)
    print(f"📡 Servidor: http://0.0.0.0:5000")
    print(f"📚 Docs: http://localhost:5000/api/info")
    print(f"💚 Status: http://localhost:5000/api/health")
    print(f"🏘️ Bairros: http://localhost:5000/api/bairros?municipality=Kilamba%20Kiaxi")
    print(f"📊 Províncias: {len(PROVINCES)}")
    print(f"🏛️ Municípios: {sum(len(m) for m in MUNICIPALITIES.values())}")
    print(f"🏘️ Bairros: {sum(len(b) for b in BAIRROS.values())}")
    print("="*70 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
