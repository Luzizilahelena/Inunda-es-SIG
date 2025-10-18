// Inicializar o mapa
const map = L.map('map').setView([-8.8383, 13.2437], 6); // Centro em Luanda, Angola
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

// Elementos do formulário
const levelSelect = document.getElementById('level');
const provinceSelect = document.getElementById('province');
const municipalitySelect = document.getElementById('municipality');
const districtSelect = document.getElementById('district');
const form = document.getElementById('simulation-form');
const statisticsDiv = document.getElementById('statistics');

// Carregar províncias
async function loadProvinces() {
    try {
        const response = await axios.get('http://localhost:5000/api/provinces');
        if (response.data.success) {
            provinceSelect.innerHTML = '<option value="all">Todas</option>';
            response.data.data.forEach(province => {
                const option = document.createElement('option');
                option.value = province.name;
                option.textContent = province.name;
                provinceSelect.appendChild(option);
            });
        } else {
            alert('Erro ao carregar províncias: ' + response.data.error);
        }
    } catch (error) {
        console.error('Erro ao carregar províncias:', error);
        alert('Erro ao conectar com a API. Verifique se o servidor está rodando.');
    }
}

// Carregar municípios com base na província selecionada
async function loadMunicipalities(province) {
    try {
        const url = province === 'all' ? 'http://localhost:5000/api/municipalities' : `http://localhost:5000/api/municipalities?province=${province}`;
        const response = await axios.get(url);
        if (response.data.success) {
            municipalitySelect.innerHTML = '<option value="all">Todas</option>';
            response.data.data.forEach(municipality => {
                const option = document.createElement('option');
                option.value = municipality.name;
                option.textContent = municipality.name;
                municipalitySelect.appendChild(option);
            });
            municipalitySelect.disabled = false;
        } else {
            alert('Erro ao carregar municípios: ' + response.data.error);
        }
    } catch (error) {
        console.error('Erro ao carregar municípios:', error);
        alert('Erro ao conectar com a API.');
    }
}

// Carregar bairros com base no município selecionado
async function loadDistricts(province, municipality) {
    try {
        let url = 'http://localhost:5000/api/districts';
        if (province !== 'all') url += `?province=${province}`;
        if (municipality !== 'all') url += `${province !== 'all' ? '&' : '?'}municipality=${municipality}`;
        const response = await axios.get(url);
        if (response.data.success) {
            districtSelect.innerHTML = '<option value="all">Todos</option>';
            response.data.data.forEach(district => {
                const option = document.createElement('option');
                option.value = district.name;
                option.textContent = district.name;
                districtSelect.appendChild(option);
            });
            districtSelect.disabled = false;
        } else {
            alert('Erro ao carregar bairros: ' + response.data.error);
        }
    } catch (error) {
        console.error('Erro ao carregar bairros:', error);
        alert('Erro ao conectar com a API.');
    }
}

// Atualizar opções de municípios e bairros quando a província mudar
provinceSelect.addEventListener('change', () => {
    const province = provinceSelect.value;
    municipalitySelect.innerHTML = '<option value="all">Todas</option>';
    districtSelect.innerHTML = '<option value="all">Todos</option>';
    municipalitySelect.disabled = province === 'all';
    districtSelect.disabled = true;
    if (province !== 'all') {
        loadMunicipalities(province);
    }
});

// Atualizar opções de bairros quando o município mudar
municipalitySelect.addEventListener('change', () => {
    const province = provinceSelect.value;
    const municipality = municipalitySelect.value;
    districtSelect.innerHTML = '<option value="all">Todos</option>';
    districtSelect.disabled = municipality === 'all';
    if (municipality !== 'all') {
        loadDistricts(province, municipality);
    }
});

// Atualizar opções de bairro quando o nível mudar
levelSelect.addEventListener('change', () => {
    const level = levelSelect.value;
    provinceSelect.disabled = false;
    municipalitySelect.disabled = level === 'province';
    districtSelect.disabled = level !== 'district';
    if (level === 'province') {
        municipalitySelect.value = 'all';
        districtSelect.value = 'all';
    } else if (level === 'municipality') {
        districtSelect.value = 'all';
        if (provinceSelect.value !== 'all') {
            loadMunicipalities(provinceSelect.value);
        }
    } else if (level === 'district' && provinceSelect.value !== 'all' && municipalitySelect.value !== 'all') {
        loadDistricts(provinceSelect.value, municipalitySelect.value);
    }
});

// Manipular envio do formulário
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const level = levelSelect.value;
    const province = provinceSelect.value;
    const municipality = municipalitySelect.value;
    const district = districtSelect.value;
    const floodRate = parseInt(document.getElementById('floodRate').value);
    const waterLevel = parseFloat(document.getElementById('waterLevel').value);
    const useRealElevation = document.getElementById('useRealElevation').checked;

    const payload = {
        level,
        province,
        municipality,
        district,
        floodRate,
        waterLevel,
        useRealElevation
    };

    try {
        const response = await axios.post('http://localhost:5000/api/simulate', payload);
        if (response.data.success) {
            map.eachLayer((layer) => {
                if (layer !== map._layers[Object.keys(map._layers)[0]]) {
                    map.removeLayer(layer);
                }
            });

            const geojson = response.data.geojson;
            L.geoJSON(geojson, {
                style: (feature) => {
                    const isFlooded = feature.properties.flooded;
                    return {
                        fillColor: isFlooded ? getSeverityColor(feature.properties.severity) : '#00ff00',
                        weight: 1,
                        opacity: 1,
                        color: '#333',
                        fillOpacity: 0.6
                    };
                },
                onEachFeature: (feature, layer) => {
                    layer.bindPopup(`
                        <b>${feature.properties.name}</b><br>
                        Província: ${feature.properties.province || 'N/A'}<br>
                        Município: ${feature.properties.municipality || 'N/A'}<br>
                        Bairro: ${feature.properties.district || 'N/A'}<br>
                        Inundada: ${feature.properties.flooded ? 'Sim' : 'Não'}<br>
                        Nível de Água: ${feature.properties.waterLevel.toFixed(2)} m<br>
                        Severidade: ${feature.properties.severity}<br>
                        Elevação Média: ${feature.properties.elevation.toFixed(2)} m<br>
                        Precipitação: ${feature.properties.rainfall.toFixed(2)} mm<br>
                        Dias de Recuperação: ${feature.properties.recoveryDays}<br>
                        População Afetada: ${feature.properties.affectedPopulation}
                    `);
                }
            }).addTo(map);

            const geojsonLayer = L.geoJSON(geojson).getBounds();
            map.fitBounds(geojsonLayer);

            const stats = response.data.statistics;
            statisticsDiv.innerHTML = `
                <h5>Estatísticas</h5>
                <p>Total de Áreas: ${stats.totalItems}</p>
                <p>Áreas Inundadas: ${stats.floodedCount} (${stats.avgRisk.toFixed(2)}%)</p>
                <p>População Afetada: ${stats.totalAffected}</p>
                <p>Dados de Elevação: ${response.data.parameters.useRealElevation ? 'Reais' : 'Estimados'}</p>
            `;
        } else {
            alert('Erro: ' + response.data.error);
        }
    } catch (error) {
        console.error('Erro na requisição:', error);
        alert('Erro ao conectar com a API. Verifique se o servidor está rodando.');
    }
});

// Função para definir cores com base na severidade
function getSeverityColor(severity) {
    switch (severity) {
        case 'Leve': return '#ffeb3b';
        case 'Moderada': return '#ff9800';
        case 'Grave': return '#f44336';
        case 'Crítica': return '#d81b60';
        default: return '#00ff00';
    }
}

// Carregar províncias ao iniciar
loadProvinces();