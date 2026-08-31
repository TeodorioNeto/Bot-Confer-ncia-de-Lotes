"""Padroes reutilizaveis de resiliencia do pipeline corporativo."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar


T = TypeVar("T")


class RetryExhaustedError(RuntimeError):
    """Indica que uma operacao critica esgotou todas as tentativas."""

    def __init__(self, operation_name: str, attempts: int, last_error: Exception):
        self.operation_name = operation_name
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"Operacao '{operation_name}' falhou apos {attempts} tentativas: "
            f"{last_error}"
        )


def executar_com_retry_linear(
    operation: Callable[[], T],
    *,
    operation_name: str,
    max_attempts: int = 3,
    initial_delay_seconds: float = 1.0,
    retryable_exceptions: tuple[type[BaseException], ...] = (OSError,),
    sleep_fn: Callable[[float], None] = time.sleep,
    logger=None,
) -> T:
    """Executa uma operacao com backoff linear entre as tentativas.

    O intervalo antes da segunda tentativa e ``initial_delay_seconds``;
    antes da terceira, o dobro; e assim por diante. Erros de negocio ou de
    formato nao incluidos em ``retryable_exceptions`` sao propagados sem
    repeticao.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts deve ser maior ou igual a 1")
    if initial_delay_seconds < 0:
        raise ValueError("initial_delay_seconds nao pode ser negativo")

    for attempt in range(1, max_attempts + 1):
        try:
            return operation()
        except retryable_exceptions as error:
            if logger is not None:
                logger.warning(
                    "Operacao critica %s falhou na tentativa %d/%d: %s",
                    operation_name,
                    attempt,
                    max_attempts,
                    error,
                )

            if attempt == max_attempts:
                raise RetryExhaustedError(
                    operation_name,
                    max_attempts,
                    error,
                ) from error

            delay = initial_delay_seconds * attempt
            if logger is not None:
                logger.info(
                    "Nova tentativa de %s em %.2f segundo(s).",
                    operation_name,
                    delay,
                )
            sleep_fn(delay)

    raise AssertionError("Fluxo de retry terminou em estado impossivel")
