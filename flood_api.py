#import os
#os.system("pip install -r requirements.txt")

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime
import logging
import requests
import geopandas as gpd
from zipfile import ZipFile
from io import BytesIO
import numpy as np

# Importar módulos de banco de dados
from database import (
    Database, get_provinces, get_municipalities, get_bairros,
    get_municipality_by_name, get_province_by_name,
    save_simulation, save_simulation_results,
    get_simulation_history, get_simulation_details
)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Inicializar conexão com banco
db = Database()

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

def compute_flow_direction(dem):
    """Calcula direção de fluxo D8"""
    rows, cols = dem.shape
    flow_dir = np.full((rows, cols), -1, dtype=int)
    drow = [-1, -1, -1,  0,  0,  1,  1,  1]
    dcol = [-1,  0,  1, -1,  1, -1,  0,  1]
    dists = [np.sqrt(2), 1, np.sqrt(2), 1, 1, np.sqrt(2), 1, np.sqrt(2)]
    
    for i in range(rows):
        for j in range(cols):
            max_slope = -np.inf
            best_k = -1
            for k in range(8):
                ni, nj = i + drow[k], j + dcol[k]
                if 0 <= ni < rows and 0 <= nj < cols:
                    slope = (dem[i, j] - dem[ni, nj]) / dists[k]
                    if slope > max_slope:
                        max_slope = slope
                        best_k = k
            if best_k >= 0:
                flow_dir[i, j] = best_k
    return flow_dir

def compute_flow_accumulation(dem, flow_dir):
    """Calcula acumulação de fluxo baseada em D8"""
    rows, cols = dem.shape
    accum = np.ones((rows, cols))
    drow = [-1, -1, -1,  0,  0,  1,  1,  1]
    dcol = [-1,  0,  1, -1,  1, -1,  0,  1]
    
    flat_indices = np.argsort(dem.ravel())[::-1]
    for flat_idx in flat_indices:
        i, j = divmod(flat_idx, cols)
        dir_k = flow_dir[i, j]
        if dir_k >= 0:
            ni, nj = i + drow[dir_k], j + dcol[dir_k]
            if 0 <= ni < rows and 0 <= nj < cols:
                accum[ni, nj] += accum[i, j]
    return accum

def get_region_elevation_stats(geometry):
    """Calcula estatísticas de elevação e acumulação de fluxo"""
    try:
        cache_key = f"{geometry.centroid.y:.4f},{geometry.centroid.x:.4f}"
        if cache_key in ELEVATION_CACHE:
            logger.info(f"Usando elevação do cache")
            return ELEVATION_CACHE[cache_key]
        
        bounds = geometry.bounds
        area = geometry.area
        
        if area > 1.0:
            grid_size = 15
        elif area > 0.1:
            grid_size = 10
        else:
            grid_size = 5
        
        lons = np.linspace(bounds[0], bounds[2], grid_size)
        lats = np.linspace(bounds[1], bounds[3], grid_size)
        coordinates = [(lat, lon) for lat in lats for lon in lons]
        
        elevations = []
        batch_size = 100
        for i in range(0, len(coordinates), batch_size):
            batch = coordinates[i:i+batch_size]
            batch_elev = get_elevation_batch(batch)
            if batch_elev:
                elevations.extend(batch_elev)
            else:
                elevations.extend([None] * len(batch))
        
        if len(elevations) != grid_size ** 2:
            raise ValueError("Erro ao obter elevações para o grid")
        
        valid_elevations = [e for e in elevations if e is not None and e >= 0]
        if not valid_elevations:
            logger.warning("Nenhuma elevação válida, usando fallback")
            result = {'avg': 400.0, 'min': 200.0, 'max': 600.0, 'range': 400.0, 'accum_max': 1.0, 'points_sampled': 0}
            ELEVATION_CACHE[cache_key] = result
            return result
        
        dem = np.array(elevations).reshape((grid_size, grid_size))
        flow_dir = compute_flow_direction(dem)
        accum = compute_flow_accumulation(dem, flow_dir)
        
        avg = np.mean(valid_elevations)
        min_elev = np.min(valid_elevations)
        max_elev = np.max(valid_elevations)
        elevation_range = max_elev - min_elev
        accum_max = float(np.max(accum))
        
        result = {
            'avg': float(avg),
            'min': float(min_elev),
            'max': float(max_elev),
            'range': float(elevation_range),
            'accum_max': accum_max,
            'points_sampled': len(valid_elevations)
        }
        
        ELEVATION_CACHE[cache_key] = result
        logger.info(f"Elevação - Média: {avg:.1f}m, Accum Max: {accum_max:.1f}")
        return result
    except Exception as e:
        logger.error(f"Erro ao calcular elevação/acumulação: {e}")
        return {'avg': 400.0, 'min': 200.0, 'max': 600.0, 'range': 400.0, 'accum_max': 1.0, 'points_sampled': 0}

# ==================== GADM ====================
def download_and_read_gadm_json(country_code, level):
    cache_key = f"{country_code}_{level}"
    
    if cache_key in GADM_CACHE:
        logger.info(f"Usando dados GADM do cache: Level {level}")
        return GADM_CACHE[cache_key]
    
    json_url = f'https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_{country_code}_{level}.json.zip'
    logger.info(f"⬇ Baixando GeoJSON: {json_url}...")
    
    try:
        response = requests.get(json_url, timeout=60)
        response.raise_for_status()
        
        with ZipFile(BytesIO(response.content)) as zip_file:
            json_filename = zip_file.namelist()[0]
            with zip_file.open(json_filename) as json_file:
                gdf = gpd.read_file(json_file, driver='GeoJSON')
        
        GADM_CACHE[cache_key] = gdf
        logger.info(f"Dados GADM Level {level} armazenados em cache ({len(gdf)} features)")
        return gdf
        
    except Exception as e:
        logger.error(f"Erro ao baixar/processar GeoJSON: {e}")
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
    """Calcula inundação considerando elevação e acumulação de fluxo"""
    risk_factors = {'Muito Alto': 0.35, 'Alto': 0.20, 'Médio': 0.05, 'Baixo': -0.10}
    drainage_factor = {'Muito Alto': 0.9, 'Alto': 0.7, 'Médio': 0.5, 'Baixo': 0.3}
    
    risk_modifier = risk_factors.get(risk_level, 0)
    drainage = drainage_factor.get(risk_level, 0.5)
    
    if elevation_stats:
        avg_elevation = elevation_stats.get('avg', area_elevation)
        elevation_range = elevation_stats.get('range', 0)
        min_elevation = elevation_stats.get('min', area_elevation)
        accum_max = elevation_stats.get('accum_max', 1.0)
    else:
        avg_elevation = area_elevation
        elevation_range = 0
        min_elevation = area_elevation
        accum_max = 1.0
    
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
    
    accum_risk = min(0.3, 0.1 * np.log(accum_max + 1))
    adjusted_probability = flood_rate + risk_modifier + elevation_risk + terrain_risk + accum_risk
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
        'message': 'API de Simulação de Inundações - Angola (Com MariaDB)',
        'version': '4.0.0',
        'status': 'online',
        'database': 'MariaDB',
        'features': ['Dados GADM', 'Elevação Real', 'Sistema de Bairros', 'Histórico de Simulações'],
        'endpoints': {
            'health': '/api/health',
            'info': '/api/info',
            'provinces': '/api/provinces',
            'municipalities': '/api/municipalities?province=X',
            'bairros': '/api/bairros?municipality=X',
            'simulate': '/api/simulate (POST)',
            'history': '/api/history',
            'simulation_details': '/api/simulation/<id>',
            'elevation': '/api/elevation?lat=X&lon=Y'
        }
    })

@app.route('/api/health', methods=['GET'])
def health():
    logger.info("Health check realizado")
    
    try:
        provinces_count = len(get_provinces(db) or [])
        db_status = 'conectado'
    except:
        provinces_count = 0
        db_status = 'erro'
    
    return jsonify({
        'status': 'ok',
        'message': 'API está ativa com MariaDB',
        'timestamp': datetime.now().isoformat(),
        'database': db_status,
        'cache_status': {
            'gadm_cached': len(GADM_CACHE),
            'elevation_cached': len(ELEVATION_CACHE)
        },
        'data_counts': {
            'provinces': provinces_count
        }
    })

@app.route('/api/info', methods=['GET'])
def api_info():
    return jsonify({
        'name': 'API de Simulação de Inundações - Angola',
        'version': '4.0.0',
        'description': 'API completa com análise de elevação, bairros e persistência em MariaDB',
        'author': 'Sistema de Gestão de Desastres Naturais',
        'database': 'MariaDB',
        'elevation_service': 'Open-Elevation API (SRTM 90m)'
    })

@app.route('/api/provinces', methods=['GET'])
def api_get_provinces():
    logger.info("Listando províncias do banco")
    
    try:
        provinces = get_provinces(db)
        
        if not provinces:
            return jsonify({'success': False, 'error': 'Nenhuma província encontrada'}), 404
        
        # Buscar geometria do GADM
        gdf = download_and_read_gadm_json('AGO', 1)
        
        result = []
        for p in provinces:
            province_data = {
                'id': p['id'],
                'name': p['name'],
                'risk': p['risk'],
                'population': p['population'],
                'area': float(p['area'])
            }
            
            if gdf is not None:
                row = gdf[gdf['NAME_1'] == p['name']]
                if not row.empty:
                    centroid = row.iloc[0]['geometry'].centroid
                    province_data['lat'] = centroid.y
                    province_data['lon'] = centroid.x
            
            result.append(province_data)
        
        return jsonify({
            'success': True,
            'data': result,
            'count': len(result),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Erro ao listar províncias: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/municipalities', methods=['GET'])
def api_get_municipalities():
    province_name = request.args.get('province', 'Luanda')
    logger.info(f"Listando municípios para: {province_name}")
    
    try:
        # Buscar província no banco
        province = get_province_by_name(db, province_name)
        
        if not province:
            return jsonify({'success': True, 'data': [], 'count': 0})
        
        # Buscar municípios
        municipalities = get_municipalities(db, province['id'])
        
        # Buscar geometria do GADM
        gdf = download_and_read_gadm_json('AGO', 2)
        
        if gdf is not None:
            gdf = gdf[gdf['NAME_1'] == province_name]
        
        result = []
        for m in municipalities:
            mun_data = {
                'id': m['id'],
                'name': m['name'],
                'province': province_name,
                'risk': m['risk'],
                'population': m['population'],
                'area': float(m['area'])
            }
            
            if gdf is not None:
                row = gdf[gdf['NAME_2'] == m['name']]
                if row.empty:
                    # Tentar match alternativo (ex: Kilamba-Kiaxi vs Kilamba Kiaxi)
                    normalized = normalize_name(m['name'])
                    for idx, gadm_row in gdf.iterrows():
                        if normalize_name(gadm_row['NAME_2']) == normalized:
                            row = gdf.loc[[idx]]
                            break
                
                if not row.empty:
                    centroid = row.iloc[0]['geometry'].centroid
                    mun_data['lat'] = centroid.y
                    mun_data['lon'] = centroid.x
            
            result.append(mun_data)
        
        return jsonify({
            'success': True,
            'data': result,
            'count': len(result),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Erro ao listar municípios: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bairros', methods=['GET'])
def api_get_bairros():
    municipality_name = request.args.get('municipality', None)
    province_name = request.args.get('province', None)
    
    logger.info(f"Listando BAIRROS - Município: {municipality_name}")
    
    try:
        if not municipality_name or municipality_name == 'all':
            bairros = get_bairros(db)
        else:
            municipality = get_municipality_by_name(db, municipality_name)
            if not municipality:
                return jsonify({
                    'success': True,
                    'data': [],
                    'count': 0,
                    'message': f'Município {municipality_name} não encontrado'
                })
            
            bairros = get_bairros(db, municipality['id'])
        
        result = []
        for b in bairros:
            result.append({
                'id': b['id'],
                'name': b['name'],
                'municipality': b['municipality_name'],
                'province': b['province_name'],
                'population': b['population'],
                'type': b['type'],
                'risk': b['risk']
            })
        
        return jsonify({
            'success': True,
            'data': result,
            'count': len(result),
            'filter': {
                'municipality': municipality_name,
                'province': province_name
            },
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Erro ao listar bairros: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/elevation', methods=['GET'])
def api_get_elevation():
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
        
        logger.info(f"Simulação - Level: {level}, Province: {province}, Municipality: {municipality}, Bairro: {bairro}")
        
        # ===== SIMULAÇÃO DE BAIRROS (do banco) =====
        if level == 'bairro':
            logger.info(f"SIMULAÇÃO DE BAIRROS INICIADA")
            
            if municipality == 'all' or not municipality:
                return jsonify({
                    'success': False,
                    'error': 'Para simular bairros, você deve selecionar um município específico'
                }), 400
            
            # Buscar município
            mun_obj = get_municipality_by_name(db, municipality)
            if not mun_obj:
                return jsonify({
                    'success': False,
                    'error': f'Município {municipality} não encontrado'
                }), 404
            
            # Buscar bairros
            bairros_list = get_bairros(db, mun_obj['id'])
            
            # Filtrar bairro específico se necessário
            if bairro and bairro != 'all':
                bairros_list = [b for b in bairros_list if b['name'] == bairro]
                if not bairros_list:
                    return jsonify({
                        'success': False,
                        'error': f'Bairro {bairro} não encontrado em {municipality}'
                    }), 404
            
            # Buscar geometria (GADM)
            gdf_level3 = download_and_read_gadm_json('AGO', 3)
            
            results = []
            features = []
            
            for bairro_data in bairros_list:
                risk = bairro_data['risk']
                pop = bairro_data['population']
                bairro_name = bairro_data['name']
                
                logger.info(f"Processando bairro: {bairro_name}")
                
                # Buscar geometria
                found_geom = None
                elevation_stats = None
                
                if gdf_level3 is not None:
                    normalized_mun = normalize_name(municipality)
                    normalized_bairro = normalize_name(bairro_name)
                    
                    gdf_filtered = gdf_level3[gdf_level3['NAME_2'].apply(normalize_name) == normalized_mun]
                    
                    for idx, row in gdf_filtered.iterrows():
                        commune_normalized = normalize_name(row['NAME_3'])
                        
                        if commune_normalized == normalized_bairro or normalized_bairro in commune_normalized:
                            found_geom = row['geometry']
                            elevation_stats = get_region_elevation_stats(found_geom)
                            logger.info(f"Geometria encontrada para {bairro_name} - Elevação: {elevation_stats['avg']:.1f}m")
                            break
                
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
            
            flooded_count = sum(1 for r in results if r['flooded'])
            total_affected = sum(r['affectedPopulation'] for r in results)
            
            geojson_data = {
                'type': 'FeatureCollection',
                'features': features
            }
            
            import json
            geojson = json.dumps(geojson_data)
            
            # Salvar no histórico
            simulation_data = {
                'level': 'bairro',
                'province': province,
                'municipality': municipality,
                'bairro': bairro,
                'flood_rate': flood_rate * 100,
                'water_level': water_level_input,
                'flooded_count': flooded_count,
                'total_affected': total_affected,
                'total_analyzed': len(results),
                'avg_risk': (flooded_count / len(results) * 100) if results else 0
            }
            
            simulation_id = save_simulation(db, simulation_data)
            save_simulation_results(db, simulation_id, results)
            
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
                'simulation_id': simulation_id,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Simulação de bairros concluída e salva (ID: {simulation_id})")
            return jsonify(response)
        
        # ===== SIMULAÇÃO DE PROVÍNCIAS/MUNICÍPIOS =====
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
        
        logger.info(f"Processando {len(gdf)} regiões...")
        
        for i, row in gdf.iterrows():
            prov = row['NAME_1']
            name = row[f'NAME_{level_num}']
            geometry = row['geometry']
            
            elevation_stats = get_region_elevation_stats(geometry)
            avg_elevation = elevation_stats['avg']
            
            # Buscar dados estáticos do banco
            if level == 'province':
                static = get_province_by_name(db, name)
            else:
                static = get_municipality_by_name(db, name)
            
            if static:
                risk = static['risk']
                pop = static['population']
            else:
                continue
            
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
        
        # Salvar no histórico
        simulation_data = {
            'level': level,
            'province': province,
            'municipality': municipality if level == 'municipality' else None,
            'bairro': None,
            'flood_rate': flood_rate * 100,
            'water_level': water_level_input,
            'flooded_count': flooded_count,
            'total_affected': total_affected,
            'total_analyzed': len(results),
            'avg_risk': (flooded_count / len(results) * 100) if results else 0
        }
        
        simulation_id = save_simulation(db, simulation_data)
        save_simulation_results(db, simulation_id, results)
        
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
            'simulation_id': simulation_id,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Simulação concluída e salva (ID: {simulation_id}) - {flooded_count} de {len(results)} áreas inundadas")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Erro na simulação: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/history', methods=['GET'])
def api_simulation_history():
    """Retorna histórico de simulações"""
    try:
        limit = int(request.args.get('limit', 50))
        history = get_simulation_history(db, limit)
        
        return jsonify({
            'success': True,
            'data': history,
            'count': len(history),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Erro ao buscar histórico: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == "__main__":
    print("=" * 70)
    print("API de Simulação de Inundações - Angola v4.0 (MariaDB)")
    print("=" * 70)

    try:
        provinces = get_provinces(db) or []
        print(f"✓ Banco de Dados: MariaDB conectado")
        print(f"✓ Províncias: {len(provinces)}")
    except Exception as e:
        print("✗ Erro ao conectar ao banco:", e)

    print("Servidor: http://0.0.0.0:5000")
    print("Docs: http://localhost:5000/api/info")
    print("Status: http://localhost:5000/api/health")
    print("=" * 70)

    app.run(host="0.0.0.0", port=5000, debug=True)
