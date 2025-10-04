from flask import Flask, request, jsonify
from flask_cors import CORS
import random
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Permite requisições de qualquer origem

# ==================== DADOS COMPLETOS DE ANGOLA ====================

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

# ==================== ROTAS ====================

@app.route('/', methods=['GET'])
def home():
    """Página inicial da API"""
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
    """Verifica se a API está funcionando"""
    logger.info("Health check realizado")
    return jsonify({
        'status': 'ok',
        'message': 'API de Simulação de Inundações está ativa',
        'timestamp': datetime.now().isoformat(),
        'uptime': 'online'
    })

@app.route('/api/info', methods=['GET'])
def api_info():
    """Retorna informações detalhadas sobre a API"""
    return jsonify({
        'name': 'API de Simulação de Inundações - Angola',
        'version': '2.0.0',
        'description': 'API completa para simulação e análise de inundações em Angola',
        'author': 'Sistema de Gestão de Desastres Naturais',
        'endpoints': {
            'GET /api/health': {
                'description': 'Verifica status da API',
                'parameters': None
            },
            'GET /api/provinces': {
                'description': 'Lista todas as 18 províncias de Angola',
                'parameters': None
            },
            'GET /api/municipalities': {
                'description': 'Lista municípios',
                'parameters': 'province (opcional) - filtra por província'
            },
            'GET /api/districts': {
                'description': 'Lista bairros/distritos',
                'parameters': 'municipality (opcional) - filtra por município'
            },
            'POST /api/simulate': {
                'description': 'Executa simulação de inundação',
                'parameters': {
                    'level': 'province | municipality | district',
                    'floodRate': 'número entre 0-100',
                    'province': 'nome da província (opcional)',
                    'municipality': 'nome do município (opcional)',
                    'district': 'nome do bairro (opcional)'
                }
            }
        },
        'data_available': {
            'provinces': len(PROVINCES),
            'municipalities': sum(len(m) for m in MUNICIPALITIES.values()),
            'districts': sum(len(d) for d in DISTRICTS.values())
        }
    })

@app.route('/api/provinces', methods=['GET'])
def get_provinces():
    """Retorna todas as províncias"""
    logger.info("Listando províncias")
    return jsonify({
        'success': True,
        'data': PROVINCES,
        'count': len(PROVINCES),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/municipalities', methods=['GET'])
def get_municipalities():
    """Retorna municípios (todos ou filtrados por província)"""
    province = request.args.get('province', None)
    
    logger.info(f"Listando municípios - Província: {province}")
    
    if province and province != 'all' and province in MUNICIPALITIES:
        # Retorna apenas municípios da província especificada
        municipalities = [
            {**m, 'province': province} 
            for m in MUNICIPALITIES[province]
        ]
    elif province == 'all' or not province:
        # Retorna todos os municípios
        municipalities = []
        for prov, munics in MUNICIPALITIES.items():
            for m in munics:
                municipalities.append({**m, 'province': prov})
    else:
        # Província não encontrada
        municipalities = []
    
    return jsonify({
        'success': True,
        'data': municipalities,
        'count': len(municipalities),
        'filter': {'province': province} if province else None,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/districts', methods=['GET'])
def get_districts():
    """Retorna bairros/distritos (todos ou filtrados por município)"""
    municipality = request.args.get('municipality', None)
    
    logger.info(f"Listando distritos - Município: {municipality}")
    
    if municipality and municipality != 'all' and municipality in DISTRICTS:
        # Retorna apenas distritos do município especificado
        districts = [
            {**d, 'municipality': municipality} 
            for d in DISTRICTS[municipality]
        ]
    elif municipality == 'all' or not municipality:
        # Retorna todos os distritos
        districts = []
        for munic, dists in DISTRICTS.items():
            for d in dists:
                districts.append({**d, 'municipality': munic})
    else:
        # Município não encontrado
        districts = []
    
    return jsonify({
        'success': True,
        'data': districts,
        'count': len(districts),
        'filter': {'municipality': municipality} if municipality else None,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/simulate', methods=['POST'])
def simulate_flood():
    """Executa a simulação de inundação"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados não fornecidos'
            }), 400
        
        # Parâmetros da simulação
        level = data.get('level', 'province')
        flood_rate = float(data.get('floodRate', 50)) / 100
        province = data.get('province', 'all')
        municipality = data.get('municipality', 'all')
        district = data.get('district', 'all')
        
        logger.info(f"Simulação iniciada - Level: {level}, Rate: {flood_rate*100}%, Province: {province}")
        
        results = []
        
        # Simulação por Província
        if level == 'province':
            data_list = PROVINCES if province == 'all' else [p for p in PROVINCES if p['name'] == province]
            
            for item in data_list:
                is_flooded = random.random() < flood_rate
                
                # Calcular nível de água e severidade
                if is_flooded:
                    water_level = round(random.uniform(0.5, 3.5), 2)  # 0.5m a 3.5m
                    
                    # Determinar severidade baseada no nível de água
                    if water_level < 1.0:
                        severity = 'Leve'
                        recovery_days = random.randint(3, 7)
                    elif water_level < 2.0:
                        severity = 'Moderada'
                        recovery_days = random.randint(7, 15)
                    elif water_level < 3.0:
                        severity = 'Grave'
                        recovery_days = random.randint(15, 30)
                    else:
                        severity = 'Crítica'
                        recovery_days = random.randint(30, 60)
                    
                    affected_comunas = random.randint(5, 20)
                    affected_population = int(item['population'] * random.uniform(0.1, 0.3))
                else:
                    water_level = 0
                    severity = 'Nenhuma'
                    recovery_days = 0
                    affected_comunas = 0
                    affected_population = 0
                
                results.append({
                    **item,
                    'flooded': is_flooded,
                    'waterLevel': water_level,
                    'severity': severity,
                    'recoveryDays': recovery_days,
                    'affectedComunas': affected_comunas,
                    'affectedPopulation': affected_population
                })
        
        # Simulação por Município
        elif level == 'municipality':
            if province != 'all' and province in MUNICIPALITIES:
                # Municípios apenas da província selecionada
                data_list = MUNICIPALITIES[province]
                for item in data_list:
                    is_flooded = random.random() < flood_rate
                    affected_districts = random.randint(2, 10) if is_flooded else 0
                    affected_population = int(item['population'] * random.uniform(0.1, 0.4)) if is_flooded else 0
                    
                    results.append({
                        **item,
                        'province': province,
                        'flooded': is_flooded,
                        'affectedDistricts': affected_districts,
                        'affectedPopulation': affected_population
                    })
            else:
                # Todos os municípios
                for prov, munics in MUNICIPALITIES.items():
                    for item in munics:
                        is_flooded = random.random() < flood_rate
                        affected_districts = random.randint(2, 10) if is_flooded else 0
                        affected_population = int(item['population'] * random.uniform(0.1, 0.4)) if is_flooded else 0
                        
                        results.append({
                            **item,
                            'province': prov,
                            'flooded': is_flooded,
                            'affectedDistricts': affected_districts,
                            'affectedPopulation': affected_population
                        })
        
        # Simulação por Bairro/Distrito
        elif level == 'district':
            if municipality != 'all' and municipality in DISTRICTS:
                # Distritos apenas do município selecionado
                data_list = DISTRICTS[municipality]
                for item in data_list:
                    is_flooded = random.random() < flood_rate
                    affected_population = int(item['population'] * random.uniform(0.2, 0.5)) if is_flooded else 0
                    
                    results.append({
                        **item,
                        'municipality': municipality,
                        'flooded': is_flooded,
                        'affectedPopulation': affected_population
                    })
            else:
                # Todos os distritos
                for munic, dists in DISTRICTS.items():
                    for item in dists:
                        is_flooded = random.random() < flood_rate
                        affected_population = int(item['population'] * random.uniform(0.2, 0.5)) if is_flooded else 0
                        
                        results.append({
                            **item,
                            'municipality': munic,
                            'flooded': is_flooded,
                            'affectedPopulation': affected_population
                        })
        else:
            return jsonify({
                'success': False,
                'error': 'Nível inválido. Use: province, municipality ou district'
            }), 400
        
        # Calcular estatísticas
        flooded_count = sum(1 for r in results if r['flooded'])
        total_affected = sum(r['affectedPopulation'] for r in results)
        
        response = {
            'success': True,
            'data': results,
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
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint não encontrado',
        'message': str(error)
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Erro interno do servidor',
        'message': str(error)
    }), 500

# ==================== MAIN ====================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🌊 API de Simulação de Inundações - Angola v2.0")
    print("="*60)
    print(f"📡 Servidor iniciado em: http://0.0.0.0:5000")
    print(f"📚 Documentação: http://localhost:5000/api/info")
    print(f"💚 Status: http://localhost:5000/api/health")
    print(f"📊 Províncias: {len(PROVINCES)}")
    print(f"🏛️ Municípios: {sum(len(m) for m in MUNICIPALITIES.values())}")
    print(f"🏘️ Bairros: {sum(len(d) for d in DISTRICTS.values())}")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
