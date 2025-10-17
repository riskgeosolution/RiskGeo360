import time
import schedule
from server import app, send_daily_caragua_summary

def job():
    """
    Função wrapper para executar a tarefa de resumo diário
    dentro do contexto da aplicação Flask.
    """
    with app.app_context():
        send_daily_caragua_summary()

# --- CONFIGURAÇÃO DO AGENDAMENTO ---
# Horário ajustado para 21:00
SCHEDULE_TIME = "21:00"
TIMEZONE = "America/Sao_Paulo"

print(f"Iniciando o agendador de tarefas (scheduler.py)...")
print(f"A tarefa de resumo diario sera executada todos os dias as {SCHEDULE_TIME} ({TIMEZONE}).")

schedule.every().day.at(SCHEDULE_TIME, TIMEZONE).do(job)

while True:
    schedule.run_pending()
    time.sleep(60) # Verifica a cada 60 segundos se há tarefas a executar

