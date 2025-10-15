import os
import requests
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta, timezone
import calendar
from dateutil.relativedelta import relativedelta

# --- CONFIGURAÇÃO ---
OPENMETEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPENMETEO_HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/era5"

# 🛑 ALTERADO: Mapeamento de URLs de câmeras públicas (Incluindo São José dos Campos)
CAMERA_URLS = {
    "São Paulo": "https://climaaovivo.com.br/sp/sao-paulo/alpha-sat-paulista-wall-street-leste",
    "Rio de Janeiro": "https://climaaovivo.com.br/rj/rio-de-janeiro/rio-de-janeiro-samba-hoteis-bossa-nova-ipanema",
    "Recife": "https://climaaovivo.com.br/pe/recife/recife-bugan-hotel-by-atlantica",
    "Belo Horizonte": "https://climaaovivo.com.br/mg/belo-horizonte/luxemburgo-e-santo-antonio",
    "Curitiba": "https://climaaovivo.com.br/pr/curitiba/curitiba-cemiterio-vertical-de-curitiba",
    "Fortaleza": "https://climaaovivo.com.br/ce/abaiara-torre-da-linkcariri",
    "Belém": "https://climaaovivo.com.br/pa/belem",
    "Goiânia": "https://climaaovivo.com.br/go/goiania/goiania-golden-tulip-goiania-address",
    "São José dos Campos": "https://climaaovivo.com.br/sp/sao-jose-dos-campos/sao-jose-dos-campos-hotel-golden-tulip", # 🛑 LINK ADICIONADO
}


# LISTA DE CAPITAIS PARA MONITORAMENTO (Campinas alterada para São José dos Campos)
CAPITAIS_BRASIL = [
    {"nome": "São Paulo", "estado": "SP", "lat": -23.55, "lon": -46.63},
    {"nome": "Rio de Janeiro", "estado": "RJ", "lat": -22.90, "lon": -43.20},
    {"nome": "Belo Horizonte", "estado": "MG", "lat": -19.91, "lon": -43.93},
    {"nome": "Salvador", "estado": "BA", "lat": -12.97, "lon": -38.50},
    {"nome": "Brasília", "estado": "DF", "lat": -15.78, "lon": -47.92},
    {"nome": "Curitiba", "estado": "PR", "lat": -25.42, "lon": -49.27},
    {"nome": "Recife", "estado": "PE", "lat": -8.05, "lon": -34.88},
    {"nome": "Fortaleza", "estado": "CE", "lat": -3.73, "lon": -38.52},
    {"nome": "Manaus", "estado": "AM", "lat": -3.11, "lon": -60.02},
    {"nome": "Porto Alegre", "estado": "RS", "lat": -30.03, "lon": -51.23},
    {"nome": "Belém", "estado": "PA", "lat": -1.45, "lon": -48.50},
    {"nome": "Goiânia", "estado": "GO", "lat": -16.68, "lon": -49.25},
    {"nome": "São José dos Campos", "estado": "SP", "lat": -23.1794, "lon": -45.8872}, # Alterada
]

# LISTA DE CIDADES COM RISCO HISTÓRICO DE ESCORREGAMENTO
CIDADES_RISCO_MONITORADAS = [
    {"nome": "Petrópolis", "estado": "RJ", "lat": -22.505, "lon": -43.18},
    {"nome": "Teresópolis", "estado": "RJ", "lat": -22.412, "lon": -42.966},
    {"nome": "Nova Friburgo", "estado": "RJ", "lat": -22.281, "lon": -42.531},
    {"nome": "Angra dos Reis", "estado": "RJ", "lat": -23.006, "lon": -44.318},
    {"nome": "Ubatuba", "estado": "SP", "lat": -23.433, "lon": -45.083},
    {"nome": "Caraguatatuba", "estado": "SP", "lat": -23.621, "lon": -45.413},
    {"nome": "São Sebastião", "estado": "SP", "lat": -23.760, "lon": -45.409},
    {"nome": "Guarujá", "estado": "SP", "lat": -23.993, "lon": -46.256},
    {"nome": "Franco da Rocha", "estado": "SP", "lat": -23.327, "lon": -46.725},
    {"nome": "Mauá", "estado": "SP", "lat": -23.667, "lon": -46.461},
    {"nome": "Ouro Preto", "estado": "MG", "lat": -20.385, "lon": -43.504},
    {"nome": "Jaboatão dos Guararapes", "estado": "PE", "lat": -8.113, "lon": -35.015},
    {"nome": "Olinda", "estado": "PE", "lat": -8.008, "lon": -34.855},
    {"nome": "Camaragibe", "estado": "PE", "lat": -8.023, "lon": -34.984},
    {"nome": "Maceió", "estado": "AL", "lat": -9.665, "lon": -35.735},
    {"nome": "Blumenau", "estado": "SC", "lat": -26.919, "lon": -49.066},
    {"nome": "Florianópolis", "estado": "SC", "lat": -27.596, "lon": -48.549},
    {"nome": "Muçum", "estado": "RS", "lat": -29.165, "lon": -51.868},
]

app = Flask(__name__, static_folder='web', static_url_path='')
CORS(app)


@app.route('/')
def serve_index():
    return send_from_directory('web', 'welcome.html')


# Função auxiliar para conversão de código do tempo
def converter_codigo_tempo(code):
    codes = {
        0: "Céu Limpo", 1: "Céu Parcialmente Nublado", 2: "Céu Nublado", 3: "Céu Encoberto",
        45: "Neblina", 48: "Névoa", 51: "Chuvisco Leve", 53: "Chuvisco Moderado", 55: "Chuvisco Intenso",
        61: "Chuva Leve", 63: "Chuva Moderada", 65: "Chuva Forte", 80: "Pancadas de Chuva Leve",
        81: "Pancadas de Chuva Moderada", 82: "Pancadas de Chuva Forte", 95: "Tempestade", 96: "Tempestade com Granizo Leve", 99: "Tempestade com Granizo Forte"
    }
    return codes.get(code, f"Cód. {code} (N/D)")


# Função para determinar o Nível de Risco
def determinar_nivel(valor):
    if valor >= 30: return {"nivel": "VERMELHO", "cor": "#FF0000"}
    if valor >= 20: return {"nivel": "LARANJA", "cor": "#FFA500"}
    if valor >= 10: return {"nivel": "AMARELO", "cor": "#FFFF00"}
    return {"nivel": "VERDE", "cor": "#008000"}


@app.route('/api/capitais', methods=['GET'])
def get_capitais_list():
    return jsonify(CAPITAIS_BRASIL)

@app.route('/api/cidades_risco', methods=['GET'])
def get_cidades_risco_list():
    return jsonify(CIDADES_RISCO_MONITORADAS)


# =========================================================
# ENDPOINT PARA SALA DE MONITORAMENTO (CARDS)
# =========================================================
@app.route('/api/capitais_risco', methods=['GET'])
def get_capitais_risco():
    dados_monitoramento = []
    agora_utc = datetime.now(timezone.utc)
    end_time_hist = agora_utc - timedelta(hours=96)
    start_time_hist = end_time_hist - timedelta(hours=72)
    start_date_hist = start_time_hist.strftime('%Y-%m-%d')
    end_date_hist = end_time_hist.strftime('%Y-%m-%d')

    for capital in CAPITAIS_BRASIL:
        lat, lon = capital['lat'], capital['lon']
        nome_capital = capital['nome']
        chuva_futura, chuva_historica, maior_risco = 0, 0, 0
        nivel_risco = {"nivel": "ERRO", "cor": "#999999"}

        try:
            params_forecast = {"latitude": lat, "longitude": lon, "hourly": "precipitation", "forecast_days": 4, "timezone": "auto"}
            resp_forecast = requests.get(OPENMETEO_FORECAST_URL, params=params_forecast)
            resp_forecast.raise_for_status()
            chuva_futura = sum(p for p in resp_forecast.json().get('hourly', {}).get('precipitation', [])[:72] if p is not None)

            params_chuva_hist = {"latitude": lat, "longitude": lon, "start_date": start_date_hist, "end_date": end_date_hist, "hourly": "precipitation", "timezone": "auto", "models": "era5"}
            resp_chuva_hist = requests.get(OPENMETEO_HISTORICAL_URL, params=params_chuva_hist)
            resp_chuva_hist.raise_for_status()
            dados_chuva_hist = resp_chuva_hist.json()
            chuva_historica = sum(p for p in dados_chuva_hist['hourly']['precipitation'] if p is not None)

            maior_risco = max(chuva_historica, chuva_futura)
            nivel_risco = determinar_nivel(maior_risco)

            # 🛑 CORRIGIDO: Adiciona a URL da câmera, que será None se a cidade não estiver no CAMERA_URLS
            camera_url = CAMERA_URLS.get(nome_capital)

            dados_monitoramento.append({
                "capital": nome_capital,
                "estado": capital['estado'],
                "risco_nivel": nivel_risco['nivel'],
                "maior_risco_valor": maior_risco,
                "camera_url": camera_url
            })
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Erro para {nome_capital}: {e}")
            dados_monitoramento.append({"capital": nome_capital, "estado": capital['estado'], "risco_nivel": "ERRO", "maior_risco_valor": 0})

    return jsonify(dados_monitoramento)


# =========================================================
# ENDPOINT PARA DADOS DO PAINEL LATERAL
# =========================================================
@app.route('/api/weather', methods=['GET'])
def get_weather_data():
    lat, lon = request.args.get('lat'), request.args.get('lon')
    nome_cidade = request.args.get('nome_cidade', 'Local')
    if not lat or not lon: return jsonify({"error": "Lat e Lon são obrigatórios."}), 400

    try:
        end_hist = datetime.now(timezone.utc) - timedelta(hours=96)
        start_hist = end_hist - timedelta(hours=72)
        params_hist = {"latitude": lat, "longitude": lon, "start_date": start_hist.strftime('%Y-%m-%d'), "end_date": end_hist.strftime('%Y-%m-%d'), "hourly": "precipitation", "timezone": "auto", "models": "era5"}
        resp_hist = requests.get(OPENMETEO_HISTORICAL_URL, params=params_hist)
        resp_hist.raise_for_status()
        chuva_hist = sum(p for p in resp_hist.json().get('hourly', {}).get('precipitation', []) if p is not None)

        params_forecast = {"latitude": lat, "longitude": lon, "hourly": "temperature_2m,apparent_temperature,windspeed_10m,windgusts_10m,surface_pressure,weather_code,precipitation,relative_humidity_2m,dewpoint_2m", "forecast_days": 4, "timezone": "auto"}
        resp_forecast = requests.get(OPENMETEO_FORECAST_URL, params=params_forecast)
        resp_forecast.raise_for_status()
        hourly = resp_forecast.json().get('hourly', {})

        def get_val(key):
            return hourly.get(key, [None])[0]

        chuva_fut = sum(p for p in hourly.get('precipitation', [])[:72] if p is not None)

        return jsonify({
            "temperatura": get_val('temperature_2m') or 0,
            "cidade_nome": nome_cidade,
            "chuva_72h_hist": chuva_hist,
            "chuva_72h_fut": chuva_fut,
            "sensacao_termica": get_val('apparent_temperature'),
            "velocidade_vento": get_val('windspeed_10m'),
            "pressao": get_val('surface_pressure'),
            "descricao_tempo": converter_codigo_tempo(get_val('weather_code')),
            "umidade_relativa": get_val('relative_humidity_2m'),
            "ponto_orvalho": get_val('dewpoint_2m'),
            "rajada_vento": get_val('windgusts_10m')
        })
    except Exception as e:
        print(f"Erro na rota /api/weather: {e}")
        return jsonify({"error": str(e)}), 500


# =========================================================
# ENDPOINTS PARA OS GRÁFICOS DO DASHBOARD
# =========================================================
@app.route('/api/historical_pluvio', methods=['GET'])
def get_historical_pluvio_data():
    lat, lon = request.args.get('lat'), request.args.get('lon')
    periodo_horas = int(request.args.get('periodo', 72))
    nome_cidade_frontend = request.args.get('nome_cidade', 'Local')
    if not lat or not lon: return jsonify({"error": "Lat e Lon são obrigatórios."}), 400

    end_time_utc = datetime.now(timezone.utc) - timedelta(days=5)
    start_time_utc = end_time_utc - timedelta(hours=periodo_horas)
    params = {"latitude": lat, "longitude": lon, "start_date": start_time_utc.strftime('%Y-%m-%d'), "end_date": end_time_utc.strftime('%Y-%m-%d'), "hourly": "precipitation", "timezone": "auto", "models": "era5"}
    try:
        resp = requests.get(OPENMETEO_HISTORICAL_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        precip = data.get('hourly', {}).get('precipitation', [])
        return jsonify({"cidade": nome_cidade_frontend, "municipio": nome_cidade_frontend, "volume_pluviometria": precip, "data_pluviometria": data.get('hourly', {}).get('time', []), "acumulado_total": sum(p for p in precip if p is not None)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/forecast_chart', methods=['GET'])
def get_forecast_chart_data():
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    nome_cidade_frontend = request.args.get('nome_cidade', 'Local')
    if not lat or not lon: return jsonify({"error": "Lat e Lon são obrigatórios."}), 400
    try:
        params_forecast = {"latitude": lat, "longitude": lon, "hourly": "temperature_2m,apparent_temperature,precipitation_probability,precipitation,dewpoint_2m,relative_humidity_2m,windspeed_10m,windgusts_10m,surface_pressure,weather_code", "forecast_days": 7, "timezone": "auto"}
        resp_forecast = requests.get(OPENMETEO_FORECAST_URL, params=params_forecast)
        resp_forecast.raise_for_status()
        dados_forecast = resp_forecast.json()
        dados_forecast['cidade_nome'] = nome_cidade_frontend
        dados_forecast['municipio'] = nome_cidade_frontend
        return jsonify(dados_forecast)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- Bloco de execução para desenvolvimento local ---
# Este bloco SÓ é executado quando você roda `python server.py`
# O Gunicorn (servidor de produção) ignora este bloco completamente.
if __name__ == '__main__':
    app.run(debug=True)