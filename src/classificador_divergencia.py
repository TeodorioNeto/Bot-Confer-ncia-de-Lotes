"""Classificador resiliente de causa provavel a partir da observacao."""

from __future__ import annotations

import json
import socket
import time
import unicodedata
from dataclasses import asdict, dataclass
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ResultadoClassificacao:
    causa_provavel: str
    confianca_ml: float
    origem_decisao: str
    motivo_fallback: str | None
    latencia_ml_ms: float

    def to_dict(self) -> dict:
        return asdict(self)


class ClassificadorDivergencia:
    """Sugere uma causa, mas nunca decide o status de negocio do item."""

    def __init__(
        self,
        *,
        enabled: bool,
        confidence_min: float,
        timeout_seconds: float = 2.0,
        endpoint_url: str = "",
        mock_delay_seconds: float = 0.0,
        force_confidence: float | None = None,
        force_error: bool = False,
        predictor: Callable[[str], dict] | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
        logger=None,
    ):
        if not 0 <= confidence_min <= 1:
            raise ValueError("confidence_min deve estar entre 0 e 1")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds deve ser maior que zero")

        self.enabled = enabled
        self.confidence_min = confidence_min
        self.timeout_seconds = timeout_seconds
        self.endpoint_url = endpoint_url.strip()
        self.mock_delay_seconds = max(0.0, mock_delay_seconds)
        self.force_confidence = force_confidence
        self.force_error = force_error
        self.predictor = predictor
        self.sleep_fn = sleep_fn
        self.logger = logger

    def classificar(self, observacao) -> ResultadoClassificacao:
        started_at = time.perf_counter()
        if not self.enabled:
            return self._fallback("ml_desabilitado", started_at)

        text = str(observacao or "").strip()
        if not text:
            return self._fallback("observacao_vazia", started_at)

        try:
            if self.force_error:
                raise URLError("falha forcada para simulacao")

            if self.mock_delay_seconds > self.timeout_seconds:
                self.sleep_fn(self.timeout_seconds)
                raise TimeoutError("classificador excedeu o timeout")
            if self.mock_delay_seconds:
                self.sleep_fn(self.mock_delay_seconds)

            if self.predictor is not None:
                raw = self.predictor(text)
            elif self.endpoint_url:
                raw = self._classificar_por_api(text)
            else:
                raw = self._classificar_mock(text)

            cause = str(raw["causa_provavel"]).strip()
            confidence = float(raw["confianca_ml"])
            if self.force_confidence is not None:
                confidence = float(self.force_confidence)
            if not cause or not 0 <= confidence <= 1:
                raise ValueError("resposta do classificador fora do contrato")

            if confidence < self.confidence_min:
                return self._fallback(
                    "baixa_confianca",
                    started_at,
                    confidence=confidence,
                )

            return ResultadoClassificacao(
                causa_provavel=cause,
                confianca_ml=confidence,
                origem_decisao="ml",
                motivo_fallback=None,
                latencia_ml_ms=_elapsed_ms(started_at),
            )
        except (TimeoutError, socket.timeout):
            return self._fallback("timeout", started_at)
        except (HTTPError, URLError, OSError):
            return self._fallback("servico_indisponivel", started_at)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return self._fallback("resposta_invalida", started_at)
        except Exception as error:  # protecao final: nunca propagar ao bot
            if self.logger is not None:
                self.logger.exception("Falha inesperada no classificador: %s", error)
            return self._fallback("erro_inesperado", started_at)

    def _classificar_por_api(self, text: str) -> dict:
        body = json.dumps({"observacao": text}).encode("utf-8")
        request = Request(
            self.endpoint_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            if response.status >= 400:
                raise HTTPError(
                    self.endpoint_url,
                    response.status,
                    "erro HTTP no classificador",
                    response.headers,
                    None,
                )
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _classificar_mock(text: str) -> dict:
        normalized = _normalize_text(text)
        patterns = [
            (("digit", "codigo errado", "cadastro"), "erro_digitacao", 0.94),
            (("faltou", "peca", "componente", "ausente"), "falta_componente", 0.92),
            (("duplic" ,), "registro_duplicado", 0.96),
            (("doca", "avaria", "transporte", "danific"), "problema_operacional", 0.88),
            (("falha no painel", "painel de controle"), "falha_componente", 0.91),
            (("uso interno", "aprovado parcial"), "status_nao_padronizado", 0.89),
            (("aguardando laudo", "laudo tecnico"), "pendencia_tecnica", 0.90),
        ]
        for keywords, cause, confidence in patterns:
            if any(keyword in normalized for keyword in keywords):
                return {
                    "causa_provavel": cause,
                    "confianca_ml": confidence,
                }
        return {"causa_provavel": "nao_classificado", "confianca_ml": 0.40}

    def _fallback(
        self,
        reason: str,
        started_at: float,
        *,
        confidence: float = 0.0,
    ) -> ResultadoClassificacao:
        result = ResultadoClassificacao(
            causa_provavel="nao_classificado",
            confianca_ml=confidence,
            origem_decisao="fallback",
            motivo_fallback=reason,
            latencia_ml_ms=_elapsed_ms(started_at),
        )
        if self.logger is not None:
            self.logger.warning(
                "Classificador em fallback. motivo=%s confianca=%.3f",
                reason,
                confidence,
            )
        return result


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower()


def _elapsed_ms(started_at: float) -> float:
    return (time.perf_counter() - started_at) * 1000
