import os
import requests
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta, timezone
import threading
import time
import schedule

# --- CONFIGURAÇÃO ---
OPENMETEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPENMETEO_HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/era5"
COMTELE_API_URL = "https://sms.comtele.com.br/api/v2/send" # URL da API Comtele

# ... (O resto do seu código de configuração, listas de cidades, etc. continua aqui sem alterações) ...
# ... (As funções converter_codigo_tempo, determinar_nivel, etc. continuam aqui) ...
# ... (As funções de busca de dados como get_sjc_weather_summary e get_caragua_weather_summary continuam aqui) ...
# --- FUNÇÕES DE ENVIO DE NOTIFICAÇÃO --- (Todo este bloco continua igual) ...
# --- ROTAS DA APLICAÇÃO --- (Todo este bloco continua igual) ...

# O bloco if __name__ == '__main__' é modificado para rodar apenas o servidor de desenvolvimento localmente
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # O agendador NÃO é mais iniciado aqui
    app.run(host='0.0.0.0', port=port, debug=True)

