import pytest
from fastapi.testclient import TestClient

from api_ml.main import app


@pytest.mark.integration
def test_predict_payload_valido():
    with TestClient(app) as client:
        resposta = client.post(
            "/predict",
            json={
                "lote_id": "LG-2026-ML9999",
                "status_raw": "EM ANALISE",
                "turno": "MANHA",
                "tem_obs": True,
            },
        )

    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["lote_id"] == "LG-2026-ML9999"
    assert dados["classe"] in {
        "válido_automático",
        "revisar",
        "recusar_automático",
    }
    assert 0 <= dados["probabilidade"] <= 1
    assert dados["nivel_confianca"] in {"alta", "media", "baixa"}


@pytest.mark.integration
def test_predict_rejeita_turno_invalido():
    with TestClient(app) as client:
        resposta = client.post(
            "/predict",
            json={
                "lote_id": "LG-2026-ML9999",
                "status_raw": "EM ANALISE",
                "turno": "MADRUGADA",
                "tem_obs": True,
            },
        )

    assert resposta.status_code == 422
