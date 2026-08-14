import logging
import os
from datetime import datetime, timezone

import geopandas as gpd
from flask import Flask, jsonify, request
from flask_cors import CORS
from shapely.ops import unary_union

from flood_model import MUNICIPALITY_RISK, FloodModel, normalize

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# ==================== CARREGAMENTO (uma vez, no arranque do processo) ====================
# Nada disto faz chamadas de rede: todos os ficheiros vêm de backend/data/,
# gerados offline por scripts/prepare_data.py. Ver flood_model.py para o
# motor de inundação (DEM real + população real).
logger.info("A carregar motor de inundação (DEM, população, limites administrativos)...")
flood_model = FloodModel(DATA_DIR)
provinces_gdf = gpd.read_file(os.path.join(DATA_DIR, "provinces.geojson"))
municipalities_gdf = gpd.read_file(os.path.join(DATA_DIR, "municipalities.geojson"))
municipalities_gdf = municipalities_gdf[municipalities_gdf["NAME_1"] == "Luanda"].reset_index(drop=True)
bairros_gdf = gpd.read_file(os.path.join(DATA_DIR, "bairros_com_municipio.geojson"))
catchments_gdf = gpd.read_file(os.path.join(DATA_DIR, "bairro_catchments.geojson"))
# Alguns bairros duplicados no mapeamento manual (fetch_bairros.py) geram
# catchments vazios (o Voronoi/fallback de buffer não deixa área depois de
# recortar pelo município) — descartar em vez de rebentar o pedido.
_n_before = len(catchments_gdf)
catchments_gdf = catchments_gdf[~catchments_gdf.geometry.is_empty].reset_index(drop=True)
if len(catchments_gdf) < _n_before:
    logger.warning(f"{_n_before - len(catchments_gdf)} catchment(s) de bairro vazio(s) descartado(s)")

BAIRRO_POINT_LOOKUP = {
    (normalize(row.get("municipality")), normalize(row.get("name"))): row.geometry
    for _, row in bairros_gdf.iterrows() if row.geometry is not None and row.get("name")
}

PROVINCES_STATIC = [{"id": 1, "name": "Luanda", "risk": "Muito Alto"}]

logger.info(
    f"Pronto: DEM {flood_model.dem_shape}, {len(municipalities_gdf)} municípios, "
    f"{len(bairros_gdf)} bairros, {len(catchments_gdf)} catchments de bairro"
)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def risk_for_municipality(name):
    return MUNICIPALITY_RISK.get(normalize(name), "Médio")


def water_level_from_payload(data):
    """Nível de água efectivo (m) usado na componente de maré/storm surge.
    Se o utilizador indicar um valor explícito, usa-o directamente (é
    literal — "se a maré/cheia atingir X metros"). Caso contrário deriva-se
    um cenário a partir do slider de taxa de inundação, numa escala
    realista para eventos extremos em Luanda (0–1.5 m de sobre-elevação)."""
    flood_rate_frac = float(data.get("floodRate", 50)) / 100
    water_level_raw = data.get("waterLevel")
    if water_level_raw not in (None, ""):
        water_level_m = float(water_level_raw)
    else:
        water_level_m = flood_rate_frac * 1.5
    return water_level_m, flood_rate_frac


# ==================== ROTAS INFORMATIVAS ====================
@app.route("/api", methods=["GET"])
def api_home():
    return jsonify({
        "message": "API de Simulação de Inundações - Angola",
        "version": "5.0.0",
        "status": "online",
        "features": [
            "Modelo físico sobre DEM real (Copernicus GLO-30, 30m)",
            "População real (WorldPop 100m, constrained)",
            "Sem chamadas de rede por pedido",
        ],
        "endpoints": {
            "health": "/api/health", "info": "/api/info", "provinces": "/api/provinces",
            "municipalities": "/api/municipalities?province=X",
            "bairros": "/api/bairros?province=X&municipality=X",
            "simulate": "/api/simulate (POST)", "elevation": "/api/elevation?lat=X&lon=Y",
        },
    })


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok", "message": "API activa", "timestamp": now_iso(),
        "dem_shape": list(flood_model.dem_shape),
        "municipios_carregados": len(municipalities_gdf),
        "bairros_carregados": len(bairros_gdf),
    })


@app.route("/api/info", methods=["GET"])
def api_info():
    return jsonify({
        "name": "API de Simulação de Inundações - Angola",
        "version": "5.0.0",
        "data_available": {
            "provinces": len(PROVINCES_STATIC), "municipalities": len(municipalities_gdf),
            "bairros": len(bairros_gdf), "bairro_catchments": len(catchments_gdf),
        },
        "elevation_source": "Copernicus GLO-30 DEM (30m), local",
        "population_source": "WorldPop 2020 constrained (100m), local",
    })


@app.route("/api/provinces", methods=["GET"])
def get_provinces():
    result = []
    for _, row in provinces_gdf.iterrows():
        name = row["NAME_1"]
        static = next((p for p in PROVINCES_STATIC if p["name"] == name), None)
        if not static:
            continue
        geom = row.geometry.__geo_interface__
        centroid = row.geometry.centroid
        result.append({
            "id": static["id"], "name": name, "risk": static["risk"],
            "population": int(round(flood_model.zone_population(geom))),
            "area": round(flood_model.zone_area_km2(geom), 1),
            "lat": centroid.y, "lon": centroid.x,
        })
    return jsonify({"success": True, "data": result, "count": len(result), "timestamp": now_iso()})


@app.route("/api/municipalities", methods=["GET"])
def get_municipalities():
    province = request.args.get("province", "Luanda")
    if normalize(province) not in ("luanda", "all", ""):
        return jsonify({"success": True, "data": [], "count": 0})

    result = []
    for _, row in municipalities_gdf.iterrows():
        name = row["NAME_2"]
        geom = row.geometry.__geo_interface__
        centroid = row.geometry.centroid
        result.append({
            "name": name, "province": "Luanda", "risk": risk_for_municipality(name),
            "population": int(round(flood_model.zone_population(geom))),
            "area": round(flood_model.zone_area_km2(geom), 1),
            "lat": centroid.y, "lon": centroid.x,
        })
    result.sort(key=lambda r: r["name"])
    for i, r in enumerate(result, start=1):
        r["id"] = i
    return jsonify({"success": True, "data": result, "count": len(result), "timestamp": now_iso()})


@app.route("/api/bairros", methods=["GET"])
def get_bairros():
    municipality = request.args.get("municipality", None)

    gdf = catchments_gdf
    if municipality and municipality != "all":
        norm_mun = normalize(municipality)
        gdf = gdf[gdf["municipality"].apply(lambda v: normalize(v) == norm_mun)]
        if gdf.empty:
            available = sorted(catchments_gdf["municipality"].dropna().unique().tolist())
            return jsonify({
                "success": True, "data": [], "count": 0,
                "message": f'Nenhum bairro cadastrado para "{municipality}"',
                "available_municipalities": available, "timestamp": now_iso(),
            })

    result = []
    for i, row in enumerate(gdf.itertuples(), start=1):
        name = row.name
        muni = row.municipality
        pt = BAIRRO_POINT_LOOKUP.get((normalize(muni), normalize(name)))
        lat, lon = (pt.y, pt.x) if pt is not None else (row.geometry.centroid.y, row.geometry.centroid.x)
        result.append({
            "id": i, "name": name, "municipality": muni, "risk": risk_for_municipality(muni),
            "population": int(round(flood_model.zone_population(row.geometry.__geo_interface__))),
            "lat": lat, "lon": lon,
        })
    return jsonify({
        "success": True, "data": result, "count": len(result),
        "filter": {"municipality": municipality}, "timestamp": now_iso(),
    })


@app.route("/api/boundaries", methods=["GET"])
def get_boundaries():
    """Nome + coordenada real (ponto, não polígono) de municípios/bairros —
    independente de qualquer simulação, usado só para rotular o mapa assim
    que a página carrega. Devolve pontos de propósito: um polígono grande
    com symbol-placement:"point" faz o MapLibre repetir o rótulo uma vez por
    "tile" interno de desenho quando o zoom é alto — um bairro aparecia com
    o nome duplicado em vários sítios do mapa."""
    level = request.args.get("level", "municipality")
    municipality = request.args.get("municipality", "all")

    if level == "bairro":
        gdf = catchments_gdf
        if municipality and municipality != "all":
            norm_mun = normalize(municipality)
            gdf = gdf[gdf["municipality"].apply(lambda v: normalize(v) == norm_mun)]
        features = []
        for row in gdf.itertuples():
            pt = BAIRRO_POINT_LOOKUP.get((normalize(row.municipality), normalize(row.name)))
            lon, lat = (pt.x, pt.y) if pt is not None else (row.geometry.centroid.x, row.geometry.centroid.y)
            features.append({
                "type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {"name": row.name, "municipality": row.municipality},
            })
        return jsonify({"success": True, "geojson": {"type": "FeatureCollection", "features": features}})

    features = []
    for row in municipalities_gdf.itertuples():
        c = row.geometry.centroid
        features.append({
            "type": "Feature", "geometry": {"type": "Point", "coordinates": [c.x, c.y]},
            "properties": {"name": row.NAME_2, "risk": risk_for_municipality(row.NAME_2)},
        })
    return jsonify({"success": True, "geojson": {"type": "FeatureCollection", "features": features}})


@app.route("/api/elevation", methods=["GET"])
def get_elevation():
    try:
        lat = float(request.args.get("lat"))
        lon = float(request.args.get("lon"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Parâmetros lat/lon inválidos"}), 400

    import rasterio.transform
    row, col = rasterio.transform.rowcol(flood_model.dem_transform, lon, lat)
    if not (0 <= row < flood_model.dem_shape[0] and 0 <= col < flood_model.dem_shape[1]):
        return jsonify({"success": False, "error": "Coordenadas fora da área coberta (Luanda)"}), 400
    elevation = float(flood_model.dem[row, col])
    return jsonify({"success": True, "latitude": lat, "longitude": lon, "elevation": elevation, "unit": "meters"})


# ==================== SIMULAÇÃO ====================
def _muni_result(row, water_level_m, flood_rate_frac, with_bairros):
    name = row.NAME_2
    geom = row.geometry.__geo_interface__
    stats = flood_model.simulate_zone(geom, water_level_m, flood_rate_frac)
    centroid = row.geometry.centroid
    result = {
        "name": name, "province": "Luanda", "risk": risk_for_municipality(name),
        "lat": centroid.y, "lon": centroid.x, **stats,
    }
    if with_bairros:
        bairros = _bairro_results_for_municipality(name, water_level_m, flood_rate_frac)
        result["bairros"] = bairros
        result["bairros_total"] = len(bairros)
        result["bairros_flooded"] = sum(1 for b in bairros if b["flooded"])
    return result


def _bairro_results_for_municipality(muni_name, water_level_m, flood_rate_frac):
    norm_mun = normalize(muni_name)
    sub = catchments_gdf[catchments_gdf["municipality"].apply(lambda v: normalize(v) == norm_mun)]
    results = []
    for row in sub.itertuples():
        name = row.name
        stats = flood_model.simulate_zone(row.geometry.__geo_interface__, water_level_m, flood_rate_frac)
        pt = BAIRRO_POINT_LOOKUP.get((norm_mun, normalize(name)))
        lat, lon = (pt.y, pt.x) if pt is not None else (row.geometry.centroid.y, row.geometry.centroid.x)
        results.append({"name": name, "municipality": muni_name, "lat": lat, "lon": lon, **stats})
    return results


@app.route("/api/simulate", methods=["POST"])
def simulate_flood():
    try:
        data = request.get_json() or {}
        level = data.get("level", "province")
        province = data.get("province", "all")
        municipality = data.get("municipality", "all")
        bairro_sel = data.get("bairro", "all")
        water_level_m, flood_rate_frac = water_level_from_payload(data)

        logger.info(f"Simulação — level={level} province={province} municipality={municipality} "
                    f"bairro={bairro_sel} waterLevel={water_level_m:.2f}m floodRate={flood_rate_frac:.2f}")

        if level == "bairro":
            return _simulate_bairro(province, municipality, bairro_sel, water_level_m, flood_rate_frac)
        if level == "municipality":
            return _simulate_municipality(province, municipality, water_level_m, flood_rate_frac)
        if level == "province":
            return _simulate_province(province, water_level_m, flood_rate_frac)
        return jsonify({"success": False, "error": "Nível inválido. Use: province, municipality ou bairro"}), 400

    except Exception as e:
        logger.exception("Erro na simulação")
        return jsonify({"success": False, "error": str(e)}), 500


def _simulate_province(province, water_level_m, flood_rate_frac):
    if province not in ("all", "Luanda"):
        return jsonify({"success": True, "data": [], "count": 0, "message": "Apenas Luanda disponível"})

    row = provinces_gdf[provinces_gdf["NAME_1"] == "Luanda"].iloc[0]
    geom = row.geometry.__geo_interface__
    stats = flood_model.simulate_zone(geom, water_level_m, flood_rate_frac)

    municipalities_results = [
        _muni_result(r, water_level_m, flood_rate_frac, with_bairros=False)
        for r in municipalities_gdf.itertuples()
    ]
    result = {
        "name": "Luanda", "risk": PROVINCES_STATIC[0]["risk"],
        "lat": row.geometry.centroid.y, "lon": row.geometry.centroid.x,
        **stats, "municipalities": municipalities_results,
    }

    flood_extent = flood_model.flood_geojson(water_level_m, flood_rate_frac, clip_geometry=geom)
    flooded_count = sum(1 for m in municipalities_results if m["flooded"])
    total_affected = sum(m["affectedPopulation"] for m in municipalities_results)

    return jsonify({
        "success": True, "data": [result], "geojson": flood_extent,
        "statistics": {
            "floodedCount": flooded_count, "totalAffected": total_affected,
            "totalItems": len(municipalities_results),
            "avgRisk": (flooded_count / len(municipalities_results) * 100) if municipalities_results else 0,
        },
        "parameters": {"level": "province", "floodRate": flood_rate_frac * 100,
                        "waterLevel": round(water_level_m, 2), "province": province},
        "timestamp": now_iso(),
    })


def _simulate_municipality(province, municipality, water_level_m, flood_rate_frac):
    sub = municipalities_gdf
    if municipality != "all":
        norm = normalize(municipality)
        sub = sub[sub["NAME_2"].apply(lambda n: normalize(n) == norm)]
        if sub.empty:
            return jsonify({"success": False, "error": f'Município "{municipality}" não encontrado'}), 404

    with_bairros = municipality != "all"
    rows = list(sub.itertuples())
    results = [_muni_result(r, water_level_m, flood_rate_frac, with_bairros) for r in rows]

    clip_geom = unary_union([r.geometry for r in rows]).__geo_interface__ if rows else None
    flood_extent = (flood_model.flood_geojson(water_level_m, flood_rate_frac, clip_geometry=clip_geom)
                     if clip_geom else {"type": "FeatureCollection", "features": []})

    flooded_count = sum(1 for r in results if r["flooded"])
    total_affected = sum(r["affectedPopulation"] for r in results)

    return jsonify({
        "success": True, "data": results, "geojson": flood_extent,
        "statistics": {
            "floodedCount": flooded_count, "totalAffected": total_affected, "totalItems": len(results),
            "avgRisk": (flooded_count / len(results) * 100) if results else 0,
        },
        "parameters": {"level": "municipality", "floodRate": flood_rate_frac * 100,
                        "waterLevel": round(water_level_m, 2), "province": province,
                        "municipality": municipality},
        "timestamp": now_iso(),
    })


def _simulate_bairro(province, municipality, bairro_sel, water_level_m, flood_rate_frac):
    if not municipality or municipality == "all":
        return jsonify({
            "success": False, "error": "Seleccione um município específico para simular bairros",
        }), 400

    norm_mun = normalize(municipality)
    sub = catchments_gdf[catchments_gdf["municipality"].apply(lambda v: normalize(v) == norm_mun)]
    if sub.empty:
        available = sorted(catchments_gdf["municipality"].dropna().unique().tolist())
        return jsonify({
            "success": False, "error": f'Nenhum bairro cadastrado para o município "{municipality}"',
            "available_municipalities": available,
        }), 404

    if bairro_sel and bairro_sel != "all":
        sub = sub[sub["name"] == bairro_sel]
        if sub.empty:
            return jsonify({
                "success": False, "error": f'Bairro "{bairro_sel}" não encontrado em {municipality}',
            }), 404

    results, features = [], []
    for row in sub.itertuples():
        name = row.name
        geom_dict = row.geometry.__geo_interface__
        stats = flood_model.simulate_zone(geom_dict, water_level_m, flood_rate_frac)
        pt = BAIRRO_POINT_LOOKUP.get((norm_mun, normalize(name)))
        lat, lon = (pt.y, pt.x) if pt is not None else (row.geometry.centroid.y, row.geometry.centroid.x)
        result_data = {
            "name": name, "municipality": municipality,
            "province": province if province != "all" else "Luanda",
            "lat": lat, "lon": lon, **stats,
        }
        results.append(result_data)
        features.append({"type": "Feature", "geometry": geom_dict, "properties": result_data})

    flooded_count = sum(1 for r in results if r["flooded"])
    total_affected = sum(r["affectedPopulation"] for r in results)
    clip_geom = unary_union([row.geometry for row in sub.itertuples()]).__geo_interface__
    flood_extent = flood_model.flood_geojson(water_level_m, flood_rate_frac, clip_geometry=clip_geom)

    return jsonify({
        "success": True, "data": results, "geojson": flood_extent,
        "bairros_boundaries": {"type": "FeatureCollection", "features": features},
        "statistics": {
            "floodedCount": flooded_count, "totalAffected": total_affected, "totalBairros": len(results),
            "avgRisk": (flooded_count / len(results) * 100) if results else 0,
        },
        "parameters": {"level": "bairro", "floodRate": flood_rate_frac * 100,
                        "waterLevel": round(water_level_m, 2), "province": province,
                        "municipality": municipality, "bairro": bairro_sel},
        "timestamp": now_iso(),
    })


@app.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "error": "Endpoint não encontrado"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"success": False, "error": "Erro interno do servidor"}), 500


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("API de Simulação de Inundações — Angola v5.0 (DEM real)")
    print("=" * 70)
    print("Servidor      : http://0.0.0.0:5000")
    print(f"Municípios    : {len(municipalities_gdf)}")
    print(f"Bairros       : {len(bairros_gdf)}")
    print(f"Grid DEM      : {flood_model.dem_shape}")
    print("=" * 70 + "\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
