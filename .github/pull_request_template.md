## Resumo

<!-- Explique em 1 ou 2 frases o objetivo deste PR. -->

## Issue relacionada

<!-- Troque pelo numero real da issue. Exemplo: Closes #4 -->
Closes #<NUMERO>

## O que foi feito

- <!-- Liste as principais mudancas feitas neste PR. -->

## Regras atendidas

<!-- Marque apenas as regras que se aplicam a este PR. -->

- [ ] RN01 - Validacao de estrutura da planilha
- [ ] RN02 - Validacao de campos obrigatorios
- [ ] RN03 - Verificacao do lote na base de referencia
- [ ] RN04/RN05 - Validacao e normalizacao de status
- [ ] RN06 - Tratamento de lotes ambiguos
- [ ] RN07 - Observacao obrigatoria para lote reprovado
- [ ] Relatorios/evidencias finais
- [ ] Documentacao/manutencao

## Fora do escopo

<!-- Informe o que este PR nao altera, quando isso ajudar na revisao. -->

- 

## Como testar

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
```

<!-- Se pytest nao estiver disponivel no ambiente, usar a alternativa abaixo. -->

```powershell
python -m unittest discover -s tests -p "test*.py"
```

## Checklist do PR

- [ ] A branch foi criada a partir da `main` atualizada
- [ ] O nome da branch segue o padrao combinado (`feature/`, `fix/`, `docs/`, etc.)
- [ ] A alteracao resolve a issue descrita
- [ ] O PR usa `Closes #<NUMERO>` quando houver issue relacionada
- [ ] O codigo foi testado manualmente ou por testes automatizados
- [ ] O README foi atualizado, se necessario
- [ ] Nao ha arquivos desnecessarios no commit (`__pycache__`, `.pytest_cache`, `.DS_Store`, etc.)
- [ ] Nenhum dado privado de planilhas foi incluido no commit
- [ ] O commit segue Conventional Commits
- [ ] A branch esta atualizada com a `main`
- [ ] O PR tem titulo e descricao claros
- [ ] O codigo sera revisado por pelo menos um colega

## Observacoes

<!-- Informe riscos, limitacoes, decisoes de escopo ou evidencias importantes. -->

