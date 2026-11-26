"""CP-01 · Rate limit e Turnstile (REQ-19 e REQ-20)."""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.models.rate_limit import RateLimitBucket
from app.services import rate_limit_service, turnstile_service
from app.utils.validation import ApiError

AGORA = datetime(2026, 12, 14, 10, 0, 30)


# REQ-19 ------------------------------------------------------------------------------------

def test_rate_limit_bloqueia_acima_do_limite_e_reinicia_na_janela(app):
    consumir = rate_limit_service.consumir
    assert consumir("candidatura", "1.2.3.4", limite=2, janela_segundos=60, agora=AGORA)
    assert consumir("candidatura", "1.2.3.4", limite=2, janela_segundos=60, agora=AGORA + timedelta(seconds=10))
    assert not consumir("candidatura", "1.2.3.4", limite=2, janela_segundos=60, agora=AGORA + timedelta(seconds=20))
    # Janela seguinte: contagem reiniciada
    assert consumir("candidatura", "1.2.3.4", limite=2, janela_segundos=60, agora=AGORA + timedelta(seconds=40))


def test_rate_limit_separa_identificador_e_acao(app):
    consumir = rate_limit_service.consumir
    assert consumir("a", "1.1.1.1", limite=1, janela_segundos=60, agora=AGORA)
    assert not consumir("a", "1.1.1.1", limite=1, janela_segundos=60, agora=AGORA)
    assert consumir("a", "2.2.2.2", limite=1, janela_segundos=60, agora=AGORA)
    assert consumir("b", "1.1.1.1", limite=1, janela_segundos=60, agora=AGORA)


def test_rate_limit_nao_guarda_ip_em_claro(app):
    rate_limit_service.consumir("candidatura", "203.0.113.77", limite=5, janela_segundos=60, agora=AGORA)
    chaves = [b.bucket_key for b in RateLimitBucket.query.all()]
    assert chaves and all("203.0.113.77" not in c for c in chaves)
    assert all(len(c) <= 120 for c in chaves)


# REQ-20 ------------------------------------------------------------------------------------

def _resposta(corpo):
    r = MagicMock()
    r.json.return_value = corpo
    return r


@pytest.fixture
def com_segredo(app):
    app.config["TURNSTILE_SECRET_KEY"] = "segredo-de-teste"
    return app


def test_turnstile_sem_segredo_em_teste_passa(app):
    assert turnstile_service.verificar(None, "candidatura") is True


def test_turnstile_sem_segredo_em_producao_recusa(app):
    app.config["TESTING"] = False
    app.debug = False
    try:
        with pytest.raises(ApiError) as erro:
            turnstile_service.verificar("tok", "candidatura")
        assert erro.value.status == 503
    finally:
        app.config["TESTING"] = True


@pytest.mark.parametrize("corpo,esperado", [
    ({"success": True, "action": "candidatura"}, True),
    ({"success": True, "action": "aceite_termo"}, False),
    ({"success": False, "action": "candidatura"}, False),
    ({"success": "true", "action": "candidatura"}, False),
    (["inesperado"], False),
])
def test_turnstile_resposta(com_segredo, corpo, esperado):
    with patch.object(turnstile_service.requests, "post", return_value=_resposta(corpo)) as post:
        assert turnstile_service.verificar("tok", "candidatura", ip="1.2.3.4") is esperado
    enviado = post.call_args.kwargs["data"]
    assert enviado["secret"] == "segredo-de-teste" and enviado["remoteip"] == "1.2.3.4"


@pytest.mark.parametrize("token", [None, "", 123, "x" * 3000])
def test_turnstile_token_invalido_nem_consulta(com_segredo, token):
    with patch.object(turnstile_service.requests, "post") as post:
        assert turnstile_service.verificar(token, "candidatura") is False
    post.assert_not_called()


def test_turnstile_falha_de_rede_reprova(com_segredo):
    with patch.object(turnstile_service.requests, "post", side_effect=requests.Timeout()):
        assert turnstile_service.verificar("tok", "candidatura") is False
