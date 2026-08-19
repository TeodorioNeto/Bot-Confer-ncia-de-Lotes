# PDD - Adendo Aula 24: Indicadores Operacionais

## Processo

Inspecao de lotes de produtos.

## Contexto

A automacao ja valida os registros de lotes, separa divergencias, ambiguidades e erros de entrada, e gera evidencias tecnicas. A Aula 24 adiciona uma camada executiva para transformar os registros validados em indicadores de negocio, dashboard em Excel e resumo em linguagem gerencial.

## Escopo Adicionado

- Criar `operational_indicators.py` como camada dedicada de calculo.
- Consolidar os 10 indicadores operacionais da Aula 24.
- Expandir o Excel executivo com as abas `Ranking de Regras` e `Dicionário`.
- Gerar `resumo_executivo.md` a partir do mesmo objeto de indicadores usado pelo Excel.
- Adicionar testes unitarios e de integracao para a nova camada.

## Fora de Escopo

- Alterar a logica das regras RN01-RN12.
- Corrigir automaticamente dados de origem.
- Versionar planilhas reais, logs, screenshots ou credenciais.
- Tratar o ganho estimado de tempo como medicao real de producao.

## Saidas Atualizadas

| Saida | Finalidade |
| --- | --- |
| `relatorio_conferencia_lotes.xlsx` | Relatorio executivo com 9 abas apos a camada ML 24-A |
| `resumo_executivo.md` | Resumo em linguagem de negocio para diretoria |
| `Ranking de Regras` | Contagem das regras mais acionadas |
| `Dicionário` | Glossario de termos e indicadores |

## Indicadores

1. Total de registros.
2. Registros validos.
3. Divergencias.
4. Ambiguos.
5. Erros de entrada.
6. Regra mais acionada.
7. Taxa de qualidade da entrada.
8. Taxa de revisao humana.
9. Taxa de retrabalho.
10. Ganho estimado de tempo.

## Premissas

O ganho estimado usa 5 minutos por registro em conferencia manual e 1 minuto por registro no fluxo automatizado. A metrica e didatica; para virar metrica produtiva, precisa ser medida em ambiente real com amostra e historico controlados.

## Criterios de Aceite

- O Excel possui as 9 abas finais, incluindo `Decisões de ML`.
- A aba `Resumo` apresenta os 10 indicadores.
- `Ranking de Regras` usa a mesma contagem usada pelo indicador de regra mais acionada.
- `resumo_executivo.md` apresenta os mesmos numeros do Excel.
- Testes novos passam com markers `unit` e `integration`.
- Cobertura permanece acima de 80%.
