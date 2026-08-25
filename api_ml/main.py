"""API FastAPI para classificacao ML de lotes ambiguos."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import joblib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

try:
    from pydantic import field_validator

    turno_validator = field_validator("turno")
except ImportError:
    from pydantic import validator

    turno_validator = validator("turno")

from api_ml.features import TURNO_MAP, codificar_features


MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "classificador_lotes.pkl"
MODELO: dict[str, Any] = {"model": None, "loaded": False, "error": None}


class LoteInput(BaseModel):
    lote_id: str = Field(..., min_length=1)
    status_raw: str = Field(..., min_length=1)
    turno: str = Field(..., min_length=1)
    tem_obs: bool

    @turno_validator
    def validar_turno(cls, valor):
        if str(valor).strip().upper() not in TURNO_MAP:
            raise ValueError("turno deve ser MANHA, TARDE ou NOITE")
        return valor


class PredictionOutput(BaseModel):
    lote_id: str
    classe: str
    probabilidade: float
    nivel_confianca: str
    acao: str
    latencia_ms: float
    modelo_carregado: bool


@asynccontextmanager
async def lifespan(app: FastAPI):
    carregar_modelo()
    yield


app = FastAPI(title="Classificador de Lotes", version="24A", lifespan=lifespan)


def carregar_modelo() -> None:
    try:
        pacote = joblib.load(MODEL_PATH)
        MODELO["model"] = pacote["model"]
        MODELO["loaded"] = True
        MODELO["error"] = None
    except Exception as erro:
        MODELO["model"] = None
        MODELO["loaded"] = False
        MODELO["error"] = str(erro)


@app.get("/health")
def health():
    return {
        "status": "ok" if MODELO["loaded"] else "degraded",
        "model_loaded": MODELO["loaded"],
        "error": MODELO["error"],
    }


@app.post("/predict", response_model=PredictionOutput)
def predict(lote: LoteInput):
    inicio = time.perf_counter()
    modelo = MODELO["model"]
    if modelo is None:
        raise HTTPException(status_code=503, detail="modelo não carregado")

    features = [codificar_features(lote.status_raw, lote.turno, lote.tem_obs)]
    probabilidades = modelo.predict_proba(features)[0]
    indice = int(probabilidades.argmax())
    classe = str(modelo.classes_[indice])
    probabilidade = float(probabilidades[indice])
    nivel, acao = calibrar_confianca(probabilidade)
    latencia_ms = (time.perf_counter() - inicio) * 1000

    return PredictionOutput(
        lote_id=lote.lote_id,
        classe=classe,
        probabilidade=probabilidade,
        nivel_confianca=nivel,
        acao=acao,
        latencia_ms=latencia_ms,
        modelo_carregado=True,
    )


def calibrar_confianca(probabilidade: float) -> tuple[str, str]:
    if probabilidade >= 0.85:
        return "alta", "acao_automatica"
    if probabilidade >= 0.65:
        return "media", "revisar"
    return "baixa", "revisar_prioritario"
