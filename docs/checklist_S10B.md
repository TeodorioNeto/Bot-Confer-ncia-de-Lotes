# Checklist S10-B — Pipeline híbrido

## Código

- [x] Bot A cria o Bot B com `create_task()`.
- [x] Bot B cria o Bot C com `create_task()`.
- [x] Cadeia rastreada por `pipeline_id`, predecessora e `execution_chain`.
- [x] Decisão de status depende somente de RN01-RN03.
- [x] ML controlado por `ML_ENABLED`.
- [x] Limiar configurável em `ML_CONFIANCA_MINIMA`.
- [x] Timeout, indisponibilidade e baixa confiança têm fallbacks distintos.
- [x] Nenhuma exceção do classificador chega ao loop principal.
- [x] Retry com backoff linear para a base de referência.
- [x] Dead letter local para erros permanentes de dado.
- [x] Relatório contém `origem_decisao` e `confianca_ml`.
- [x] Telegram é o canal principal.
- [x] Email é canal adicional e fallback.
- [x] Log local é o último fallback de notificação.
- [x] Alerta de pipeline operando sem ML implementado.

## Configuração externa

- [ ] Registrar os três bots no Maestro com os labels configurados.
- [ ] Configurar token e chat do Telegram no ambiente de homologação.
- [ ] Configurar SMTP e destinatário de homologação.
- [ ] Confirmar que instrutor e mentor acessam o repositório privado.

## Evidências da apresentação

- [ ] Capturar execução com base de referência indisponível.
- [ ] Capturar execução com serviço de ML fora do ar.
- [ ] Capturar execução com ML acima do timeout.
- [ ] Capturar execução com confiança abaixo do limiar.
- [ ] Capturar execução com Telegram inválido e Email funcionando.
