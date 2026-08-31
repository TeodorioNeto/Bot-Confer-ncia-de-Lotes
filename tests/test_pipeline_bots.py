from types import SimpleNamespace

import openpyxl

import bot_conferencia_ml
import bot_relatorio_alertas
from src.alertas import ResultadoAlerta
from src.classificador_divergencia import ClassificadorDivergencia
from src.dead_letter import DeadLetterStore


def valid_values(**overrides):
    values = {
        "lote_id": "LG-2026-00101",
        "produto": "TV",
        "linha": "L1",
        "turno": "A",
        "status": "APROVADO",
        "responsavel": "Ana",
        "data": "14/06/2026",
        "observacao": "digitei errado o codigo",
    }
    values.update(overrides)
    return values


class FakeItem:
    def __init__(self, values):
        self.values = values
        self.report = None

    def get_value(self, key):
        return self.values.get(key)

    def report_done(self, finish_message=""):
        self.report = ("done", finish_message)

    def report_error(self, error_type=None, finish_message=""):
        self.report = ("error", finish_message)


class FakeDataPool:
    def __init__(self, items):
        self.items = list(items)

    def has_next(self):
        return bool(self.items)

    def next(self, task_id=None):
        return self.items.pop(0) if self.items else None


class FakeMaestroB:
    def __init__(self, items):
        self.task_id = "TASK-B"
        self.datapool = FakeDataPool(items)
        self.created = []
        self.finished = []
        self.task = SimpleNamespace(
            parameters={
                "pipeline_id": "PIPE-001",
                "predecessor_task_id": "TASK-A",
                "execution_chain": [],
                "base_reference_status": "disponivel",
            }
        )

    def get_task(self, task_id):
        return self.task

    def get_datapool(self, label):
        return self.datapool

    def create_task(self, **kwargs):
        self.created.append(kwargs)
        return SimpleNamespace(id="TASK-C")

    def finish_task(self, **kwargs):
        self.finished.append(kwargs)


class FakeAlertSystem:
    def __init__(self):
        self.calls = []

    def send(self, **kwargs):
        self.calls.append(kwargs)
        return ResultadoAlerta(
            severidade=kwargs["severity"],
            canais_enviados=("telegram",),
            canal_fallback=None,
            sucesso=True,
        )


class FakeMaestroC:
    def __init__(self, parameters):
        self.task_id = "TASK-C"
        self.task = SimpleNamespace(parameters=parameters)
        self.artifacts = []
        self.finished = []

    def get_task(self, task_id):
        return self.task

    def post_artifact(self, **kwargs):
        self.artifacts.append(kwargs)

    def finish_task(self, **kwargs):
        self.finished.append(kwargs)


def classifier(**overrides):
    config = {
        "enabled": True,
        "confidence_min": 0.85,
        "sleep_fn": lambda _: None,
    }
    config.update(overrides)
    return ClassificadorDivergencia(**config)


def test_ml_enriquece_divergencia_sem_alterar_status_de_negocio():
    item = FakeItem(valid_values(lote_id="LG-INVALIDO"))

    result = bot_conferencia_ml.processar_item_hibrido(
        item,
        base_reference={"LG-2026-00101"},
        base_available=True,
        classifier=classifier(),
        pipeline_id="PIPE-001",
    )

    assert result["status_decisao"] == "DIVERGENCIA"
    assert result["causa_provavel"] == "erro_digitacao"
    assert result["origem_decisao"] == "ml"


def test_base_indisponivel_gera_pendente_sem_chamar_ml():
    calls = []
    item = FakeItem(valid_values(lote_id="LG-INVALIDO"))

    result = bot_conferencia_ml.processar_item_hibrido(
        item,
        base_reference=set(),
        base_available=False,
        classifier=classifier(predictor=lambda text: calls.append(text)),
        pipeline_id="PIPE-001",
    )

    assert result["status_decisao"] == "PENDENTE_REVISAO"
    assert result["origem_decisao"] == "nao_aplicavel"
    assert calls == []


def test_nan_da_planilha_e_tratado_como_campo_vazio():
    item = FakeItem(valid_values(lote_id=float("nan"), observacao=float("nan")))

    result = bot_conferencia_ml.processar_item_hibrido(
        item,
        base_reference={"LG-2026-00101"},
        base_available=True,
        classifier=classifier(),
        pipeline_id="PIPE-001",
    )

    assert result["lote_id"] is None
    assert result["erro_dado"] is True
    assert result["status_decisao"] == "DIVERGENCIA"
    assert "RN02" in result["regras_violadas"][0]
    assert result["motivo_fallback"] == "observacao_vazia"


def test_bot_b_processa_lote_inteiro_e_cria_bot_c(tmp_path):
    valid_item = FakeItem(valid_values())
    divergence_item = FakeItem(valid_values(lote_id="LG-INVALIDO"))
    invalid_data_item = FakeItem(valid_values(lote_id=""))
    maestro = FakeMaestroB([valid_item, divergence_item, invalid_data_item])

    result = bot_conferencia_ml.executar_bot_b(
        maestro,
        classifier=classifier(),
        load_base=lambda _: {"LG-2026-00101"},
        wait_predecessor=lambda *args, **kwargs: None,
        dead_letter_store=DeadLetterStore(tmp_path / "dead_letter.jsonl"),
        sleep_fn=lambda _: None,
    )

    assert result["summary"]["total"] == 3
    assert result["summary"]["divergencias"] == 2
    assert result["summary"]["dead_letter"] == 1
    assert maestro.created[0]["activity_label"] == "teodorio-relatorio-alertas-v1"
    assert len(maestro.created[0]["parameters"]["pipeline_results"]) == 3
    assert valid_item.report[0] == "done"
    assert divergence_item.report[0] == "done"
    assert invalid_data_item.report[0] == "error"
    assert (tmp_path / "dead_letter.jsonl").exists()
    assert maestro.finished[0]["total_items"] == 3
    assert maestro.finished[0]["processed_items"] == 2
    assert maestro.finished[0]["failed_items"] == 1


def test_bot_c_gera_relatorio_e_alerta_pipeline_sem_ml():
    results = [
        {
            "pipeline_id": "PIPE-002",
            "lote_id": "LG-1",
            "status_decisao": "DIVERGENCIA",
            "regras_violadas": ["RN03"],
            "observacao": "texto desconhecido",
            "causa_provavel": "nao_classificado",
            "origem_decisao": "fallback",
            "confianca_ml": 0.4,
            "motivo_fallback": "baixa_confianca",
            "latencia_ml_ms": 1.0,
            "erro_dado": False,
        }
    ]
    parameters = {
        "pipeline_id": "PIPE-002",
        "predecessor_task_id": "TASK-B",
        "pipeline_results": results,
        "bot_b_summary": {
            "total": 1,
            "validos": 0,
            "divergencias": 1,
            "pendentes_revisao": 0,
            "fallback_ml": 1,
            "dead_letter": 0,
            "pipeline_sem_ml": True,
        },
        "execution_chain": [],
    }
    maestro = FakeMaestroC(parameters)
    alert_system = FakeAlertSystem()

    result = bot_relatorio_alertas.executar_bot_c(
        maestro,
        alert_system=alert_system,
        wait_predecessor=lambda *args, **kwargs: None,
    )

    assert alert_system.calls[0]["severity"] == "AVISO"
    assert alert_system.calls[0]["title"] == "Pipeline operando sem ML"
    assert len(maestro.artifacts) == 2
    assert maestro.finished
    assert maestro.finished[0]["total_items"] == 1
    assert maestro.finished[0]["processed_items"] == 1
    assert maestro.finished[0]["failed_items"] == 0

    workbook = openpyxl.load_workbook(result["report_path"], read_only=True)
    assert workbook["Resultados"]["G2"].value == "fallback"
    assert workbook["Resultados"]["H2"].value == 0.4
    workbook.close()
