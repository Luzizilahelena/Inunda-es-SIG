"""
flood_model.py
===============
Motor de inundação baseado num DEM real (Copernicus GLO-30, 30 m) em vez da
antiga fórmula heurística. Todos os dados (elevação, população, limites
administrativos, catchments de bairro) são carregados uma única vez, no
arranque do processo, a partir de backend/data/ — sem chamadas de rede por
pedido (ver scripts/prepare_data.py para como esses ficheiros são gerados).

Modelo físico (ver README/plano para o racional e limites):
  1. Componente costeira/de maré: células com elevação <= nível de água,
     mantidas apenas se hidrologicamente ligadas ao mar (flood-fill a partir
     de uma máscara-semente de células ao nível do mar), representando maré
     alta / storm surge.
  2. Componente de poças interiores: depressões do terreno (calculadas por
     reconstrução morfológica, tipo "priority-flood") que transbordam quando
     a intensidade de chuva (floodRate) é suficiente, moduladas por um
     factor de drenagem por município (más condições de drenagem = poças
     transbordam com menos chuva).

Não é uma simulação hidráulica 2D (sem velocidade/caudal) — é o mesmo tipo de
modelo "bathtub hidrologicamente conectado" usado por visualizadores públicos
de risco costeiro.
"""

import os
import unicodedata
from functools import lru_cache

import numpy as np
import rasterio
import rasterio.features
import rasterio.warp
from scipy import ndimage
from shapely.geometry import shape as shapely_shape
from skimage.morphology import reconstruction

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Profundidade de água (m) a partir da qual uma célula é considerada
# "inundada" — abaixo disto é ruído numérico / poça insignificante.
MIN_FLOOD_DEPTH = 0.05

# Classificação de severidade por profundidade média (m) na zona — recalibrada
# para profundidades reais de inundação urbana (a antiga heurística usava
# limiares de 8/15/25 m que não correspondiam a metros de água real).
SEVERITY_BANDS = [
    (0.30, "Leve", lambda d: int(5 + d * 20)),
    (0.80, "Moderada", lambda d: int(12 + d * 25)),
    (1.50, "Grave", lambda d: int(25 + d * 35)),
    (float("inf"), "Crítica", lambda d: int(60 + d * 45)),
]

# Factor de drenagem por município: usado apenas para modular quão facilmente
# as depressões do terreno transbordam com chuva (não decide sozinho se há
# inundação — isso agora vem do DEM real). 1.0 = pior drenagem (satura mais
# depto depressa), valores menores = melhor drenagem.
DRAINAGE_FACTOR = {
    "muitoalto": 1.0, "alto": 0.75, "medio": 0.5, "médio": 0.5, "baixo": 0.3,
}
MUNICIPALITY_RISK = {
    "belas": "Alto", "cacuaco": "Muito Alto", "cazenga": "Muito Alto",
    "viana": "Alto", "kilambakiaxi": "Muito Alto", "talatona": "Médio",
    "maianga": "Alto", "rangel": "Muito Alto", "ingombota": "Médio",
    "samba": "Alto", "sambizanga": "Muito Alto", "hojiyahenda": "Muito Alto",
    "camama": "Alto", "kilamba": "Médio", "mulenvos": "Alto",
}


def normalize(name):
    s = unicodedata.normalize("NFD", str(name or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace(" ", "").replace("-", "").replace("_", "").lower()


def classify_severity(avg_depth_m):
    for threshold, label, recovery_fn in SEVERITY_BANDS:
        if avg_depth_m <= threshold:
            return label, recovery_fn(avg_depth_m)
    return "Crítica", 90


class FloodModel:
    def __init__(self, data_dir=DATA_DIR):
        dem_path = os.path.join(data_dir, "dem_luanda.tif")
        pop_path = os.path.join(data_dir, "population_luanda.tif")

        with rasterio.open(dem_path) as ds:
            self.dem = ds.read(1).astype("float32")
            self.dem_transform = ds.transform
            self.dem_crs = ds.crs
            self.dem_shape = self.dem.shape

        with rasterio.open(pop_path) as ds:
            self.population = ds.read(1).astype("float32")
            self.pop_transform = ds.transform
            self.pop_crs = ds.crs
            self.pop_shape = self.population.shape

        # Depressões preenchidas por reconstrução morfológica (equivalente a
        # "priority-flood"/imfill): filled - dem = profundidade da depressão
        # até ao ponto de transbordo mais baixo.
        seed = self.dem.copy()
        seed[1:-1, 1:-1] = self.dem.max()
        self.filled_dem = reconstruction(seed, self.dem, method="erosion").astype("float32")
        self.depression_depth = np.clip(self.filled_dem - self.dem, 0, None)

        # Máscara-semente do "mar": células muito próximas do nível do mar.
        # A área de interesse foi recortada com margem à volta da província,
        # pelo que o oceano a oeste está sempre representado dentro do grid.
        self.sea_seed = self.dem <= 0.3

        # Água permanente (o próprio oceano Atlântico dentro da AOI): a maior
        # componente ligada ao nível do mar. Excluída de tudo o resto — não é
        # "inundação", já é água em qualquer cenário, e sem esta exclusão
        # cada pedido devolvia o oceano inteiro como mancha inundada.
        labeled_sea, _ = ndimage.label(self.dem <= 0.05)
        if labeled_sea.max() > 0:
            counts = np.bincount(labeled_sea.ravel())
            counts[0] = 0  # fundo (não-água) não conta
            largest_label = counts.argmax()
            self.permanent_water_mask = labeled_sea == largest_label
        else:
            self.permanent_water_mask = np.zeros(self.dem_shape, dtype=bool)

        self.drainage_grid = self._build_drainage_grid(data_dir)

        self._flood_cache = {}

    # ---------------------------------------------------------------- setup
    def _build_drainage_grid(self, data_dir):
        import geopandas as gpd

        munis_path = os.path.join(data_dir, "municipalities.geojson")
        gdf = gpd.read_file(munis_path)
        gdf = gdf[gdf["NAME_1"] == "Luanda"]

        shapes = []
        for _, row in gdf.iterrows():
            risk = MUNICIPALITY_RISK.get(normalize(row["NAME_2"]), "Médio")
            factor = DRAINAGE_FACTOR.get(normalize(risk), 0.5)
            shapes.append((row.geometry, factor))

        if not shapes:
            return np.full(self.dem_shape, 0.5, dtype="float32")

        grid = rasterio.features.rasterize(
            shapes, out_shape=self.dem_shape, transform=self.dem_transform,
            fill=0.5, dtype="float32",
        )
        return grid

    # ------------------------------------------------------------ flood core
    def _flood_key(self, water_level_m, flood_rate_frac):
        return (round(water_level_m, 2), round(flood_rate_frac, 3))

    def compute_flood(self, water_level_m, flood_rate_frac):
        """Devolve (flood_mask, depth) alinhados ao grid do DEM, com cache
        por combinação (nível de água, taxa de inundação) — reutilizado
        entre municípios/bairros de um mesmo pedido de província."""
        key = self._flood_key(water_level_m, flood_rate_frac)
        if key in self._flood_cache:
            return self._flood_cache[key]

        water_level_m, flood_rate_frac = key

        # 1) Maré / storm surge: ligado hidrologicamente ao mar.
        coastal_candidate = self.dem <= max(water_level_m, 0)
        if water_level_m > 0 and coastal_candidate.any():
            labeled, _ = ndimage.label(coastal_candidate)
            sea_labels = set(np.unique(labeled[self.sea_seed & coastal_candidate]))
            sea_labels.discard(0)
            coastal_mask = np.isin(labeled, list(sea_labels)) if sea_labels else np.zeros_like(coastal_candidate)
        else:
            coastal_mask = np.zeros_like(coastal_candidate)
        coastal_depth = np.where(coastal_mask, np.clip(water_level_m - self.dem, 0, None), 0.0)

        # 2) Poças interiores: depressões que transbordam com a chuva,
        #    moduladas pela drenagem local (pior drenagem -> transborda com
        #    menos chuva).
        max_pond_depth = (flood_rate_frac * 2.0) * self.drainage_grid
        pond_mask = (self.depression_depth > 0) & (self.depression_depth <= max_pond_depth)
        pond_depth = np.where(pond_mask, self.depression_depth, 0.0)

        depth = np.maximum(coastal_depth, pond_depth).astype("float32")
        depth[self.permanent_water_mask] = 0.0
        flood_mask = depth > MIN_FLOOD_DEPTH

        result = (flood_mask, depth)
        self._flood_cache[key] = result
        # Cada entrada guarda dois arrays do tamanho do DEM (~39MB); limite
        # baixo de propósito para não deixar a memória crescer sem controlo
        # num processo de longa duração (ex.: worker gunicorn em produção) —
        # o alocador do Python/numpy nem sempre devolve memória libertada ao
        # SO, por isso o tecto real de RSS fica bem acima do valor "lógico"
        # da cache; mantém-se este número pequeno de propósito.
        if len(self._flood_cache) > 6:
            self._flood_cache.pop(next(iter(self._flood_cache)))
        return result

    @lru_cache(maxsize=6)
    def _flood_fraction_on_pop_grid(self, water_level_m, flood_rate_frac):
        flood_mask, _ = self.compute_flood(water_level_m, flood_rate_frac)
        fraction = np.zeros(self.pop_shape, dtype="float32")
        rasterio.warp.reproject(
            source=flood_mask.astype("float32"),
            destination=fraction,
            src_transform=self.dem_transform, src_crs=self.dem_crs,
            dst_transform=self.pop_transform, dst_crs=self.pop_crs,
            resampling=rasterio.warp.Resampling.average,
        )
        return fraction

    # ------------------------------------------------------- info sem cenário
    def zone_population(self, geometry):
        """População real (WorldPop) dentro da zona, sem correr nenhum
        cenário de inundação — usado pelos endpoints informativos."""
        pop_zone_mask = rasterio.features.geometry_mask(
            [geometry], out_shape=self.pop_shape, transform=self.pop_transform, invert=True,
        )
        return float(self.population[pop_zone_mask].sum())

    def zone_area_km2(self, geometry):
        deg_to_km_lat = 111.0
        deg_to_km_lon = 111.0 * np.cos(np.radians(8.8))
        return shapely_shape(geometry).area * deg_to_km_lat * deg_to_km_lon

    def zone_elevation(self, geometry):
        zone_mask = rasterio.features.geometry_mask(
            [geometry], out_shape=self.dem_shape, transform=self.dem_transform, invert=True,
        )
        if not zone_mask.any():
            zone_mask = self._nearest_cell_mask(geometry)
        vals = self.dem[zone_mask]
        return float(vals.mean()) if vals.size else 0.0

    # --------------------------------------------------------------- zonas
    def simulate_zone(self, geometry, water_level_m, flood_rate_frac):
        """geometry: dict GeoJSON (WGS84) da zona (província/município/bairro
        catchment). Devolve estatísticas + a mancha de inundação recortada à
        zona, em metros e população reais."""
        water_level_m = float(water_level_m)
        flood_rate_frac = float(flood_rate_frac)
        flood_mask, depth = self.compute_flood(water_level_m, flood_rate_frac)

        zone_mask = rasterio.features.geometry_mask(
            [geometry], out_shape=self.dem_shape, transform=self.dem_transform, invert=True,
        )
        if not zone_mask.any():
            zone_mask = self._nearest_cell_mask(geometry)

        zone_dem = self.dem[zone_mask]
        elevation = {
            "avg": float(zone_dem.mean()) if zone_dem.size else 0.0,
            "min": float(zone_dem.min()) if zone_dem.size else 0.0,
            "max": float(zone_dem.max()) if zone_dem.size else 0.0,
        }

        flooded_depths = depth[zone_mask & flood_mask]
        is_flooded = flooded_depths.size > 0
        avg_depth = float(flooded_depths.mean()) if is_flooded else 0.0
        max_depth = float(flooded_depths.max()) if is_flooded else 0.0
        flooded_area_km2 = flooded_depths.size * self._dem_cell_area_km2()

        pop_zone_mask = rasterio.features.geometry_mask(
            [geometry], out_shape=self.pop_shape, transform=self.pop_transform, invert=True,
        )
        total_population = float(self.population[pop_zone_mask].sum())
        fraction = self._flood_fraction_on_pop_grid(*self._flood_key(water_level_m, flood_rate_frac))
        affected_population = float((self.population * fraction)[pop_zone_mask].sum())
        affected_population = min(affected_population, total_population)

        severity, recovery_days = (classify_severity(avg_depth) if is_flooded else ("Nenhuma", 0))

        return {
            "flooded": bool(is_flooded),
            "waterLevel": round(avg_depth, 2),
            "maxWaterLevel": round(max_depth, 2),
            "severity": severity,
            "recoveryDays": recovery_days if is_flooded else 0,
            "affectedPopulation": int(round(affected_population)) if is_flooded else 0,
            "totalPopulation": int(round(total_population)),
            "floodedAreaKm2": round(flooded_area_km2, 3),
            "elevation": round(elevation["avg"], 1),
            "elevation_min": round(elevation["min"], 1),
            "elevation_max": round(elevation["max"], 1),
        }

    def _dem_cell_area_km2(self):
        # graus -> km aproximados a esta latitude (Luanda, ~-8.8°)
        deg_to_km_lat = 111.0
        deg_to_km_lon = 111.0 * np.cos(np.radians(8.8))
        px_w = abs(self.dem_transform.a) * deg_to_km_lon
        px_h = abs(self.dem_transform.e) * deg_to_km_lat
        return px_w * px_h

    def _nearest_cell_mask(self, geometry):
        """Fallback para zonas menores que um pixel do DEM (ex.: bairro
        pontual sem catchment válido): usa a célula mais próxima do
        centróide."""
        geom = shapely_shape(geometry)
        c = geom.centroid
        row, col = rasterio.transform.rowcol(self.dem_transform, c.x, c.y)
        mask = np.zeros(self.dem_shape, dtype=bool)
        row = min(max(row, 0), self.dem_shape[0] - 1)
        col = min(max(col, 0), self.dem_shape[1] - 1)
        mask[row, col] = True
        return mask

    # ------------------------------------------------------------- polígonos
    def flood_geojson(self, water_level_m, flood_rate_frac, clip_geometry=None):
        """Vectoriza a mancha de inundação em polígonos por banda de
        severidade, para desenho no mapa (substitui os pontos aleatórios do
        heatmap antigo por geometria real)."""
        flood_mask, depth = self.compute_flood(float(water_level_m), float(flood_rate_frac))

        if clip_geometry is not None:
            clip_mask = rasterio.features.geometry_mask(
                [clip_geometry], out_shape=self.dem_shape, transform=self.dem_transform, invert=True,
            )
            flood_mask = flood_mask & clip_mask

        if not flood_mask.any():
            return {"type": "FeatureCollection", "features": []}

        # Remove manchas de poucos pixels (ruído do DEM/depressões pontuais)
        # antes de classificar por severidade — sem isto um único pedido
        # gera dezenas de milhares de polígonos minúsculos e demora segundos
        # a construir. Sieva-se a máscara binária (uma só classe) em vez do
        # raster já dividido por banda: sievar por banda fragmenta uma
        # mancha contígua nas fronteiras de profundidade (Leve/Moderada/...)
        # em pedaços cada um pequeno de mais, apagando manchas reais inteiras.
        # O tamanho do sieve escala com a extensão inundada: zonas pequenas
        # (bairro/município) mantêm detalhe fino; uma vista de toda a
        # província precisa de mais agregação para o payload ficar leve.
        n_flooded = int(flood_mask.sum())
        if n_flooded < 5_000:
            sieve_size = 8
        elif n_flooded < 50_000:
            sieve_size = 25
        elif n_flooded < 300_000:
            sieve_size = 80
        else:
            sieve_size = 200
        flood_mask = rasterio.features.sieve(flood_mask.astype("uint8"), size=sieve_size, connectivity=8) > 0
        if not flood_mask.any():
            return {"type": "FeatureCollection", "features": []}

        band_edges = [b[0] for b in SEVERITY_BANDS]
        band_labels = [b[1] for b in SEVERITY_BANDS]
        band_id = np.zeros(self.dem_shape, dtype="uint8")
        prev = 0.0
        for i, edge in enumerate(band_edges):
            band_id[(depth > prev) & (depth <= edge) & flood_mask] = i + 1
            prev = edge

        features = []
        for i, label in enumerate(band_labels, start=1):
            band_mask = band_id == i
            if not band_mask.any():
                continue
            band_depth = float(depth[band_mask].mean())
            for geom_dict, value in rasterio.features.shapes(
                band_id, mask=band_mask, transform=self.dem_transform
            ):
                poly = shapely_shape(geom_dict).simplify(0.0003, preserve_topology=True)
                if poly.is_empty or poly.area < 1e-8:
                    continue
                features.append({
                    "type": "Feature",
                    "geometry": poly.__geo_interface__,
                    "properties": {"severity": label, "avgDepth": round(band_depth, 2)},
                })

        return {"type": "FeatureCollection", "features": features}
