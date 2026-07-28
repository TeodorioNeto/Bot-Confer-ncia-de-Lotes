# Auditor de Lotes

Bot corporativo para conferir lotes de qualidade, identificar divergencias na planilha de inspecao e preencher automaticamente as abas de evidencia da planilha final. O projeto pode ser executado localmente ou pelo BotCity Maestro, com DataPool, Credentials Vault, logs e evidencias da execucao.

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
- gera screenshot por item processado pela automacao web;
- replica no simulador web as linhas que feriram regras, como na aba `Formulario_Analise`;
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
|-- simulador_inspecao_lotes.html # tela web simulada para Playwright/Selenium
|-- testar_local.py          # simulacao local do processamento por item
|-- vault_client.py          # leitura segura da credencial do ERP
|-- src/
|   |-- analise_formulario.py
|   |-- base_referencia.py
|   |-- config.py
|   |-- logging_config.py
|   |-- relatorio.py
|   |-- validacao.py
|   |-- web_automation.py
|   |-- web_automation_playwright.py
|   `-- web_automation_selenium.py
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

Para executar a versao Playwright pela primeira vez, instale tambem o navegador usado pela biblioteca:

```powershell
python -m playwright install chromium
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

WEB_AUTOMATION_ENABLED=false
WEB_AUTOMATION_DRIVER=playwright
WEB_AUTOMATION_URL=
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

O Dispatcher envia uma linha da planilha por item e inclui o campo `screenshot` para registrar a evidencia visual. O Performer marca cada item como concluido ou com erro e continua consumindo a fila mesmo quando um registro apresenta divergencia.

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

### Automacao web de lotes

O projeto mantem duas versoes da automacao web para registrar lotes e divergencias em uma tela web simulada:

- `src/web_automation_playwright.py`, usando Playwright;
- `src/web_automation_selenium.py`, usando Selenium WebDriver.

Os dados preenchidos pela automacao web saem da mesma origem usada pelo BotCity: a planilha `dados_entrada/inspecao_lotes_dia.xlsx`. No fluxo corporativo, o Dispatcher le essa planilha, envia os itens para o DataPool e o Performer aciona a automacao web para registrar a evidencia do item.

O arquivo `src/web_automation.py` funciona como ponto de entrada comum. Por padrao, ele executa a versao Playwright:

```powershell
python -m src.web_automation
```

Quando executado isoladamente, `python -m src.web_automation` carrega o primeiro lote com ocorrencia da planilha configurada em `ARQUIVO_INSPECAO`. Se nao houver ocorrencia, usa o primeiro lote valido. Se a planilha nao existir, usa apenas um registro demonstrativo para permitir teste local da tela.

A URL da tela e configurada por `WEB_AUTOMATION_URL`. Se essa variavel ficar vazia, o projeto usa `simulador_inspecao_lotes.html` como tela local simulada. Em homologacao, basta apontar para a URL do sistema de inspecao de lotes:

```dotenv
WEB_AUTOMATION_URL=https://ambiente-homologacao/sistema-lotes
```

No fluxo com BotCity/DataPool, a automacao web so roda quando `WEB_AUTOMATION_ENABLED=true`. Ela e acionada pelo Performer para cada lote processado. Quando o item possui divergencias, o simulador insere as linhas na tabela `Formulario_Analise` com linha da planilha, `lote_id`, problema, regra violada, acao recomendada e status de revisao.

Cada item processado pela automacao web gera um screenshot em:

```text
logs/screenshots/
```

O caminho do screenshot e registrado no resultado do item, no `resumo_execucao.json` e, quando a execucao ocorre pelo Runner, a imagem tambem e publicada como artefato no Maestro. A pasta de screenshots fica fora do Git pelo `.gitignore`.

Para executar a versao Selenium:

```powershell
$env:WEB_AUTOMATION_DRIVER='selenium'
$env:SELENIUM_HEADLESS='true'
python -m src.web_automation
```

Tambem e possivel executar cada versao diretamente:

```powershell
python -m src.web_automation_playwright
python -m src.web_automation_selenium
```

Comparacao pratica:

| Criterio | Playwright | Selenium |
| --- | --- | --- |
| Padrao do projeto | Sim | Alternativa de laboratorio |
| Inicializacao | Mais direta, com navegador gerenciado pelo Playwright | Depende do ChromeDriver via `webdriver-manager` |
| Esperas | `wait_for` e auto-wait dos locators | `WebDriverWait` com condicoes esperadas |
| Velocidade percebida | Geralmente mais rapido no setup apos instalacao | Pode ser mais lento na primeira execucao por causa do driver |
| Uso recomendado | Fluxo principal da automacao web local | Comparacao, compatibilidade WebDriver e estudo da Aula 18 |

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
## Execucao com Docker

Construa a imagem:

```powershell
docker compose build
```

Execute o bot:

```powershell
docker compose run --rm auditor-lotes
```

A pasta `dados_entrada/` e montada no container em modo somente leitura.
Os logs e relatorios gerados em `/app/logs` sao persistidos na pasta
`logs/` da maquina host.

As variaveis `EXECUTION_ID` e `BOT_ID` identificam cada execucao nos
logs estruturados em JSON.

## Saidas e evidencias

Os arquivos gerados ficam na pasta `logs/`:

| Arquivo | Conteudo |
| --- | --- |
| `execucao.log` | Eventos da execucao com timestamp e severidade |
| `resumo_execucao.json` | Totais, falhas e divergencias encontradas |
| `screenshots/*.png` | Evidencias visuais geradas por item na automacao web |
| `inspecao_lotes_dia_analisado.xlsx` | Copia da planilha com `Formulario_Analise`, `lotes_ambiguos` e `Resumo_Diario` preenchidos |

Quando a execucao ocorre pelo Runner, o JSON, a planilha analisada e os screenshots gerados tambem sao publicados como artefatos da tarefa no Maestro.

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
44 passed
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
simulador_inspecao_lotes.html
src/
dados_entrada/inspecao_lotes_dia.xlsx
```

O arquivo `.zip` e artefato de build e nao deve ser commitado. Quando necessario, gere o pacote localmente e suba o zip pelo painel do Maestro.
