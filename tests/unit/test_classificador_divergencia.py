from src.classificador_divergencia import ClassificadorDivergencia


def build_classifier(**overrides):
    config = {
        "enabled": True,
        "confidence_min": 0.85,
        "sleep_fn": lambda _: None,
    }
    config.update(overrides)
    return ClassificadorDivergencia(**config)


def test_mock_classifica_causa_a_partir_da_observacao():
    result = build_classifier().classificar("digitei errado o codigo do lote")

    assert result.causa_provavel == "erro_digitacao"
    assert result.confianca_ml == 0.94
    assert result.origem_decisao == "ml"
    assert result.motivo_fallback is None


def test_feature_flag_desliga_classificador_sem_chamar_predictor():
    calls = []
    classifier = build_classifier(
        enabled=False,
        predictor=lambda text: calls.append(text),
    )

    result = classifier.classificar("lancamento duplicado")

    assert calls == []
    assert result.origem_decisao == "fallback"
    assert result.motivo_fallback == "ml_desabilitado"


def test_ml_lento_respeita_timeout():
    classifier = build_classifier(
        timeout_seconds=0.1,
        mock_delay_seconds=1,
    )

    result = classifier.classificar("faltou peca")

    assert result.origem_decisao == "fallback"
    assert result.motivo_fallback == "timeout"


def test_baixa_confianca_descarta_sugestao():
    classifier = build_classifier(force_confidence=0.50)

    result = classifier.classificar("lancamento duplicado")

    assert result.causa_provavel == "nao_classificado"
    assert result.confianca_ml == 0.50
    assert result.origem_decisao == "fallback"
    assert result.motivo_fallback == "baixa_confianca"


def test_servico_fora_do_ar_nunca_propaga_excecao():
    classifier = build_classifier(force_error=True)

    result = classifier.classificar("faltou peca na doca 3")

    assert result.origem_decisao == "fallback"
    assert result.motivo_fallback == "servico_indisponivel"
