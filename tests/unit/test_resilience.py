import pytest

from src.resilience import RetryExhaustedError, executar_com_retry_linear


def test_retry_linear_recupera_na_terceira_tentativa():
    attempts = []
    delays = []

    def operation():
        attempts.append(len(attempts) + 1)
        if len(attempts) < 3:
            raise FileNotFoundError("base temporariamente indisponivel")
        return {"LG-001"}

    result = executar_com_retry_linear(
        operation,
        operation_name="base_referencia",
        max_attempts=3,
        initial_delay_seconds=1,
        sleep_fn=delays.append,
    )

    assert result == {"LG-001"}
    assert attempts == [1, 2, 3]
    assert delays == [1, 2]


def test_retry_linear_informa_esgotamento():
    with pytest.raises(RetryExhaustedError) as captured:
        executar_com_retry_linear(
            lambda: (_ for _ in ()).throw(OSError("sem acesso")),
            operation_name="base_referencia",
            max_attempts=2,
            initial_delay_seconds=0,
            sleep_fn=lambda _: None,
        )

    assert captured.value.attempts == 2
    assert captured.value.operation_name == "base_referencia"
    assert isinstance(captured.value.last_error, OSError)


def test_retry_nao_repete_erro_de_formato():
    attempts = []

    def operation():
        attempts.append(1)
        raise ValueError("aba Base_Referencia invalida")

    with pytest.raises(ValueError, match="Base_Referencia"):
        executar_com_retry_linear(
            operation,
            operation_name="base_referencia",
            sleep_fn=lambda _: None,
        )

    assert attempts == [1]
