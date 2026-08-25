# PDD — Pipeline Híbrido S10-B

## 6. Arquitetura do pipeline

O pipeline possui três responsabilidades independentes:

1. Bot A — `orchestrator.py`: preflight, Dispatcher, DataPool e criação da
   tarefa do Bot B.
2. Bot B — conferência e enriquecimento das divergências com ML.
3. Bot C — relatório consolidado e notificação multicanal.

Os três pontos de entrada estão implementados. Os labels dos bots são
configurados por ambiente e devem corresponder aos registros do BotCity
Maestro.

```text
Bot A -> create_task(Bot B) -> create_task(Bot C)
```

## 8. Integrações

O Bot A usa o SDK do Maestro para:

- consultar os dados da tarefa atual com `get_task()`;
- popular `FilaAuditoriaLotes` pelo Dispatcher;
- criar o Bot B com `create_task()`;
- finalizar sua tarefa com `finish_task()`.

Os parâmetros enviados ao Bot B preservam os parâmetros recebidos e
acrescentam `pipeline_id`, `correlation_id`, identificação da tarefa
predecessora, resultado, estado da base, resumo do Dispatcher e histórico da
cadeia.

O Bot B consome o DataPool, aplica RN01-RN03 e chama exclusivamente
`ClassificadorDivergencia` para enriquecer itens com status `DIVERGENCIA`.
O componente recebe `observacao` e devolve causa, confiança, origem e motivo
do fallback. O retorno do ML não participa do cálculo de `status_decisao`.

O Bot C recebe os resultados do Bot B, produz o relatório Excel e publica as
evidências no Maestro. O `SistemaAlertas` usa Telegram como canal principal,
Email como canal adicional/fallback e log local como último recurso.

A base de referência pode ser configurada separadamente por
`ARQUIVO_BASE_REFERENCIA`. Assim, uma falha da base não torna a planilha de
entrada do Dispatcher indisponível.

## 9. Segurança e configuração

Labels, prioridade, modo de teste, timeout e intervalos não são fixados em
código. Eles são lidos de variáveis de ambiente. Nenhuma credencial do Maestro
é registrada nos parâmetros ou nos logs da cadeia.

Tokens do Telegram e credenciais SMTP são lidos somente do `.env`/ambiente.
Nenhuma senha é incluída em relatório, parâmetros de tarefa ou mensagem de
log.

## 16. Tratamento de exceções e resiliência

A consulta à base de referência usa retry com backoff linear. Com a
configuração padrão, são feitas três tentativas, aguardando um segundo antes da
segunda e dois segundos antes da terceira.

Erros de infraestrutura derivados de `OSError` são repetidos. Erros de formato
ou de regra, como uma aba inválida, são propagados imediatamente porque uma
nova tentativa não corrigiria o dado.

Se as tentativas forem esgotadas, o pipeline segue degradado:

```text
base_reference_status = indisponivel
predecessor_result = PENDENTE_REVISAO
Bot A = PARTIALLY_COMPLETED
```

O Bot B ainda é criado, evitando a interrupção completa da cadeia.

O helper `wait_for_predecessor.py` aplica polling com timeout configurável e
aceita predecessores finalizados como `SUCCESS` ou `PARTIALLY_COMPLETED`.

O classificador diferencia os seguintes fallbacks:

- `ml_desabilitado`;
- `servico_indisponivel`;
- `timeout`;
- `baixa_confianca`;
- `resposta_invalida`;
- `observacao_vazia`.

Todos retornam `causa_provavel=nao_classificado` e
`origem_decisao=fallback`, sem lançar exceção ao Bot B. Erros permanentes de
dado são escritos em `logs/dead_letter_pipeline.jsonl`.

Se o Telegram falhar, o Email é tentado. Se os dois canais falharem, o evento
é registrado em log com o marcador `ALERTA_LOCAL`.

## 17. Observabilidade e rastreamento

Cada transição adiciona uma entrada em `execution_chain`, contendo:

- label da atividade;
- ID da tarefa;
- resultado;
- horário UTC de conclusão.

O mesmo `pipeline_id` e `correlation_id` acompanha todas as tarefas, permitindo
reconstruir quem disparou quem e em qual estado a infraestrutura se encontrava.

Os logs do Bot A registram o identificador do pipeline, a disponibilidade da
base, o ID da tarefa predecessora e o ID da tarefa criada.

O relatório final contém `causa_provavel`, `origem_decisao`,
`confianca_ml`, `motivo_fallback` e `latencia_ml_ms`. Quando todas as
divergências usam fallback, o Bot C emite o alerta obrigatório
`Pipeline operando sem ML`.
