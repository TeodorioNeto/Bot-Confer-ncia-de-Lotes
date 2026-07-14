# Bot de Conferencia de Lotes

Automacao didatica para validar planilhas `.xlsx` de inspecao de lotes conforme o PDD v0.2.

## Regras implementadas nesta branch

- RN01: valida se a planilha possui exatamente as 8 colunas do layout: `lote_id`, `produto`, `linha`, `turno`, `status`, `responsavel`, `data`, `observacao`.
- RN02: valida campos obrigatorios em cada registro: `lote_id`, `produto`, `linha`, `turno`, `status`, `responsavel`, `data`.

## Instalacao

```powershell
python -m pip install -r requirements.txt
```

## Execucao

```powershell
python bot.py "caminho\para\planilha.xlsx"
```

O arquivo de entrada deve estar no formato `.xlsx`. Planilhas reais ou privadas nao devem ser versionadas no Git; use arquivos locais ou dados ficticios/sanitizados para testes e demonstracoes.

## Testes

```powershell
python -m pytest -q
```

Alternativa com a biblioteca padrao do Python:

```powershell
python -m unittest discover -s tests -p "test*.py"
```
