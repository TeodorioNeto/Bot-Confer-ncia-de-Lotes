from types import SimpleNamespace

import pytest

from wait_for_predecessor import (
    PredecessorFailedError,
    PredecessorTimeoutError,
    predecessor_task_id_from_parameters,
    wait_for_predecessor,
)


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def monotonic(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds


class FakeMaestro:
    def __init__(self, tasks):
        self.tasks = list(tasks)
        self.calls = []

    def get_task(self, task_id):
        self.calls.append(task_id)
        if len(self.tasks) > 1:
            return self.tasks.pop(0)
        return self.tasks[0]


def test_aguarda_predecessor_ate_sucesso():
    maestro = FakeMaestro(
        [
            SimpleNamespace(state="RUNNING", finish_status="", finish_message=""),
            SimpleNamespace(
                state="FINISHED",
                finish_status="SUCCESS",
                finish_message="Dispatcher concluido",
            ),
        ]
    )
    clock = FakeClock()

    result = wait_for_predecessor(
        maestro,
        101,
        timeout_seconds=10,
        poll_interval_seconds=1,
        sleep_fn=clock.sleep,
        monotonic_fn=clock.monotonic,
    )

    assert result.task_id == "101"
    assert result.finish_status == "SUCCESS"
    assert maestro.calls == ["101", "101"]


def test_rejeita_predecessor_finalizado_com_falha():
    maestro = FakeMaestro(
        [
            SimpleNamespace(
                state="FINISHED",
                finish_status="FAILED",
                finish_message="Erro de entrada",
            )
        ]
    )

    with pytest.raises(PredecessorFailedError, match="FAILED"):
        wait_for_predecessor(maestro, "102")


def test_timeout_impede_espera_infinita():
    maestro = FakeMaestro(
        [SimpleNamespace(state="RUNNING", finish_status="", finish_message="")]
    )
    clock = FakeClock()

    with pytest.raises(PredecessorTimeoutError, match="103"):
        wait_for_predecessor(
            maestro,
            "103",
            timeout_seconds=2,
            poll_interval_seconds=1,
            sleep_fn=clock.sleep,
            monotonic_fn=clock.monotonic,
        )


def test_extrai_id_do_predecessor_dos_parametros():
    assert predecessor_task_id_from_parameters({"predecessor_task_id": 104}) == "104"
    assert predecessor_task_id_from_parameters({}) is None
    assert predecessor_task_id_from_parameters(None) is None
