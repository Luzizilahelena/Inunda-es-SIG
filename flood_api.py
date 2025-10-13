from flask import Flask, request, jsonify
from flask_cors import CORS
from flask import render_template
import random
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
def download_and_read_gadm_json(country_code, level):
    json_url = f'https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_{country_code}_{level}.json.zip'
    logger.info(f"Tentando baixar GeoJSON: {json_url}...")
    
    try:
        response = requests.get(json_url)
        response.raise_for_status()
        with ZipFile(BytesIO(response.content)) as zip_file:
            json_filename = zip_file.namelist()[0]
            with zip_file.open(json_filename) as json_file:
                gdf = gpd.read_file(json_file, driver='GeoJSON')
        return gdf
    except Exception as e:
        logger.error(f"Erro ao baixar/processar GeoJSON: {e}")
        return None

# ==================== FUNÇÃO DE CÁLCULO ====================
def calculate_flood_risk(risk_level, flood_rate, specified_water_level=None):
    """Calcula se uma área será inundada baseado em fatores reais"""
    risk_factors = {
        'Muito Alto': 0.35,
        'Alto': 0.20,
        'Médio': 0.05,
        'Baixo': -0.10
    }
    
    risk_modifier = risk_factors.get(risk_level, 0)
    adjusted_probability = max(0, min(1, flood_rate + risk_modifier))
    rainfall = random.uniform(0, 500)
    
    if specified_water_level is not None:
        # MODIFICAÇÃO: Se nível de água for especificado, use-o diretamente e force inundação se > 0
        water_level = max(0, specified_water_level)  # Garanta que seja >= 0
        is_flooded = water_level > 0
    else:
        # Cálculo dinâmico original (sem override estático)
        is_flooded = (random.random() < adjusted_probability) and (rainfall > 150)
        if is_flooded:
            drainage_factor = {
                'Muito Alto': 0.8,
                'Alto': 0.6,
                'Médio': 0.4,
                'Baixo': 0.2
            }
            
            retention = drainage_factor.get(risk_level, 0.5)
            base_water = 5.0
            max_water = 20.0
            water_level = base_water + (rainfall / 500) * (max_water - base_water) * retention
        else:
            water_level = 0
    
    if is_flooded:
        # MODIFICAÇÃO: Severidade baseada no water_level (seja calculado ou especificado)
        if water_level < 8.0:
            severity = 'Leve'
            recovery_days = random.randint(5, 10)
        elif water_level < 12.0:
            severity = 'Moderada'
            recovery_days = random.randint(10, 20)
        elif water_level < 16.0:
            severity = 'Grave'
            recovery_days = random.randint(20, 40)
        else:
            severity = 'Crítica'
            recovery_days = random.randint(40, 90)
    else:
        severity = 'Nenhuma'
        recovery_days = 0
    
    return is_flooded, water_level, severity, recovery_days

# ==================== ROTAS ====================
@app.route('/', methods=['GET'])
def home():
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
    logger.info(f"Listando distritos - Município: {municipality}")
    
    if municipality and municipality != 'all' and municipality in DISTRICTS:
        districts = [{**d, 'municipality': municipality} for d in DISTRICTS[municipality]]
    elif municipality == 'all' or not municipality:
        districts = []
        for munic, dists in DISTRICTS.items():
            for d in dists:
                districts.append({**d, 'municipality': munic})
    else:
        districts = []
    
    return jsonify({
        'success': True,
        'data': districts,
        'count': len(districts),
        'filter': {'municipality': municipality} if municipality else None,
        'timestamp': datetime.now().isoformat()
    })
    
@app.route('/index', methods=['GET'])
def template():
	return render_template("teste_api.html")

@app.route('/api/simulate', methods=['POST'])
def simulate_flood():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400
        
        level = data.get('level', 'province')
        flood_rate = float(data.get('floodRate', 50)) / 100
        # MODIFICAÇÃO: Adicionar parâmetro opcional para nível de água especificado
        specified_water_level = data.get('waterLevel', None)  # Em metros, ex.: 10.5
        province = data.get('province', 'all')
        municipality = data.get('municipality', 'all')
        
        logger.info(f"Simulação iniciada - Level: {level}, Rate: {flood_rate*100}%, WaterLevel: {specified_water_level}, Province: {province}")
        
        results = []
        geojson = None
        
        level_map = {'province': 1, 'municipality': 2, 'district': 3}
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
            
            # MODIFICAÇÃO: Passar specified_water_level para a função de cálculo
            is_flooded, water_level, severity, recovery_days = calculate_flood_risk(
                risk, flood_rate, specified_water_level
            )
            
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
                gdf.at[i, 'affectedComunas'] = random.randint(5, 20)
            elif level == 'municipality' and is_flooded:
                gdf.at[i, 'affectedDistricts'] = random.randint(2, 10)
        
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
                'waterLevel': specified_water_level,  # MODIFICAÇÃO: Incluir no response para depuração
                'province': province,
                'municipality': municipality
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
