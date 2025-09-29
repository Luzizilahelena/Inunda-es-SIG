import requests
import geopandas as gpd
from zipfile import ZipFile
from io import BytesIO
import matplotlib.pyplot as plt
import flask as fs
import numpy as np

def download_and_read_gadm_json(country_code, level):
    """
    Baixa e lê um arquivo GeoJSON (.json.zip) do GADM para um país e nível administrativo.
    
    :param country_code: Código ISO de 3 letras do país (ex: 'AGO' para Angola)
    :param level: Nível administrativo (0 = país, 1 = províncias, 2 = municípios, 3 = comunas)
    :return: GeoDataFrame com os dados espaciais
    """
    # URL para o arquivo GeoJSON
    json_url = f'https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_{country_code}_{level}.json.zip'
    print(f"Tentando baixar GeoJSON: {json_url}...")
    
    try:
        # Baixar o arquivo
        response = requests.get(json_url)
        response.raise_for_status()
        # Extrair o GeoJSON da ZIP
        with ZipFile(BytesIO(response.content)) as zip_file:
            json_filename = zip_file.namelist()[0]  # Pega o primeiro arquivo GeoJSON
            with zip_file.open(json_filename) as json_file:
                # Ler o GeoJSON com geopandas
                gdf = gpd.read_file(json_file, driver='GeoJSON')
        return gdf
    except requests.exceptions.HTTPError as e:
        print(f"Erro ao baixar GeoJSON: {e}")
        return None
    except Exception as e:
        print(f"Erro ao processar arquivo: {e}")
        return None

def simulate_and_plot_flood(gdf, country_code, level):
    """
    Simula inundações baseadas em províncias propensas e plota o mapa.
    
    :param gdf: GeoDataFrame com os dados espaciais
    :param country_code: Código do país
    :param level: Nível administrativo
    """
    if gdf is None or gdf.empty:
        print("Nenhum dado para plotar.")
        return
    
    # Lista de províncias propensas a inundações em Angola (baseado em dados históricos)
    flood_prone_provinces = [
        'Benguela', 'Bié', 'Cuando Cubango', 'Cunene', 'Cuanza Norte', 
        'Huambo', 'Luanda', 'Lunda Sul', 'Malanje', 'Moxico', 'Uíge', 'Zaire'
    ]
    
    # Identificar comunas em províncias propensas (usando coluna 'NAME_1' do GADM)
    gdf['prone_to_flood'] = gdf['NAME_1'].isin(flood_prone_provinces)
    
    # Simulação: Inundar aleatoriamente 50% das comunas propensas (para demonstração)
    flood_rate = 0.5  # Ajuste esta taxa (0.0 a 1.0)
    gdf['flooded'] = False
    prone_indices = gdf[gdf['prone_to_flood']].index
    num_to_flood = int(len(prone_indices) * flood_rate)
    flood_indices = np.random.choice(prone_indices, num_to_flood, replace=False)
    gdf.loc[flood_indices, 'flooded'] = True
    
    # Plotar o mapa com simulação de inundação
    fig, ax = plt.subplots(figsize=(10, 8))
    gdf.plot(ax=ax, color='lightgrey', edgecolor='black', linewidth=0.5)  # Fundo
    gdf[gdf['flooded']].plot(ax=ax, color='blue', edgecolor='black', linewidth=0.5)  # Áreas inundadas
    plt.title(f"Simulação de Inundação em {country_code} - Nível {level} (Comunas Inundadas em Azul)")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.show()
    
    # Exibir informações básicas e resumo da simulação
    print("Colunas disponíveis:", gdf.columns.tolist())
    print("Número de features totais:", len(gdf))
    print("Número de comunas propensas a inundação:", gdf['prone_to_flood'].sum())
    print("Número de comunas simuladas como inundadas:", gdf['flooded'].sum())
    print(gdf[gdf['flooded']].head())  # Exibe as primeiras comunas inundadas

def main():
    country_code = input("Digite o código ISO do país (ex: AGO para Angola): ").upper()
    level = input("Digite o nível administrativo (0 = país, 1 = províncias, 2 = municípios, 3 = comunas): ")

    if not country_code:
        country_code = "AGO"
    if not level:
        level = "3"  # Default para nível 3 (comunas em Angola)

    try:
        level = int(level)
        if level < 0:
            level = 3
        gdf = download_and_read_gadm_json(country_code, level)
        simulate_and_plot_flood(gdf, country_code, level)
        
    except ValueError as e:
        print(f"Erro: {e}")
    except Exception as e:
        print(f"Erro inesperado: {e}")

app = fs.Flask(__name__)

@app.route('/flood_map')
def flood_map():
    country_code = fs.request.args.get('country', default='AGO', type=str).upper()
    level = fs.request.args.get('level', default=3, type=int)

    gdf = download_and_read_gadm_json(country_code, level)
    if gdf is None or gdf.empty:
        return fs.jsonify({"error": "Nenhum dado disponível para o país e nível especificados."}), 404

    # Simulação de inundação
    flood_prone_provinces = [
        'Benguela', 'Bié', 'Cuando Cubango', 'Cunene', 'Cuanza Norte', 
        'Huambo', 'Luanda', 'Lunda Sul', 'Malanje', 'Moxico', 'Uíge', 'Zaire'
    ]
    gdf['prone_to_flood'] = gdf['NAME_1'].isin(flood_prone_provinces)
    flood_rate = 0.5
    gdf['flooded'] = False
    prone_indices = gdf[gdf['prone_to_flood']].index
    num_to_flood = int(len(prone_indices) * flood_rate)
    flood_indices = np.random.choice(prone_indices, num_to_flood, replace=False)
    gdf.loc[flood_indices, 'flooded'] = True

    # Converter GeoDataFrame para GeoJSON
    geojson_data = gdf.to_json()

    return fs.jsonify(geojson_data)

if __name__ == "__main__":
    app.run(debug=True)

# import requests
# import geopandas as gpd
# from zipfile import ZipFile
# from io import BytesIO
# import matplotlib.pyplot as plt
# import os
# import shutil

# def download_and_read_gadm_json(country_code, level):
#     # URL para o arquivo GeoJSON
#     json_url = f'https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_{country_code}_{level}.json.zip'
#     print(f"Tentando baixar GeoJSON: {json_url}...")
    
#     try:
#         # Baixar o arquivo
#         response = requests.get(json_url)
#         response.raise_for_status()
#         # Extrair o GeoJSON da ZIP
#         with ZipFile(BytesIO(response.content)) as zip_file:
#             json_filename = zip_file.namelist()[0]  # Pega o primeiro arquivo GeoJSON
#             with zip_file.open(json_filename) as json_file:
#                 # Ler o GeoJSON com geopandas
#                 gdf = gpd.read_file(json_file, driver='GeoJSON')
#         return gdf
#     except requests.exceptions.HTTPError as e:
#         print(f"Erro ao baixar GeoJSON: {e}")
#         return None
#     except Exception as e:
#         print(f"Erro ao processar arquivo: {e}")
#         return None

# def plot_gadm_map(gdf, country_code, level):
#     if gdf is None or gdf.empty:
#         print("Nenhum dado para plotar.")
#         return
    
#     # Plotar o mapa
#     gdf.plot(figsize=(10, 8), edgecolor='black', linewidth=0.5)
#     plt.title(f"Mapa de {country_code} - Nível Administrativo {level}")
#     plt.xlabel("Longitude")
#     plt.ylabel("Latitude")
#     plt.show()
    
#     # Exibir informações básicas
#     print("Colunas disponíveis:", gdf.columns.tolist())
#     print("Número de features:", len(gdf))
#     print(gdf.head())

# def main():
#     country_code = input("Digite o código ISO do país (ex: BRA para Brasil): ").upper()
#     level = input("Digite o nível administrativo (0 = país, 1 = estados, 2 = municípios, etc.): ")

#     if not country_code:
#         country_code = "AGO"
#     if not level:
#         level = 3

#     try:
#         level = int(level)
#         if level < 0:
#             level = 3
#         gdf = download_and_read_gadm_json(country_code, level)
#         plot_gadm_map(gdf, country_code, level)
        
#     except ValueError as e:
#         print(f"Erro: {e}")
#     except Exception as e:
#         print(f"Erro inesperado: {e}")

# if __name__ == "__main__":
#     main()