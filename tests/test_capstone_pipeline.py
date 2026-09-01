from types import SimpleNamespace

import pytest

import bot_classificador_ml
import bot_coleta_desktop
import bot_coleta_web
import bot_consolidacao
import capstone_orchestrator
from capstone_pipeline import executar_pipeline_local
from src.capstone_collectors import (
    load_inventory_from_reference,
    load_orders_from_inspection,
)
from src.classificador_divergencia import ClassificadorDivergencia
from src.migration_control import DesktopSessionBusyError, MigrationController


class FakeMaestro:
    def __init__(self):
        self.task_id = "TASK-CAP-A"
        self.task = SimpleNamespace(parameters={"execution_chain": []})
        self.created = []
        self.finished = []

    def get_task(self, task_id):
        assert task_id == self.task_id
        return self.task

    def create_task(self, **kwargs):
        self.created.append(kwargs)
        return SimpleNamespace(id="TASK-DESKTOP")

    def finish_task(self, **kwargs):
        self.finished.append(kwargs)


class FakeStageMaestro:
    def __init__(self, task_id, parameters):
        self.task_id = task_id
        self.task = SimpleNamespace(parameters=parameters)
        self.created = []
        self.finished = []
        self.artifacts = []

    def get_task(self, task_id):
        assert task_id == self.task_id
        return self.task

    def create_task(self, **kwargs):
        self.created.append(kwargs)
        return SimpleNamespace(id=f"NEXT-{self.task_id}")

    def finish_task(self, **kwargs):
        self.finished.append(kwargs)

    def post_artifact(self, **kwargs):
        self.artifacts.append(kwargs)


class FakeCollector:
    def __init__(self, payload):
        self.payload = payload
        self.mode = "simulated"

    def collect(self, pipeline_id):
        return dict(self.payload)


def valid_order(**overrides):
    values = {
        "lote_id": "LG-2026-00101",
        "produto": "TV55-4K-B",
        "linha": "L1",
        "turno": "A",
        "status": "APROVADO",
        "responsavel": "Ana",
        "data": "14/06/2026",
        "observacao": "cadastro conferido",
        "quantidade_pedido": 1,
    }
    values.update(overrides)
    return values


def inventory():
    return {
        "LG-2026-00101": {
            "lote_id": "LG-2026-00101",
            "produto": "TV55-4K-B",
            "quantidade_estoque": 1,
        }
    }


def test_coletores_simulados_reaproveitam_as_duas_abas_da_planilha():
    inventory_records = load_inventory_from_reference()
    order_records = load_orders_from_inspection()

    assert len(inventory_records) == 23
    assert len(order_records) == 25
    assert inventory_records[0]["lote_id"] == "LG-2026-00101"
    assert order_records[0]["produto"] == "TV55-4K-B"


def test_consolidacao_decide_sem_ml_e_detecta_divergencia():
    result = bot_consolidacao.consolidar_item(
        valid_order(produto="PRODUTO-DIVERGENTE"),
        inventory_by_lot=inventory(),
        desktop_available=True,
        web_available=True,
        pipeline_id="PIPE-1",
    )

    assert result["status_decisao"] == "DIVERGENCIA"
    assert any("RN08" in rule for rule in result["regras_violadas"])
    assert result["origem_decisao"] == "nao_aplicavel"


def test_indisponibilidade_desktop_gera_pendente_revisao():
    result = bot_consolidacao.consolidar_item(
        valid_order(),
        inventory_by_lot={},
        desktop_available=False,
        web_available=True,
        pipeline_id="PIPE-2",
    )

    assert result["status_decisao"] == "PENDENTE_REVISAO"
    assert result["desktop_disponivel"] is False


def test_ml_enriquece_sem_alterar_decisao_deterministica():
    classifier = ClassificadorDivergencia(
        enabled=True,
        confidence_min=0.85,
        sleep_fn=lambda _: None,
    )
    original = bot_consolidacao.consolidar_item(
        valid_order(lote_id="LG-INEXISTENTE", observacao="codigo digitado errado"),
        inventory_by_lot=inventory(),
        desktop_available=True,
        web_available=True,
        pipeline_id="PIPE-3",
    )

    enriched = bot_classificador_ml.enriquecer_resultados([original], classifier)[0]

    assert enriched["status_decisao"] == "DIVERGENCIA"
    assert enriched["causa_provavel"] == "erro_digitacao"
    assert enriched["origem_decisao"] == "ml"


def test_migracao_shadow_nao_reserva_saida_oficial(tmp_path):
    controller = MigrationController(tmp_path, "shadow")

    first = controller.claim_execution("lotes:2026-09-01", "PIPE-A")
    second = controller.claim_execution("lotes:2026-09-01", "PIPE-B")

    assert first.allowed is True
    assert second.allowed is True
    assert first.official is False


def test_migracao_novo_impede_execucao_oficial_duplicada(tmp_path):
    controller = MigrationController(tmp_path, "novo")

    first = controller.claim_execution("lotes:2026-09-01", "PIPE-A")
    second = controller.claim_execution("lotes:2026-09-01", "PIPE-B")

    assert first.allowed is True
    assert first.official is True
    assert second.allowed is False
    assert second.reason == "execucao_oficial_duplicada"


def test_lock_impede_concorrencia_na_sessao_desktop(tmp_path):
    controller = MigrationController(tmp_path, "shadow")

    with controller.desktop_session("PIPE-A"):
        with pytest.raises(DesktopSessionBusyError):
            with controller.desktop_session("PIPE-B"):
                pass


def test_orquestrador_cria_primeiro_bot_com_prioridade_desktop(tmp_path):
    maestro = FakeMaestro()
    controller = MigrationController(tmp_path, "shadow")

    result = capstone_orchestrator.executar_capstone_orchestrador(
        maestro,
        migration_controller=controller,
        populate_queue=lambda _: {
            "enviados": 25,
            "ignorados": 0,
            "fila_ja_populada": False,
        },
        business_key="lotes:demo",
    )

    assert result["claim"]["allowed"] is True
    assert maestro.created[0]["activity_label"] == "teodorio-coleta-desktop-v1"
    assert maestro.created[0]["priority"] == 9
    assert maestro.finished[0]["processed_items"] == 25


def test_bots_capstone_criam_a_proxima_tarefa_no_maestro(tmp_path):
    initial = {
        "pipeline_id": "PIPE-CHAIN",
        "orchestrator_mode": "shadow",
        "execution_chain": [],
    }
    desktop_maestro = FakeStageMaestro("TASK-DESKTOP", initial)
    desktop = bot_coleta_desktop.executar_bot_coleta_desktop(
        desktop_maestro,
        collector=FakeCollector(
            {
                "status": "sucesso",
                "mode": "simulated",
                "records": list(inventory().values()),
                "screenshot": None,
            }
        ),
        migration_controller=MigrationController(tmp_path, "shadow"),
        wait_predecessor_fn=lambda *args, **kwargs: None,
        sleep_fn=lambda _: None,
    )
    assert desktop_maestro.created[0]["activity_label"] == "teodorio-coleta-web-v1"

    web_maestro = FakeStageMaestro("TASK-WEB", desktop["next_task_parameters"])
    web = bot_coleta_web.executar_bot_coleta_web(
        web_maestro,
        collector=FakeCollector(
            {
                "status": "sucesso",
                "mode": "simulated",
                "records": [valid_order()],
                "evidences": [],
            }
        ),
        wait_predecessor_fn=lambda *args, **kwargs: None,
        sleep_fn=lambda _: None,
    )
    assert web_maestro.created[0]["activity_label"] == "teodorio-consolidacao-v1"

    consolidation_maestro = FakeStageMaestro(
        "TASK-CONSOLIDACAO",
        web["next_task_parameters"],
    )
    consolidation = bot_consolidacao.executar_bot_consolidacao(
        consolidation_maestro,
        wait_predecessor_fn=lambda *args, **kwargs: None,
        dead_letter_store=SimpleNamespace(register=lambda **kwargs: kwargs),
    )
    assert consolidation_maestro.created[0]["activity_label"] == (
        "teodorio-classificador-ml-v1"
    )

    ml_maestro = FakeStageMaestro("TASK-ML", consolidation["next_task_parameters"])
    ml = bot_classificador_ml.executar_bot_classificador_ml(
        ml_maestro,
        classifier=ClassificadorDivergencia(
            enabled=True,
            confidence_min=0.85,
            sleep_fn=lambda _: None,
        ),
        wait_predecessor_fn=lambda *args, **kwargs: None,
    )
    assert ml_maestro.created[0]["activity_label"] == (
        "teodorio-relatorio-alertas-v1"
    )
    assert len(ml["next_task_parameters"]["execution_chain"]) == 4


def test_pipeline_local_executa_seis_papeis_em_shadow(tmp_path):
    result = executar_pipeline_local(
        business_key="lotes:teste-local",
        migration_controller=MigrationController(tmp_path, "shadow"),
    )

    assert result["status"] == "concluido"
    assert result["consolidation"]["summary"]["total"] == 25
    assert len(result["report"]["execution_chain"]) == 6
    assert result["report"]["alerts"][0]["canais_enviados"] == ["shadow_local"]
