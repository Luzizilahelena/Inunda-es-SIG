Simulador de Inundações – Angola

Este projeto é um simulador de inundações desenvolvido em Python (Flask) com um frontend web interativo. Ele permite analisar riscos de inundação em diferentes províncias, municípios e bairros de Angola, utilizando dados geográficos, populacionais e estatísticas de elevação.

🚀 Funcionalidades

    API REST em Flask para simulação de inundações

    Integração com Open-Elevation API para dados reais de altimetria

    Modelagem de risco considerando:

        Elevação média e mínima

        Acumulação de fluxo (hidrologia D8)

        Fatores de drenagem e risco pré-definidos

    Endpoints para listar províncias, municípios e bairros

    Frontend web para visualização dos resultados e interação com os dados

🛠️ Tecnologias Utilizadas
Backend

    Python 3.x

    Flask + Flask-CORS

    GeoPandas

    NumPy

    Requests

    Open-Elevation API

Frontend

    HTML, CSS, JavaScript

    Consome os endpoints da API Flask

    Interface para configurar parâmetros de simulação e visualizar resultados

Instalação

Clone este repositório e instale as dependências:
bash
    git clone https://github.com/Luzizilahelena/simulador-inundacoes.git
    cd simulador-inundacoes
    pip install -r requirements.txt

Como Usar
1. Iniciar o backend (API Flask)
bash
    python3 app.py
A API estará disponível em:
http://127.0.0.1:5000/api

Acessar o frontend

Abra o arquivo index.html na pasta frontend/ em seu navegador.
O frontend se conecta automaticamente à API para buscar dados e rodar simulações.

🔗 Endpoints Principais

    /api → Informações gerais da API.

    /api/provinces → Lista de províncias.

    /api/municipalities?province=X → Lista de municípios.

    /api/bairros?municipality=X → Lista de bairros.

    /api/simulate (POST) → Simulação de inundação.
Feedback

Se encontrar algum erro ou tiver sugestões:

    Abra uma issue aqui no GitHub

    Entre em contato por e-mail: seuemail@exemplo.com
    /api/elevation?lat=X&lon=Y → Dados de elevação.

Contribuição

Contribuições são bem-vindas!
Você pode abrir uma issue ou enviar um pull request com melhorias.

Feedback

Se encontrar algum erro ou tiver sugestões:

    * Abra uma issue aqui no GitHub
    * Entre em contato por e-mail: luzizilahelena687@gmail.com