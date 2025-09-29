import React, { useState, useEffect, useRef } from 'react';
import { MapPin, Droplets, AlertTriangle, BarChart3, RefreshCw, Home, Building2 } from 'lucide-react';
import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

const FloodSimulationDashboard = () => {
  const [simulationData, setSimulationData] = useState(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [floodRate, setFloodRate] = useState(50);
  const [viewLevel, setViewLevel] = useState('province'); // province, municipality, district
  const [selectedProvince, setSelectedProvince] = useState('all');
  const [selectedMunicipality, setSelectedMunicipality] = useState('all');
  const [selectedDistrict, setSelectedDistrict] = useState('all');
  const [geoData, setGeoData] = useState(null);

  const mapRef = useRef();

  // URLs for GeoJSON
  const adm1Url = 'https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/AGO/ADM1/geoBoundaries-AGO-ADM1.geojson';
  const adm2Url = 'https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/AGO/ADM2/geoBoundaries-AGO-ADM2.geojson';

  // Function to normalize names (remove accents and case-insensitive)
  const normalizeName = (name) => {
    if (!name) return '';
    return name.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  };

  // Dados das províncias (expanded if possible, but keeping original)
  const provinces = [
    { name: 'Benguela', risk: 'Alto', population: 2231385, area: 31788 },
    { name: 'Bié', risk: 'Médio', population: 1455255, area: 70314 },
    { name: 'Cuando Cubango', risk: 'Baixo', population: 534002, area: 199049 },
    { name: 'Cunene', risk: 'Médio', population: 990087, area: 78342 },
    { name: 'Cuanza Norte', risk: 'Alto', population: 443386, area: 24110 },
    { name: 'Huambo', risk: 'Alto', population: 2019555, area: 34270 },
    { name: 'Luanda', risk: 'Muito Alto', population: 8329517, area: 2417 },
    { name: 'Lunda Sul', risk: 'Médio', population: 537587, area: 77637 },
    { name: 'Malanje', risk: 'Alto', population: 1108404, area: 97602 },
    { name: 'Moxico', risk: 'Baixo', population: 758568, area: 223023 },
    { name: 'Uíge', risk: 'Alto', population: 1483118, area: 58698 },
    { name: 'Zaire', risk: 'Médio', population: 594428, area: 40130 }
  ];

  // Dados dos municípios por província
  const municipalities = {
    'Luanda': [
      { name: 'Belas', population: 600000, area: 500 },
      { name: 'Cacuaco', population: 850000, area: 450 },
      { name: 'Cazenga', population: 980000, area: 32 },
      { name: 'Icolo e Bengo', population: 150000, area: 3600 },
      { name: 'Luanda', population: 2200000, area: 116 },
      { name: 'Quiçama', population: 25000, area: 13900 },
      { name: 'Viana', population: 2000000, area: 1700 }
    ],
    'Benguela': [
      { name: 'Balombo', population: 35000, area: 3000 },
      { name: 'Benguela', population: 555000, area: 2800 },
      { name: 'Bocoio', population: 120000, area: 4500 },
      { name: 'Caimbambo', population: 95000, area: 2100 },
      { name: 'Catumbela', population: 300000, area: 3600 },
      { name: 'Lobito', population: 450000, area: 3600 }
    ],
    'Huambo': [
      { name: 'Bailundo', population: 400000, area: 5000 },
      { name: 'Cachiungo', population: 75000, area: 3200 },
      { name: 'Caála', population: 180000, area: 3400 },
      { name: 'Huambo', population: 650000, area: 4200 },
      { name: 'Londuimbali', population: 85000, area: 2800 },
      { name: 'Longonjo', population: 120000, area: 4100 }
    ]
  };

  // Dados dos bairros/distritos por município
  const districts = {
    'Luanda': [
      { name: 'Ingombota', population: 150000, type: 'Comercial' },
      { name: 'Maianga', population: 180000, type: 'Residencial' },
      { name: 'Rangel', population: 220000, type: 'Residencial' },
      { name: 'Sambizanga', population: 280000, type: 'Residencial' },
      { name: 'Ilha de Luanda', population: 45000, type: 'Turístico' },
      { name: 'Maculusso', population: 90000, type: 'Residencial' }
    ],
    'Cacuaco': [
      { name: 'Kikolo', population: 180000, type: 'Residencial' },
      { name: 'Sequele', population: 140000, type: 'Residencial' },
      { name: 'Funda', population: 160000, type: 'Residencial' },
      { name: 'Quiage', population: 95000, type: 'Residencial' }
    ],
    'Viana': [
      { name: 'Viana Sede', population: 250000, type: 'Residencial' },
      { name: 'Calumbo', population: 180000, type: 'Residencial' },
      { name: 'Catete', population: 120000, type: 'Residencial' },
      { name: 'Kikuxi', population: 200000, type: 'Industrial' }
    ],
    'Benguela': [
      { name: 'Centro', population: 85000, type: 'Comercial' },
      { name: 'Compão', population: 70000, type: 'Residencial' },
      { name: 'Calombotão', population: 55000, type: 'Residencial' },
      { name: 'Praia Morena', population: 40000, type: 'Residencial' }
    ],
    'Lobito': [
      { name: 'Canata', population: 90000, type: 'Residencial' },
      { name: 'Caponte', population: 75000, type: 'Residencial' },
      { name: 'Compão', population: 60000, type: 'Residencial' },
      { name: 'Restinga', population: 50000, type: 'Portuário' }
    ]
  };

  const riskColors = {
    'Muito Alto': { bg: 'bg-red-600', hex: '#DC2626' },
    'Alto': { bg: 'bg-orange-500', hex: '#EA580C' },
    'Médio': { bg: 'bg-yellow-500', hex: '#EAB308' },
    'Baixo': { bg: 'bg-green-500', hex: '#16A34A' }
  };

  const getRiskBgColor = (risk) => riskColors[risk]?.bg || 'bg-gray-400';
  const getRiskHexColor = (risk) => riskColors[risk]?.hex || '#9CA3AF';

  useEffect(() => {
    let url = '';
    if (viewLevel === 'province') {
      url = adm1Url;
    } else if (viewLevel === 'municipality') {
      url = adm2Url;
    } else {
      setGeoData(null);
      return;
    }

    fetch(url)
      .then((res) => res.json())
      .then((data) => setGeoData(data))
      .catch((error) => console.error('Error fetching GeoJSON:', error));
  }, [viewLevel]);

  const runSimulation = () => {
    setIsSimulating(true);

    setTimeout(() => {
      const rate = floodRate / 100;
      let simulated;

      if (viewLevel === 'province') {
        simulated = provinces.map((province) => {
          const shouldFlood = selectedProvince === 'all' || selectedProvince === province.name;
          const isFlooded = shouldFlood && Math.random() < rate;
          const affectedComunas = isFlooded ? Math.floor(Math.random() * 15) + 5 : 0;
          const affectedPopulation = isFlooded ? Math.floor(province.population * (Math.random() * 0.3 + 0.1)) : 0;

          return {
            ...province,
            flooded: isFlooded,
            affectedComunas,
            affectedPopulation
          };
        });
      } else if (viewLevel === 'municipality') {
        const municList = selectedProvince !== 'all' && municipalities[selectedProvince]
          ? municipalities[selectedProvince]
          : Object.values(municipalities).flat();

        simulated = municList.map((munic) => {
          const isFlooded = Math.random() < rate;
          const affectedDistricts = isFlooded ? Math.floor(Math.random() * 8) + 2 : 0;
          const affectedPopulation = isFlooded ? Math.floor(munic.population * (Math.random() * 0.4 + 0.1)) : 0;

          return {
            ...munic,
            province: selectedProvince !== 'all' ? selectedProvince : Object.keys(municipalities).find((p) => municipalities[p].some((m) => m.name === munic.name)),
            flooded: isFlooded,
            affectedDistricts,
            affectedPopulation,
            risk: isFlooded ? 'Alto' : 'Baixo'
          };
        });
      } else if (viewLevel === 'district') {
        let districtList;

        if (selectedDistrict !== 'all') {
          districtList = Object.values(districts).flat().filter((d) => d.name === selectedDistrict);
        } else if (selectedMunicipality !== 'all' && districts[selectedMunicipality]) {
          districtList = districts[selectedMunicipality];
        } else if (selectedProvince !== 'all') {
          const provinceMunicipalities = municipalities[selectedProvince] || [];
          districtList = provinceMunicipalities
            .map((m) => districts[m.name] || [])
            .flat();
        } else {
          districtList = Object.values(districts).flat();
        }

        simulated = districtList.map((district) => {
          const isFlooded = Math.random() < rate;
          const affectedPopulation = isFlooded ? Math.floor(district.population * (Math.random() * 0.5 + 0.2)) : 0;

          return {
            ...district,
            municipality: selectedMunicipality !== 'all' ? selectedMunicipality : Object.keys(districts).find((m) => districts[m].some((d) => d.name === district.name)),
            flooded: isFlooded,
            affectedPopulation,
            risk: isFlooded ? 'Alto' : 'Baixo'
          };
        });
      }

      setSimulationData(simulated);
      setIsSimulating(false);
    }, 1500);
  };

  const getStatistics = () => {
    if (!simulationData) return null;

    const floodedCount = simulationData.filter((p) => p.flooded).length;
    const totalAffected = simulationData.reduce((sum, p) => sum + p.affectedPopulation, 0);
    const totalAreas =
      viewLevel === 'province'
        ? simulationData.reduce((sum, p) => sum + (p.affectedComunas || 0), 0)
        : viewLevel === 'municipality'
        ? simulationData.reduce((sum, p) => sum + (p.affectedDistricts || 0), 0)
        : floodedCount;
    const avgRisk = (floodedCount / simulationData.length) * 100;

    return { floodedCount, totalAffected, totalAreas, avgRisk };
  };

  const stats = getStatistics();

  const availableMunicipalities =
    selectedProvince !== 'all' && municipalities[selectedProvince] ? municipalities[selectedProvince] : [];

  const availableDistricts =
    selectedMunicipality !== 'all' && districts[selectedMunicipality] ? districts[selectedMunicipality] : [];

  const getMapStyle = (feature) => {
    const name = feature.properties.shapeName;
    let item;
    if (simulationData) {
      item = simulationData.find((i) => normalizeName(i.name) === normalizeName(name));
    } else if (viewLevel === 'province') {
      item = provinces.find((p) => normalizeName(p.name) === normalizeName(name));
    } else if (viewLevel === 'municipality') {
      item = Object.values(municipalities).flat().find((m) => normalizeName(m.name) === normalizeName(name));
    }
    const risk = item ? item.risk : 'Baixo';
    const flooded = item ? item.flooded : false;
    const color = flooded ? '#3B82F6' : getRiskHexColor(risk);
    return {
      fillColor: color,
      color: '#000',
      weight: 1,
      opacity: 1,
      fillOpacity: 0.7
    };
  };

  const onEachFeature = (feature, layer) => {
    layer.bindPopup(feature.properties.shapeName);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-cyan-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-2xl shadow-xl p-8 mb-6">
          <div className="flex items-center gap-4 mb-4">
            <div className="bg-blue-600 p-3 rounded-xl">
              <Droplets className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-800">Simulador de Inundações</h1>
              <p className="text-gray-600">Sistema de Análise e Previsão - Angola</p>
            </div>
          </div>

          {/* Seleção de Nível de Visualização */}
          <div className="bg-blue-50 rounded-xl p-4 mb-6">
            <label className="block text-sm font-semibold text-gray-700 mb-3">
              Nível de Visualização
            </label>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <button
                onClick={() => {
                  setViewLevel('province');
                  setSimulationData(null);
                  setSelectedMunicipality('all');
                  setSelectedDistrict('all');
                }}
                className={`p-4 rounded-lg font-semibold transition-all ${
                  viewLevel === 'province'
                    ? 'bg-blue-600 text-white shadow-lg'
                    : 'bg-white text-gray-700 hover:bg-blue-100'
                }`}
              >
                <MapPin className="w-5 h-5 mx-auto mb-2" />
                Províncias
              </button>
              <button
                onClick={() => {
                  setViewLevel('municipality');
                  setSimulationData(null);
                  setSelectedDistrict('all');
                }}
                className={`p-4 rounded-lg font-semibold transition-all ${
                  viewLevel === 'municipality'
                    ? 'bg-blue-600 text-white shadow-lg'
                    : 'bg-white text-gray-700 hover:bg-blue-100'
                }`}
              >
                <Building2 className="w-5 h-5 mx-auto mb-2" />
                Municípios
              </button>
              <button
                onClick={() => {
                  setViewLevel('district');
                  setSimulationData(null);
                }}
                className={`p-4 rounded-lg font-semibold transition-all ${
                  viewLevel === 'district'
                    ? 'bg-blue-600 text-white shadow-lg'
                    : 'bg-white text-gray-700 hover:bg-blue-100'
                }`}
              >
                <Home className="w-5 h-5 mx-auto mb-2" />
                Bairros/Distritos
              </button>
            </div>
          </div>

          {/* Controles de Simulação */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
            {/* Taxa de Inundação */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Taxa de Inundação (%)
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={floodRate}
                onChange={(e) => setFloodRate(e.target.value)}
                className="w-full h-2 bg-blue-200 rounded-lg appearance-none cursor-pointer"
              />
              <div className="text-center mt-2 text-2xl font-bold text-blue-600">
                {floodRate}%
              </div>
            </div>

            {/* Seleção de Província */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Província
              </label>
              <select
                value={selectedProvince}
                onChange={(e) => {
                  setSelectedProvince(e.target.value);
                  setSelectedMunicipality('all');
                  setSelectedDistrict('all');
                  setSimulationData(null);
                }}
                className="w-full p-3 border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none"
              >
                <option value="all">Todas</option>
                {provinces.map((p) => (
                  <option key={p.name} value={p.name}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Seleção de Município */}
            {(viewLevel === 'municipality' || viewLevel === 'district') && (
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Município
                </label>
                <select
                  value={selectedMunicipality}
                  onChange={(e) => {
                    setSelectedMunicipality(e.target.value);
                    setSelectedDistrict('all');
                    setSimulationData(null);
                  }}
                  disabled={availableMunicipalities.length === 0}
                  className="w-full p-3 border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none disabled:bg-gray-100 disabled:cursor-not-allowed"
                >
                  <option value="all">Todos</option>
                  {availableMunicipalities.map((m) => (
                    <option key={m.name} value={m.name}>
                      {m.name}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Seleção de Bairro/Distrito */}
            {viewLevel === 'district' && (
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Bairro/Distrito
                </label>
                <select
                  value={selectedDistrict}
                  onChange={(e) => {
                    setSelectedDistrict(e.target.value);
                    setSimulationData(null);
                  }}
                  disabled={availableDistricts.length === 0}
                  className="w-full p-3 border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none disabled:bg-gray-100 disabled:cursor-not-allowed"
                >
                  <option value="all">Todos</option>
                  {availableDistricts.map((d) => (
                    <option key={d.name} value={d.name}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Botão de Simulação */}
            <div className="flex items-end">
              <button
                onClick={runSimulation}
                disabled={isSimulating}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-bold py-3 px-6 rounded-lg flex items-center justify-center gap-2 transition-all transform hover:scale-105"
              >
                {isSimulating ? (
                  <>
                    <RefreshCw className="w-5 h-5 animate-spin" />
                    Simulando...
                  </>
                ) : (
                  <>
                    <BarChart3 className="w-5 h-5" />
                    Executar
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Mapa */}
        {(viewLevel === 'province' || viewLevel === 'municipality') && (
          <div className="bg-white rounded-2xl shadow-xl p-6 mb-6">
            <h2 className="text-2xl font-bold text-gray-800 mb-4 flex items-center gap-2">
              <MapPin className="w-6 h-6" />
              Mapa de {viewLevel === 'province' ? 'Províncias' : 'Municípios'}
            </h2>
            {geoData ? (
              <MapContainer
                center={[-12.5, 18.5]}
                zoom={5}
                style={{ height: '500px', width: '100%' }}
                ref={mapRef}
              >
                <TileLayer
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                />
                <GeoJSON
                  data={geoData}
                  style={getMapStyle}
                  onEachFeature={onEachFeature}
                />
              </MapContainer>
            ) : (
              <p className="text-center text-gray-500">Carregando mapa...</p>
            )}
          </div>
        )}

        {/* Estatísticas */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-xl shadow-lg p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm font-semibold">
                    {viewLevel === 'province'
                      ? 'Províncias'
                      : viewLevel === 'municipality'
                      ? 'Municípios'
                      : 'Bairros'}{' '}
                    Afetados
                  </p>
                  <p className="text-3xl font-bold text-red-600 mt-2">{stats.floodedCount}</p>
                </div>
                <AlertTriangle className="w-12 h-12 text-red-400" />
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-lg p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm font-semibold">População Afetada</p>
                  <p className="text-3xl font-bold text-orange-600 mt-2">
                    {stats.totalAffected.toLocaleString('pt-AO')}
                  </p>
                </div>
                <MapPin className="w-12 h-12 text-orange-400" />
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-lg p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm font-semibold">
                    {viewLevel === 'province'
                      ? 'Comunas'
                      : viewLevel === 'municipality'
                      ? 'Distritos'
                      : 'Áreas'}{' '}
                    Afetadas
                  </p>
                  <p className="text-3xl font-bold text-blue-600 mt-2">{stats.totalAreas}</p>
                </div>
                <Droplets className="w-12 h-12 text-blue-400" />
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-lg p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm font-semibold">Taxa de Risco</p>
                  <p className="text-3xl font-bold text-purple-600 mt-2">
                    {stats.avgRisk.toFixed(1)}%
                  </p>
                </div>
                <BarChart3 className="w-12 h-12 text-purple-400" />
              </div>
            </div>
          </div>
        )}

        {/* Tabela de Dados */}
        <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
          <div className="bg-gradient-to-r from-blue-600 to-cyan-600 p-6">
            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
              {viewLevel === 'province' && <MapPin className="w-6 h-6" />}
              {viewLevel === 'municipality' && <Building2 className="w-6 h-6" />}
              {viewLevel === 'district' && <Home className="w-6 h-6" />}
              Dados de{' '}
              {viewLevel === 'province'
                ? 'Províncias'
                : viewLevel === 'municipality'
                ? 'Municípios'
                : 'Bairros/Distritos'}
            </h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                    {viewLevel === 'province'
                      ? 'Província'
                      : viewLevel === 'municipality'
                      ? 'Município'
                      : 'Bairro/Distrito'}
                  </th>
                  {viewLevel === 'district' && (
                    <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                      Tipo
                    </th>
                  )}
                  {viewLevel !== 'district' && (
                    <>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                        Nível de Risco
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                        Área (km²)
                      </th>
                    </>
                  )}
                  <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                    População Total
                  </th>
                  {simulationData && (
                    <>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                        População Afetada
                      </th>
                      {viewLevel === 'province' && (
                        <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                          Comunas Afetadas
                        </th>
                      )}
                      {viewLevel === 'municipality' && (
                        <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                          Distritos Afetados
                        </th>
                      )}
                    </>
                  )}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {simulationData ? (
                  simulationData.map((item, idx) => (
                    <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          {viewLevel === 'province' && <MapPin className="w-5 h-5 text-blue-500 mr-2" />}
                          {viewLevel === 'municipality' && <Building2 className="w-5 h-5 text-green-500 mr-2" />}
                          {viewLevel === 'district' && <Home className="w-5 h-5 text-purple-500 mr-2" />}
                          <span className="font-semibold text-gray-900">{item.name}</span>
                        </div>
                      </td>
                      {viewLevel === 'district' && (
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs font-semibold">
                            {item.type}
                          </span>
                        </td>
                      )}
                      {viewLevel !== 'district' && (
                        <>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span
                              className={`px-3 py-1 rounded-full text-white text-xs font-bold ${getRiskBgColor(
                                item.risk
                              )}`}
                            >
                              {item.risk}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-gray-700">
                            {item.area.toLocaleString('pt-AO')}
                          </td>
                        </>
                      )}
                      <td className="px-6 py-4 whitespace-nowrap text-gray-700">
                        {item.population.toLocaleString('pt-AO')}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {item.flooded ? (
                          <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-bold flex items-center gap-1 w-fit">
                            <Droplets className="w-4 h-4" />
                            Inundada
                          </span>
                        ) : (
                          <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-xs font-bold">
                            Segura
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`font-semibold ${item.flooded ? 'text-red-600' : 'text-gray-400'}`}>
                          {item.affectedPopulation.toLocaleString('pt-AO')}
                        </span>
                      </td>
                      {viewLevel === 'province' && (
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`font-semibold ${item.flooded ? 'text-blue-600' : 'text-gray-400'}`}>
                            {item.affectedComunas}
                          </span>
                        </td>
                      )}
                      {viewLevel === 'municipality' && (
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`font-semibold ${item.flooded ? 'text-blue-600' : 'text-gray-400'}`}>
                            {item.affectedDistricts}
                          </span>
                        </td>
                      )}
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="8" className="p-12 text-center">
                      <Droplets className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                      <p className="text-gray-500 text-lg">
                        Selecione os parâmetros e execute uma simulação para visualizar os dados
                      </p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Legenda */}
        <div className="mt-6 bg-white rounded-xl shadow-lg p-6">
          <h3 className="font-bold text-gray-800 mb-3 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-yellow-600" />
            Níveis de Risco
          </h3>
          <div className="flex flex-wrap gap-4">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-red-600 rounded"></div>
              <span className="text-sm text-gray-700">Muito Alto</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-orange-500 rounded"></div>
              <span className="text-sm text-gray-700">Alto</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-yellow-500 rounded"></div>
              <span className="text-sm text-gray-700">Médio</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-green-500 rounded"></div>
              <span className="text-sm text-gray-700">Baixo</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-blue-500 rounded"></div>
              <span className="text-sm text-gray-700">Inundada (Simulação)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FloodSimulationDashboard;