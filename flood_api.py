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

# Todas as 18 províncias de Angola
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

# Municípios por província
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

# Bairros/Distritos por município
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

# ==================== FUNÇÃO PARA BAIXAR E LER GADM ====================

# Cache global para dados GADM (evitar downloads repetidos)
GADM_CACHE = {}

# Mapeamento de nomes alternativos (dados estáticos → GADM)
# Para resolver inconsistências entre dados hardcoded e GADM
MUNICIPALITY_NAME_MAPPING = {
    'Caimbambo': 'Caiambambo',  # Benguela - variação ortográfica
    'Catumbela': 'Catumbela',   # Pode não existir no GADM - usar fallback
    # Adicionar mais mapeamentos conforme necessário
}

def download_and_read_gadm_json(country_code, level):
    cache_key = f"{country_code}_{level}"
    
    # Verificar se já está em cache
    if cache_key in GADM_CACHE:
        logger.info(f"Usando dados GADM do cache: Level {level}")
        return GADM_CACHE[cache_key]
    
    json_url = f'https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_{country_code}_{level}.json.zip'
    logger.info(f"Baixando GeoJSON pela primeira vez: {json_url}...")

    try:
        response = requests.get(json_url)
        response.raise_for_status()
        with ZipFile(BytesIO(response.content)) as zip_file:
            json_filename = zip_file.namelist()[0]
            with zip_file.open(json_filename) as json_file:
                gdf = gpd.read_file(json_file, driver='GeoJSON')
        
        # Armazenar em cache
        GADM_CACHE[cache_key] = gdf
        logger.info(f"Dados GADM Level {level} armazenados em cache")
        return gdf
    except Exception as e:
        logger.error(f"Erro ao baixar/processar GeoJSON: {e}")
        return None

def normalize_name(name):
    """Normaliza nomes para comparação (remove espaços, hífens, acentos e converte para minúsculas)"""
    import unicodedata
    # Remove acentos
    name = unicodedata.normalize('NFD', name)
    name = ''.join(char for char in name if unicodedata.category(char) != 'Mn')
    # Remove espaços, hífens e converte para minúsculas
    name = name.replace(' ', '').replace('-', '').replace('_', '').lower()
    return name

def find_commune_in_gadm(district_name, municipality_name, gdf):
    """
    Encontra a comuna correspondente no GeoDataFrame do GADM
    usando correspondência fuzzy de nomes
    """
    district_normalized = normalize_name(district_name)
    municipality_normalized = normalize_name(municipality_name)
    
    # Filtrar por município primeiro
    municipality_data = gdf[gdf['NAME_2'].apply(normalize_name) == municipality_normalized]
    
    if len(municipality_data) == 0:
        logger.warning(f"Município '{municipality_name}' não encontrado no GADM")
        return None
    
    # Procurar distrito/comuna
    for idx, row in municipality_data.iterrows():
        commune_normalized = normalize_name(row['NAME_3'])
        
        # Correspondência exata
        if commune_normalized == district_normalized:
            return row
        
        # Correspondência parcial (comuna contém distrito ou vice-versa)
        if district_normalized in commune_normalized or commune_normalized in district_normalized:
            return row
    
    # Se não encontrar, retornar o primeiro da lista do município
    logger.warning(f"Distrito '{district_name}' não encontrado exatamente em '{municipality_name}', usando primeira comuna disponível")
    return municipality_data.iloc[0] if len(municipality_data) > 0 else None

# ==================== FUNÇÃO DE CÁLCULO ====================

def calculate_flood_risk(risk_level, flood_rate, water_level_input, area_elevation=0):
    """
    Calcula se uma área será inundada baseado em fatores reais e determinísticos.
    
    Args:
        risk_level: Nível de risco da área ('Muito Alto', 'Alto', 'Médio', 'Baixo')
        flood_rate: Taxa de inundação (0-1)
        water_level_input: Nível de água fornecido pelo usuário em metros (0-100)
        area_elevation: Elevação da área (usado para cálculos mais precisos)
    
    Returns:
        (is_flooded, water_level, severity, recovery_days)
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
    
    adjusted_probability = max(0, min(1, flood_rate + risk_modifier))
    
    effective_water_level = water_level_input * drainage * adjusted_probability
    
    is_flooded = effective_water_level > 2.0
    
    if is_flooded:
        water_level = effective_water_level
        
        if water_level < 8.0:
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
        
        return True, water_level, severity, recovery_days
    else:
        return False, 0, 'Nenhuma', 0

# ==================== ROTAS ====================

@app.route('/index')
def home():
    return render_template('teste_api.html')

@app.route('/api', methods=['GET'])
def api_home():
    return jsonify({
        'message': 'API de Simulação de Inundações - Angola',
        'version': '2.0.0',
        'status': 'online',
        'endpoints': {
            'health': '/api/health',
            'info': '/api/info',
            'provinces': '/api/provinces',
            'municipalities': '/api/municipalities',
            'districts': '/api/districts',
            'simulate': '/api/simulate (POST)'
        }
    })

@app.route('/api/health', methods=['GET'])
def health():
    logger.info("Health check realizado")
    return jsonify({
        'status': 'ok',
        'message': 'API de Simulação de Inundações está ativa',
        'timestamp': datetime.now().isoformat(),
        'uptime': 'online'
    })

@app.route('/api/info', methods=['GET'])
def api_info():
    return jsonify({
        'name': 'API de Simulação de Inundações - Angola',
        'version': '2.0.0',
        'description': 'API completa para simulação e análise de inundações em Angola',
        'author': 'Sistema de Gestão de Desastres Naturais',
        'data_available': {
            'provinces': len(PROVINCES),
            'municipalities': sum(len(m) for m in MUNICIPALITIES.values()),
            'districts': sum(len(d) for d in DISTRICTS.values())
        }
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
    
    # Normalizar nome do município (converter hífen em espaço)
    if municipality:
        municipality = municipality.replace('-', ' ')
    
    # Carregar dados do GADM Level 3 (comunas/distritos)
    gdf_level3 = download_and_read_gadm_json('AGO', 3)
    if gdf_level3 is None:
        logger.error("Erro ao carregar GADM Level 3")
        return jsonify({'success': False, 'error': 'Erro ao carregar dados do GADM'}), 500
    
    # Carregar dados do GADM Level 2 (municípios) para obter informações adicionais
    gdf_level2 = download_and_read_gadm_json('AGO', 2)
    
    districts = []
    
    # Filtrar por província se especificado
    if province and province != 'all':
        gdf_level3 = gdf_level3[gdf_level3['NAME_1'] == province]
    
    # Filtrar por município se especificado
    if municipality and municipality != 'all':
        municipality_normalized = normalize_name(municipality)
        gdf_filtered = gdf_level3[gdf_level3['NAME_2'].apply(normalize_name) == municipality_normalized]
    else:
        gdf_filtered = gdf_level3
    
    # Processar cada distrito/comuna do GADM
    for index, row in gdf_filtered.iterrows():
        district_name = row['NAME_3']
        mun_name = row['NAME_2']
        prov_name = row['NAME_1']
        
        # Verificar se existe dados estáticos para este distrito
        static_district = None
        if mun_name in DISTRICTS:
            static_district = next((d for d in DISTRICTS[mun_name] if normalize_name(d['name']) == normalize_name(district_name)), None)
        
        if static_district:
            # Usar dados estáticos se existirem
            pop = static_district.get('population', 50000)
            district_type = static_district.get('type', 'Urbano')
            risk = static_district.get('risk', 'Médio')
        else:
            # Gerar dados baseados na província e município
            # Obter dados do município
            if gdf_level2 is not None:
                mun_data = gdf_level2[gdf_level2['NAME_2'] == mun_name]
                if len(mun_data) > 0:
                    # Estimar população do distrito com base no município
                    # Município grande = distritos maiores
                    base_pop = 50000
                else:
                    base_pop = 30000
            else:
                base_pop = 50000
            
            pop = base_pop
            district_type = 'Urbano'
            
            # Obter risco da província
            static_prov = next((p for p in PROVINCES if p['name'] == prov_name), None)
            risk = static_prov['risk'] if static_prov else 'Médio'
        
        # Calcular centróide para coordenadas
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
        	water_level_input = 5.5
        province = data.get('province', 'all')
        municipality = data.get('municipality', 'all')
        district = data.get('district', 'all')

        logger.info(f"Simulação iniciada - Level: {level}, Rate: {flood_rate*100}%, WaterLevel: {water_level_input}m, Province: {province}, Municipality: {municipality}, District: {district}")

        results = []
        geojson = None

        if level == 'district':
            # Normalizar nome do município
            logger.info(f"Município recebido (antes da normalização): '{municipality}'")
            if municipality and municipality != 'all':
                # Converter hífen em espaço
                municipality = municipality.replace('-', ' ')
                # Adicionar espaço antes de maiúsculas no meio da palavra (ex: KilambaKiaxi -> Kilamba Kiaxi)
                import re
                municipality = re.sub(r'([a-z])([A-Z])', r'\1 \2', municipality)
            logger.info(f"Município após normalização: '{municipality}'")
            
            # Baixar dados GADM nível 2 (municípios) e nível 3 (comunas)
            gdf_level2 = download_and_read_gadm_json('AGO', 2)
            gdf_level3 = download_and_read_gadm_json('AGO', 3)
            
            if gdf_level2 is None or gdf_level3 is None:
                return jsonify({'success': False, 'error': 'Erro ao carregar dados do GADM'}), 500
            
            munic_to_province = {}
            for prov_name, munics in MUNICIPALITIES.items():
                for m in munics:
                    munic_to_province[m['name']] = prov_name
            
            # ESTRATÉGIA: Tentar dados estáticos primeiro, se não houver, usar GADM
            districts_to_process = []
            
            # 1. Tentar obter distritos estáticos
            if municipality != 'all' and municipality in DISTRICTS:
                # Município tem dados hardcoded, usar esses
                for d in DISTRICTS[municipality]:
                    if district != 'all' and d['name'] != district:
                        continue
                    dist_data = {**d, 'municipality': municipality}
                    districts_to_process.append(dist_data)
                logger.info(f"Usando {len(districts_to_process)} distritos estáticos para {municipality}")
            elif municipality == 'all':
                # Usar todos os distritos estáticos
                for munic, dists in DISTRICTS.items():
                    munic_province = munic_to_province.get(munic)
                    if province != 'all' and munic_province != province:
                        continue
                    for d in dists:
                        if district != 'all' and d['name'] != district:
                            continue
                        dist_data = {**d, 'municipality': munic}
                        districts_to_process.append(dist_data)
                logger.info(f"Usando {len(districts_to_process)} distritos estáticos")
            else:
                # 2. Município não tem dados estáticos, buscar do GADM
                logger.info(f"Município '{municipality}' não tem dados estáticos, buscando do GADM")
                
                # Aplicar mapeamento de nomes se necessário
                municipality_gadm = MUNICIPALITY_NAME_MAPPING.get(municipality, municipality)
                municipality_normalized = normalize_name(municipality_gadm)
                
                # Filtrar por município no GADM Level 3
                gdf_mun_districts = gdf_level3[gdf_level3['NAME_2'].apply(normalize_name) == municipality_normalized]
                
                if len(gdf_mun_districts) > 0:
                    # Encontrou distritos/comunas no GADM Level 3
                    for idx, row in gdf_mun_districts.iterrows():
                        dist_name = row['NAME_3']
                        prov_name = row['NAME_1']
                        
                        # Obter risco da província
                        static_prov = next((p for p in PROVINCES if p['name'] == prov_name), None)
                        risk = static_prov['risk'] if static_prov else 'Médio'
                        
                        dist_data = {
                            'name': dist_name,
                            'municipality': municipality,
                            'population': 50000,  # Estimativa padrão
                            'type': 'Urbano',
                            'risk': risk
                        }
                        districts_to_process.append(dist_data)
                    
                    logger.info(f"Encontrados {len(districts_to_process)} distritos do GADM Level 3 para {municipality}")
                else:
                    # Fallback: se não houver Level 3, usar o próprio município como distrito único
                    logger.warning(f"Nenhum distrito Level 3 encontrado para {municipality}, usando o município como distrito único")
                    
                    # Buscar dados estáticos do município
                    static_mun = None
                    for prov_munics in MUNICIPALITIES.values():
                        static_mun = next((m for m in prov_munics if m['name'] == municipality), None)
                        if static_mun:
                            break
                    
                    if static_mun:
                        # Usar dados estáticos do município
                        pop = static_mun['population']
                        risk = static_mun['risk']
                        
                        dist_data = {
                            'name': municipality,  # Usar o nome do município
                            'municipality': municipality,
                            'population': pop,
                            'type': 'Municipal',
                            'risk': risk,
                            'is_municipality_fallback': True  # Marca para tratamento especial
                        }
                        districts_to_process.append(dist_data)
                        logger.info(f"Usando município {municipality} como distrito único com dados estáticos (fallback)")
                    else:
                        # Buscar no GADM Level 2 se não houver dados estáticos
                        gdf_mun_level2 = gdf_level2[gdf_level2['NAME_2'].apply(normalize_name) == municipality_normalized]
                        
                        if len(gdf_mun_level2) > 0:
                            row = gdf_mun_level2.iloc[0]
                            prov_name = row['NAME_1']
                            
                            # Obter risco da província
                            static_prov = next((p for p in PROVINCES if p['name'] == prov_name), None)
                            risk = static_prov['risk'] if static_prov else 'Médio'
                            
                            dist_data = {
                                'name': municipality,
                                'municipality': municipality,
                                'population': 100000,
                                'type': 'Municipal',
                                'risk': risk,
                                'is_municipality_fallback': True
                            }
                            districts_to_process.append(dist_data)
                            logger.info(f"Usando município {municipality} como distrito único do GADM Level 2 (fallback)")
                        else:
                            logger.error(f"Município {municipality} não encontrado nem em dados estáticos nem no GADM!")
            
            results = []
            features = []
            
            for dist in districts_to_process:
                risk = dist['risk']
                pop = dist['population']
                
                is_flooded, water_level, severity, recovery_days = calculate_flood_risk(risk, flood_rate, water_level_input)
                
                affected_population = 0
                if is_flooded:
                    impact_factor = min(water_level / 20.0, 0.7)
                    affected_population = int(pop * impact_factor)
                
                results.append({
                    'name': dist['name'],
                    'municipality': dist['municipality'],
                    'flooded': is_flooded,
                    'waterLevel': water_level,
                    'severity': severity,
                    'recoveryDays': recovery_days,
                    'affectedPopulation': affected_population
                })
                
                # Primeiro, tentar encontrar como município (Level 2)
                dist_normalized = normalize_name(dist['name'])
                found_geom = None
                
                # Filtrar por província se especificado
                if province != 'all':
                    gdf_filtered = gdf_level2[gdf_level2['NAME_1'] == province]
                else:
                    gdf_filtered = gdf_level2
                
                # Procurar distrito como município (Level 2)
                for idx, row in gdf_filtered.iterrows():
                    if normalize_name(row['NAME_2']) == dist_normalized:
                        found_geom = row['geometry']
                        logger.info(f"Distrito '{dist['name']}' encontrado como município (Level 2)")
                        break
                
                # Se não encontrar como município, tentar como comuna (Level 3)
                if found_geom is None:
                    commune_row = find_commune_in_gadm(dist['name'], dist['municipality'], gdf_level3)
                    if commune_row is not None:
                        found_geom = commune_row['geometry']
                        logger.info(f"Distrito '{dist['name']}' encontrado como comuna (Level 3)")
                
                if found_geom is not None:
                    # Converter geometria para GeoJSON
                    import json
                    geom_json = json.loads(gpd.GeoSeries([found_geom]).to_json())['features'][0]['geometry']
                    
                    features.append({
                        'type': 'Feature',
                        'geometry': geom_json,
                        'properties': {
                            'name': dist['name'],
                            'municipality': dist['municipality'],
                            'flooded': is_flooded,
                            'waterLevel': water_level,
                            'severity': severity,
                            'recoveryDays': recovery_days,
                            'affectedPopulation': affected_population
                        }
                    })
                else:
                    # Fallback: usar centróide da província ou município
                    logger.warning(f"Não foi possível encontrar geometria para {dist['name']}, usando fallback")
                    
                    # Tentar encontrar o centróide do município primeiro
                    fallback_coords = None
                    
                    # Procurar município na cache do Level 2
                    for idx, row in gdf_level2.iterrows():
                        if normalize_name(row['NAME_2']) == normalize_name(dist['municipality']):
                            centroid = row['geometry'].centroid
                            fallback_coords = [centroid.x, centroid.y]
                            logger.info(f"Usando centróide do município {dist['municipality']} como fallback")
                            break
                    
                    # Se não encontrar município, usar centróide da província
                    if fallback_coords is None and province != 'all':
                        gdf_prov = download_and_read_gadm_json('AGO', 1)
                        if gdf_prov is not None:
                            prov_row = gdf_prov[gdf_prov['NAME_1'] == province]
                            if len(prov_row) > 0:
                                centroid = prov_row.iloc[0]['geometry'].centroid
                                fallback_coords = [centroid.x, centroid.y]
                                logger.info(f"Usando centróide da província {province} como fallback")
                    
                    # Último recurso: coordenadas de Luanda (capital)
                    if fallback_coords is None:
                        fallback_coords = [13.2437, -8.8383]  # Luanda, Angola
                        logger.warning(f"Usando coordenadas de Luanda como último recurso para {dist['name']}")
                    
                    features.append({
                        'type': 'Feature',
                        'geometry': {
                            'type': 'Point',
                            'coordinates': fallback_coords
                        },
                        'properties': {
                            'name': dist['name'],
                            'municipality': dist['municipality'],
                            'flooded': is_flooded,
                            'waterLevel': water_level,
                            'severity': severity,
                            'recoveryDays': recovery_days,
                            'affectedPopulation': affected_population
                        }
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
                    'district': district
                },
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Simulação de distrito concluída - {flooded_count} de {len(results)} áreas inundadas")
            return jsonify(response)
        
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
        if level == 'province':
            gdf['affectedComunas'] = 0
        elif level == 'municipality':
            gdf['affectedDistricts'] = 0

        for i, row in gdf.iterrows():
            prov = row['NAME_1']
            name = row[f'NAME_{level_num}']

            if level == 'province':
                static = next((p for p in PROVINCES if p['name'] == name), None)
            elif level == 'municipality':
                static = next((m for m in MUNICIPALITIES.get(prov, []) if m['name'] == name), None)
            else:  # district (comuna)
                static = next((d for d in DISTRICTS.get(prov, []) if d['name'] == name), None)
            if static:
                risk = static['risk']
                pop = static['population']
            else:
                static_prov = next((p for p in PROVINCES if p['name'] == prov), None)
                risk = static_prov['risk'] if static_prov else 'Médio'
                pop = 0

            is_flooded, water_level, severity, recovery_days = calculate_flood_risk(risk, flood_rate, water_level_input)

            affected_population = 0
            if is_flooded:
                impact_factor = min(water_level / 20.0, 0.5 if level == 'province' else 0.6 if level == 'municipality' else 0.7)
                affected_population = int(pop * impact_factor)

            gdf.at[i, 'flooded'] = is_flooded
            gdf.at[i, 'waterLevel'] = water_level
            gdf.at[i, 'severity'] = severity
            gdf.at[i, 'recoveryDays'] = recovery_days
            gdf.at[i, 'affectedPopulation'] = affected_population

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
                'district': district
            },
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"Simulação concluída - {flooded_count} de {len(results)} áreas inundadas")

        return jsonify(response)

    except Exception as e:
        logger.error(f"Erro na simulação: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Endpoint não encontrado'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

if __name__ == '__main__':
    print("\n" + "="*60)
    print("API de Simulação de Inundações - Angola v2.0")
    print("="*60)
    print(f"📡 Servidor iniciado em: http://0.0.0.0:5000")
    print(f"📚 Documentação: http://localhost:5000/api/info")
    print(f"💚 Status: http://localhost:5000/api/health")
    print(f"📊 Províncias: {len(PROVINCES)}")
    print(f"🏛️ Municípios: {sum(len(m) for m in MUNICIPALITIES.values())}")
    print(f"🏘️ Bairros: {sum(len(d) for d in DISTRICTS.values())}")
    print("="*60 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
