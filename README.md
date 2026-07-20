# Auditor de Lotes

Bot corporativo para conferir lotes de qualidade, identificar divergencias na planilha de inspecao e preencher automaticamente as abas de evidencia da planilha final. O projeto pode ser executado localmente ou pelo BotCity Maestro, com DataPool, Credentials Vault, logs e evidencias da execucao.

Este repositorio adapta o exercicio integrado de BotCity para o cenario de sala "verificacao de lotes". Por isso, o fluxo usa `lote_id` e planilha `.xlsx` em vez de CPF e CSV.

## Funcionalidades

- valida a estrutura e os campos obrigatorios da planilha;
- confere os lotes usando a aba `Base_Referencia`;
- valida e normaliza os status de inspecao;
- verifica a observacao obrigatoria de lotes reprovados;
- preenche a aba `Formulario_Analise` em uma copia da planilha;
- cria/atualiza a aba `lotes_ambiguos` com os casos RN06;
- cria/atualiza a aba `Resumo_Diario` com indicadores consolidados;
- publica e consome itens pelo DataPool `FilaAuditoriaLotes`;
- recupera a credencial do ERP pelo Credentials Vault;
- registra logs locais com data, hora e severidade;
- publica o resumo JSON e a planilha analisada como artefatos no Maestro;
- isola erros por item para que os registros seguintes continuem sendo processados.

## Regras de negocio

| Regra | Validacao |
| --- | --- |
| RN01 | A planilha deve ter exatamente as colunas `lote_id`, `produto`, `linha`, `turno`, `status`, `responsavel`, `data` e `observacao` |
| RN02 | `lote_id`, `produto`, `linha`, `turno`, `status`, `responsavel` e `data` nao podem estar vazios |
| RN03 | O `lote_id` deve existir na aba `Base_Referencia` |
| RN04 | O status deve ser `APROVADO`, `REPROVADO` ou `PENDENTE` |
| RN05 | `OK` equivale a `APROVADO` e `NOK` equivale a `REPROVADO`; a normalizacao ocorre antes da validacao |
| RN06 | Status nao reconhecivel nem normalizavel e um caso ambiguo encaminhado para revisao humana |
| RN07 | Lote com status `REPROVADO` ou `NOK` deve ter a observacao preenchida |

## Estrutura do projeto

```text
.
|-- bot.py                   # regras aplicadas a cada item
|-- config.py                # ambiente, caminhos, DataPool e Vault
|-- dispatcher.py            # valida a planilha e alimenta a fila
|-- main.py                  # orquestracao e finalizacao no Maestro
|-- testar_local.py          # simulacao local do processamento por item
|-- vault_client.py          # leitura segura da credencial do ERP
|-- src/
|   |-- analise_formulario.py
|   |-- base_referencia.py
|   |-- config.py
|   |-- relatorio.py
|   `-- validacao.py
|-- tests/
|   |-- test_analise_formulario.py
|   `-- test_validacao.py
|-- dados_entrada/           # planilhas de entrada, nao versionadas
`-- logs/                    # logs e artefatos gerados
```

## Requisitos

- Python 3.10 ou superior;
- acesso a uma workspace do BotCity Maestro para a execucao corporativa;
- planilha de inspecao no formato esperado pelo projeto.

Instale as dependencias:

```powershell
python -m pip install -r requirements.txt
```

## Configuracao local

Crie um arquivo `.env` na raiz do projeto. Esse arquivo e ignorado pelo Git e nao deve ser enviado ao repositorio.

```dotenv
MAESTRO_ENABLED=false
VAULT_ENABLED=false

MAESTRO_SERVER=
MAESTRO_LOGIN=
MAESTRO_KEY=

DATAPOOL_LABEL=FilaAuditoriaLotes
CREDENCIAL_LABEL=credencial_erp
ARQUIVO_INSPECAO=dados_entrada/inspecao_lotes_dia.xlsx
```

Para usar os servicos do Maestro durante uma execucao local, informe as credenciais de acesso e altere `MAESTRO_ENABLED` para `true`. A senha do ERP nunca deve ser colocada no codigo nem no `.env`.

## Planilha de entrada

Antes de iniciar o bot, crie a pasta `dados_entrada` e coloque nela o arquivo:

```text
dados_entrada/inspecao_lotes_dia.xlsx
```

O caminho pode ser alterado pela variavel `ARQUIVO_INSPECAO`. A planilha deve possuir, no minimo, as abas:

- `Inspecao_14_06_2026`, com os registros de inspecao;
- `Base_Referencia`, com os lotes validos;
- `Formulario_Analise`, onde as divergencias serao registradas.

A planilha final gerada tambem tera:

- `lotes_ambiguos`, com registros de RN06 enviados para revisao humana;
- `Resumo_Diario`, com indicadores de registros, divergencias, normalizacoes e ambiguidades.

O bot aplica validacao *fail fast*: se a pasta ou o arquivo de entrada nao existir, a execucao termina imediatamente. Quando estiver rodando pelo Runner, a falha tambem e reportada ao Maestro.

## Configuracao no BotCity Maestro

### DataPool

Crie um DataPool com o nome:

```text
FilaAuditoriaLotes
```

O Dispatcher envia uma linha da planilha por item. O Performer marca cada item como concluido ou com erro e continua consumindo a fila mesmo quando um registro apresenta divergencia.

### Credentials Vault

Crie uma credencial com o label:

```text
credencial_erp
```

A credencial deve conter as chaves:

- `usuario`;
- `senha`.

Somente o usuario pode aparecer nos logs. A senha nunca e registrada.

## Fluxo de execucao

```text
Planilha -> Dispatcher -> DataPool -> Performer -> Relatorio e evidencias
```

Quando `main.py` esta conectado ao Maestro, ele executa o Dispatcher antes do Performer. Nao e necessario iniciar `dispatcher.py` separadamente nesse fluxo.

O Dispatcher tambem pode ser executado de forma independente para apenas alimentar a fila:

```powershell
python dispatcher.py
```

### Execucao local

Com `MAESTRO_ENABLED=false`, execute:

```powershell
python main.py
```

Nesse modo, o bot analisa diretamente a planilha, preenche o formulario e grava os resultados em `logs/`, sem consumir o DataPool.

Para simular localmente o processamento item a item:

```powershell
python testar_local.py
```

### Execucao pelo Runner

Cadastre e publique o pacote do bot no Maestro com `main.py` como ponto de entrada. O Runner fornece os argumentos de autenticacao e o identificador da tarefa automaticamente.

Durante a execucao, o bot:

1. registra o inicio da auditoria;
2. valida a pasta e a planilha de entrada;
3. recupera a credencial do Vault, quando habilitado;
4. executa o Dispatcher;
5. consome os itens do DataPool;
6. publica as evidencias;
7. finaliza a tarefa com sucesso ou falha.

## Saidas e evidencias

Os arquivos gerados ficam na pasta `logs/`:

| Arquivo | Conteudo |
| --- | --- |
| `execucao.log` | Eventos da execucao com timestamp e severidade |
| `resumo_execucao.json` | Totais, falhas e divergencias encontradas |
| `inspecao_lotes_dia_analisado.xlsx` | Copia da planilha com `Formulario_Analise`, `lotes_ambiguos` e `Resumo_Diario` preenchidos |

Quando a execucao ocorre pelo Runner, o JSON e a planilha analisada tambem sao publicados como artefatos da tarefa no Maestro.

## Testes

Execute a suite principal:

```powershell
python -m pytest -q
```

Alternativa com o `unittest`:

```powershell
python -m unittest discover -s tests -p "test*.py"
```

Resultado esperado no estado atual:

```text
36 passed
```

## Pacote para BotCity Maestro

O pacote de upload deve seguir o layout abaixo, igual ao zip usado em aula:

```text
main.py
bot.py
config.py
dispatcher.py
vault_client.py
requirements.txt
README.md
src/
dados_entrada/inspecao_lotes_dia.xlsx
```

O arquivo `.zip` e artefato de build e nao deve ser commitado. Quando necessario, gere o pacote localmente e suba o zip pelo painel do Maestro.

## Seguranca

- nao versione o arquivo `.env`;
- nao inclua planilhas reais ou dados pessoais nos commits;
- nao registre senhas, chaves ou tokens nos logs;
- mantenha a credencial do ERP exclusivamente no Credentials Vault;
- use valores ficticios em testes e demonstracoes.

## Tecnologias

- Python;
- BotCity Maestro SDK;
- BotCity DataPool;
- BotCity Credentials Vault;
- OpenPyXL;
- python-dotenv;
- pytest.
