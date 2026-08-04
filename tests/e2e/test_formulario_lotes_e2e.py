def test_pagina_carrega_com_titulo(page, pagina_html):
    page.goto(pagina_html)

    assert "Cadastro de Lotes" in page.title()


def test_campo_lote_aceita_preenchimento(formulario_page):
    formulario_page.preencher_lote("LG-2026-99001")

    assert formulario_page.campo_lote.input_value() == "LG-2026-99001"


def test_select_produto_aceita_categoria(formulario_page):
    formulario_page.selecionar_produto("TV55-4K-B")

    assert formulario_page.campo_produto.input_value() == "TV"


def test_status_pendente_vem_selecionado_por_padrao(formulario_page):
    assert formulario_page.obter_status_selecionado() == "PENDENTE"


def test_formulario_completo_exibe_mensagem_de_sucesso(formulario_page):
    formulario_page.preencher_lote(
        {
            "lote_id": "LG-2026-99002",
            "produto": "MON27-QHD",
            "linha": "L2",
            "turno": "TARDE",
            "status": "APROVADO",
            "responsavel": "Usuario Teste",
            "data": "2026-07-14",
            "observacao": "",
        }
    )

    formulario_page.submeter()

    assert formulario_page.mensagem_sucesso_visivel()


def test_formulario_espelha_todas_as_colunas_da_planilha(formulario_page):
    formulario_page.preencher_lote(
        {
            "lote_id": "LG-2026-99008",
            "produto": "AC12-SPLIT",
            "linha": "L3",
            "turno": "NOITE",
            "status": "REPROVADO",
            "responsavel": "Maria Analista",
            "data": "2026-07-15",
            "observacao": "Avaria identificada na embalagem",
        }
    )

    assert formulario_page.campo_lote.input_value() == "LG-2026-99008"
    assert formulario_page.campo_codigo_produto.input_value() == "AC12-SPLIT"
    assert formulario_page.campo_produto.input_value() == "AC"
    assert formulario_page.campo_linha.input_value() == "L3"
    assert formulario_page.campo_turno.input_value() == "NOITE"
    assert formulario_page.campo_responsavel.input_value() == "Maria Analista"
    assert formulario_page.campo_data.input_value() == "2026-07-15"
    assert formulario_page.campo_observacao.input_value() == "Avaria identificada na embalagem"


def test_nao_submete_sem_produto(formulario_page):
    formulario_page.preencher_lote("LG-2026-99003")
    formulario_page.selecionar_status("APROVADO")

    formulario_page.submeter()

    assert not formulario_page.mensagem_sucesso_visivel()


def test_nao_submete_sem_lote(formulario_page):
    formulario_page.selecionar_produto("AC12-SPLIT")
    formulario_page.selecionar_status("REPROVADO")

    formulario_page.submeter()

    assert not formulario_page.mensagem_sucesso_visivel()


def test_captura_evidencia_visual(formulario_page, tmp_path):
    caminho_screenshot = tmp_path / "evidencia-formulario.png"
    formulario_page.preencher_lote(
        {
            "lote_id": "LG-2026-99004",
            "produto": "TV55-4K-B",
            "linha": "L1",
            "turno": "MANHA",
            "status": "APROVADO",
            "responsavel": "Usuario Teste",
            "data": "2026-07-14",
            "observacao": "",
        }
    )

    formulario_page.submeter()
    formulario_page.capturar_evidencia(caminho_screenshot)

    assert caminho_screenshot.exists()
    assert caminho_screenshot.stat().st_size > 0


def test_registra_analise_do_bot_na_tela(formulario_page):
    formulario_page.registrar_analises(
        [
            {
                "regra": "RN07",
                "problema": "Reprovacao sem Justificativa Obrigatoria",
                "acao": "Preencher a observacao com a justificativa da reprovacao",
                "categoria": "divergencia",
            }
        ],
        {"lote_id": "LG-2026-99005", "linha_planilha": 5},
    )

    corpo = formulario_page.page.get_by_test_id("analysis-body")
    assert "LG-2026-99005" in corpo.inner_text()
    assert "RN07" in corpo.inner_text()
    assert "Preencher a observacao" in corpo.inner_text()


def test_acumula_historico_de_divergencias(formulario_page):
    formulario_page.registrar_analises(
        [
            {
                "regra": "RN03",
                "problema": "lote_id nao existe na base de referencia",
                "acao": "Corrigir o lote_id ou cadastrar o lote",
                "categoria": "divergencia",
            }
        ],
        {"lote_id": "LG-2026-99006", "linha_planilha": 6},
    )
    formulario_page.registrar_analises(
        [
            {
                "regra": "RN07",
                "problema": "Reprovacao sem Justificativa Obrigatoria",
                "acao": "Preencher a observacao com a justificativa",
                "categoria": "divergencia",
            }
        ],
        {"lote_id": "LG-2026-99007", "linha_planilha": 7},
    )

    corpo = formulario_page.page.get_by_test_id("analysis-body")
    texto = corpo.inner_text()
    assert "LG-2026-99006" in texto
    assert "LG-2026-99007" in texto
    assert corpo.locator("tr").count() == 2
