import os
import requests
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta, timezone
import threading
import time

# --- CONFIGURAÇÃO ---
OPENMETEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPENMETEO_HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/era5"

CAMERA_URLS = {
    "São Paulo": "https://climaaovivo.com.br/sp/sao-paulo/alpha-sat-paulista-wall-street-leste",
    "Rio de Janeiro": "https://climaaovivo.com.br/rj/rio-de-janeiro/rio-de-janeiro-samba-hoteis-bossa-nova-ipanema",
    "Recife": "https://climaaovivo.com.br/pe/recife/recife-bugan-hotel-by-atlantica",
    "Belo Horizonte": "https://climaaovivo.com.br/mg/belo-horizonte/luxemburgo-e-santo-antonio",
    "Curitiba": "https://climaaovivo.com.br/pr/curitiba/curitiba-cemiterio-vertical-de-curitiba",
    "Fortaleza": "https://climaaovivo.com.br/ce/abaiara-torre-da-linkcariri",
    "Belém": "https://climaaovivo.com.br/pa/belem",
    "Goiânia": "https://climaaovivo.com.br/go/goiania/goiania-golden-tulip-goiania-address",
    "São José dos Campos": "https://climaaovivo.com.br/sp/sao-jose-dos-campos/sao-jose-dos-campos-hotel-golden-tulip",
}

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
    {"nome": "São José dos Campos", "estado": "SP", "lat": -23.1794, "lon": -45.8872},
]

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


def converter_codigo_tempo(code):
    codes = {
        0: "Céu Limpo", 1: "Céu Parcialmente Nublado", 2: "Céu Nublado", 3: "Céu Encoberto",
        45: "Neblina", 48: "Névoa", 51: "Chuvisco Leve", 53: "Chuvisco Moderado", 55: "Chuvisco Intenso",
        61: "Chuva Leve", 63: "Chuva Moderada", 65: "Chuva Forte", 80: "Pancadas de Chuva Leve",
        81: "Pancadas de Chuva Moderada", 82: "Pancadas de Chuva Forte", 95: "Tempestade",
        96: "Tempestade com Granizo Leve", 99: "Tempestade com Granizo Forte"
    }
    return codes.get(code, f"Cód. {code} (N/D)")


def determinar_nivel(valor):
    if valor >= 30: return {"nivel": "VERMELHO", "cor": "#FF0000"}
    if valor >= 20: return {"nivel": "LARANJA", "cor": "#FFA500"}
    if valor >= 10: return {"nivel": "AMARELO", "cor": "#FFFF00"}
    return {"nivel": "VERDE", "cor": "#008000"}


def get_sjc_weather_summary():
    sjc_lat, sjc_lon = -23.1794, -45.8872
    try:
        params_forecast = {"latitude": sjc_lat, "longitude": sjc_lon,
                           "hourly": "temperature_2m,apparent_temperature,windspeed_10m,weather_code,precipitation,relative_humidity_2m",
                           "forecast_days": 3, "timezone": "auto"}
        resp_forecast = requests.get(OPENMETEO_FORECAST_URL, params=params_forecast)
        resp_forecast.raise_for_status()
        hourly = resp_forecast.json().get('hourly', {})

        def get_val(key):
            values = hourly.get(key)
            return values[0] if values and len(values) > 0 else None

        chuva_fut = sum(p for p in hourly.get('precipitation', [])[:72] if p is not None)

        end_hist, start_hist = datetime.now(timezone.utc) - timedelta(days=1), datetime.now(timezone.utc) - timedelta(
            days=4)
        params_hist = {"latitude": sjc_lat, "longitude": sjc_lon, "start_date": start_hist.strftime('%Y-%m-%d'),
                       "end_date": end_hist.strftime('%Y-%m-%d'), "hourly": "precipitation", "timezone": "auto"}
        resp_hist = requests.get(OPENMETEO_HISTORICAL_URL, params=params_hist)
        resp_hist.raise_for_status()
        chuva_hist = sum(p for p in resp_hist.json().get('hourly', {}).get('precipitation', [])[-72:] if p is not None)

        maior_risco = max(chuva_hist, chuva_fut)
        nivel_risco = determinar_nivel(maior_risco)

        return {"temperatura": get_val('temperature_2m'), "sensacao_termica": get_val('apparent_temperature'),
                "descricao_tempo": converter_codigo_tempo(get_val('weather_code')), "chuva_72h_fut": chuva_fut,
                "velocidade_vento": get_val('windspeed_10m'), "umidade_relativa": get_val('relative_humidity_2m'),
                "chuva_72h_hist": chuva_hist, "risco_nivel": nivel_risco}
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] Erro ao buscar dados de SJC: {e}")
        return None


# --- FUNÇÃO DE ENVIO DE E-MAIL VIA API HTTP (POR ACESSO) ---
def send_emails_in_background():
    """
    Envia e-mails de acesso e resumo de SJC usando a API HTTP do SMTP2GO.
    """
    with app.app_context():
        api_key = os.environ.get('SMTP2GO_API_KEY')
        sender_email = os.environ.get('SENDER_EMAIL')
        recipient_email = os.environ.get('NOTIFICATION_EMAIL')
        api_url = "https://api.smtp2go.com/v3/email/send"

        if not all([api_key, sender_email, recipient_email]):
            print(f"[{datetime.now().isoformat()}] ERRO: Configuração da API do SMTP2GO ou e-mails faltando.")
            return

        agora = datetime.now(timezone.utc) - timedelta(hours=3)
        agora_formatado = agora.strftime('%d/%m/%Y às %H:%M:%S')

        try:
            # 1. E-mail de Acesso
            html_content_acesso = f"<html><body><p>Olá,</p><p>Um novo acesso à plataforma <b>RiskGeo 360</b> foi registado.</p><p><b>Data e Hora:</b> {agora_formatado}</p></body></html>"

            payload_acesso = {
                "api_key": api_key, "to": [recipient_email], "sender": sender_email,
                "subject": "Aviso: Acesso à Plataforma RiskGeo 360", "html_body": html_content_acesso,
                "text_body": f"Novo acesso à plataforma RiskGeo 360 em {agora_formatado}."
            }
            response_acesso = requests.post(api_url, json=payload_acesso)
            if response_acesso.status_code == 200:
                print(f"[{datetime.now().isoformat()}] E-mail de ACESSO enviado com sucesso via API.")
            else:
                print(
                    f"[{datetime.now().isoformat()}] FALHA ao enviar e-mail de ACESSO via API: {response_acesso.text}")

            time.sleep(2)

            # 2. E-mail de Resumo de SJC (acionado no acesso)
            resumo_sjc = get_sjc_weather_summary()
            if resumo_sjc:
                html_content_resumo = f"""
                <html><body style="font-family: Arial, sans-serif;">
                    <p>Olá,</p>
                    <p>Segue o resumo das condições climáticas para <b>São José dos Campos</b>:</p>
                    {_build_html_summary_list(resumo_sjc)}
                </body></html>
                """
                payload_resumo = {
                    "api_key": api_key, "to": [recipient_email], "sender": sender_email,
                    "subject": f'RiskGeo Resumo: SJC {agora.strftime("%d/%m %H:%M")}',
                    "html_body": html_content_resumo,
                    "text_body": "Resumo do tempo para São José dos Campos. Ative o HTML para ver."
                }
                response_resumo = requests.post(api_url, json=payload_resumo)
                if response_resumo.status_code == 200:
                    print(f"[{datetime.now().isoformat()}] E-mail de RESUMO de SJC enviado com sucesso via API.")
                else:
                    print(
                        f"[{datetime.now().isoformat()}] FALHA ao enviar e-mail de RESUMO via API: {response_resumo.text}")

        except requests.exceptions.RequestException as e:
            print(f"[{datetime.now().isoformat()}] FALHA DE CONEXÃO AO ENVIAR E-MAILS VIA API: {e}")
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] FALHA GERAL AO ENVIAR E-MAILS VIA API: {e}")


# --- FUNÇÕES PARA E-MAIL (CARAGUATATUBA) E SMS (UBATUBA) AGENDADOS ---

def get_caragua_weather_summary():
    """Busca dados climáticos para Caraguatatuba."""
    caragua_lat, caragua_lon = -23.621, -45.413
    try:
        params_forecast = {"latitude": caragua_lat, "longitude": caragua_lon,
                           "hourly": "temperature_2m,apparent_temperature,windspeed_10m,weather_code,precipitation,relative_humidity_2m",
                           "forecast_days": 3, "timezone": "auto"}
        resp_forecast = requests.get(OPENMETEO_FORECAST_URL, params=params_forecast)
        resp_forecast.raise_for_status()
        hourly = resp_forecast.json().get('hourly', {})

        def get_val(key):
            values = hourly.get(key)
            return values[0] if values and len(values) > 0 else None

        chuva_fut = sum(p for p in hourly.get('precipitation', [])[:72] if p is not None)
        end_hist, start_hist = datetime.now(timezone.utc) - timedelta(days=1), datetime.now(timezone.utc) - timedelta(
            days=4)
        params_hist = {"latitude": caragua_lat, "longitude": caragua_lon, "start_date": start_hist.strftime('%Y-%m-%d'),
                       "end_date": end_hist.strftime('%Y-%m-%d'), "hourly": "precipitation", "timezone": "auto"}
        resp_hist = requests.get(OPENMETEO_HISTORICAL_URL, params=params_hist)
        resp_hist.raise_for_status()
        chuva_hist = sum(p for p in resp_hist.json().get('hourly', {}).get('precipitation', [])[-72:] if p is not None)
        maior_risco = max(chuva_hist, chuva_fut)
        nivel_risco = determinar_nivel(maior_risco)
        return {"temperatura": get_val('temperature_2m'), "sensacao_termica": get_val('apparent_temperature'),
                "descricao_tempo": converter_codigo_tempo(get_val('weather_code')), "chuva_72h_fut": chuva_fut,
                "velocidade_vento": get_val('windspeed_10m'), "umidade_relativa": get_val('relative_humidity_2m'),
                "chuva_72h_hist": chuva_hist, "risco_nivel": nivel_risco}
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] Erro ao buscar dados de Caraguatatuba: {e}")
        return None


def get_ubatuba_weather_summary():
    """Busca dados climáticos para Ubatuba."""
    uba_lat, uba_lon = -23.433, -45.083
    try:
        params_forecast = {"latitude": uba_lat, "longitude": uba_lon,
                           "hourly": "temperature_2m,apparent_temperature,windspeed_10m,weather_code,precipitation,relative_humidity_2m",
                           "forecast_days": 3, "timezone": "auto"}
        resp_forecast = requests.get(OPENMETEO_FORECAST_URL, params=params_forecast)
        resp_forecast.raise_for_status()
        hourly = resp_forecast.json().get('hourly', {})

        def get_val(key):
            values = hourly.get(key)
            return values[0] if values and len(values) > 0 else None

        chuva_fut = sum(p for p in hourly.get('precipitation', [])[:72] if p is not None)
        end_hist, start_hist = datetime.now(timezone.utc) - timedelta(days=1), datetime.now(timezone.utc) - timedelta(
            days=4)
        params_hist = {"latitude": uba_lat, "longitude": uba_lon, "start_date": start_hist.strftime('%Y-%m-%d'),
                       "end_date": end_hist.strftime('%Y-%m-%d'), "hourly": "precipitation", "timezone": "auto"}
        resp_hist = requests.get(OPENMETEO_HISTORICAL_URL, params=params_hist)
        resp_hist.raise_for_status()
        chuva_hist = sum(p for p in resp_hist.json().get('hourly', {}).get('precipitation', [])[-72:] if p is not None)
        maior_risco = max(chuva_hist, chuva_fut)
        nivel_risco = determinar_nivel(maior_risco)

        return {"temperatura": get_val('temperature_2m'), "sensacao_termica": get_val('apparent_temperature'),
                "descricao_tempo": converter_codigo_tempo(get_val('weather_code')), "chuva_72h_fut": chuva_fut,
                "velocidade_vento": get_val('windspeed_10m'), "umidade_relativa": get_val('relative_humidity_2m'),
                "chuva_72h_hist": chuva_hist, "risco_nivel": nivel_risco}
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] Erro ao buscar dados de Ubatuba: {e}")
        return None


def _build_html_summary_list(summary_data):
    """Função auxiliar para construir a lista HTML do corpo do e-mail."""
    if not summary_data: return ""
    risco = summary_data.get('risco_nivel', {})
    temp = f"{summary_data.get('temperatura'):.1f}°C" if summary_data.get('temperatura') is not None else "N/D"
    sensacao = f"{summary_data.get('sensacao_termica'):.1f}°C" if summary_data.get(
        'sensacao_termica') is not None else "N/D"
    humidade = f"{summary_data.get('umidade_relativa')}%" if summary_data.get('umidade_relativa') is not None else "N/D"
    vento = f"{summary_data.get('velocidade_vento'):.1f} km/h" if summary_data.get(
        'velocidade_vento') is not None else "N/D"
    chuva_fut = f"{summary_data.get('chuva_72h_fut'):.1f} mm" if summary_data.get(
        'chuva_72h_fut') is not None else "N/D"
    chuva_hist = f"{summary_data.get('chuva_72h_hist'):.1f} mm" if summary_data.get(
        'chuva_72h_hist') is not None else "N/D"
    risco_nivel = risco.get('nivel', 'INDETERMINADO')
    risco_cor = risco.get('cor', '#999999')
    cor_texto_risco = "#000000" if risco_nivel == 'AMARELO' else "#FFFFFF"

    return f"""
    <ul style="list-style-type: none; padding-left: 0;">
        <li style="margin-bottom: 5px;"><b>Nível de Risco:</b> <span style="background-color: {risco_cor}; color: {cor_texto_risco}; padding: 3px 8px; border-radius: 4px; font-weight: bold;">{risco_nivel}</span></li>
        <li style="margin-bottom: 5px;"><b>Condição Atual:</b> {summary_data.get('descricao_tempo', 'N/D')}</li>
        <li style="margin-bottom: 5px;"><b>Temperatura:</b> {temp}</li>
        <li style="margin-bottom: 5px;"><b>Sensação Térmica:</b> {sensacao}</li>
        <li style="margin-bottom: 5px;"><b>Humidade Relativa:</b> {humidade}</li>
        <li style="margin-bottom: 5px;"><b>Vento:</b> {vento}</li>
        <li style="margin-bottom: 5px;"><b>Chuva Acumulada (72h Histórico):</b> {chuva_hist}</li>
        <li style="margin-bottom: 5px;"><b>Previsão de Chuva (Próximas 72h):</b> {chuva_fut}</li>
    </ul>
    """


def send_daily_caragua_summary():
    """Envia o e-mail de resumo diário para Caraguatatuba."""
    with app.app_context():
        print(f"[{datetime.now().isoformat()}] Executando tarefa agendada: Resumo de Caraguatatuba.")
        api_key = os.environ.get('SMTP2GO_API_KEY')
        sender_email = os.environ.get('SENDER_EMAIL')
        recipient_email = os.environ.get('NOTIFICATION_EMAIL')
        api_url = "https://api.smtp2go.com/v3/email/send"
        if not all([api_key, sender_email, recipient_email]):
            print(f"[{datetime.now().isoformat()}] ERRO (Agendado E-mail): Configuração da API ou e-mails faltando.")
            return

        resumo_caragua = get_caragua_weather_summary()
        if resumo_caragua:
            agora = datetime.now()
            html_content = f"""
            <html><body style="font-family: Arial, sans-serif;">
                <p>Olá,</p>
                <p>Segue o resumo diário das condições climáticas para <b>Caraguatatuba</b>:</p>
                {_build_html_summary_list(resumo_caragua)}
            </body></html>
            """
            payload = {
                "api_key": api_key, "to": [recipient_email], "sender": sender_email,
                "subject": f'RiskGeo Resumo Diário: Caraguatatuba {agora.strftime("%d/%m/%Y")}',
                "html_body": html_content, "text_body": "Resumo diário do tempo para Caraguatatuba."
            }
            response = requests.post(api_url, json=payload, timeout=10)
            if response.status_code == 200:
                print(f"[{datetime.now().isoformat()}] E-mail AGENDADO de Caraguatatuba enviado com sucesso.")
            else:
                print(
                    f"[{datetime.now().isoformat()}] FALHA (Agendado E-mail) ao enviar e-mail de Caraguatatuba: {response.text}")


def send_daily_ubatuba_sms():
    """Envia o SMS de resumo diário para Ubatuba via Comtele."""
    with app.app_context():
        print(f"[{datetime.now().isoformat()}] Executando tarefa agendada: Resumo SMS Ubatuba.")

        api_key = os.environ.get('COMTELE_API_KEY')
        phone_number = os.environ.get('NOTIFICATION_PHONE')

        api_url = "https://sms.comtele.com.br/api/v2/send"

        if not all([api_key, phone_number]):
            print(
                f"[{datetime.now().isoformat()}] ERRO (Agendado SMS): COMTELE_API_KEY ou NOTIFICATION_PHONE faltando.")
            return

        resumo_uba = get_ubatuba_weather_summary()
        if resumo_uba:
            risco = resumo_uba.get('risco_nivel', {}).get('nivel', 'N/D')
            temp = f"{resumo_uba.get('temperatura'):.1f}C" if resumo_uba.get('temperatura') is not None else "N/D"
            chuva_hist = f"{resumo_uba.get('chuva_72h_hist'):.1f}mm" if resumo_uba.get(
                'chuva_72h_hist') is not None else "N/D"
            chuva_fut = f"{resumo_uba.get('chuva_72h_fut'):.1f}mm" if resumo_uba.get(
                'chuva_72h_fut') is not None else "N/D"

            message_content = f"RiskGeo Resumo Ubatuba:\nRisco: {risco}\nTemp: {temp}\nHist 72h: {chuva_hist}\nPrev 72h: {chuva_fut}"

            headers = {
                "auth-key": api_key,
                "Content-Type": "application/x-www-form-urlencoded"
            }
            payload = {
                "Sender": str("RiskGeo"),
                "Receivers": str(phone_number),
                "Content": str(message_content)
            }

            print(f"[{datetime.now().isoformat()}] Tentando enviar SMS para: {phone_number}")
            print(f"[{datetime.now().isoformat()}] Payload: {payload}")

            try:
                response = requests.post(api_url, data=payload, headers=headers, timeout=10)
                response.raise_for_status()

                print(
                    f"[{datetime.now().isoformat()}] Resposta da API Comtele (Status: {response.status_code}): {response.text}")

                if response.json().get("Success", False):
                    print(f"[{datetime.now().isoformat()}] SMS AGENDADO de Ubatuba enviado com sucesso.")
                else:
                    print(
                        f"[{datetime.now().isoformat()}] FALHA (Agendado SMS) ao enviar SMS de Ubatuba: Resposta da API indica falha.")

            except requests.exceptions.RequestException as e:
                print(f"[{datetime.now().isoformat()}] FALHA DE CONEXÃO (Agendado SMS) ao enviar SMS: {e}")
                if e.response:
                    print(f"[{datetime.now().isoformat()}] Detalhes da resposta de erro: {e.response.text}")
            except Exception as e:
                print(f"[{datetime.now().isoformat()}] FALHA GERAL (Agendado SMS): {e}")


def run_scheduler():
    """Verifica a cada minuto se é hora de enviar os resumos agendados."""

    email_hour, email_minute = 15, 45
    sms_hour, sms_minute = 17, 30

    last_sent_date_email = None
    last_sent_date_sms = None

    print(f"[*] Agendador iniciado.")
    print(
        f"    -> E-mail (Caraguá) será enviado diariamente às {email_hour:02d}:{email_minute:02d} (Horário de Brasília).")
    print(f"    -> SMS (Ubatuba) será enviado diariamente às {sms_hour:02d}:{sms_minute:02d} (Horário de Brasília).")

    while True:
        now_utc = datetime.now(timezone.utc)
        brazil_tz = timezone(timedelta(hours=-3))
        now_brazil = now_utc.astimezone(brazil_tz)

        # Adiciona um log a cada minuto para verificação no Render
        print(
            f"[{datetime.now().isoformat()}] Verificando agendador. Hora atual (Brasília): {now_brazil.strftime('%H:%M:%S')}")

        if now_brazil.date() != last_sent_date_email:
            if now_brazil.hour == email_hour and now_brazil.minute == email_minute:
                send_daily_caragua_summary()
                last_sent_date_email = now_brazil.date()

        if now_brazil.date() != last_sent_date_sms:
            if now_brazil.hour == sms_hour and now_brazil.minute == sms_minute:
                send_daily_ubatuba_sms()
                last_sent_date_sms = now_brazil.date()

        time.sleep(60)


# --- ROTAS DA APLICAÇÃO ---
@app.route('/')
def serve_welcome():
    return send_from_directory('web', 'welcome.html')


@app.route('/index.html')
def serve_map_page():
    return send_from_directory('web', 'index.html')


@app.route('/api/notify_access', methods=['POST'])
def notify_access():
    threading.Thread(target=send_emails_in_background).start()
    return jsonify({"status": "processamento iniciado"}), 202


@app.route('/api/todos_os_pontos', methods=['GET'])
def get_todos_os_pontos():
    todos_os_pontos = CAPITAIS_BRASIL + CIDADES_RISCO_MONITORADAS
    pontos_unicos = list({ponto['nome']: ponto for ponto in todos_os_pontos}.values())
    return jsonify(pontos_unicos)


@app.route('/api/cidades_risco', methods=['GET'])
def get_cidades_risco():
    return jsonify(CIDADES_RISCO_MONITORADAS)


@app.route('/api/capitais_risco', methods=['GET'])
def get_capitais_risco():
    dados_monitoramento = []
    agora_utc = datetime.now(timezone.utc)
    end_date_hist = agora_utc - timedelta(days=1)
    start_date_hist = end_date_hist - timedelta(days=3)

    for capital in CAPITAIS_BRASIL:
        lat, lon = capital['lat'], capital['lon']
        nome_capital = capital['nome']
        try:
            params_forecast = {"latitude": lat, "longitude": lon, "hourly": "precipitation", "forecast_days": 3,
                               "timezone": "auto"}
            resp_forecast = requests.get(OPENMETEO_FORECAST_URL, params=params_forecast, timeout=10)
            resp_forecast.raise_for_status()
            dados_forecast = resp_forecast.json().get('hourly', {}).get('precipitation', [])
            chuva_futura = sum(p for p in dados_forecast[:72] if p is not None)

            params_chuva_hist = {"latitude": lat, "longitude": lon, "start_date": start_date_hist.strftime('%Y-%m-%d'),
                                 "end_date": end_date_hist.strftime('%Y-%m-%d'), "hourly": "precipitation",
                                 "timezone": "auto"}
            resp_chuva_hist = requests.get(OPENMETEO_HISTORICAL_URL, params=params_chuva_hist, timeout=10)
            resp_chuva_hist.raise_for_status()
            dados_chuva_hist_hourly = resp_chuva_hist.json().get('hourly', {}).get('precipitation', [])
            chuva_historica_completa = [p for p in dados_chuva_hist_hourly if p is not None][-72:]
            chuva_72h = sum(chuva_historica_completa)
            chuva_24h = sum(chuva_historica_completa[-24:])
            maior_risco = max(chuva_72h, chuva_futura)
            nivel_risco = determinar_nivel(maior_risco)
            camera_url = CAMERA_URLS.get(nome_capital)

            dados_monitoramento.append({"capital": nome_capital, "estado": capital['estado'], "lat": lat, "lon": lon,
                                        "risco_nivel": nivel_risco, "maior_risco_valor": maior_risco,
                                        "chuva_24h": chuva_24h, "chuva_72h": chuva_72h,
                                        "chuva_72h_fut": chuva_futura, "camera_url": camera_url})
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Erro para {nome_capital}: {e}")
            dados_monitoramento.append({"capital": nome_capital, "estado": capital['estado'],
                                        "risco_nivel": {"nivel": "ERRO", "cor": "#999999"}, "maior_risco_valor": 0,
                                        "chuva_24h": 0, "chuva_72h": 0, "chuva_72h_fut": 0, "camera_url": None})
    return jsonify(dados_monitoramento)


@app.route('/api/weather', methods=['GET'])
def get_weather_data():
    lat, lon = request.args.get('lat'), request.args.get('lon')
    nome_cidade = request.args.get('nome_cidade', 'Local')
    if not lat or not lon: return jsonify({"error": "Lat e Lon são obrigatórios."}), 400
    try:
        end_hist = datetime.now(timezone.utc) - timedelta(days=1)
        start_hist = end_hist - timedelta(days=3)
        params_hist = {"latitude": lat, "longitude": lon, "start_date": start_hist.strftime('%Y-%m-%d'),
                       "end_date": end_hist.strftime('%Y-%m-%d'), "hourly": "precipitation", "timezone": "auto"}
        resp_hist = requests.get(OPENMETEO_HISTORICAL_URL, params=params_hist, timeout=10)
        resp_hist.raise_for_status()
        chuva_hist = sum(p for p in resp_hist.json().get('hourly', {}).get('precipitation', [])[-72:] if p is not None)
        params_forecast = {"latitude": lat, "longitude": lon,
                           "hourly": "temperature_2m,apparent_temperature,windspeed_10m,windgusts_10m,surface_pressure,weather_code,precipitation,relative_humidity_2m,dewpoint_2m",
                           "forecast_days": 3, "timezone": "auto"}
        resp_forecast = requests.get(OPENMETEO_FORECAST_URL, params=params_forecast, timeout=10)
        resp_forecast.raise_for_status()
        hourly = resp_forecast.json().get('hourly', {})

        def get_val(key):
            values = hourly.get(key)
            return values[0] if values and len(values) > 0 else None

        chuva_fut = sum(p for p in hourly.get('precipitation', [])[:72] if p is not None)
        return jsonify(
            {"temperatura": get_val('temperature_2m'), "cidade_nome": nome_cidade, "chuva_72h_hist": chuva_hist,
             "chuva_72h_fut": chuva_fut, "sensacao_termica": get_val('apparent_temperature'),
             "velocidade_vento": get_val('windspeed_10m'), "pressao": get_val('surface_pressure'),
             "descricao_tempo": converter_codigo_tempo(get_val('weather_code')),
             "umidade_relativa": get_val('relative_humidity_2m'), "ponto_orvalho": get_val('dewpoint_2m'),
             "rajada_vento": get_val('windgusts_10m')})
    except Exception as e:
        print(f"Erro na rota /api/weather: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/historical_pluvio', methods=['GET'])
def get_historical_pluvio_data():
    lat, lon = request.args.get('lat'), request.args.get('lon')
    periodo_horas = int(request.args.get('periodo', 72))
    nome_cidade_frontend = request.args.get('nome_cidade', 'Local')
    if not lat or not lon: return jsonify({"error": "Lat e Lon são obrigatórios."}), 400
    end_time_utc = datetime.now(timezone.utc) - timedelta(days=1)
    start_time_utc = end_time_utc - timedelta(hours=periodo_horas)
    params = {"latitude": lat, "longitude": lon, "start_date": start_time_utc.strftime('%Y-%m-%d'),
              "end_date": end_time_utc.strftime('%Y-%m-%d'), "hourly": "precipitation", "timezone": "auto"}
    try:
        resp = requests.get(OPENMETEO_HISTORICAL_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        precip = data.get('hourly', {}).get('precipitation', [])[-periodo_horas:]
        times = data.get('hourly', {}).get('time', [])[-periodo_horas:]
        return jsonify(
            {"cidade": nome_cidade_frontend, "municipio": nome_cidade_frontend, "volume_pluviometria": precip,
             "data_pluviometria": times, "acumulado_total": sum(p for p in precip if p is not None)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/forecast_chart', methods=['GET'])
def get_forecast_chart_data():
    lat, lon = request.args.get('lat'), request.args.get('lon')
    nome_cidade_frontend = request.args.get('nome_cidade', 'Local')
    if not lat or not lon: return jsonify({"error": "Lat e Lon são obrigatórios."}), 400
    try:
        params_forecast = {"latitude": lat, "longitude": lon,
                           "hourly": "temperature_2m,apparent_temperature,precipitation_probability,precipitation,dewpoint_2m,relative_humidity_2m,windspeed_10m,windgusts_10m,surface_pressure,weather_code",
                           "forecast_days": 7, "timezone": "auto"}
        resp_forecast = requests.get(OPENMETEO_FORECAST_URL, params=params_forecast, timeout=10)
        resp_forecast.raise_for_status()
        dados_forecast = resp_forecast.json()
        dados_forecast['cidade_nome'] = nome_cidade_frontend
        dados_forecast['municipio'] = nome_cidade_frontend
        return jsonify(dados_forecast)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)

