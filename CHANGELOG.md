# Changelog

## 0.5.0 - Aula 24-A ML + RPA

- Adicionada API FastAPI em `api_ml/` com endpoints `/predict` e `/health`.
- Adicionado treinamento de `RandomForestClassifier` em `train_model.py`.
- Adicionado modelo serializado em `models/classificador_lotes.pkl`.
- Criado `src/ml_client.py` com timeout, fallback seguro e circuit breaker.
- Integrada classificacao ML para casos RN06 sem interromper o bot.
- Adicionada aba `Decisões de ML` ao relatorio executivo.
- Adicionados testes para API, MLClient, API offline e circuit breaker.

## 0.4.0 - Aula 24 Indicadores Operacionais

- Adicionada camada `operational_indicators.py` como fonte unica dos indicadores executivos.
- Expandido o relatorio Excel para incluir `Ranking de Regras` e `Dicionário`.
- Redesenhada a aba `Resumo` com os 10 indicadores operacionais da Aula 24.
- Adicionada geracao de `resumo_executivo.md` com os mesmos numeros do Excel.
- Criados testes unitarios e de integracao para indicadores, Excel consolidado e resumo executivo.
- Atualizada documentacao com premissas, comandos e checklist final da automacao.
