"""Cliente resiliente para a API ML de classificacao de lotes."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class MLPrediction:
    lote_id: str
    classe: str
    probabilidade: float
    nivel_confianca: str
    acao: str
    latencia_ms: float


class MLClient:
    """Cliente que nunca propaga excecoes para o bot."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        *,
        timeout: float = 2.0,
        max_failures: int = 5,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_failures = max_failures
        self.failures = 0
        self.disabled = False

    def classificar(self, payload: dict[str, Any]) -> MLPrediction | None:
        if self.disabled:
            return None

        inicio = time.perf_counter()
        try:
            corpo = json.dumps(payload).encode("utf-8")
            request = Request(
                f"{self.base_url}/predict",
                data=corpo,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=self.timeout) as resposta:
                if resposta.status >= 400:
                    self._registrar_falha()
                    return None
                dados = json.loads(resposta.read().decode("utf-8"))
            self.failures = 0
            return MLPrediction(
                lote_id=str(dados.get("lote_id", payload.get("lote_id", ""))),
                classe=str(dados["classe"]),
                probabilidade=float(dados["probabilidade"]),
                nivel_confianca=str(dados["nivel_confianca"]),
                acao=str(dados["acao"]),
                latencia_ms=float(dados.get("latencia_ms", 0))
                or ((time.perf_counter() - inicio) * 1000),
            )
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError):
            self._registrar_falha()
            return None

    def _registrar_falha(self) -> None:
        self.failures += 1
        if self.failures >= self.max_failures:
            self.disabled = True

    def reset(self) -> None:
        self.failures = 0
        self.disabled = False
