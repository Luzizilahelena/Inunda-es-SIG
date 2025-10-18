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

# ==================== DADOS ESTÁTICOS COMO FALLBACK ====================

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

DISTRICTS = {
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
    'Kilamba Kiaxi': [
        {'id': 19, 'name': 'Golfe', 'population': 300000, 'type': 'Residencial', 'risk': 'Alto'},
        {'id': 20, 'name': 'Palanca', 'population': 280000, 'type': 'Residencial', 'risk': 'Alto'},
        {'id': 21, 'name': 'Kilamba', 'population': 450000, 'type': 'Residencial', 'risk': 'Médio'},
        {'id': 22, 'name': 'Camama', 'population': 320000, 'type': 'Residencial', 'risk': 'Alto'}
    ],
    'Cazenga': [
        {'id': 23, 'name': 'Hoji-ya-Henda', 'population': 220000, 'type': 'Residencial', 'risk': 'Muito Alto'},
        {'id': 24, 'name': 'Tala Hady', 'population': 180000, 'type': 'Residencial', 'risk': 'Alto'},
        {'id': 25, 'name': 'Cazenga Sede', 'population': 250000, 'type': 'Residencial', 'risk': 'Muito Alto'},
        {'id': 26, 'name': 'Sapu', 'population': 150000, 'type': 'Residencial', 'risk': 'Alto'}
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

MUNICIPALITY_NAME_MAPPING = {
    'Caimbambo': 'Caiambambo',
    'Catumbela': 'Catumbela',
}

# ==================== FUNÇÕES DE ELEVAÇÃO ====================

def get_elevation_batch(coordinates):
    """
    Obtém elevação de múltiplos pontos usando Open-Elevation API
    coordinates: lista de tuplas [(lat, lon), ...]
    Retorna: lista de elevações em metros
    """
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
    """
    Calcula estatísticas de elevação para uma região
    Retorna: {'avg': média, 'min': mínima, 'max': máxima, 'range': variação}
    """
    try:
        # Verificar cache
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
                
                # Salvar no cache
                ELEVATION_CACHE[cache_key] = result
                
                logger.info(f"🗻 Elevação - Média: {avg:.1f}m, Min: {min_elev:.1f}m, Max: {max_elev:.1f}m, Variação: {elevation_range:.1f}m")
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

# ==================== FUNÇÃO PARA BAIXAR E LER GADM ====================

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

def find_commune_in_gadm(district_name, municipality_name, gdf):
    """Encontra a comuna correspondente no GeoDataFrame do GADM"""
    district_normalized = normalize_name(district_name)
    municipality_normalized = normalize_name(municipality_name)
    
    municipality_data = gdf[gdf['NAME_2'].apply(normalize_name) == municipality_normalized]
    
    if len(municipality_data) == 0:
        logger.warning(f"Município '{municipality_name}' não encontrado no GADM")
        return None
    
    for idx, row in municipality_data.iterrows():
        commune_normalized = normalize_name(row['NAME_3'])
        
        if commune_normalized == district_normalized:
            return row
        
        if district_normalized in commune_normalized or commune_normalized in district_normalized:
            return row
    
    logger.warning(f"Distrito '{district_name}' não encontrado exatamente em '{municipality_name}'")
    return municipality_data.iloc[0] if len(municipality_data) > 0 else None

# ==================== FUNÇÃO DE CÁLCULO COM ELEVAÇÃO ====================

def calculate_flood_risk(risk_level, flood_rate, water_level_input, area_elevation=0, elevation_stats=None):
    """
    Calcula inundação considerando elevação do terreno
    
    Args:
        risk_level: Nível de risco ('Muito Alto', 'Alto', 'Médio', 'Baixo')
        flood_rate: Taxa de inundação (0-1)
        water_level_input: Nível de água do usuário (metros)
        area_elevation: Elevação média da área (metros)
        elevation_stats: Dict com estatísticas de elevação {'avg', 'min', 'max', 'range'}
    """
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
    
    # Usar elevation_stats se disponível
    if elevation_stats:
        avg_elevation = elevation_stats.get('avg', area_elevation)
        elevation_range = elevation_stats.get('range', 0)
        min_elevation = elevation_stats.get('min', area_elevation)
    else:
        avg_elevation = area_elevation
        elevation_range = 0
        min_elevation = area_elevation
    
    # FATOR DE ELEVAÇÃO - Quanto menor, maior o risco
    if avg_elevation < 50:
        elevation_risk = 0.40  # Costa/planície baixa = altíssimo risco
    elif avg_elevation < 200:
        elevation_risk = 0.30  # Baixa altitude = alto risco
    elif avg_elevation < 500:
        elevation_risk = 0.15  # Média altitude = médio risco
    elif avg_elevation < 1000:
        elevation_risk = 0.05  # Alta altitude = baixo risco
    else:
        elevation_risk = -0.10  # Montanhas = muito baixo risco
    
    # FATOR DE TERRENO - Grande variação = água acumula
    if elevation_range > 300:
        terrain_risk = 0.25
    elif elevation_range > 150:
        terrain_risk = 0.15
    elif elevation_range > 50:
        terrain_risk = 0.08
    else:
        terrain_risk = 0.0
    
    # Probabilidade ajustada com TODOS os fatores
    adjusted_probability = flood_rate + risk_modifier + elevation_risk + terrain_risk
    adjusted_probability = max(0, min(1, adjusted_probability))
    
    # Calcular nível de água efetivo
    if water_level_input and water_level_input > 0:
        # Usuário forneceu nível específico
        base_water = water_level_input
        
        # Ajustar baseado em drenagem e elevação
        elevation_multiplier = max(0.5, (1000 - avg_elevation) / 1000)
        effective_water_level = base_water * drainage * elevation_multiplier
    else:
        # Calcular baseado em probabilidade
        if adjusted_probability > 0.5:
            base_water = 10.0 * (adjusted_probability - 0.5) / 0.5
        else:
            base_water = 5.0 * adjusted_probability / 0.5
        
        elevation_multiplier = max(0.5, (1000 - avg_elevation) / 1000)
        effective_water_level = base_water * drainage * adjusted_probability * elevation_multiplier
    
    # Determinar se inunda - Áreas baixas inundam com menos água
    flood_threshold = max(2.0, min_elevation / 100)
    is_flooded = effective_water_level > flood_threshold
    
    if is_flooded:
        water_level = effective_water_level
        
        # Severidade baseada no nível de água E elevação
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
        
        # Áreas muito baixas = recuperação mais lenta
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
        'message': 'API de Simulação de Inundações - Angola (Com Elevação)',
        'version': '3.0.0',
        'status': 'online',
        'features': ['Dados GADM', 'Elevação Real (SRTM)', 'Análise de Terreno'],
        'endpoints': {
            'health': '/api/health',
            'info': '/api/info',
            'provinces': '/api/provinces',
            'municipalities': '/api/municipalities',
            'districts': '/api/districts',
            'simulate': '/api/simulate (POST)',
            'elevation': '/api/elevation?lat=X&lon=Y'
        }
    })

@app.route('/api/health', methods=['GET'])
def health():
    logger.info("Health check realizado")
    return jsonify({
        'status': 'ok',
        'message': 'API está ativa com suporte a elevação',
        'timestamp': datetime.now().isoformat(),
        'uptime': 'online',
        'cache_status': {
            'gadm_cached': len(GADM_CACHE),
            'elevation_cached': len(ELEVATION_CACHE)
        }
    })

@app.route('/api/elevation', methods=['GET'])
def get_elevation():
    """Endpoint para testar elevação de um ponto específico"""
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

@app.route('/api/info', methods=['GET'])
def api_info():
    return jsonify({
        'name': 'API de Simulação de Inundações - Angola',
        'version': '3.0.0',
        'description': 'API completa com análise de elevação e terreno',
        'author': 'Sistema de Gestão de Desastres Naturais',
        'data_available': {
            'provinces': len(PROVINCES),
            'municipalities': sum(len(m) for m in MUNICIPALITIES.values()),
            'districts': sum(len(d) for d in DISTRICTS.values())
        },
        'elevation_service': 'Open-Elevation API (SRTM 90m)'
    })

@app.route('/api/provinces', methods=['GET'])
def get_provinces():
    logger.info("Listando províncias do GADM")
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
    logger.info(f"Listando municípios do GADM - Província: {province}")
    
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

@app.route('/api/districts', methods=['GET'])
def get_districts():
    municipality = request.args.get('municipality', None)
    province = request.args.get('province', None)
    logger.info(f"Listando distritos do GADM - Município: {municipality}, Província: {province}")
    
    if municipality:
        municipality = municipality.replace('-', ' ')
    
    gdf_level3 = download_and_read_gadm_json('AGO', 3)
    if gdf_level3 is None:
        logger.error("Erro ao carregar GADM Level 3")
        return jsonify({'success': False, 'error': 'Erro ao carregar dados do GADM'}), 500
    
    gdf_level2 = download_and_read_gadm_json('AGO', 2)
    
    districts = []
    
    if province and province != 'all':
        gdf_level3 = gdf_level3[gdf_level3['NAME_1'] == province]
    
    if municipality and municipality != 'all':
        municipality_normalized = normalize_name(municipality)
        gdf_filtered = gdf_level3[gdf_level3['NAME_2'].apply(normalize_name) == municipality_normalized]
    else:
        gdf_filtered = gdf_level3
    
    for index, row in gdf_filtered.iterrows():
        district_name = row['NAME_3']
        mun_name = row['NAME_2']
        prov_name = row['NAME_1']
        
        static_district = None
        if mun_name in DISTRICTS:
            static_district = next((d for d in DISTRICTS[mun_name] if normalize_name(d['name']) == normalize_name(district_name)), None)
        
        if static_district:
            pop = static_district.get('population', 50000)
            district_type = static_district.get('type', 'Urbano')
            risk = static_district.get('risk', 'Médio')
        else:
            if gdf_level2 is not None:
                mun_data = gdf_level2[gdf_level2['NAME_2'] == mun_name]
                base_pop = 50000 if len(mun_data) > 0 else 30000
            else:
                base_pop = 50000
            
            pop = base_pop
            district_type = 'Urbano'
            
            static_prov = next((p for p in PROVINCES if p['name'] == prov_name), None)
            risk = static_prov['risk'] if static_prov else 'Médio'
        
        centroid = row['geometry'].centroid
        
        districts.append({
            'id': index + 1,
            'name': district_name,
            'municipality': mun_name,
            'province': prov_name,
            'population': pop,
            'type': district_type,
            'risk': risk,
            'lat': centroid.y,
            'lon': centroid.x
        })
    
    return jsonify({
        'success': True,
        'data': districts,
        'count': len(districts),
        'filter': {
            'municipality': municipality if municipality else None,
            'province': province if province else None
        },
        'timestamp': datetime.now().isoformat()
    })

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
        district = data.get('district', 'all')
        
        logger.info(f"🌊 Simulação iniciada - Level: {level}, Rate: {flood_rate*100}%, WaterLevel: {water_level_input}, Province: {province}")
        
        results = []
        geojson = None
        
        if level == 'district':
            logger.info(f"Município recebido: '{municipality}'")
            
            if municipality and municipality != 'all':
                municipality = municipality.replace('-', ' ')
                import re
                municipality = re.sub(r'([a-z])([A-Z])', r'\1 \2', municipality)
            
            logger.info(f"Município normalizado: '{municipality}'")
            
            gdf_level2 = download_and_read_gadm_json('AGO', 2)
            gdf_level3 = download_and_read_gadm_json('AGO', 3)
            
            if gdf_level2 is None or gdf_level3 is None:
                return jsonify({'success': False, 'error': 'Erro ao carregar dados do GADM'}), 500
            
            munic_to_province = {}
            for prov_name, munics in MUNICIPALITIES.items():
                for m in munics:
                    munic_to_province[m['name']] = prov_name
            
            districts_to_process = []
            
            if municipality != 'all' and municipality in DISTRICTS:
                for d in DISTRICTS[municipality]:
                    if district != 'all' and d['name'] != district:
                        continue
                    dist_data = {**d, 'municipality': municipality}
                    districts_to_process.append(dist_data)
                logger.info(f"✅ Usando {len(districts_to_process)} distritos estáticos para {municipality}")
                
            elif municipality == 'all':
                for munic, dists in DISTRICTS.items():
                    munic_province = munic_to_province.get(munic)
                    if province != 'all' and munic_province != province:
                        continue
                    for d in dists:
                        if district != 'all' and d['name'] != district:
                            continue
                        dist_data = {**d, 'municipality': munic}
                        districts_to_process.append(dist_data)
                logger.info(f"✅ Usando {len(districts_to_process)} distritos estáticos")
                
            else:
                logger.info(f"⚠️ Município '{municipality}' não tem dados estáticos, buscando do GADM")
                
                municipality_gadm = MUNICIPALITY_NAME_MAPPING.get(municipality, municipality)
                municipality_normalized = normalize_name(municipality_gadm)
                
                gdf_mun_districts = gdf_level3[gdf_level3['NAME_2'].apply(normalize_name) == municipality_normalized]
                
                if len(gdf_mun_districts) > 0:
                    for idx, row in gdf_mun_districts.iterrows():
                        dist_name = row['NAME_3']
                        prov_name = row['NAME_1']
                        
                        static_prov = next((p for p in PROVINCES if p['name'] == prov_name), None)
                        risk = static_prov['risk'] if static_prov else 'Médio'
                        
                        dist_data = {
                            'name': dist_name,
                            'municipality': municipality,
                            'population': 50000,
                            'type': 'Urbano',
                            'risk': risk
                        }
                        districts_to_process.append(dist_data)
                    
                    logger.info(f"✅ Encontrados {len(districts_to_process)} distritos do GADM Level 3")
                else:
                    logger.warning(f"⚠️ Usando município como distrito único (fallback)")
                    
                    static_mun = None
                    for prov_munics in MUNICIPALITIES.values():
                        static_mun = next((m for m in prov_munics if m['name'] == municipality), None)
                        if static_mun:
                            break
                    
                    if static_mun:
                        pop = static_mun['population']
                        risk = static_mun['risk']
                        
                        dist_data = {
                            'name': municipality,
                            'municipality': municipality,
                            'population': pop,
                            'type': 'Municipal',
                            'risk': risk,
                            'is_municipality_fallback': True
                        }
                        districts_to_process.append(dist_data)
                        logger.info(f"✅ Usando município como distrito único (fallback)")
            
            results = []
            features = []
            
            for dist in districts_to_process:
                risk = dist['risk']
                pop = dist['population']
                
                # BUSCAR GEOMETRIA E ELEVAÇÃO
                dist_normalized = normalize_name(dist['name'])
                found_geom = None
                elevation_stats = None
                
                if province != 'all':
                    gdf_filtered = gdf_level2[gdf_level2['NAME_1'] == province]
                else:
                    gdf_filtered = gdf_level2
                
                for idx, row in gdf_filtered.iterrows():
                    if normalize_name(row['NAME_2']) == dist_normalized:
                        found_geom = row['geometry']
                        # OBTER ELEVAÇÃO
                        elevation_stats = get_region_elevation_stats(found_geom)
                        logger.info(f"🗻 {dist['name']}: Elevação = {elevation_stats['avg']:.1f}m")
                        break
                
                if found_geom is None:
                    commune_row = find_commune_in_gadm(dist['name'], dist['municipality'], gdf_level3)
                    if commune_row is not None:
                        found_geom = commune_row['geometry']
                        # OBTER ELEVAÇÃO
                        elevation_stats = get_region_elevation_stats(found_geom)
                        logger.info(f"🗻 {dist['name']}: Elevação = {elevation_stats['avg']:.1f}m")
                
                # CALCULAR INUNDAÇÃO COM ELEVAÇÃO
                avg_elevation = elevation_stats['avg'] if elevation_stats else 400.0
                
                is_flooded, water_level, severity, recovery_days = calculate_flood_risk(
                    risk, 
                    flood_rate, 
                    water_level_input, 
                    avg_elevation, 
                    elevation_stats
                )
                
                affected_population = 0
                if is_flooded:
                    impact_factor = min(water_level / 20.0, 0.7)
                    affected_population = int(pop * impact_factor)
                
                result_data = {
                    'name': dist['name'],
                    'municipality': dist['municipality'],
                    'flooded': is_flooded,
                    'waterLevel': water_level,
                    'severity': severity,
                    'recoveryDays': recovery_days,
                    'affectedPopulation': affected_population,
                    'elevation': round(avg_elevation, 1) if elevation_stats else None,
                    'elevation_min': round(elevation_stats['min'], 1) if elevation_stats else None,
                    'elevation_max': round(elevation_stats['max'], 1) if elevation_stats else None
                }
                
                results.append(result_data)
                
                if found_geom is not None:
                    import json
                    geom_json = json.loads(gpd.GeoSeries([found_geom]).to_json())['features'][0]['geometry']
                    
                    features.append({
                        'type': 'Feature',
                        'geometry': geom_json,
                        'properties': result_data
                    })
                else:
                    fallback_coords = None
                    
                    for idx, row in gdf_level2.iterrows():
                        if normalize_name(row['NAME_2']) == normalize_name(dist['municipality']):
                            centroid = row['geometry'].centroid
                            fallback_coords = [centroid.x, centroid.y]
                            break
                    
                    if fallback_coords is None:
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
                    'totalItems': len(results),
                    'avgRisk': (flooded_count / len(results) * 100) if results else 0
                },
                'parameters': {
                    'level': level,
                    'floodRate': flood_rate * 100,
                    'province': province,
                    'municipality': municipality,
                    'district': district,
                    'elevation_used': True
                },
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Simulação concluída - {flooded_count} de {len(results)} áreas inundadas")
            return jsonify(response)
        
        # SIMULAÇÃO PARA PROVINCES E MUNICIPALITIES
        level_map = {'province': 1, 'municipality': 2}
        level_num = level_map.get(level)
        
        if level_num is None:
            return jsonify({'success': False, 'error': 'Nível inválido'}), 400
        
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
        gdf['elevation_min'] = 0.0
        gdf['elevation_max'] = 0.0
        
        if level == 'province':
            gdf['affectedComunas'] = 0
        elif level == 'municipality':
            gdf['affectedDistricts'] = 0
        
        logger.info(f"🔄 Processando {len(gdf)} regiões com elevação...")
        
        for i, row in gdf.iterrows():
            prov = row['NAME_1']
            name = row[f'NAME_{level_num}']
            geometry = row['geometry']
            
            # OBTER ELEVAÇÃO DA REGIÃO
            elevation_stats = get_region_elevation_stats(geometry)
            avg_elevation = elevation_stats['avg']
            
            logger.info(f"🗻 Processando {name} - Elevação: {avg_elevation:.1f}m")
            
            if level == 'province':
                static = next((p for p in PROVINCES if p['name'] == name), None)
            elif level == 'municipality':
                static = next((m for m in MUNICIPALITIES.get(prov, []) if m['name'] == name), None)
            else:
                static = next((d for d in DISTRICTS.get(prov, []) if d['name'] == name), None)
            
            if static:
                risk = static['risk']
                pop = static['population']
            else:
                static_prov = next((p for p in PROVINCES if p['name'] == prov), None)
                risk = static_prov['risk'] if static_prov else 'Médio'
                pop = 0
            
            # CALCULAR INUNDAÇÃO COM ELEVAÇÃO
            is_flooded, water_level, severity, recovery_days = calculate_flood_risk(
                risk, 
                flood_rate, 
                water_level_input, 
                avg_elevation, 
                elevation_stats
            )
            
            affected_population = 0
            if is_flooded:
                impact_factor = min(water_level / 20.0, 0.5 if level == 'province' else 0.6)
                affected_population = int(pop * impact_factor)
            
            gdf.at[i, 'flooded'] = is_flooded
            gdf.at[i, 'waterLevel'] = water_level
            gdf.at[i, 'severity'] = severity
            gdf.at[i, 'recoveryDays'] = recovery_days
            gdf.at[i, 'affectedPopulation'] = affected_population
            gdf.at[i, 'elevation'] = round(avg_elevation, 1)
            gdf.at[i, 'elevation_min'] = round(elevation_stats['min'], 1)
            gdf.at[i, 'elevation_max'] = round(elevation_stats['max'], 1)
            
            if level == 'province' and is_flooded:
                affected_comunas = int(5 + (water_level / 100) * 15)
                gdf.at[i, 'affectedComunas'] = affected_comunas
            elif level == 'municipality' and is_flooded:
                affected_districts = int(2 + (water_level / 100) * 8)
                gdf.at[i, 'affectedDistricts'] = affected_districts
        
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
                'district': district,
                'elevation_used': True
            },
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"✅ Simulação concluída - {flooded_count} de {len(results)} áreas inundadas")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"❌ Erro na simulação: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Endpoint não encontrado'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🌊 API de Simulação de Inundações - Angola v3.0")
    print("🗻 COM DADOS DE ELEVAÇÃO REAIS (SRTM)")
    print("="*70)
    print(f"📡 Servidor: http://0.0.0.0:5000")
    print(f"📚 Docs: http://localhost:5000/api/info")
    print(f"💚 Status: http://localhost:5000/api/health")
    print(f"🗻 Elevação: http://localhost:5000/api/elevation?lat=-8.8&lon=13.2")
    print(f"📊 Províncias: {len(PROVINCES)}")
    print(f"🏛️ Municípios: {sum(len(m) for m in MUNICIPALITIES.values())}")
    print(f"🏘️ Bairros: {sum(len(d) for d in DISTRICTS.values())}")
    print("="*70 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
