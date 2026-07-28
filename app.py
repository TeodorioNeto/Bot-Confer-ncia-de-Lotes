"""
app.py
Servidor Backend Local com Transmissão de Logs em Tempo Real (SSE) e Suporte a Temas.
"""

import queue
import threading
from flask import Flask, Response, jsonify, request
from flask_cors import CORS

from src.web_automation_playwright import processar_datapool_playwright
from src.web_automation_selenium import processar_datapool_selenium

app = Flask(__name__)
CORS(app)

log_queue = queue.Queue()


def enviar_log_live(mensagem, tipo="info"):
    """Envia a mensagem para a fila SSE."""
    log_queue.put({"mensagem": mensagem, "tipo": tipo})


@app.route("/stream-logs")
def stream_logs():
    def generate():
        while True:
            try:
                item = log_queue.get(timeout=20)
                msg = item["mensagem"].replace("\n", " ")
                tipo = item["tipo"]
                yield f"data: {{\"mensagem\": \"{msg}\", \"tipo\": \"{tipo}\"}}\n\n"
            except queue.Empty:
                yield ": keep-alive\n\n"

    return Response(generate(), mimetype="text/event-stream")


@app.route("/run-playwright", methods=["POST"])
def run_playwright():
    data = request.get_json(silent=True) or {}
    theme = data.get("theme", "dark")

    def worker():
        try:
            total = processar_datapool_playwright(delay_passo=0.2, callback_log=enviar_log_live, theme=theme)
            enviar_log_live(f"Playwright finalizado! Total de lotes: {total}", "success")
        except Exception as e:
            enviar_log_live(f"Falha na execução Playwright: {e}", "error")

    threading.Thread(target=worker).start()
    return jsonify({"status": "iniciado", "mensagem": "Automação Playwright iniciada!"})


@app.route("/run-selenium", methods=["POST"])
def run_selenium():
    data = request.get_json(silent=True) or {}
    theme = data.get("theme", "dark")

    def worker():
        try:
            total = processar_datapool_selenium(delay_passo=0.1, callback_log=enviar_log_live, theme=theme)
            enviar_log_live(f"Selenium finalizado! Total de lotes: {total}", "success")
        except Exception as e:
            enviar_log_live(f"Falha na execução Selenium: {e}", "error")

    threading.Thread(target=worker).start()
    return jsonify({"status": "iniciado", "mensagem": "Automação Selenium iniciada!"})


if __name__ == "__main__":
    print("==================================================")
    print("Servidor de Automação Ativo em: http://127.0.0.1:5000")
    print("==================================================")
    app.run(host="127.0.0.1", port=5000, debug=True)