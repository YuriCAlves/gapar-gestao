"""Homologação do deploy (Checkpoint 7): confere a aplicação publicada de fora para dentro.

Uso:
    python scripts/homologacao.py https://gapar.vercel.app

Não precisa de login nem altera dados: só verifica roteamento, HTTPS, travas de acesso e a
configuração exposta. Os fluxos autenticados (Google) são conferidos no roteiro manual do docs/.
Sai com código 1 se alguma verificação falhar.
"""
import re
import sys
from urllib.parse import parse_qs, urlparse

import requests

TIMEOUT = 20


class Homologacao:
    def __init__(self, base):
        self.base = base.rstrip("/")
        self.falhas = 0
        self.sessao = requests.Session()

    def get(self, caminho, **kw):
        return self.sessao.get(self.base + caminho, timeout=TIMEOUT, allow_redirects=False, **kw)

    def checar(self, descricao, condicao, detalhe=""):
        print(f"[{'OK ' if condicao else 'FALHOU'}] {descricao}" + (f" ({detalhe})" if detalhe and not condicao else ""))
        if not condicao:
            self.falhas += 1

    def executar(self):
        print(f"Homologando {self.base}\n")
        self.checar("Endereço usa HTTPS", self.base.startswith("https://"))

        # --- Camada View: SPA servida pela CDN, inclusive em links diretos ---
        raiz = self.get("/")
        self.checar("SPA responde em /", raiz.status_code == 200 and "text/html" in raiz.headers.get("content-type", ""),
                    f"status {raiz.status_code}")
        for rota in ("/animais", "/hoje", "/admin", "/rota-que-nao-existe"):
            r = self.get(rota)
            self.checar(f"Link direto {rota} cai na SPA", r.status_code == 200 and 'id="root"' in r.text,
                        f"status {r.status_code}")
        scripts = re.findall(r'src="(/assets/[^"]+\.js)"', raiz.text)
        self.checar("index.html referencia o bundle em /assets", bool(scripts))
        for script in scripts[:1]:
            r = self.get(script)
            self.checar("Bundle JS é servido", r.status_code == 200 and "javascript" in r.headers.get("content-type", ""),
                        f"status {r.status_code}")

        # --- Controllers: API Flask na função serverless ---
        status = self.get("/auth/status")
        corpo = status.json() if status.headers.get("content-type", "").startswith("application/json") else {}
        self.checar("API responde em /auth/status", status.status_code == 200 and bool(corpo), f"status {status.status_code}")
        self.checar("Sem sessão, /auth/status informa deslogado", corpo.get("autenticado") is False,
                    str(corpo)[:120])

        resposta_login = self.get("/auth/login")
        try:
            login = resposta_login.json()
        except ValueError:
            login = {}
            self.checar("/auth/login responde JSON (não está atrás de proteção da Vercel?)", False,
                        f"status {resposta_login.status_code}")
        self.checar("Login de desenvolvimento desligado", login.get("dev_login") is False, str(login))
        self.checar("Google OAuth configurado", login.get("google_configurado") is True, str(login))

        dev = self.sessao.post(self.base + "/auth/dev-login", json={}, timeout=TIMEOUT)
        self.checar("POST /auth/dev-login não existe (404)", dev.status_code == 404, f"status {dev.status_code}")

        for rota in ("/api/hoje", "/api/animais", "/api/admin/whitelist", "/api/admin/nao-aptos"):
            r = self.get(rota)
            json_ok = r.headers.get("content-type", "").startswith("application/json")
            self.checar(f"{rota} exige login (401 em JSON)", r.status_code == 401 and json_ok and r.json().get("codigo") == 401,
                        f"status {r.status_code}")

        google = self.get("/auth/google")
        destino = google.headers.get("Location", "")
        parametros = parse_qs(urlparse(destino).query)
        redirect_uri = parametros.get("redirect_uri", [""])[0]
        client_id = parametros.get("client_id", [""])[0]
        self.checar("Client ID do Google é real (não é o de exemplo)",
                    client_id.endswith(".apps.googleusercontent.com") and "mock" not in client_id, client_id)
        self.checar("/auth/google redireciona ao Google", google.status_code == 302 and "accounts.google.com" in destino,
                    f"status {google.status_code}")
        self.checar("Retorno do Google aponta para este domínio em HTTPS", redirect_uri == self.base + "/auth/callback",
                    redirect_uri or "sem redirect_uri")
        cookie = google.headers.get("Set-Cookie", "")
        self.checar("Cookie de sessão é Secure e HttpOnly", "Secure" in cookie and "HttpOnly" in cookie, cookie[:120])

        print(f"\n{'Homologação aprovada' if not self.falhas else f'{self.falhas} verificação(ões) falharam'}.")
        return 0 if not self.falhas else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(Homologacao(sys.argv[1]).executar())
