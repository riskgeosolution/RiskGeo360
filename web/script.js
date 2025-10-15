// Constantes e Variáveis Globais
const INITIAL_LATITUDE = -15.78;       // Latitude de Brasília (centro do mapa)
const INITIAL_LONGITUDE = -47.92;      // Longitude de Brasília (centro do mapa)
const ZOOM_LEVEL = 4;                  // Nível de zoom para ver o Brasil
let updateIntervalId = null;
let currentCoords = { lat: INITIAL_LATITUDE, lon: INITIAL_LONGITUDE };
let currentCityName = "Brasília"; // Cidade inicial para carregar os dados
let currentCharts = {};
let pluvioChartInstance = null;

// Mapeamento de níveis de risco para texto
const riskTextMap = {
    VERDE: "Observação",
    AMARELO: "Atenção",
    LARANJA: "Alto Risco",
    VERMELHO: "Risco Extremo",
    ERRO: "Erro"
};

// Mapeamento de cor para Nível (para o painel lateral)
const colorToRiskMap = {
    "#008000": "Observação", // Verde
    "#FFFF00": "Atenção",    // Amarelo
    "#FFA500": "Alto Risco", // Laranja
    "#FF0000": "Risco Extremo",// Vermelho
    "#999": "Carregando"
};


// ==========================================================
// Mapeamento de Elementos e Navegação
// ==========================================================
const tempElement = document.getElementById('temperatura');
const chuvaHistElement = document.getElementById('chuva-agora');
const chuvaFutElement = document.getElementById('chuva-futura');
const nomeCidadeElement = document.getElementById('nome-cidade');
const alertaPanel = document.getElementById('alerta-panel');
const mapContainer = document.getElementById('map-container');
const dashboardContainer = document.getElementById('dashboard-container');
const dashboardTitle = document.getElementById('dashboard-title');
const openDashboardBtn = document.getElementById('open-dashboard-btn');
const backToMapBtn = document.getElementById('back-to-map-btn');
const periodoSelector = document.getElementById('periodo-selector');
const municipioDisplay = document.getElementById('municipio-display');
const toggleDetalhesBtn = document.getElementById('toggle-detalhes-btn');
const detalhesContainer = document.getElementById('detalhes-adicionais-container');
const monitorRoomBtn = document.getElementById('monitor-room-btn');
const monitorRoomContainer = document.getElementById('monitor-room-container');
const backToMapFromMonitorBtn = document.getElementById('back-to-map-from-monitor-btn');
const capitaisGridContainer = document.getElementById('capitais-grid-container');
const alertaTituloElement = document.getElementById('alerta-titulo');


// Mapeamento dos Cards de Detalhe
const detailDescricao = document.getElementById('detail-descricao');
const detailFeelsLike = document.getElementById('detail-feels-like');
const detailHumidity = document.getElementById('detail-humidity');
const detailDewpoint = document.getElementById('detail-dewpoint');
const detailPressure = document.getElementById('detail-pressure');
const detailWind = document.getElementById('detail-wind');
const detailGusts = document.getElementById('detail-gusts');


// ==========================================================
// FUNÇÕES DE NAVEGAÇÃO E SALA DE MONITORAMENTO
// ==========================================================

function showDashboard() {
    mapContainer.style.display = 'none';
    monitorRoomContainer.style.display = 'none';
    dashboardContainer.style.display = 'block';
    dashboardTitle.textContent = `Pluviometria Histórica para ${currentCityName}`;
    municipioDisplay.textContent = `Município: ${currentCityName}/SP - Estação: Modelo ERA5`;
    periodoSelector.value = '72';
    fetchAndRenderPluvioChart(currentCoords.lat, currentCoords.lon, currentCityName, periodoSelector.value);
    fetchAndRenderForecastChart(currentCoords.lat, currentCoords.lon, currentCityName);
    fetchAndPreFillDetails(currentCoords.lat, currentCoords.lon, currentCityName);
    map.invalidateSize();
}

function showMap() {
    dashboardContainer.style.display = 'none';
    monitorRoomContainer.style.display = 'none';
    mapContainer.style.display = 'block';
    detalhesContainer.style.display = 'none';
    toggleDetalhesBtn.textContent = 'Ver Detalhes Adicionais';
    map.invalidateSize();
}

function showMonitorRoom() {
    mapContainer.style.display = 'none';
    dashboardContainer.style.display = 'none';
    monitorRoomContainer.style.display = 'block';
    fetchCapitaisRisco();
}

async function fetchCapitaisRisco() {
    capitaisGridContainer.innerHTML = '<div class="loading-row">Aguardando dados das cidades...</div>';
    const API_CAPITAIS_URL = `/api/capitais_risco`;

    try {
        const response = await fetch(API_CAPITAIS_URL);
        const dados = await response.json();

        if (!response.ok || dados.error) {
            console.error('Erro ao buscar dados das capitais:', dados.error);
            capitaisGridContainer.innerHTML = `<div class="loading-row">ERRO: ${dados.error || 'Falha na comunicação com o servidor.'}</div>`;
            return;
        }
        renderCapitaisCards(dados);

    } catch (error) {
        console.error("Falha na rede ao buscar Sala de Monitoramento:", error);
        capitaisGridContainer.innerHTML = `<div class="loading-row">ERRO DE CONEXÃO: Verifique o console do navegador e o terminal do servidor Flask.</div>`;
    }
}

function renderCapitaisCards(capitais) {
    capitaisGridContainer.innerHTML = '';
    let htmlContent = '';
    capitais.forEach(cidade => {
        const riscoNivel = cidade.risco_nivel;
        const riscoTexto = riskTextMap[riscoNivel] || 'Indefinido'; // Pega o texto do mapa

        // 🛑 NOVO: Botão de Câmera (mantido como no ponto de salvamento 2)
        const cameraButton = cidade.camera_url ?
            `<a href="${cidade.camera_url}" target="_blank" class="camera-btn" style="background-color: #3f51b5; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none; font-size: 0.9em; margin-top: 10px;">Ver Câmera</a>` :
            '';

        htmlContent += `
            <div class="capital-card" style="flex-direction: column; align-items: flex-start;">
                <span class="card-city-name">${cidade.capital} (${cidade.estado})</span>
                <span class="card-risk-level nivel-${riscoNivel}" title="Acumulado: ${cidade.maior_risco_valor !== undefined ? cidade.maior_risco_valor.toFixed(1) : '--'} mm" style="margin-top: 5px; margin-bottom: 5px;">
                    ${riscoTexto}
                </span>
                ${cameraButton}
            </div>
        `;
    });
    capitaisGridContainer.innerHTML = htmlContent;
}

const toggleDetalhes = () => {
    const isHidden = detalhesContainer.style.display === 'none';
    detalhesContainer.style.display = isHidden ? 'grid' : 'none';
    toggleDetalhesBtn.textContent = isHidden ? 'Ocultar Detalhes Adicionais' : 'Ver Detalhes Adicionais';
};

periodoSelector.onchange = function() {
    fetchAndRenderPluvioChart(currentCoords.lat, currentCoords.lon, currentCityName, this.value);
};

openDashboardBtn.onclick = showDashboard;
backToMapBtn.onclick = showMap;
toggleDetalhesBtn.onclick = toggleDetalhes;
monitorRoomBtn.onclick = showMonitorRoom;
backToMapFromMonitorBtn.onclick = showMap;


// ==========================================================
// FUNÇÕES DE BUSCA DE DADOS
// ==========================================================

function preencherCardsDetalhe(dados) {
    detailDescricao.textContent = dados.descricao_tempo || '--';
    detailFeelsLike.textContent = (dados.sensacao_termica !== undefined && dados.sensacao_termica !== null) ? `${dados.sensacao_termica.toFixed(1)} °C` : '--';
    detailHumidity.textContent = (dados.umidade_relativa !== undefined && dados.umidade_relativa !== null) ? `${dados.umidade_relativa.toFixed(0)} %` : '--';
    detailDewpoint.textContent = (dados.ponto_orvalho !== undefined && dados.ponto_orvalho !== null) ? `${dados.ponto_orvalho.toFixed(1)} °C` : '--';
    detailPressure.textContent = (dados.pressao !== undefined && dados.pressao !== null) ? `${dados.pressao.toFixed(0)} hPa` : '--';
    detailWind.textContent = (dados.velocidade_vento !== undefined && dados.velocidade_vento !== null) ? `${dados.velocidade_vento.toFixed(1)} km/h` : '--';
    detailGusts.textContent = (dados.rajada_vento !== undefined && dados.rajada_vento !== null) ? `${dados.rajada_vento.toFixed(1)} km/h` : '--';
}

async function fetchAndPreFillDetails(latitude, longitude, nomeLocal) {
    const API_URL = `/api/weather?lat=${latitude}&lon=${longitude}&nome_cidade=${encodeURIComponent(nomeLocal)}`;
    try {
        const response = await fetch(API_URL);
        const dados = await response.json();
        if (!response.ok || dados.error) {
            console.error('Falha ao pré-carregar detalhes:', dados.error);
            return;
        }
        preencherCardsDetalhe(dados);
    } catch (error) {
        console.error("Falha na rede ao pré-carregar detalhes:", error);
    }
}

function determinarNivelAlerta(historico, futura) {
    const maiorRisco = Math.max(historico, futura);
    if (maiorRisco >= 30) { return "#FF0000"; }
    else if (maiorRisco >= 20) { return "#FFA500"; }
    else if (maiorRisco >= 10) { return "#FFFF00"; }
    else { return "#008000"; }
}

async function fetchAndRenderPluvioChart(latitude, longitude, nomeLocal, periodoHoras) {
    dashboardTitle.textContent = `Carregando dados de ${periodoHoras}h para ${nomeLocal}...`;
    const API_PLUVIO_URL = `/api/historical_pluvio?lat=${latitude}&lon=${longitude}&periodo=${periodoHoras}&nome_cidade=${encodeURIComponent(nomeLocal)}`;
    try {
        const response = await fetch(API_PLUVIO_URL);
        const data = await response.json();
        if (!response.ok || data.error || data.volume_pluviometria === undefined) {
            throw new Error(`Erro: ${data.error || 'Dados incompletos da API.'}`);
        }
        const hourlyData = data.volume_pluviometria || [];
        const labels = data.data_pluviometria.map(t => {
            const date = new Date(t + 'Z');
            return date.toLocaleTimeString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }).replace(' ', '\n');
        });
        let acumulado = 0;
        const acumuladoArray = hourlyData.map(val => {
            if (val !== null) { acumulado += val; }
            return acumulado;
        });
        const pluvioCtx = document.getElementById('pluvioChart').getContext('2d');
        if (currentCharts.pluvio) currentCharts.pluvio.destroy();
        currentCharts.pluvio = new Chart(pluvioCtx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    { label: 'Pluviometria (mm)', data: hourlyData, backgroundColor: 'rgba(54, 162, 235, 0.7)', yAxisID: 'y-pluv', order: 2 },
                    { label: `Acumulado ${periodoHoras}h: ${data.acumulado_total.toFixed(1)} mm`, data: acumuladoArray, type: 'line', borderColor: 'black', borderWidth: 2, pointRadius: 0, fill: false, yAxisID: 'y-pluv', order: 1 }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                scales: {
                    y: { id: 'y-pluv', type: 'linear', position: 'left', beginAtZero: true, title: { display: true, text: 'Pluviometria (mm)' } },
                    x: { ticks: { autoSkip: true, maxRotation: 45, minRotation: 45, font: { size: 10 } } }
                }
            }
        });
        dashboardTitle.textContent = `Pluviometria Histórica para ${data.cidade}`;
        municipioDisplay.textContent = `Município: ${data.municipio} | Total Acumulado: ${data.acumulado_total.toFixed(1)} mm`;
    } catch (error) {
        console.error("Falha ao carregar Gráfico de Pluviometria:", error);
        dashboardTitle.textContent = `ERRO ao carregar Pluviometria: ${error.message}`;
        municipioDisplay.textContent = 'Verifique as datas históricas (máximo 4 dias atrás).';
    }
}

async function fetchAndRenderForecastChart(latitude, longitude, nomeLocal) {
    const API_CHART_URL = `/api/forecast_chart?lat=${latitude}&lon=${longitude}&nome_cidade=${encodeURIComponent(nomeLocal)}`;
    try {
        const forecastResponse = await fetch(API_CHART_URL);
        const forecastData = await forecastResponse.json();
        if (!forecastResponse.ok || forecastData.error || !forecastData.hourly) {
            throw new Error(`Erro: ${forecastData.error || 'Dados de previsão incompletos.'}`);
        }
        const hourlyData = forecastData.hourly.precipitation.slice(0, 72) || [];
        const timeLabels = forecastData.hourly.time.slice(0, 72) || [];
        let acumulado = 0;
        const acumuladoArray = hourlyData.map(val => {
            if (val !== null) { acumulado += val; }
            return acumulado;
        });
        const acumuladoTotal = acumulado;
        const labels = timeLabels.map(t => {
            const date = new Date(t);
            return date.toLocaleTimeString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }).replace(' ', '\n');
        });
        const previsaoCtx = document.getElementById('previsaoChart').getContext('2d');
        if (currentCharts.previsao) currentCharts.previsao.destroy();
        currentCharts.previsao = new Chart(previsaoCtx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    { label: 'Pluviometria Prevista (mm)', data: hourlyData, backgroundColor: 'rgba(255, 159, 64, 0.7)', yAxisID: 'y-pluv', order: 2 },
                    { label: `Acumulado Futuro: ${acumuladoTotal.toFixed(1)} mm`, data: acumuladoArray, type: 'line', borderColor: '#FF4500', borderWidth: 2, pointRadius: 0, fill: false, yAxisID: 'y-pluv', order: 1 }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                scales: {
                    y: { id: 'y-pluv', type: 'linear', position: 'left', beginAtZero: true, title: { display: true, text: 'Pluviometria (mm)' } },
                    x: { ticks: { autoSkip: true, maxRotation: 45, minRotation: 45, font: { size: 10 } } }
                }
            }
        });
    } catch (error) {
        console.error("Falha ao carregar Gráfico de Previsão:", error);
    }
}


// INICIALIZAÇÃO DO MAPA E FLUXO DE DADOS
const map = L.map('map').setView([INITIAL_LATITUDE, INITIAL_LONGITUDE], ZOOM_LEVEL);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

const geocoder = L.Control.geocoder({
    position: 'topleft',
    collapsed: false,
    placeholder: 'Pesquisar cidade aqui...',
    title: 'Pesquisar uma nova localização',
    defaultMarkGeocode: false
}).addTo(map);

geocoder.on('markgeocode', function (e) {
    const lat = e.geocode.center.lat;
    const lon = e.geocode.center.lng;
    const nomeCurto = e.geocode.name.split(',')[0].trim();
    map.setView([lat, lon], 13);
    processarNovoLocal(lat, lon, nomeCurto);
});

function processarNovoLocal(latitude, longitude, nomeLocal) {
    if (updateIntervalId) { clearInterval(updateIntervalId); updateIntervalId = null; }
    currentCoords = { lat: latitude, lon: longitude };
    currentCityName = nomeLocal;

    nomeCidadeElement.textContent = nomeLocal;
    carregarDadosClimaticos(latitude, longitude, nomeLocal);
    updateIntervalId = setInterval(() => { carregarDadosClimaticos(currentCoords.lat, currentCoords.lon, currentCityName); }, 60000);
}

async function carregarDadosClimaticos(latitude, longitude, nomeLocal) {
    const API_URL = `/api/weather?lat=${latitude}&lon=${longitude}&nome_cidade=${encodeURIComponent(nomeLocal)}`;
    tempElement.textContent = "Carregando...";
    chuvaHistElement.textContent = "Carregando...";
    chuvaFutElement.textContent = "Carregando...";
    nomeCidadeElement.textContent = nomeLocal;
    alertaPanel.style.backgroundColor = 'white';
    const alertaTituloElement = document.getElementById('alerta-titulo');

    try {
        const resposta = await fetch(API_URL);
        if (!resposta.ok) {
            const erro = await resposta.json();
            throw new Error(`Erro ${resposta.status}: ${erro.error}`);
        }
        const dados = await resposta.json();
        const nomeReal = dados.cidade_nome || nomeLocal;
        const volumeChuvaHist = dados.chuva_72h_hist || 0;
        const volumeChuvaFut = dados.chuva_72h_fut || 0;
        const corAlerta = determinarNivelAlerta(volumeChuvaHist, volumeChuvaFut);

        // 🛑 Lógica para obter o nome do nível
        let nivelNome = colorToRiskMap[corAlerta] || 'Nível Indefinido';

        // 🛑 ATUALIZA O TÍTULO
        alertaTituloElement.textContent = `Nível: ${nivelNome}`;

        // 🛑 ATUALIZA O FUNDO E AS CLASSES DE COR DO TEXTO
        alertaPanel.style.backgroundColor = corAlerta;

        if (corAlerta === "#FFFF00" || corAlerta === "#008000") {
            alertaPanel.classList.add('color-dark');
            alertaPanel.classList.remove('color-light');
        } else {
            alertaPanel.classList.add('color-light');
            alertaPanel.classList.remove('color-dark');
        }

        nomeCidadeElement.textContent = nomeReal;
        tempElement.textContent = dados.temperatura.toFixed(2) + "°C";
        chuvaHistElement.textContent = volumeChuvaHist.toFixed(1) + " mm";
        chuvaFutElement.textContent = volumeChuvaFut.toFixed(1) + " mm";

    } catch (error) {
        // 🛑 Tratamento de erro para o título
        alertaTituloElement.textContent = `ERRO DE DADOS`;
        alertaPanel.style.backgroundColor = 'white';
        alertaPanel.classList.add('color-dark');
        alertaPanel.classList.remove('color-light');

        nomeCidadeElement.textContent = "ERRO NA BUSCA";
        tempElement.textContent = "ERRO"; chuvaHistElement.textContent = "ERRO"; chuvaFutElement.textContent = "ERRO";
    }
}

async function fetchAndPlaceCapitaisMarkers() {
    try {
        const response = await fetch('/api/capitais_risco');
        const capitais = await response.json();
        if (!response.ok) throw new Error('Falha ao buscar capitais');

        capitais.forEach(c => {
            if (c.risco_nivel === 'ERRO') return;
            const icon = L.divIcon({
                className: `capital-marker-icon nivel-${c.risco_nivel}`,
                html: `<b>${Math.round(c.maior_risco_valor || 0)}</b>`,
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            });
            const marker = L.marker([c.lat, c.lon], { icon }).addTo(map)
                .bindTooltip(`${c.capital} (${c.estado})`)
                .on('click', () => {
                    map.setView([c.lat, c.lon], 11);
                    processarNovoLocal(c.lat, c.lon, c.capital);
                });
        });
    } catch (error) {
        console.error("Erro nos marcadores das capitais:", error);
    }
}

async function fetchAndPlaceRiscoMarkers() {
    try {
        const response = await fetch('/api/cidades_risco');
        const cidadesDeRisco = await response.json();
        cidadesDeRisco.forEach(cidade => {
            const marker = L.marker([cidade.lat, cidade.lon]).addTo(map)
                .bindTooltip(cidade.nome)
                .on('click', () => {
                    map.setView([cidade.lat, cidade.lon], 11);
                    processarNovoLocal(cidade.lat, cidade.lon, cidade.nome);
                });
        });
    } catch (error) {
        console.error("Erro ao colocar marcadores de risco:", error);
    }
}


// INICIALIZAÇÃO
processarNovoLocal(INITIAL_LATITUDE, INITIAL_LONGITUDE, "Brasília");
fetchAndPlaceCapitaisMarkers();
fetchAndPlaceRiscoMarkers();
