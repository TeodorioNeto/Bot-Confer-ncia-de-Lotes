import json
from urllib.error import URLError

import pytest

import src.ml_client as ml_client_module
from item_processor import REVISAO_ML_OFFLINE, classificar_ambiguo_com_ml
from src.ml_client import MLClient


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(
            {
                "lote_id": "LG-2026-ML0001",
                "classe": "revisar",
                "probabilidade": 0.7,
                "nivel_confianca": "media",
                "acao": "revisar",
                "latencia_ms": 12.5,
            }
        ).encode("utf-8")


@pytest.mark.unit
def test_ml_client_sucesso(monkeypatch):
    monkeypatch.setattr(ml_client_module, "urlopen", lambda request, timeout: FakeResponse())
    client = MLClient("http://ml.local")

    predicao = client.classificar(
        {
            "lote_id": "LG-2026-ML0001",
            "status_raw": "EM ANALISE",
            "turno": "MANHA",
            "tem_obs": True,
        }
    )

    assert predicao is not None
    assert predicao.classe == "revisar"
    assert predicao.probabilidade == 0.7
    assert client.failures == 0


@pytest.mark.unit
def test_ml_client_api_fora_do_ar_retorna_none(monkeypatch):
    monkeypatch.setattr(
        ml_client_module,
        "urlopen",
        lambda request, timeout: (_ for _ in ()).throw(URLError("offline")),
    )
    client = MLClient("http://ml.local")

    assert client.classificar({"lote_id": "LG-2026-ML0001"}) is None
    assert client.failures == 1


@pytest.mark.unit
def test_circuit_breaker_abre_apos_cinco_falhas(monkeypatch):
    chamadas = {"total": 0}

    def falhar(request, timeout):
        chamadas["total"] += 1
        raise URLError("offline")

    monkeypatch.setattr(ml_client_module, "urlopen", falhar)
    client = MLClient("http://ml.local", max_failures=5)

    for _ in range(5):
        assert client.classificar({"lote_id": "LG-2026-ML0001"}) is None

    assert client.disabled is True
    assert client.classificar({"lote_id": "LG-2026-ML0001"}) is None
    assert chamadas["total"] == 5


@pytest.mark.unit
def test_item_processor_aplica_revisao_ml_offline_quando_predicao_none():
    class ItemFake:
        def get_value(self, chave):
            return {
                "lote_id": "LG-2026-ML0002",
                "status": "EM ANALISE",
                "turno": "TARDE",
                "observacao": "",
            }.get(chave)

    class ClientOffline:
        def classificar(self, payload):
            return None

    decisao = classificar_ambiguo_com_ml(ItemFake(), ClientOffline())

    assert decisao["classe"] == REVISAO_ML_OFFLINE
    assert decisao["fallback"] is True
