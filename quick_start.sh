#!/bin/bash

# Script de Inicialização Rápida
# Sistema de Simulação de Inundações - Angola

set -e  # Parar em caso de erro

echo "======================================================================"
echo "  Sistema de Simulação de Inundações - Instalação Rápida"
echo "======================================================================"
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função para mensagens
info() {
    echo -e "${GREEN}[✓]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Verificar se está rodando como root para instalação do MariaDB
check_sudo() {
    if [[ $EUID -ne 0 ]] && command -v sudo &> /dev/null; then
        SUDO="sudo"
    else
        SUDO=""
    fi
}

# Passo 1: Verificar Python
echo "─────────────────────────────────────────────────────────────────────"
echo "Passo 1: Verificando Python..."
echo "─────────────────────────────────────────────────────────────────────"

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    info "Python $PYTHON_VERSION encontrado"
else
    error "Python 3 não encontrado. Instale Python 3.8 ou superior"
    exit 1
fi

# Passo 2: Verificar MariaDB
echo ""
echo "─────────────────────────────────────────────────────────────────────"
echo "Passo 2: Verificando MariaDB..."
echo "─────────────────────────────────────────────────────────────────────"

if command -v mysql &> /dev/null; then
    info "MariaDB/MySQL encontrado"
    
    # Verificar se está rodando
    if systemctl is-active --quiet mariadb || systemctl is-active --quiet mysql; then
        info "MariaDB está rodando"
    else
        warn "MariaDB não está rodando. Tentando iniciar..."
        check_sudo
        $SUDO systemctl start mariadb || $SUDO systemctl start mysql
        info "MariaDB iniciado"
    fi
else
    error "MariaDB não encontrado"
    warn "Instalando MariaDB..."
    check_sudo
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        $SUDO apt update
        $SUDO apt install -y mariadb-server mariadb-client
        $SUDO systemctl start mariadb
        $SUDO systemctl enable mariadb
        info "MariaDB instalado"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &> /dev/null; then
            brew install mariadb
            brew services start mariadb
            info "MariaDB instalado"
        else
            error "Homebrew não encontrado. Instale manualmente"
            exit 1
        fi
    else
        error "Sistema operacional não suportado para instalação automática"
        exit 1
    fi
fi

# Passo 3: Criar ambiente virtual
echo ""
echo "─────────────────────────────────────────────────────────────────────"
echo "Passo 3: Configurando ambiente Python..."
echo "─────────────────────────────────────────────────────────────────────"

if [ ! -d "venv" ]; then
    info "Criando ambiente virtual..."
    python3 -m venv venv
else
    info "Ambiente virtual já existe"
fi

# Ativar ambiente virtual
source venv/bin/activate

# Instalar dependências
info "Instalando dependências Python..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

info "Dependências instaladas"

# Passo 4: Configurar banco de dados
echo ""
echo "─────────────────────────────────────────────────────────────────────"
echo "Passo 4: Configurando banco de dados..."
echo "─────────────────────────────────────────────────────────────────────"

warn "Você precisará da senha do root do MariaDB"
echo -n "Digite a senha do root do MariaDB (ou ENTER se não tiver): "
read -s DB_ROOT_PASSWORD
echo ""

# Criar banco
if [ -z "$DB_ROOT_PASSWORD" ]; then
    mysql -u root < setup_database.sql 2>/dev/null || {
        error "Erro ao criar banco. Tente manualmente:"
        echo "  sudo mysql -u root -p < setup_database.sql"
        exit 1
    }
else
    mysql -u root -p"$DB_ROOT_PASSWORD" < setup_database.sql 2>/dev/null || {
        error "Erro ao criar banco. Verifique a senha"
        exit 1
    }
fi

info "Banco de dados criado com sucesso"

# Passo 5: Configurar credenciais
echo ""
echo "─────────────────────────────────────────────────────────────────────"
echo "Passo 5: Configurando credenciais..."
echo "─────────────────────────────────────────────────────────────────────"

echo -n "Digite a senha para o usuário 'inundacoes_user' (padrão: SuaSenhaSegura123!): "
read -s APP_DB_PASSWORD
echo ""

if [ -z "$APP_DB_PASSWORD" ]; then
    APP_DB_PASSWORD="SuaSenhaSegura123!"
fi

# Atualizar config.py
cat > config.py << EOF
import os

# Configurações do Banco de Dados
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'inundacoes_user'),
    'password': os.getenv('DB_PASSWORD', '$APP_DB_PASSWORD'),
    'database': os.getenv('DB_NAME', 'inundacoes_db'),
    'charset': 'utf8mb4',
    'cursorclass': 'DictCursor'
}
EOF

info "Credenciais configuradas"

# Passo 6: Testar conexão
echo ""
echo "─────────────────────────────────────────────────────────────────────"
echo "Passo 6: Testando conexão com banco..."
echo "─────────────────────────────────────────────────────────────────────"

python3 test_database.py || {
    error "Teste de conexão falhou"
    warn "Verifique manualmente as credenciais em config.py"
    exit 1
}

# Resumo final
echo ""
echo "======================================================================"
echo "  INSTALAÇÃO CONCLUÍDA COM SUCESSO! ✓"
echo "======================================================================"
echo ""
echo "Para iniciar a API:"
echo "  1. Ativar ambiente virtual:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Iniciar servidor:"
echo "     python app.py"
echo ""
echo "  3. Acessar no navegador:"
echo "     http://localhost:5000"
echo ""
echo "Para testar endpoints:"
echo "  curl http://localhost:5000/api/health"
echo "  curl http://localhost:5000/api/provinces"
echo ""
echo "======================================================================"
