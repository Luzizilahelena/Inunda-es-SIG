import os

# Configurações do Banco de Dados
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'lnzila'),  # ← Seu usuário do SQL
    'password': os.getenv('DB_PASSWORD', 'inunda123!'),  # ← Sua senha do SQL
    'database': os.getenv('DB_NAME', 'inundacoes_db'),
    'charset': 'utf8mb4',
    'cursorclass': 'DictCursor'
}

# Para produção, use variáveis de ambiente:
# export DB_HOST=localhost
# export DB_USER=lnzila
# export DB_PASSWORD=inunda123!
# export DB_NAME=inundacoes_db
