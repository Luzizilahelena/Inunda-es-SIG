import pymysql
from pymysql.cursors import DictCursor
from config import DB_CONFIG
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.connection = None
    
    def connect(self):
        """Estabelece conexão com o banco"""
        try:
            self.connection = pymysql.connect(
                host=DB_CONFIG['host'],
                port=DB_CONFIG['port'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                database=DB_CONFIG['database'],
                charset=DB_CONFIG['charset'],
                cursorclass=DictCursor,
                autocommit=False
            )
            logger.info("✓ Conexão com MariaDB estabelecida")
            return self.connection
        except pymysql.Error as e:
            logger.error(f"✗ Erro ao conectar ao MariaDB: {e}")
            raise
    
    def close(self):
        """Fecha conexão com o banco"""
        if self.connection:
            self.connection.close()
            logger.info("Conexão com MariaDB fechada")
    
    def execute_query(self, query, params=None):
        """Executa query SELECT e retorna resultados"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params or ())
                return cursor.fetchall()
        except pymysql.Error as e:
            logger.error(f"Erro ao executar query: {e}")
            return None
    
    def execute_update(self, query, params=None):
        """Executa INSERT/UPDATE/DELETE"""
        try:
            with self.connection.cursor() as cursor:
                affected = cursor.execute(query, params or ())
                self.connection.commit()
                return affected
        except pymysql.Error as e:
            self.connection.rollback()
            logger.error(f"Erro ao executar update: {e}")
            return 0
    
    def execute_many(self, query, data_list):
        """Executa múltiplas inserções"""
        try:
            with self.connection.cursor() as cursor:
                affected = cursor.executemany(query, data_list)
                self.connection.commit()
                return affected
        except pymysql.Error as e:
            self.connection.rollback()
            logger.error(f"Erro ao executar batch: {e}")
            return 0

# Funções auxiliares para acesso aos dados

def get_provinces(db):
    """Retorna todas as províncias"""
    query = "SELECT * FROM provinces ORDER BY name"
    return db.execute_query(query)

def get_municipalities(db, province_id=None):
    """Retorna municípios (opcionalmente filtrados por província)"""
    if province_id:
        query = """
            SELECT m.*, p.name as province_name 
            FROM municipalities m
            JOIN provinces p ON m.province_id = p.id
            WHERE m.province_id = %s
            ORDER BY m.name
        """
        return db.execute_query(query, (province_id,))
    else:
        query = """
            SELECT m.*, p.name as province_name 
            FROM municipalities m
            JOIN provinces p ON m.province_id = p.id
            ORDER BY m.name
        """
        return db.execute_query(query)

def get_bairros(db, municipality_id=None):
    """Retorna bairros (opcionalmente filtrados por município)"""
    if municipality_id:
        query = """
            SELECT b.*, m.name as municipality_name, p.name as province_name
            FROM bairros b
            JOIN municipalities m ON b.municipality_id = m.id
            JOIN provinces p ON m.province_id = p.id
            WHERE b.municipality_id = %s
            ORDER BY b.name
        """
        return db.execute_query(query, (municipality_id,))
    else:
        query = """
            SELECT b.*, m.name as municipality_name, p.name as province_name
            FROM bairros b
            JOIN municipalities m ON b.municipality_id = m.id
            JOIN provinces p ON m.province_id = p.id
            ORDER BY b.name
        """
        return db.execute_query(query)

def get_municipality_by_name(db, name):
    """Busca município por nome"""
    query = "SELECT * FROM municipalities WHERE name = %s LIMIT 1"
    result = db.execute_query(query, (name,))
    return result[0] if result else None

def get_province_by_name(db, name):
    """Busca província por nome"""
    query = "SELECT * FROM provinces WHERE name = %s LIMIT 1"
    result = db.execute_query(query, (name,))
    return result[0] if result else None

def save_simulation(db, simulation_data):
    """Salva uma simulação no histórico"""
    query = """
        INSERT INTO simulations 
        (level, province, municipality, bairro, flood_rate, water_level, 
         flooded_count, total_affected, total_analyzed, avg_risk)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        simulation_data['level'],
        simulation_data.get('province'),
        simulation_data.get('municipality'),
        simulation_data.get('bairro'),
        simulation_data['flood_rate'],
        simulation_data.get('water_level'),
        simulation_data['flooded_count'],
        simulation_data['total_affected'],
        simulation_data['total_analyzed'],
        simulation_data['avg_risk']
    )
    
    db.execute_update(query, params)
    
    with db.connection.cursor() as cursor:
        cursor.execute("SELECT LAST_INSERT_ID() as id")
        return cursor.fetchone()['id']

def save_simulation_results(db, simulation_id, results):
    """Salva resultados detalhados da simulação"""
    query = """
        INSERT INTO simulation_results
        (simulation_id, area_name, area_type, flooded, water_level, severity,
         recovery_days, affected_population, total_population, elevation,
         elevation_min, elevation_max)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    data_list = []
    for r in results:
        data_list.append((
            simulation_id,
            r['name'],
            r.get('type', 'unknown'),
            r['flooded'],
            r['waterLevel'],
            r['severity'],
            r['recoveryDays'],
            r['affectedPopulation'],
            r.get('totalPopulation', 0),
            r.get('elevation'),
            r.get('elevation_min'),
            r.get('elevation_max')
        ))
    
    return db.execute_many(query, data_list)

def get_simulation_history(db, limit=50):
    """Retorna histórico de simulações"""
    query = """
        SELECT * FROM simulations 
        ORDER BY created_at DESC 
        LIMIT %s
    """
    return db.execute_query(query, (limit,))

def get_simulation_details(db, simulation_id):
    """Retorna detalhes completos de uma simulação"""
    sim_query = "SELECT * FROM simulations WHERE id = %s"
    results_query = "SELECT * FROM simulation_results WHERE simulation_id = %s"
    
    simulation = db.execute_query(sim_query, (simulation_id,))
    results = db.execute_query(results_query, (simulation_id,))
    
    if simulation:
        return {
            'simulation': simulation[0],
            'results': results
        }
    return None
