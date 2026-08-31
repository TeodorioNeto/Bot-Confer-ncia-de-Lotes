from types import SimpleNamespace

from botcity.maestro import AutomationTaskFinishStatus

import orchestrator


class FakeMaestro:
    def __init__(self):
        self.task_id = "TASK-A-101"
        self.created_tasks = []
        self.finished_tasks = []
        self.current_task = SimpleNamespace(
            parameters={"solicitante": "teste", "execution_chain": []}
        )

    def get_task(self, task_id):
        assert task_id == self.task_id
        return self.current_task

    def create_task(self, **kwargs):
        self.created_tasks.append(kwargs)
        return SimpleNamespace(id="TASK-B-202")

    def finish_task(self, **kwargs):
        self.finished_tasks.append(kwargs)


def test_bot_a_cria_bot_b_com_rastreamento_completo():
    maestro = FakeMaestro()
    dispatch_result = {
        "enviados": 25,
        "ignorados": 1,
        "fila_ja_populada": False,
    }

    result = orchestrator.executar_orquestrador(
        maestro,
        load_base=lambda _: {"LG-001", "LG-002"},
        populate_queue=lambda _: dispatch_result,
        next_bot_label="teodorio-conferencia-ml-v1",
        priority=7,
        test_mode=True,
        sleep_fn=lambda _: None,
    )

    assert result["connected_maestro"] is True
    assert result["base_reference_status"] == "disponivel"
    assert result["base_reference_count"] == 2
    assert result["next_task_id"] == "TASK-B-202"

    created = maestro.created_tasks[0]
    assert created["activity_label"] == "teodorio-conferencia-ml-v1"
    assert created["priority"] == 7
    assert created["test"] is True

    parameters = created["parameters"]
    assert parameters["pipeline_id"] == parameters["correlation_id"]
    assert parameters["predecessor_task_id"] == "TASK-A-101"
    assert parameters["predecessor_result"] == "BASE_REFERENCIA_OK"
    assert parameters["base_reference_status"] == "disponivel"
    assert parameters["dispatcher_result"] == dispatch_result
    assert parameters["solicitante"] == "teste"
    assert parameters["execution_chain"][0]["task_id"] == "TASK-A-101"

    finished = maestro.finished_tasks[0]
    assert finished["status"] == AutomationTaskFinishStatus.SUCCESS
    assert finished["total_items"] == 26
    assert finished["processed_items"] == 25
    assert finished["failed_items"] == 1


def test_bot_a_segue_degradado_quando_base_esgota_retry():
    maestro = FakeMaestro()
    attempts = []

    def unavailable_base(_):
        attempts.append(1)
        raise FileNotFoundError("base fora do ar")

    result = orchestrator.executar_orquestrador(
        maestro,
        load_base=unavailable_base,
        populate_queue=lambda _: {
            "enviados": 25,
            "ignorados": 0,
            "fila_ja_populada": False,
        },
        retry_max_attempts=3,
        retry_delay_seconds=1,
        sleep_fn=lambda _: None,
    )

    assert len(attempts) == 3
    assert result["base_reference_status"] == "indisponivel"
    assert result["predecessor_result"] == "PENDENTE_REVISAO"
    assert maestro.created_tasks[0]["parameters"]["predecessor_result"] == (
        "PENDENTE_REVISAO"
    )
    assert maestro.finished_tasks[0]["status"] == (
        AutomationTaskFinishStatus.PARTIALLY_COMPLETED
    )
    assert maestro.finished_tasks[0]["total_items"] == 25
    assert maestro.finished_tasks[0]["processed_items"] == 25
    assert maestro.finished_tasks[0]["failed_items"] == 0


def test_prioridade_fora_do_intervalo_e_rejeitada():
    maestro = FakeMaestro()

    try:
        orchestrator.executar_orquestrador(maestro, priority=11)
    except ValueError as error:
        assert "entre 0 e 10" in str(error)
    else:
        raise AssertionError("Prioridade invalida deveria gerar ValueError")
