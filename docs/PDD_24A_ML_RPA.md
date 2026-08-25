# PDD - Adendo Aula 24-A: ML + RPA

## Objetivo

Adicionar uma camada de Machine Learning para apoiar a decisão sobre lotes ambíguos, mantendo as regras RN01-RN12 como fonte determinística do processo.

## Escopo

- Gerar dataset histórico fictício com no mínimo 200 amostras.
- Treinar `RandomForestClassifier` com `status_raw`, `turno` e `tem_obs`.
- Servir o modelo por FastAPI em `api_ml/`.
- Consumir a API por `src/ml_client.py` com timeout e circuit breaker.
- Aplicar fallback `REVISAO_ML_OFFLINE` quando a API estiver fora do ar.
- Registrar decisões em log estruturado.
- Adicionar a aba `Decisões de ML` ao relatório Excel.

## Fora de Escopo

- Substituir as regras RN01-RN12.
- Usar dados reais de produção.
- Parar o bot quando a API ML falhar.

## Critérios de Aceite

- `/predict` aceita payload válido e rejeita turno inválido.
- `/health` informa o estado de carregamento do modelo.
- `MLClient` nunca lança exceção para o bot.
- Circuit breaker abre após 5 falhas consecutivas.
- Bot continua processando com `REVISAO_ML_OFFLINE`.
- Relatório contém a aba `Decisões de ML`.
- Testes automatizados da nova camada passam.
