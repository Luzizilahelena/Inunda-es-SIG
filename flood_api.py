import os
os.system("pip install -r requirements.txt")
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime
import logging
import requests
import math
import geopandas as gpd
from zipfile import ZipFile
from io import BytesIO
import numpy as np
from shapely.geometry import Point

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

# Risco por defeito para bairros sem correspondência estática
BAIRRO_RISK_DEFAULT = 'Médio'
BAIRRO_POP_DEFAULT  = 50000

# ==================== CARREGAMENTO DO GEOJSON DE BAIRROS ====================
# O ficheiro bairros_com_municipio.geojson deve ser gerado pelo script
# enrich_bairros.py — contém o campo "municipality" correcto para cada bairro.
# Fallback para bairros.geojson original caso o enriquecido não exista.
_BAIRROS_FILE = (
    "bairros_com_municipio.geojson"
    if os.path.exists("bairros_com_municipio.geojson")
    else "bairros.geojson"
)
logger.info(f"A carregar bairros de: {_BAIRROS_FILE}")
BAIRROS_GEO = gpd.read_file(_BAIRROS_FILE)

# Normalizar o nome do campo de município:
# O Overpass gera "municipio"; o enriquecido gera "municipality".
# Unificamos tudo em "municipality".
if "municipality" not in BAIRROS_GEO.columns:
    if "municipio" in BAIRROS_GEO.columns:
        BAIRROS_GEO = BAIRROS_GEO.rename(columns={"municipio": "municipality"})
    else:
        # Se não existir nenhum campo, atribuir valor vazio para não quebrar
        BAIRROS_GEO["municipality"] = ""

# Garantir que existe campo "risk" e "population" (podem não existir no GeoJSON do Overpass)
if "risk" not in BAIRROS_GEO.columns:
    BAIRROS_GEO["risk"] = BAIRRO_RISK_DEFAULT
if "population" not in BAIRROS_GEO.columns:
    BAIRROS_GEO["population"] = BAIRRO_POP_DEFAULT

logger.info(f"Bairros carregados: {len(BAIRROS_GEO)} features | "
            f"municípios únicos: {BAIRROS_GEO['municipality'].nunique()}")


# ==================== CACHES ====================
GADM_CACHE = {}
ELEVATION_CACHE = {}


# ==================== NORMALIZAÇÃO ====================
def normalize_name(name):
    import unicodedata
    if not name:
        return ""
    name = unicodedata.normalize('NFD', str(name))
    name = ''.join(char for char in name if unicodedata.category(char) != 'Mn')
    name = name.replace(' ', '').replace('-', '').replace('_', '').lower()
    return name


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
            logger.info(f"Elevações obtidas: {len(elevations)} pontos")
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
            'avg': 70.0, 'min': 50.0, 'max': 90.0, 'range': 40.0, 'points_sampled': 0
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


# ==================== CÁLCULO DE INUNDAÇÃO ====================
def calculate_flood_risk(risk_level, flood_rate, water_level_input, area_elevation=0, elevation_stats=None):
    risk_factors    = {'Muito Alto': 0.35, 'Alto': 0.20, 'Médio': 0.05, 'Baixo': -0.10}
    drainage_factor = {'Muito Alto': 0.9,  'Alto': 0.7,  'Médio': 0.5,  'Baixo': 0.3}

    risk_modifier = risk_factors.get(risk_level, 0)
    drainage = drainage_factor.get(risk_level, 0.5)

    avg_elevation  = elevation_stats.get('avg', area_elevation) if elevation_stats else area_elevation
    elevation_range = elevation_stats.get('range', 0) if elevation_stats else 0
    min_elevation  = elevation_stats['min'] if elevation_stats else area_elevation

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

    score = (
        flood_rate * 2.0 +
        risk_modifier * 1.5 +
        elevation_risk * 1.2 +
        terrain_risk * 1.0
    )

    adjusted_probability = 1 / (1 + math.exp(-score))

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
        'version': '4.2.0',
        'status': 'online',
        'features': ['Dados GADM', 'Elevação Real por Ponto', 'Bairros GeoJSON com município correcto'],
        'endpoints': {
            'health':         '/api/health',
            'info':           '/api/info',
            'provinces':      '/api/provinces',
            'municipalities': '/api/municipalities?province=X',
            'bairros':        '/api/bairros?province=X&municipality=X',
            'simulate':       '/api/simulate (POST)',
            'elevation':      '/api/elevation?lat=X&lon=Y',
        }
    })


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'message': 'API activa',
        'timestamp': datetime.now().isoformat(),
        'cache_status': {
            'gadm_cached': len(GADM_CACHE),
            'elevation_cached': len(ELEVATION_CACHE),
        },
        'bairros_loaded': len(BAIRROS_GEO),
        'bairros_file': _BAIRROS_FILE,
    })


@app.route('/api/info', methods=['GET'])
def api_info():
    return jsonify({
        'name': 'API de Simulação de Inundações - Angola',
        'version': '4.2.0',
        'data_available': {
            'provinces':     len(PROVINCES),
            'municipalities': sum(len(m) for m in MUNICIPALITIES.values()),
            'bairros':       len(BAIRROS_GEO),
            'bairros_file':  _BAIRROS_FILE,
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

    return jsonify({'success': True, 'data': provinces, 'count': len(provinces),
                    'timestamp': datetime.now().isoformat()})


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
        'Belas':         'Belas',
        'Cacuaco':       'Cacuaco',
        'Cazenga':       'Cazenga',
        'Viana':         'Viana',
        'Kilamba-Kiaxi': 'Kilamba Kiaxi',
        'Talatona':      'Talatona',
        'Maianga':       'Maianga',
        'Rangel':        'Rangel',
        'Ingombota':     'Ingombota',
        'Samba':         'Samba',
        'Sambizanga':    'Sambizanga',
    }

    municipalities = []
    for _, row in gdf.iterrows():
        gadm_name = row['NAME_2']
        static_name = gadm_to_static.get(gadm_name)
        if static_name:
            static_mun = next((m for m in static_muns if m['name'] == static_name), None)
            if static_mun:
                centroid = row.geometry.centroid
                municipalities.append({
                    'id': static_mun['id'], 'name': static_name, 'province': 'Luanda',
                    'risk': static_mun['risk'], 'population': static_mun['population'],
                    'area': static_mun['area'], 'lat': centroid.y, 'lon': centroid.x,
                })

    # Municípios que o GADM 4.1 ainda não tem como polígonos separados
    fallbacks = [
        {'id': 12, 'name': 'Hoji Ya Henda', 'lat': -8.808,  'lon': 13.294,  'risk': 'Muito Alto', 'population': 700000,  'area': 30},
        {'id': 13, 'name': 'Camama',         'lat': -8.945,  'lon': 13.268,  'risk': 'Alto',       'population': 320000,  'area': 45},
        {'id': 14, 'name': 'Kilamba',        'lat': -8.935,  'lon': 13.295,  'risk': 'Médio',      'population': 250000,  'area': 55},
        {'id': 15, 'name': 'Mulenvos',       'lat': -8.781,  'lon': 13.269,  'risk': 'Alto',       'population': 180000,  'area': 20},
    ]
    for fb in fallbacks:
        if not any(m['name'] == fb['name'] for m in municipalities):
            municipalities.append({
                'id': fb['id'], 'name': fb['name'], 'province': 'Luanda',
                'risk': fb['risk'], 'population': fb['population'],
                'area': fb['area'], 'lat': fb['lat'], 'lon': fb['lon'],
            })

    return jsonify({'success': True, 'data': municipalities, 'count': len(municipalities),
                    'timestamp': datetime.now().isoformat()})


# ==================== ROTA DE BAIRROS (CORRIGIDA) ====================
@app.route('/api/bairros', methods=['GET'])
def get_bairros():
    municipality = request.args.get('municipality', None)
    province     = request.args.get('province', None)

    # ── Sem filtro: devolve todos os bairros ──────────────────────────────────
    if not municipality or municipality == 'all':
        result = []
        for _, row in BAIRROS_GEO.iterrows():
            name = row.get('name')
            if not name:
                continue
            geom = row.geometry
            if geom is None:
                continue
            # Suporte a Point e Polygon/MultiPolygon
            if geom.geom_type == 'Point':
                lat, lon = geom.y, geom.x
            else:
                c = geom.centroid
                lat, lon = c.y, c.x
            result.append({
                'id':           row.name,          # índice do GeoDataFrame
                'name':         name,
                'municipality': row.get('municipality', ''),
                'risk':         row.get('risk', BAIRRO_RISK_DEFAULT),
                'population':   int(row.get('population', BAIRRO_POP_DEFAULT)),
                'lat':          lat,
                'lon':          lon,
            })
        return jsonify({'success': True, 'data': result, 'count': len(result),
                        'timestamp': datetime.now().isoformat()})

    # ── Com filtro de município ───────────────────────────────────────────────
    norm_mun = normalize_name(municipality)

    # Filtrar pelo campo "municipality" do GeoDataFrame
    mask = BAIRROS_GEO['municipality'].apply(
        lambda v: normalize_name(v) == norm_mun
    )
    subset = BAIRROS_GEO[mask]

    if subset.empty:
        logger.warning(f"Nenhum bairro encontrado para município: {municipality} (normalizado: {norm_mun})")
        # Listar municípios disponíveis para ajudar no debug
        available = sorted(BAIRROS_GEO['municipality'].dropna().unique().tolist())
        return jsonify({
            'success': True,
            'data': [],
            'count': 0,
            'message': f'Nenhum bairro cadastrado para "{municipality}"',
            'available_municipalities': available,
            'timestamp': datetime.now().isoformat()
        })

    # Filtro opcional por bairro específico
    bairro_filter = request.args.get('bairro', 'all')
    if bairro_filter and bairro_filter != 'all':
        subset = subset[subset['name'] == bairro_filter]
        if subset.empty:
            return jsonify({'success': False,
                            'error': f'Bairro "{bairro_filter}" não encontrado em {municipality}'}), 404

    result = []
    for _, row in subset.iterrows():
        name = row.get('name')
        if not name:
            continue
        geom = row.geometry
        if geom is None:
            continue
        if geom.geom_type == 'Point':
            lat, lon = geom.y, geom.x
        else:
            c = geom.centroid
            lat, lon = c.y, c.x

        entry = {
            'id':           row.name,
            'name':         name,
            'municipality': row.get('municipality', municipality),
            'risk':         row.get('risk', BAIRRO_RISK_DEFAULT),
            'population':   int(row.get('population', BAIRRO_POP_DEFAULT)),
            'lat':          lat,
            'lon':          lon,
        }
        if province:
            entry['province'] = province
        result.append(entry)

    logger.info(f"Bairros devolvidos para {municipality}: {len(result)}")
    return jsonify({
        'success': True,
        'data':    result,
        'count':   len(result),
        'filter':  {'municipality': municipality, 'province': province},
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/elevation', methods=['GET'])
def get_elevation():
    try:
        lat = float(request.args.get('lat'))
        lon = float(request.args.get('lon'))
        elevations = get_elevation_batch([(lat, lon)])
        if elevations:
            return jsonify({'success': True, 'latitude': lat, 'longitude': lon,
                            'elevation': elevations[0], 'unit': 'meters'})
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

        level            = data.get('level', 'province')
        flood_rate       = float(data.get('floodRate', 50)) / 100
        water_level_raw  = data.get('waterLevel')
        water_level_input = float(water_level_raw) if water_level_raw is not None else None

        province     = data.get('province', 'all')
        municipality = data.get('municipality', 'all')
        bairro_sel   = data.get('bairro', 'all')

        logger.info(f"Simulação — level={level} province={province} municipality={municipality} bairro={bairro_sel}")

        # ============================================================
        # SIMULAÇÃO DE BAIRROS
        # ============================================================
        if level == 'bairro':

            if not municipality or municipality == 'all':
                return jsonify({'success': False,
                                'error': 'Seleccione um município específico para simular bairros'}), 400

            norm_mun = normalize_name(municipality)
            mask = BAIRROS_GEO['municipality'].apply(
                lambda v: normalize_name(v) == norm_mun
            )
            subset = BAIRROS_GEO[mask]

            if subset.empty:
                available = sorted(BAIRROS_GEO['municipality'].dropna().unique().tolist())
                return jsonify({
                    'success': False,
                    'error': f'Nenhum bairro cadastrado para o município "{municipality}"',
                    'available_municipalities': available
                }), 404

            if bairro_sel and bairro_sel != 'all':
                subset = subset[subset['name'] == bairro_sel]
                if subset.empty:
                    return jsonify({'success': False,
                                    'error': f'Bairro "{bairro_sel}" não encontrado em {municipality}'}), 404
                logger.info(f"Simulando apenas o bairro: {bairro_sel}")
            else:
                logger.info(f"Simulando todos os {len(subset)} bairros de {municipality}")

            results  = []
            features = []

            for _, bairro_row in subset.iterrows():
                bairro_name = bairro_row.get('name')
                if not bairro_name:
                    continue

                risk = bairro_row.get('risk', BAIRRO_RISK_DEFAULT)
                pop  = int(bairro_row.get('population', BAIRRO_POP_DEFAULT))
                geom = bairro_row.geometry

                if geom is None:
                    continue

                if geom.geom_type == 'Point':
                    b_lat, b_lon = geom.y, geom.x
                else:
                    c = geom.centroid
                    b_lat, b_lon = c.y, c.x

                elevation_stats = get_region_elevation_stats(geom)
                avg_elevation   = elevation_stats['avg']

                logger.info(f"Bairro {bairro_name}: lat={b_lat:.4f} lon={b_lon:.4f} elev={avg_elevation:.1f}m")

                is_flooded, wl, severity, recovery_days = calculate_flood_risk(
                    risk, flood_rate, water_level_input, avg_elevation, elevation_stats
                )

                affected_population = 0
                if is_flooded:
                    impact_factor = min(wl / 20.0, 0.7)
                    affected_population = int(pop * impact_factor)

                result_data = {
                    'name':               bairro_name,
                    'municipality':       municipality,
                    'province':           province if province != 'all' else 'Luanda',
                    'flooded':            is_flooded,
                    'waterLevel':         wl,
                    'severity':           severity,
                    'recoveryDays':       recovery_days,
                    'affectedPopulation': affected_population,
                    'totalPopulation':    pop,
                    'risk':               risk,
                    'elevation':          round(avg_elevation, 1),
                    'elevation_min':      round(elevation_stats['min'], 1),
                    'elevation_max':      round(elevation_stats['max'], 1),
                    'lat':                b_lat,
                    'lon':                b_lon,
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

            flooded_count  = sum(1 for r in results if r['flooded'])
            total_affected = sum(r['affectedPopulation'] for r in results)

            geojson = {'type': 'FeatureCollection', 'features': features}

            return jsonify({
                'success': True,
                'data':    results,
                'geojson': geojson,
                'statistics': {
                    'floodedCount': flooded_count,
                    'totalAffected': total_affected,
                    'totalBairros':  len(results),
                    'avgRisk': (flooded_count / len(results) * 100) if results else 0,
                },
                'parameters': {
                    'level':          'bairro',
                    'floodRate':      flood_rate * 100,
                    'province':       province,
                    'municipality':   municipality,
                    'bairro':         bairro_sel,
                    'elevation_used': True,
                },
                'timestamp': datetime.now().isoformat(),
            })

        # ============================================================
        # SIMULAÇÃO DE PROVÍNCIAS / MUNICÍPIOS
        # ============================================================
        level_map = {'province': 1, 'municipality': 2}
        level_num = level_map.get(level)
        if level_num is None:
            return jsonify({'success': False,
                            'error': 'Nível inválido. Use: province, municipality ou bairro'}), 400

        gdf = download_and_read_gadm_json('AGO', level_num)
        if gdf is None:
            return jsonify({'success': False, 'error': 'Erro ao carregar dados do GADM'}), 500

        if province != 'all' and province != 'Luanda':
            return jsonify({'success': True, 'data': [], 'count': 0,
                            'message': 'Apenas Luanda disponível'})

        if province != 'all':
            gdf = gdf[gdf['NAME_1'] == province]
        if level == 'municipality' and municipality != 'all':
            gdf = gdf[gdf['NAME_2'] == municipality]

        gdf['name']               = gdf[f'NAME_{level_num}']
        gdf['flooded']            = False
        gdf['waterLevel']         = 0.0
        gdf['severity']           = 'Nenhuma'
        gdf['recoveryDays']       = 0
        gdf['affectedPopulation'] = 0
        gdf['elevation']          = 0.0

        for i, row in gdf.iterrows():
            prov = row['NAME_1']
            name = row[f'NAME_{level_num}']
            elevation_stats = get_region_elevation_stats(row['geometry'])
            avg_elevation   = elevation_stats['avg']

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

            gdf.at[i, 'flooded']            = is_flooded
            gdf.at[i, 'waterLevel']         = wl
            gdf.at[i, 'severity']           = severity
            gdf.at[i, 'recoveryDays']       = recovery_days
            gdf.at[i, 'affectedPopulation'] = affected_population
            gdf.at[i, 'elevation']          = round(avg_elevation, 1)

        gdf_copy        = gdf.copy()
        gdf_copy['lat'] = gdf.geometry.centroid.y
        gdf_copy['lon'] = gdf.geometry.centroid.x
        results  = gdf_copy.drop(columns=['geometry']).to_dict('records')
        geojson  = gdf.to_json()
        flooded_count  = len(gdf[gdf['flooded']])
        total_affected = sum(item['affectedPopulation'] for item in results)

        return jsonify({
            'success': True,
            'data':    results,
            'geojson': geojson,
            'statistics': {
                'floodedCount': flooded_count,
                'totalAffected': total_affected,
                'totalItems':    len(results),
                'avgRisk': (flooded_count / len(results) * 100) if results else 0,
            },
            'parameters': {
                'level':          level,
                'floodRate':      flood_rate * 100,
                'province':       province,
                'municipality':   municipality,
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
    print("API de Simulação de Inundações — Angola v4.2")
    print("=" * 70)
    print(f"Servidor  : http://0.0.0.0:5000")
    print(f"Províncias: {len(PROVINCES)}")
    print(f"Municípios: {sum(len(m) for m in MUNICIPALITIES.values())}")
    print(f"Bairros   : {len(BAIRROS_GEO)}")
    print(f"Ficheiro  : {_BAIRROS_FILE}")
    print("=" * 70 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)