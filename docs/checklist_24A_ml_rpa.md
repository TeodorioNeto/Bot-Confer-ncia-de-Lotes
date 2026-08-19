# Checklist Final - Aula 24-A ML + RPA

## Modelo e dataset

- [X] Dataset fictício com 240 amostras gerado por script versionado.
- [X] Features `status_raw`, `turno` e `tem_obs`.
- [X] Classes `válido_automático`, `revisar` e `recusar_automático`.
- [X] Modelo serializado em `models/classificador_lotes.pkl`.

## API

- [X] `POST /predict` implementado com Pydantic.
- [X] Turno inválido retorna erro 422.
- [X] `GET /health` informa carregamento do modelo.
- [X] `api_ml/` possui Dockerfile e requirements.
- [X] `docker-compose.yml` inclui serviço `api-ml` com healthcheck.

## Integração e resiliência

- [X] `src/ml_client.py` nunca propaga exceção.
- [X] Timeout, erro HTTP e erro de rede retornam `None`.
- [X] Circuit breaker abre após 5 falhas consecutivas.
- [X] Fallback `REVISAO_ML_OFFLINE` implementado.

## Auditoria e relatório

- [X] Decisão ML registra lote, classe, probabilidade, confiança e latência.
- [X] Relatório Excel possui aba `Decisões de ML`.
- [X] README documenta dataset, modelo, API e fallback.

## Testes

- [X] Teste de API com payload válido.
- [X] Teste de API com turno inválido.
- [X] Teste de MLClient com sucesso.
- [X] Teste de MLClient com API fora do ar.
- [X] Teste de circuit breaker com 5 falhas.
