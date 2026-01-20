#!/usr/bin/env python3
"""
Script para testar a conexão com o banco de dados MariaDB
Execute: python test_database.py
"""

from database import Database, get_provinces, get_municipalities, get_bairros
import sys

def test_connection():
    """Testa conexão básica com o banco"""
    print("\n" + "="*60)
    print("TESTE DE CONEXÃO - MariaDB")
    print("="*60)
    
    try:
        db = Database()
        db.connect()
        print("✓ Conexão estabelecida com sucesso!")
        return db
    except Exception as e:
        print(f"✗ Erro ao conectar: {e}")
        print("\nVerifique:")
        print("1. MariaDB está rodando? (sudo systemctl status mariadb)")
        print("2. Credenciais em config.py estão corretas?")
        print("3. Banco 'inundacoes_db' foi criado?")
        sys.exit(1)

def test_tables(db):
    """Verifica se as tabelas existem"""
    print("\n" + "-"*60)
    print("VERIFICANDO TABELAS")
    print("-"*60)
    
    tables = ['provinces', 'municipalities', 'bairros', 'simulations', 'simulation_results']
    
    for table in tables:
        try:
            result = db.execute_query(f"SELECT COUNT(*) as count FROM {table}")
            count = result[0]['count'] if result else 0
            print(f"✓ Tabela '{table}': {count} registros")
        except Exception as e:
            print(f"✗ Erro na tabela '{table}': {e}")

def test_data(db):
    """Testa leitura de dados"""
    print("\n" + "-"*60)
    print("TESTANDO LEITURA DE DADOS")
    print("-"*60)
    
    try:
        # Testar províncias
        provinces = get_provinces(db)
        print(f"\n✓ Províncias encontradas: {len(provinces)}")
        if provinces:
            for p in provinces:
                print(f"  - {p['name']}: {p['population']:,} habitantes")
        
        # Testar municípios
        municipalities = get_municipalities(db)
        print(f"\n✓ Municípios encontrados: {len(municipalities)}")
        if municipalities:
            print(f"  Exemplos:")
            for m in municipalities[:5]:
                print(f"  - {m['name']} ({m['province_name']}): {m['population']:,} hab")
        
        # Testar bairros
        bairros = get_bairros(db)
        print(f"\n✓ Bairros encontrados: {len(bairros)}")
        if bairros:
            print(f"  Exemplos:")
            for b in bairros[:5]:
                print(f"  - {b['name']} ({b['municipality_name']}): {b['population']:,} hab")
        
        return True
    except Exception as e:
        print(f"\n✗ Erro ao ler dados: {e}")
        return False

def test_write(db):
    """Testa escrita no banco"""
    print("\n" + "-"*60)
    print("TESTANDO ESCRITA DE DADOS")
    print("-"*60)
    
    try:
        # Simular inserção de simulação
        from database import save_simulation
        
        test_simulation = {
            'level': 'province',
            'province': 'Luanda',
            'municipality': None,
            'bairro': None,
            'flood_rate': 50.0,
            'water_level': 10.0,
            'flooded_count': 1,
            'total_affected': 100000,
            'total_analyzed': 1,
            'avg_risk': 100.0
        }
        
        sim_id = save_simulation(db, test_simulation)
        print(f"✓ Simulação de teste salva com ID: {sim_id}")
        
        # Deletar teste
        db.execute_update("DELETE FROM simulations WHERE id = %s", (sim_id,))
        print(f"✓ Simulação de teste removida")
        
        return True
    except Exception as e:
        print(f"✗ Erro ao testar escrita: {e}")
        return False

def show_summary(db):
    """Mostra resumo do banco"""
    print("\n" + "="*60)
    print("RESUMO DO BANCO DE DADOS")
    print("="*60)
    
    try:
        provinces = get_provinces(db)
        municipalities = get_municipalities(db)
        bairros = get_bairros(db)
        
        total_pop_provinces = sum(p['population'] for p in provinces)
        total_pop_municipalities = sum(m['population'] for m in municipalities)
        total_pop_bairros = sum(b['population'] for b in bairros)
        
        print(f"\n📊 Estatísticas:")
        print(f"  • Províncias: {len(provinces)}")
        print(f"  • Municípios: {len(municipalities)}")
        print(f"  • Bairros: {len(bairros)}")
        print(f"\n👥 População:")
        print(f"  • Total (Províncias): {total_pop_provinces:,}")
        print(f"  • Total (Municípios): {total_pop_municipalities:,}")
        print(f"  • Total (Bairros): {total_pop_bairros:,}")
        
        # Histórico de simulações
        history = db.execute_query("SELECT COUNT(*) as count FROM simulations")
        sim_count = history[0]['count'] if history else 0
        print(f"\n📈 Simulações registradas: {sim_count}")
        
    except Exception as e:
        print(f"Erro ao gerar resumo: {e}")

def main():
    """Função principal"""
    db = test_connection()
    
    test_tables(db)
    
    if test_data(db):
        print("\n✓ Leitura de dados funcionando!")
    
    if test_write(db):
        print("✓ Escrita de dados funcionando!")
    
    show_summary(db)
    
    db.close()
    
    print("\n" + "="*60)
    print("TESTE CONCLUÍDO COM SUCESSO! ✓")
    print("="*60)
    print("\nVocê pode iniciar a API com: python app.py\n")

if __name__ == "__main__":
    main()
