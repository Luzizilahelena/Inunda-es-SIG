"""
prepare_data.py
================
Script offline (corre-se uma vez, manualmente, não em produção) que gera
todos os ficheiros estáticos usados pelo motor de inundação em backend/data/:

  - provinces.geojson         limites GADM nível 1 (Angola)
  - municipalities.geojson    limites GADM nível 2 (Angola)
  - dem_luanda.tif            elevação real (Copernicus GLO-30, 30m) recortada
                               à área de Luanda + margem
  - population_luanda.tif     população real (WorldPop 100m, constrained
                               2020) recortada à mesma área
  - bairro_catchments.geojson polígonos de Voronoi por bairro (recortados ao
                               município), usados para agregar estatísticas
                               por bairro já que os bairros só existem como
                               pontos

Uso:
    cd backend && source .venv/bin/activate && python scripts/prepare_data.py

Todas as fontes são públicas e não exigem chave de API.
"""

import io
import os
import zipfile

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import requests
from rasterio.mask import mask as rio_mask
from rasterio.merge import merge as rio_merge
from rasterio.windows import from_bounds
from shapely.ops import unary_union

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
TMP_DIR = "/tmp/inundacoes_prepare_data"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)

GADM_URL = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_AGO_{level}.json.zip"
COPERNICUS_TILE_URL = (
    "https://copernicus-dem-30m.s3.amazonaws.com/"
    "Copernicus_DSM_COG_10_{ns}{lat:02d}_00_{ew}{lon:03d}_00_DEM/"
    "Copernicus_DSM_COG_10_{ns}{lat:02d}_00_{ew}{lon:03d}_00_DEM.tif"
)
WORLDPOP_URL = (
    "https://data.worldpop.org/GIS/Population/Global_2015_2030/R2024B/2020/AGO/v1/100m/"
    "constrained/ago_pop_2020_CN_100m_R2024B_v1.tif"
)
AOI_BUFFER_DEG = 0.06  # ~6-7 km de margem à volta da fronteira da província


def log(msg):
    print(f"[prepare_data] {msg}")


# ==================== 1. LIMITES ADMINISTRATIVOS (GADM) ====================
def fetch_gadm(level):
    log(f"A descarregar GADM nível {level}...")
    r = requests.get(GADM_URL.format(level=level), timeout=60)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        name = z.namelist()[0]
        gdf = gpd.read_file(io.BytesIO(z.read(name)))
    log(f"GADM nível {level}: {len(gdf)} feições")
    return gdf


def step_boundaries():
    gdf1 = fetch_gadm(1)
    gdf2 = fetch_gadm(2)
    gdf1.to_file(os.path.join(DATA_DIR, "provinces.geojson"), driver="GeoJSON")
    gdf2.to_file(os.path.join(DATA_DIR, "municipalities.geojson"), driver="GeoJSON")
    log("Guardado provinces.geojson e municipalities.geojson")
    return gdf1, gdf2


# ==================== 2. DEM (Copernicus GLO-30) ====================
def dem_tile_urls_for_bounds(minx, miny, maxx, maxy):
    lat_lo, lat_hi = int(np.floor(miny)), int(np.floor(maxy))
    lon_lo, lon_hi = int(np.floor(minx)), int(np.floor(maxx))
    urls = []
    # `lat`/`lon` percorrem os graus-grade inteiros (limite inferior de cada
    # tile de 1°x1°). O rótulo do tile é sempre o valor absoluto desse
    # limite inferior, tanto no hemisfério sul/oeste como no norte/este
    # (ex.: lat=-9 -> tile cobre [-9,-8) -> rótulo "S09").
    for lat in range(lat_lo, lat_hi + 1):
        ns = "S" if lat < 0 else "N"
        lat_band = abs(lat)
        for lon in range(lon_lo, lon_hi + 1):
            ew = "E" if lon >= 0 else "W"
            lon_band = abs(lon)
            urls.append(COPERNICUS_TILE_URL.format(ns=ns, lat=lat_band, ew=ew, lon=lon_band))
    return urls


def step_dem(aoi_bounds):
    minx, miny, maxx, maxy = aoi_bounds
    urls = dem_tile_urls_for_bounds(minx, miny, maxx, maxy)
    srcs = []
    for url in urls:
        try:
            ds = rasterio.open(f"/vsicurl/{url}")
            srcs.append(ds)
            log(f"Tile DEM OK: {url.split('/')[-1]}")
        except Exception:
            log(f"Tile DEM indisponível (assume oceano/sem dados): {url.split('/')[-1]}")
    if not srcs:
        raise RuntimeError("Nenhum tile Copernicus DEM encontrado para a área de Luanda")

    res = srcs[0].res
    mosaic, out_transform = rio_merge(srcs, bounds=aoi_bounds, res=res)
    for ds in srcs:
        ds.close()

    mosaic = mosaic.astype("float32")
    mosaic[mosaic < -100] = 0.0  # nodata/oceano -> nível do mar

    out_path = os.path.join(DATA_DIR, "dem_luanda.tif")
    profile = {
        "driver": "GTiff",
        "height": mosaic.shape[1],
        "width": mosaic.shape[2],
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": out_transform,
        "compress": "deflate",
        "predictor": 2,
        "nodata": None,
    }
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(mosaic[0], 1)
    size_mb = os.path.getsize(out_path) / 1e6
    log(f"Guardado dem_luanda.tif ({mosaic.shape[2]}x{mosaic.shape[1]} px, {size_mb:.1f} MB, "
        f"elevação {mosaic.min():.1f}–{mosaic.max():.1f} m)")


# ==================== 3. POPULAÇÃO (WorldPop) ====================
def step_population(aoi_bounds):
    minx, miny, maxx, maxy = aoi_bounds
    raw_path = os.path.join(TMP_DIR, "ago_pop_full.tif")
    if not os.path.exists(raw_path):
        log("A descarregar raster de população WorldPop (Angola, ~50MB)...")
        r = requests.get(WORLDPOP_URL, timeout=180, stream=True)
        r.raise_for_status()
        with open(raw_path, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)

    with rasterio.open(raw_path) as ds:
        window = from_bounds(minx, miny, maxx, maxy, ds.transform)
        data = ds.read(1, window=window)
        transform = ds.window_transform(window)
        profile = ds.profile.copy()

    data = data.astype("float32")
    data[data < 0] = 0.0  # nodata (-99999) -> 0 habitantes

    profile.update({
        "height": data.shape[0],
        "width": data.shape[1],
        "transform": transform,
        "dtype": "float32",
        "compress": "deflate",
        "predictor": 2,
        "nodata": 0,
    })
    out_path = os.path.join(DATA_DIR, "population_luanda.tif")
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(data, 1)

    size_mb = os.path.getsize(out_path) / 1e6
    log(f"Guardado population_luanda.tif ({data.shape[1]}x{data.shape[0]} px, {size_mb:.1f} MB, "
        f"população total na área: {data.sum():,.0f})")
    os.remove(raw_path)


# ==================== 4. CATCHMENTS DE BAIRRO (Voronoi) ====================
def step_bairro_catchments(municipalities_gdf):
    from geovoronoi import voronoi_regions_from_coords

    bairros_path = os.path.join(DATA_DIR, "bairros_com_municipio.geojson")
    bairros = gpd.read_file(bairros_path)
    bairros = bairros[bairros.geometry.notnull() & bairros["name"].notnull()]

    muni_luanda = municipalities_gdf[municipalities_gdf["NAME_1"] == "Luanda"]

    def normalize(s):
        import unicodedata
        s = unicodedata.normalize("NFD", str(s))
        s = "".join(c for c in s if unicodedata.category(c) != "Mn")
        return s.replace(" ", "").replace("-", "").replace("_", "").lower()

    muni_lookup = {normalize(r["NAME_2"]): r["geometry"] for _, r in muni_luanda.iterrows()}

    all_rows = []
    for muni_name, group in bairros.groupby("municipality"):
        if not muni_name or len(group) < 1:
            continue
        muni_poly = muni_lookup.get(normalize(muni_name))
        if muni_poly is None:
            # município novo (pós-2024) sem polígono GADM próprio: usa o
            # casco convexo dos próprios bairros com uma margem, como
            # aproximação da área do município
            muni_poly = unary_union(group.geometry).convex_hull.buffer(0.02)

        coords = np.array([[p.x, p.y] for p in group.geometry])
        names = group["name"].tolist()

        if len(coords) == 1:
            # só um bairro no município: catchment = polígono do município inteiro
            all_rows.append({"name": names[0], "municipality": muni_name,
                              "geometry": muni_poly})
            continue

        try:
            region_polys, region_pts = voronoi_regions_from_coords(coords, muni_poly)
        except Exception as e:
            log(f"Voronoi falhou para {muni_name} ({e}); a usar buffers como aproximação")
            for name, pt in zip(names, group.geometry):
                all_rows.append({"name": name, "municipality": muni_name,
                                  "geometry": pt.buffer(0.01).intersection(muni_poly)})
            continue

        for region_id, poly in region_polys.items():
            pt_indices = region_pts[region_id]
            for pi in pt_indices:
                all_rows.append({"name": names[pi], "municipality": muni_name,
                                  "geometry": poly})

    out_gdf = gpd.GeoDataFrame(all_rows, crs="EPSG:4326")
    out_path = os.path.join(DATA_DIR, "bairro_catchments.geojson")
    out_gdf.to_file(out_path, driver="GeoJSON")
    log(f"Guardado bairro_catchments.geojson ({len(out_gdf)} polígonos)")
    return out_gdf


# Municípios de Luanda pós-2024 que o GADM 4.1 ainda não separou como
# polígonos próprios (continuam agregados no município-mãe ou em nenhum).
KNOWN_MUNICIPALITIES = [
    "Belas", "Cacuaco", "Cazenga", "Viana", "Kilamba Kiaxi", "Talatona",
    "Maianga", "Rangel", "Ingombota", "Samba", "Sambizanga",
    "Hoji Ya Henda", "Camama", "Kilamba", "Mulenvos",
]

# Nenhum bairro do mapeamento manual (fetch_bairros.py) cai em Mulenvos, logo
# não há pontos para gerar um catchment por união. Usa-se um círculo à volta
# do centro aproximado do município (área ~20 km², de MUNICIPALITIES em
# flood_api.py) como última aproximação.
MANUAL_FALLBACK_CENTROIDS = {
    "Mulenvos": {"lat": -8.781, "lon": 13.269, "area_km2": 20},
}


def step_fill_missing_municipalities(municipalities_gdf, catchments_gdf):
    """Para municípios sem polígono no GADM 4.1 (subdivisões pós-2024),
    aproxima o polígono do município pela união dos catchments de bairro
    já calculados, e acrescenta-o a municipalities.geojson."""
    import unicodedata

    def normalize(s):
        s = unicodedata.normalize("NFD", str(s))
        s = "".join(c for c in s if unicodedata.category(c) != "Mn")
        return s.replace(" ", "").replace("-", "").replace("_", "").lower()

    muni_luanda = municipalities_gdf[municipalities_gdf["NAME_1"] == "Luanda"]
    existing = {normalize(n) for n in muni_luanda["NAME_2"]}

    new_rows = []
    for name in KNOWN_MUNICIPALITIES:
        if normalize(name) in existing:
            continue
        group = catchments_gdf[catchments_gdf["municipality"] == name]
        if group.empty:
            manual = MANUAL_FALLBACK_CENTROIDS.get(name)
            if not manual:
                log(f"Sem bairros para aproximar polígono de {name}; ignorado")
                continue
            radius_deg = (manual["area_km2"] / np.pi) ** 0.5 / 111.0
            poly = gpd.points_from_xy([manual["lon"]], [manual["lat"]])[0].buffer(radius_deg)
            log(f"Polígono aproximado (círculo manual) para município novo: {name}")
        else:
            poly = unary_union(group.geometry.values)
            log(f"Polígono aproximado (via catchments) para município novo: {name}")
        new_rows.append({"NAME_1": "Luanda", "NAME_2": name, "GID_2": f"FALLBACK.{name}",
                          "geometry": poly})

    if new_rows:
        addition = gpd.GeoDataFrame(new_rows, crs=municipalities_gdf.crs)
        municipalities_gdf = gpd.GeoDataFrame(
            pd.concat([municipalities_gdf, addition], ignore_index=True),
            crs=municipalities_gdf.crs,
        )
        municipalities_gdf.to_file(
            os.path.join(DATA_DIR, "municipalities.geojson"), driver="GeoJSON"
        )
        log(f"municipalities.geojson actualizado com {len(new_rows)} município(s) adicional(is)")
    return municipalities_gdf


# ==================== MAIN ====================
def main():
    gdf1, gdf2 = step_boundaries()
    luanda = gdf1[gdf1["NAME_1"] == "Luanda"]
    minx, miny, maxx, maxy = luanda.total_bounds
    aoi_bounds = (minx - AOI_BUFFER_DEG, miny - AOI_BUFFER_DEG,
                  maxx + AOI_BUFFER_DEG, maxy + AOI_BUFFER_DEG)
    log(f"AOI (Luanda + margem): {aoi_bounds}")

    step_dem(aoi_bounds)
    step_population(aoi_bounds)
    catchments_gdf = step_bairro_catchments(gdf2)
    step_fill_missing_municipalities(gdf2, catchments_gdf)

    log("Concluído. Ficheiros em backend/data/:")
    for f in sorted(os.listdir(DATA_DIR)):
        p = os.path.join(DATA_DIR, f)
        log(f"  {f}  ({os.path.getsize(p)/1e6:.2f} MB)")


if __name__ == "__main__":
    main()
