import requests

# --- Configurações ---
# 1. SUBSTITUA 'SUA_CHAVE_AQUI' PELA SUA CHAVE REAL DO OPENWEATHERMAP!
API_KEY = "a117d22f7dbbd7f0391134810e7c6f85"
CIDADE = "Sao Paulo"
# Você pode trocar para qualquer cidade que desejar, por exemplo: "Rio de Janeiro"

BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

# --- 1. Montagem da URL da Requisição ---
parametros = {
    "q": CIDADE,
    "appid": API_KEY,
    "units": "metric",  # Para obter a temperatura em Celsius
    "lang": "pt_br"  # Para obter a descrição do tempo em português
}

print(f"Buscando dados para: {CIDADE}...")

# --- 2. Realização da Requisição HTTP GET ---
try:
    resposta = requests.get(BASE_URL, params=parametros)

    # Levanta uma exceção para códigos de status HTTP ruins (4xx ou 5xx)
    resposta.raise_for_status()

    # Converte a resposta JSON em um dicionário Python
    dados = resposta.json()

    # --- 3. Processamento dos Dados ---
    if dados["cod"] == 200:

        # Extração das informações principais
        temperatura = dados["main"]["temp"]
        sensacao_termica = dados["main"]["feels_like"]
        umidade = dados["main"]["humidity"]
        descricao = dados["weather"][0]["description"].capitalize()
        vento = dados["wind"]["speed"]

        # Exibição dos resultados
        print("\n--- Condição Climática Atual ---")
        print(f"Cidade: {dados['name']}, {dados['sys']['country']}")
        print(f"Descrição: {descricao}")
        print(f"Temperatura: {temperatura}°C")
        print(f"Sensação Térmica: {sensacao_termica}°C")
        print(f"Umidade: {umidade}%")
        print(f"Velocidade do Vento: {vento} m/s")

    else:
        print(f"\nErro na resposta da API: {dados.get('message', 'Mensagem de erro não disponível')}")

except requests.exceptions.HTTPError as e:
    # Este erro ocorre frequentemente se a API_KEY estiver errada ou a cidade não for encontrada (erro 401 ou 404)
    print(f"\nErro HTTP: Verifique sua chave de API ou o nome da cidade. Detalhes: {e}")
except requests.exceptions.RequestException as e:
    print(f"\nErro de conexão (Sem internet?): {e}")
except Exception as e:
    print(f"\nOcorreu um erro inesperado: {e}")