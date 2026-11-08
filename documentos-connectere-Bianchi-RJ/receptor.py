#!/usr/bin/env python3
"""Recebe PDF e imagem enviados pelo navegador logado no +Gestão.

Uso, a partir desta pasta, uma fazenda por vez:

    python3 receptor.py baixados/pj-faz-luciano-mt
    python3 receptor.py baixados/pj-carlos
    python3 receptor.py baixados/pj-faz-bianchi

Encerre o processo da porta 8765 antes de apontar para outra fazenda.
Nome de arquivo começando com _ entra em append (logs).
Os demais vão para a subpasta AAAA-MM do próprio nome.
"""
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

if len(sys.argv) < 2:
    sys.exit("uso: python3 receptor.py PASTA_DESTINO [porta]")

DEST = os.path.abspath(sys.argv[1])
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
os.makedirs(DEST, exist_ok=True)


class Receptor(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Filename")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        tamanho = int(self.headers.get("Content-Length", "0"))
        data = self.rfile.read(tamanho)
        nome = os.path.basename(self.headers.get("X-Filename", "arquivo.bin"))
        if nome.startswith("_"):
            caminho = os.path.join(DEST, nome)
            modo = "ab"
        else:
            mes = nome[:7] if len(nome) >= 7 and nome[4] == "-" and nome[:4].isdigit() else "sem-data"
            pasta = os.path.join(DEST, mes)
            os.makedirs(pasta, exist_ok=True)
            caminho = os.path.join(pasta, nome)
            modo = "wb"
        with open(caminho, modo) as arquivo:
            arquivo.write(data)
        corpo = b"ok"
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def log_message(self, formato, *args):
        return


print(f"escutando 127.0.0.1:{PORT} -> {DEST}", flush=True)
ThreadingHTTPServer(("127.0.0.1", PORT), Receptor).serve_forever()
