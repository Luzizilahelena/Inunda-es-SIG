"""
fetch_bairros.py
================
Dados dos bairros de Luanda embutidos directamente no script
(fonte: OpenStreetMap via Overpass, exportado em 2026-06-03).

Faz spatial join com polígonos GADM 4.1 para atribuir o município
correcto a cada bairro e gera bairros_com_municipio.geojson.

Uso:
    python fetch_bairros.py

Dependências:
    pip install requests geopandas shapely
"""

import unicodedata
import requests
import geopandas as gpd
from zipfile import ZipFile
from io import BytesIO
from shapely.geometry import Point

# ── Mapeamento GADM NAME_2 → nome usado no sistema ───────────────────────────

GADM_TO_SYSTEM = {
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

# Municípios novos sem polígono no GADM 4.1 (círculos aproximados)
# Centros e raios calculados a partir das coordenadas reais dos bairros conhecidos
NEW_MUNICIPALITIES = [
    # Hoji Ya Henda — Tala-Hady, Cariango, Cazenga Popular, Patricio, Mabor, Kikolo
    # zona nordeste de Luanda, lon ~13.29–13.33
    {'name': 'Hoji Ya Henda', 'lat': -8.7988, 'lon': 13.3136, 'radius': 0.07},
    # Camama — a sul/sudeste de Kilamba Kiaxi
    {'name': 'Camama',        'lat': -8.932,  'lon': 13.262,  'radius': 0.05},
    # Kilamba — Cidade do Kilamba, Quarteirões, lat ~-8.99 a -9.01
    {'name': 'Kilamba',       'lat': -8.9988, 'lon': 13.2644, 'radius': 0.05},
    # Mulenvos — zona norte, Mulenvos de Baixo/Cima
    {'name': 'Mulenvos',      'lat': -8.7810, 'lon': 13.2685, 'radius': 0.05},
]

MUNICIPALITY_RISK = {
    'Belas':          'Alto',
    'Cacuaco':        'Muito Alto',
    'Cazenga':        'Muito Alto',
    'Viana':          'Alto',
    'Kilamba Kiaxi':  'Muito Alto',
    'Talatona':       'Médio',
    'Maianga':        'Alto',
    'Rangel':         'Muito Alto',
    'Ingombota':      'Médio',
    'Samba':          'Alto',
    'Sambizanga':     'Muito Alto',
    'Hoji Ya Henda':  'Muito Alto',
    'Camama':         'Alto',
    'Kilamba':        'Médio',
    'Mulenvos':       'Alto',
}

POPULATION_DEFAULT = 50000
OUTPUT_PATH = "bairros_com_municipio.geojson"

# ── Dados dos bairros (OpenStreetMap, Luanda, 2026-06-03) ─────────────────────
# Fonte: Overpass API — nodes/ways com place=suburb ou place=neighbourhood

BAIRROS_RAW = [
    {"name": "Urbanização Nova Vida",                    "lon": 13.2299477,  "lat": -8.9072958},
    {"name": "Calemba 2",                                "lon": 13.2695279,  "lat": -8.9013802},
    {"name": "Distrito do Kilamba Kiaxe",                "lon": 13.2505403,  "lat": -8.8659013},
    {"name": "Bairro Mande",                             "lon": 13.1512944,  "lat": -8.9847054},
    {"name": "Galenha/Mirantes",                         "lon": 13.1742181,  "lat": -8.9166957},
    {"name": "Cassenda",                                 "lon": 13.2288331,  "lat": -8.8449267},
    {"name": "Bairro da Cambamba",                       "lon": 13.2174759,  "lat": -8.9173093},
    {"name": "Bairro Neves Bendinha",                    "lon": 13.2666961,  "lat": -8.8482944},
    {"name": "Bairro Kifica",                            "lon": 13.1823308,  "lat": -8.9501136},
    {"name": "Futungo I",                                "lon": 13.1683794,  "lat": -8.9124279},
    {"name": "Futungo II",                               "lon": 13.1712148,  "lat": -8.8992847},
    {"name": "Prenda",                                   "lon": 13.2218077,  "lat": -8.8385399},
    {"name": "Bairro Militar",                           "lon": 13.2202597,  "lat": -8.9035626},
    {"name": "Morro Bento II",                           "lon": 13.2099308,  "lat": -8.8896221},
    {"name": "Bairro Marçal",                            "lon": 13.2579517,  "lat": -8.8214589},
    {"name": "Valódia",                                  "lon": 13.2507578,  "lat": -8.820963},
    {"name": "Combatentes",                              "lon": 13.2516792,  "lat": -8.8181918},
    {"name": "Calemba",                                  "lon": 13.2495175,  "lat": -8.8386129},
    {"name": "Projecto Crédito Jovem",                   "lon": 13.2555106,  "lat": -8.9377805},
    {"name": "Chimbicato",                               "lon": 13.2513636,  "lat": -8.9332702},
    {"name": "Fubú",                                     "lon": 13.2251021,  "lat": -8.9262349},
    {"name": "Iraque",                                   "lon": 13.2505615,  "lat": -8.9135148},
    {"name": "Morro da Luz",                             "lon": 13.2063809,  "lat": -8.8651341},
    {"name": "Bairro 30",                                "lon": 13.4762191,  "lat": -8.9765895},
    {"name": "Miramar",                                  "lon": 13.2488398,  "lat": -8.8087611},
    {"name": "Benfica",                                  "lon": 13.1901626,  "lat": -8.9640285},
    {"name": "Quifica",                                  "lon": 13.1633226,  "lat": -8.9588913},
    {"name": "Vila Alice",                               "lon": 13.2502261,  "lat": -8.8269164},
    {"name": "Bairro Operario",                          "lon": 13.2467117,  "lat": -8.8136659},
    {"name": "Sapu km 12",                               "lon": 13.3315027,  "lat": -8.8975362},
    {"name": "Talatona",                                 "lon": 13.1911229,  "lat": -8.9205561},
    {"name": "Prenda",                                   "lon": 13.2226291,  "lat": -8.8368115},
    {"name": "Cassenda",                                 "lon": 13.2295263,  "lat": -8.8453029},
    {"name": "Vila Alice",                               "lon": 13.2476469,  "lat": -8.8267641},
    {"name": "São Paulo",                                "lon": 13.2559223,  "lat": -8.8135247},
    {"name": "Cuca",                                     "lon": 13.2773103,  "lat": -8.8152316},
    {"name": "Maianga",                                  "lon": 13.2303908,  "lat": -8.8267755},
    {"name": "Camama",                                   "lon": 13.2647271,  "lat": -8.9402366},
    {"name": "Boavista",                                 "lon": 13.2633994,  "lat": -8.8016755},
    {"name": "Sambizanga",                               "lon": 13.2715131,  "lat": -8.8043556},
    {"name": "Benfica",                                  "lon": 13.1639942,  "lat": -8.944328},
    {"name": "Bairro Mundimba",                          "lon": 13.3933616,  "lat": -8.9883615},
    {"name": "Sector 4",                                 "lon": 13.2672128,  "lat": -8.9236816},
    {"name": "Vila Chinesa",                             "lon": 13.3768985,  "lat": -8.9429109},
    {"name": "Bairro Cabolombo",                         "lon": 13.1673709,  "lat": -8.9297646},
    {"name": "Sector 11A",                               "lon": 13.2755452,  "lat": -8.8814105},
    {"name": "Triangulo",                                "lon": 13.2676749,  "lat": -8.8314666},
    {"name": "Kapalanga",                                "lon": 13.3915178,  "lat": -8.911638},
    {"name": "Kapalanga II",                             "lon": 13.3913462,  "lat": -8.9034976},
    {"name": "Bairro das Tendas",                        "lon": 13.1469098,  "lat": -8.9794935},
    {"name": "Bairro Mande",                             "lon": 13.1506446,  "lat": -8.9855596},
    {"name": "Bairro das Tendas",                        "lon": 13.1554611,  "lat": -8.9718602},
    {"name": "Zona Verde",                               "lon": 13.179005,   "lat": -8.9857332},
    {"name": "Precol",                                   "lon": 13.2699647,  "lat": -8.8218393},
    {"name": "Bairro dos CTT",                           "lon": 13.2656303,  "lat": -8.8174395},
    {"name": "Terra Nova",                               "lon": 13.2680979,  "lat": -8.8367559},
    {"name": "Bairro Nelito Soares",                     "lon": 13.2591297,  "lat": -8.8309049},
    {"name": "Marcal",                                   "lon": 13.2582917,  "lat": -8.8202809},
    {"name": "Cassequel do Buraco",                      "lon": 13.2483671,  "lat": -8.8421891},
    {"name": "Cassequel",                                "lon": 13.248174,   "lat": -8.8491329},
    {"name": "Palanca",                                  "lon": 13.2660695,  "lat": -8.8607037},
    {"name": "Onjo-Yeto",                                "lon": 13.3029526,  "lat": -8.9115862},
    {"name": "Sapu",                                     "lon": 13.3080216,  "lat": -8.9339035},
    {"name": "Projecto Crédito Jovem",                   "lon": 13.2547882,  "lat": -8.937348},
    {"name": "Chimbicato",                               "lon": 13.2483913,  "lat": -8.9311326},
    {"name": "Iraque",                                   "lon": 13.2484072,  "lat": -8.9211255},
    {"name": "Fubu",                                     "lon": 13.2304632,  "lat": -8.9313418},
    {"name": "Dangereux",                                "lon": 13.2082813,  "lat": -8.9331234},
    {"name": "Bairro Sossego",                           "lon": 13.2184942,  "lat": -9.0011476},
    {"name": "Kifangondo",                               "lon": 13.4239856,  "lat": -8.7633837},
    {"name": "500 casas",                                "lon": 13.3707156,  "lat": -8.9367855},
    {"name": "Vila Chinesa",                             "lon": 13.3766031,  "lat": -8.9427111},
    {"name": "Zona Verde II",                            "lon": 13.1880943,  "lat": -9.0062537},
    {"name": "Tala-Hady",                                "lon": 13.2795293,  "lat": -8.8383568},
    {"name": "Cariango",                                 "lon": 13.2813746,  "lat": -8.8356948},
    {"name": "Cazenga Popular",                          "lon": 13.287747,   "lat": -8.8335326},
    {"name": "Patricio",                                 "lon": 13.2868243,  "lat": -8.8210438},
    {"name": "Mabor",                                    "lon": 13.3067371,  "lat": -8.7941139},
    {"name": "Bairro Kikolo",                            "lon": 13.3326579,  "lat": -8.7896501},
    {"name": "Golf II",                                  "lon": 13.2529023,  "lat": -8.879369},
    {"name": "Golf",                                     "lon": 13.2567861,  "lat": -8.8620478},
    {"name": "Bairro Mundial",                           "lon": 13.1279968,  "lat": -8.9962496},
    {"name": "Kinanga",                                  "lon": 13.2239267,  "lat": -8.8185685},
    {"name": "Praia do Bispo",                           "lon": 13.2205632,  "lat": -8.8194855},
    {"name": "Coreia",                                   "lon": 13.2183262,  "lat": -8.8275642},
    {"name": "Samba",                                    "lon": 13.212125,   "lat": -8.8387912},
    {"name": "Mabunda",                                  "lon": 13.2076618,  "lat": -8.8483112},
    {"name": "Corimba",                                  "lon": 13.1997546,  "lat": -8.8651984},
    {"name": "Gamek a Direita",                          "lon": 13.202431,   "lat": -8.8840544},
    {"name": "Gamek",                                    "lon": 13.2080373,  "lat": -8.8894838},
    {"name": "Bairro das Salinas",                       "lon": 13.1446148,  "lat": -8.9737469},
    {"name": "Comissão do Rangel",                       "lon": 13.272378,   "lat": -8.8313793},
    {"name": "Valódia",                                  "lon": 13.2506414,  "lat": -8.8206078},
    {"name": "Combatentes",                              "lon": 13.2538707,  "lat": -8.8177877},
    {"name": "Cruzeiro",                                 "lon": 13.2504375,  "lat": -8.8107161},
    {"name": "Miramar",                                  "lon": 13.2490368,  "lat": -8.8093346},
    {"name": "Coqueiros",                                "lon": 13.2268984,  "lat": -8.8135363},
    {"name": "Mutamba",                                  "lon": 13.2323702,  "lat": -8.8150577},
    {"name": "Bairro Operario",                          "lon": 13.2478456,  "lat": -8.8137964},
    {"name": "Zangado",                                  "lon": 13.2620568,  "lat": -8.8220285},
    {"name": "Vila Clotilde",                            "lon": 13.2445796,  "lat": -8.8204382},
    {"name": "Martires de Kifangondo",                   "lon": 13.2367468,  "lat": -8.8411802},
    {"name": "Alvalade",                                 "lon": 13.235761,   "lat": -8.8307726},
    {"name": "Calumbo",                                  "lon": 13.4131159,  "lat": -9.15002},
    {"name": "Maculusso",                                "lon": 13.2420405,  "lat": -8.8227802},
    {"name": "Bairro dos Saiotes",                       "lon": 13.2615243,  "lat": -8.8347589},
    {"name": "Bairro Indigena",                          "lon": 13.2581448,  "lat": -8.8271469},
    {"name": "Bairro Azul",                              "lon": 13.22189,    "lat": -8.8258862},
    {"name": "Jacinto Chipa",                            "lon": 13.3327631,  "lat": -8.9235683},
    {"name": "Rocha Pinto",                              "lon": 13.2131886,  "lat": -8.8579198},
    {"name": "Grafanil Bar",                             "lon": 13.3108054,  "lat": -8.8648487},
    {"name": "Calemba",                                  "lon": 13.2497256,  "lat": -8.8386404},
    {"name": "Bairro da Bandeira",                       "lon": 13.1351915,  "lat": -9.004073},
    {"name": "Estalagem",                                "lon": 13.3355037,  "lat": -8.8811816},
    {"name": "Bairro Matadouro",                         "lon": 13.1139522,  "lat": -8.9791031},
    {"name": "Bairro do Chinguar",                       "lon": 13.1556327,  "lat": -8.9613013},
    {"name": "Bacia de Retenção do Coelho",              "lon": 13.3235601,  "lat": -8.8739265},
    {"name": "Bairro Neves Bendinha",                    "lon": 13.2608733,  "lat": -8.8437378},
    {"name": "Morro Bento II",                           "lon": 13.2105969,  "lat": -8.8919363},
    {"name": "Morro Bento I",                            "lon": 13.1888278,  "lat": -8.8991811},
    {"name": "Centralidade do Zango V",                  "lon": 13.4599173,  "lat": -9.0849985},
    {"name": "Urbanização Nova Vida",                    "lon": 13.2305372,  "lat": -8.9071488},
    {"name": "Quarteirão Hungu- Bloco A",                "lon": 13.2537649,  "lat": -8.9927716},
    {"name": "Quarteirão- Bloco B",                      "lon": 13.2578843,  "lat": -8.9926868},
    {"name": "Quarteirão Marimba- Bloco C",              "lon": 13.261972,   "lat": -8.992814},
    {"name": "Quarteirão Serra da Kanda- Bloco H",       "lon": 13.2611137,  "lat": -9.0009942},
    {"name": "Quarteirão Rio Kwanza- Bloco U",           "lon": 13.2713275,  "lat": -9.0003796},
    {"name": "Quarteirão Ngoma- Bloco F",                "lon": 13.2620149,  "lat": -8.9965435},
    {"name": "Quarteirão Miradouro Da Lua- Bloco G",     "lon": 13.2579283,  "lat": -9.0007833},
    {"name": "Quarteirão Rio Chivango- Bloco Y",         "lon": 13.2750611,  "lat": -9.0049256},
    {"name": "Quarteirão Vale do Pembe- Bloco K",        "lon": 13.2619087,  "lat": -9.0042802},
    {"name": "Quarteirão Rio Curoca- Bloco X",           "lon": 13.2700186,  "lat": -9.004693},
    {"name": "Quarteirão Olombendo- Bloco E",            "lon": 13.2576087,  "lat": -8.9964443},
    {"name": "Quarteirão Batuque- Bloco D",              "lon": 13.2541399,  "lat": -8.9962256},
    {"name": "Quarteirão Rio Chivango - Bloco W",        "lon": 13.2789664,  "lat": -9.0009624},
    {"name": "Quarteirão Rio Cunene- Bloco V",           "lon": 13.2750933,  "lat": -9.0006127},
    {"name": "Quarteirão Ekuikui II- Bloco T",           "lon": 13.2789235,  "lat": -8.996427},
    {"name": "Quarteirão Rio Longa- Bloco Z",            "lon": 13.2787948,  "lat": -9.0045653},
    {"name": "Quarteirão Nzinga Mbandi- Bloco L",        "lon": 13.2678846,  "lat": -8.992814},
    {"name": "Quarteirão Nhaca Tolo- Bloco N",           "lon": 13.2754903,  "lat": -8.992877},
    {"name": "Quarteirão Mini-Ya-Lukene- Bloco Q",       "lon": 13.2682054,  "lat": -8.9963104},
    {"name": "Quarteirão Bula Matadi- Bloco R",          "lon": 13.2715957,  "lat": -8.9964487},
    {"name": "Quarteirão Kimpavita- Bloco P",            "lon": 13.278827,   "lat": -8.9930042},
    {"name": "Quarteirão N'gola M'bandi- Bloco M",       "lon": 13.2717888,  "lat": -8.9930148},
    {"name": "Quarteirão Rei Katiavala- Bloco S",        "lon": 13.2749431,  "lat": -8.99648},
    {"name": "Patriota",                                 "lon": 13.2014057,  "lat": -8.9505281},
    {"name": "Areia Branca",                             "lon": 13.2085007,  "lat": -8.8263796},
    {"name": "Bairro Vitrona",                           "lon": 13.1487969,  "lat": -9.106279},
    {"name": "Xuxa Dela",                                "lon": 13.1420172,  "lat": -8.9844154},
    {"name": "Bairro Cabolombo",                         "lon": 13.1680179,  "lat": -8.9294643},
    {"name": "Bairro da Nzinga Mbandi",                  "lon": 13.2452436,  "lat": -9.100911},
    {"name": "Bairro da Mabor",                          "lon": 13.3147313,  "lat": -8.8155037},
    {"name": "Bairro São Pedro da Barra",                "lon": 13.2938437,  "lat": -8.7887346},
    {"name": "Bairro Militar",                           "lon": 13.2116539,  "lat": -8.9100644},
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def normalize(name):
    name = unicodedata.normalize('NFD', str(name))
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    return name.replace(' ', '').replace('-', '').replace('_', '').lower()


def dedup(bairros):
    """Remove duplicados por (nome normalizado, coords arredondadas)."""
    seen = set()
    result = []
    for b in bairros:
        key = (normalize(b['name']), round(b['lat'], 4), round(b['lon'], 4))
        if key not in seen:
            seen.add(key)
            result.append(b)
    return result


# ── Passo 1: Construir GeoDataFrame de bairros ───────────────────────────────

def build_bairros_gdf():
    bairros = dedup(BAIRROS_RAW)
    features = [
        {
            "type": "Feature",
            "properties": {"name": b["name"]},
            "geometry": {"type": "Point", "coordinates": [b["lon"], b["lat"]]}
        }
        for b in bairros
    ]
    gdf = gpd.GeoDataFrame.from_features(features, crs='EPSG:4326')
    print(f"Bairros carregados: {len(gdf)} ({len(BAIRROS_RAW) - len(bairros)} duplicados removidos)")
    return gdf


# ── Passo 2: Construir GeoDataFrame de municípios (GADM) ─────────────────────

def build_municipality_gdf():
    url = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_AGO_2.json.zip"
    print("A descarregar polígonos GADM (municípios de Luanda)...")
    resp = requests.get(url, timeout=90)
    resp.raise_for_status()

    with ZipFile(BytesIO(resp.content)) as zf:
        with zf.open(zf.namelist()[0]) as f:
            gadm = gpd.read_file(f, driver='GeoJSON')

    luanda = gadm[gadm['NAME_1'] == 'Luanda']
    rows = []
    for _, row in luanda.iterrows():
        sys_name = GADM_TO_SYSTEM.get(row['NAME_2'])
        if sys_name:
            rows.append({'municipality': sys_name, 'geometry': row.geometry})

    for nm in NEW_MUNICIPALITIES:
        circle = Point(nm['lon'], nm['lat']).buffer(nm['radius'])
        rows.append({'municipality': nm['name'], 'geometry': circle})

    mun_gdf = gpd.GeoDataFrame(rows, crs='EPSG:4326')
    print(f"Municípios: {sorted(mun_gdf['municipality'].tolist())}")
    return mun_gdf


# ── Passo 3: Spatial join ────────────────────────────────────────────────────

def enrich(bairros_gdf, mun_gdf):
    print("A fazer spatial join...")

    joined = gpd.sjoin(
        bairros_gdf,
        mun_gdf[['municipality', 'geometry']],
        how='left',
        predicate='within'
    )
    joined = joined[~joined.index.duplicated(keep='first')]

    missing = joined['municipality'].isna()
    n_missing = missing.sum()
    if n_missing:
        print(f"  {n_missing} bairros fora dos polígonos — fallback por proximidade...")
        # Usar CRS projectado (UTM zona 33S) para distâncias correctas sem avisos
        mun_proj     = mun_gdf.to_crs('EPSG:32733')
        bairros_proj = bairros_gdf.to_crs('EPSG:32733')
        mun_pts = mun_proj.copy()
        mun_pts['geometry'] = mun_pts.geometry.centroid
        for idx in joined[missing].index:
            pt   = bairros_proj.loc[idx, 'geometry']
            dist = mun_pts.geometry.distance(pt)
            joined.at[idx, 'municipality'] = mun_pts.iloc[dist.argmin()]['municipality']

    joined['risk']       = joined['municipality'].map(MUNICIPALITY_RISK).fillna('Médio')
    joined['population'] = POPULATION_DEFAULT

    return joined[['name', 'municipality', 'risk', 'population', 'geometry']]


# ── Passo 4: Guardar ─────────────────────────────────────────────────────────

def save(gdf, path):
    gdf.to_file(path, driver='GeoJSON')
    print(f"\nFicheiro gerado: {path}")
    print(f"Total: {len(gdf)} bairros\n")
    print("Distribuição por município:")
    for mun, count in gdf['municipality'].value_counts().sort_index().items():
        print(f"  {mun:<20} {count} bairros")
    n = gdf['municipality'].isna().sum()
    print(f"\n{'✓ Todos os bairros têm município.' if not n else f'⚠ {n} bairros sem município.'}")


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    bairros_gdf = build_bairros_gdf()
    mun_gdf     = build_municipality_gdf()
    result      = enrich(bairros_gdf, mun_gdf)
    save(result, OUTPUT_PATH)