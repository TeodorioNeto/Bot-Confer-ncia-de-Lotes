"""
gerar_relatorio.py

Escopo deste script: Etapas 5.1 e 5.2 do exercício "Geração de Dashboard com
Excel e Criação de Relatórios" (Aula 22).

5.1 - Consolidar e validar
    - Lê as 10 abas diárias (Insp_DD_MM_2026) e a aba Base_Referencia de
      inspecao_lotes_10dias.xlsx.
    - Deduplica por Counter, por dia, ANTES de validar (RN11 é por
      execução/dia — um lote repetido em dois dias diferentes não conta
      como duplicado).
    - Chama validar_registro() em cada linha (RN01-RN12) e monta uma lista
      de objetos RegistroValidado, já com a data de referência do dia.
    - Usa RegistroValidado.to_dict() para montar os DataFrames do relatório.

5.2 - Gerar o relatório em Excel (6 abas)
    - Resumo, Todos, Válidos, Divergências, Ambíguos, Erros de Entrada.
    - Cada aba mostra só os registros da sua categoria (nenhuma mistura).
    - A aba "Resumo" aqui contém apenas os indicadores numéricos (total,
      contagem e % por classificação). O dashboard visual (gráfico de
      rosca + gráfico de evolução por dia, com openpyxl.chart) é a Etapa
      5.3 do enunciado e NÃO faz parte deste script, por escopo.

Fora do escopo deste script: 5.3 (gráficos nativos) e 5.4 (log de execução
em arquivo/aba separada).
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import openpyxl
import pandas as pd
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

ARQUIVO_ENTRADA = "inspecao_lotes_10dias.xlsx"
ARQUIVO_SAIDA = "relatorio_conferencia_lotes.xlsx"

COLUNAS_ENTRADA = [
    "lote_id", "produto", "linha", "turno",
    "status", "responsavel", "data", "observacao",
]

STATUS_PADRAO = {"APROVADO", "REPROVADO", "PENDENTE"}
SINONIMOS_STATUS = {"OK": "APROVADO", "NOK": "REPROVADO"}
STATUS_REPROVADO_ORIGINAL = {"REPROVADO", "NOK"}

# RN12: data no formato DD/MM/AAAA
DATA_REGEX = re.compile(r"^\d{2}/\d{2}/\d{4}$")


# ---------------------------------------------------------------------------
# RegistroValidado
# ---------------------------------------------------------------------------

@dataclass
class RegistroValidado:
    aba_origem: str
    linha_planilha: int
    data_referencia: str            # data do dia da coleta (nome da aba), AAAA-MM-DD
    lote_id: Optional[str]
    produto: Optional[str]
    linha: Optional[str]
    turno: Optional[str]
    status_original: Optional[str]
    status_normalizado: Optional[str]
    responsavel: Optional[str]
    data_inspecao: Optional[str]    # valor originalmente digitado na coluna "data"
    observacao: Optional[str]
    classificacao: str              # Válido | Divergência | Ambíguo | Erro de Entrada
    regra_violada: str              # ex.: "RN05", "RN01-RN04", "-"
    motivo: str

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Regras de negócio RN01-RN12
# ---------------------------------------------------------------------------

def vazio(valor) -> bool:
    return valor is None or str(valor).strip() == ""


def normalizar_status(status) -> Optional[str]:
    """RN06-RN07: 'OK' -> APROVADO, 'NOK' -> REPROVADO. Demais valores, upper/strip."""
    if vazio(status):
        return None
    s = str(status).strip().upper()
    return SINONIMOS_STATUS.get(s, s)


def data_valida(data_texto) -> bool:
    """RN12: data ausente ou fora do formato DD/MM/AAAA é inválida.

    Além do padrão dd/mm/aaaa (dois dígitos / dois dígitos / quatro dígitos),
    valida se dia e mês existem de fato (ex.: '06/23/2026' bate no padrão
    posicional mas não é uma data válida em DD/MM/AAAA, pois não existe o
    mês 23 — deve cair em RN12).
    """
    if vazio(data_texto):
        return False
    texto = str(data_texto).strip()
    if not DATA_REGEX.match(texto):
        return False
    try:
        datetime.strptime(texto, "%d/%m/%Y")
        return True
    except ValueError:
        return False


def validar_registro(registro: dict, ocorrencia_no_dia: int, base_referencia: set) -> RegistroValidado:
    """
    Aplica as regras RN01-RN12 a uma linha de inspeção e retorna o
    RegistroValidado já classificado.

    Ordem de avaliação (a primeira regra violada define a classificação):
      1) RN01-RN04 - campos obrigatórios vazios         -> Erro de Entrada
      2) RN12      - data ausente/fora do formato        -> Erro de Entrada
      3) RN11      - duplicidade no mesmo dia (2ª+ vez)  -> Divergência
      4) RN09      - status não normalizável              -> Ambíguo
      5) RN05      - lote_id fora da Base_Referencia      -> Divergência
      6) RN10      - REPROVADO/NOK sem observação         -> Divergência
      7) RN08      - status padronizado, sem violações    -> Válido

    Args:
        registro: dict com aba_origem, linha_planilha, data_referencia e as
                  colunas lote_id/produto/linha/turno/status/responsavel/
                  data/observacao.
        ocorrencia_no_dia: nº da ocorrência do lote_id dentro do mesmo dia
                            (1 = primeira vez, 2+ = duplicado).
        base_referencia: set de lote_id cadastrados na aba Base_Referencia.
    """
    produto = registro.get("produto")
    linha = registro.get("linha")
    status_original = registro.get("status")
    data_inspecao = registro.get("data")
    observacao = registro.get("observacao")

    status_normalizado = normalizar_status(status_original)

    # RN01-RN04
    campos_vazios = [
        nome for nome, valor in [
            ("lote_id", registro.get("lote_id")), ("produto", produto),
            ("linha", linha), ("status", status_original),
        ] if vazio(valor)
    ]
    if campos_vazios:
        return _montar_registro(
            registro, status_original, status_normalizado,
            classificacao="Erro de Entrada",
            regra_violada="RN01-RN04",
            motivo=f"Campo(s) obrigatório(s) vazio(s): {', '.join(campos_vazios)}",
        )

    # RN12
    if not data_valida(data_inspecao):
        return _montar_registro(
            registro, status_original, status_normalizado,
            classificacao="Erro de Entrada",
            regra_violada="RN12",
            motivo=f"Data de inspeção ausente ou fora do formato DD/MM/AAAA: '{data_inspecao}'",
        )

    # RN11
    if ocorrencia_no_dia >= 2:
        return _montar_registro(
            registro, status_original, status_normalizado,
            classificacao="Divergência",
            regra_violada="RN11",
            motivo=f"Lote duplicado no mesmo dia (ocorrência nº {ocorrencia_no_dia})",
        )

    # RN09
    if status_normalizado not in STATUS_PADRAO:
        return _montar_registro(
            registro, status_original, status_normalizado,
            classificacao="Ambíguo",
            regra_violada="RN09",
            motivo=f"Status '{status_original}' não reconhecido — necessita revisão humana",
        )

    # RN05
    lote_id_str = str(registro.get("lote_id")).strip()
    if lote_id_str not in base_referencia:
        return _montar_registro(
            registro, status_original, status_normalizado,
            classificacao="Divergência",
            regra_violada="RN05",
            motivo=f"Lote '{lote_id_str}' não encontrado na Base_Referencia",
        )

    # RN10
    if str(status_original).strip().upper() in STATUS_REPROVADO_ORIGINAL and vazio(observacao):
        return _montar_registro(
            registro, status_original, status_normalizado,
            classificacao="Divergência",
            regra_violada="RN10",
            motivo="Lote reprovado sem observação preenchida",
        )

    # RN08
    return _montar_registro(
        registro, status_original, status_normalizado,
        classificacao="Válido",
        regra_violada="-",
        motivo="Registro consistente com todas as regras RN01-RN12",
    )


def _montar_registro(registro, status_original, status_normalizado, classificacao, regra_violada, motivo) -> RegistroValidado:
    lote_id = registro.get("lote_id")
    return RegistroValidado(
        aba_origem=registro["aba_origem"],
        linha_planilha=registro["linha_planilha"],
        data_referencia=registro["data_referencia"],
        lote_id=None if vazio(lote_id) else str(lote_id).strip(),
        produto=registro.get("produto"),
        linha=registro.get("linha"),
        turno=registro.get("turno"),
        status_original=status_original,
        status_normalizado=status_normalizado,
        responsavel=registro.get("responsavel"),
        data_inspecao=registro.get("data"),
        observacao=registro.get("observacao"),
        classificacao=classificacao,
        regra_violada=regra_violada,
        motivo=motivo,
    )


# ---------------------------------------------------------------------------
# Etapa 5.1 - Leitura, deduplicação e consolidação
# ---------------------------------------------------------------------------

def carregar_base_referencia(caminho) -> set:
    """Lê a aba Base_Referencia e retorna o set de lote_id cadastrados (RN05)."""
    wb = openpyxl.load_workbook(caminho, data_only=True)
    ws = wb["Base_Referencia"]
    base = set()
    for linha in ws.iter_rows(min_row=3, values_only=True):  # pula título e cabeçalho
        lote_id = linha[0] if linha else None
        if lote_id and str(lote_id).strip().startswith("LG-"):
            base.add(str(lote_id).strip())
    wb.close()
    return base


def nome_aba_para_data(nome_aba: str) -> str:
    """'Insp_15_06_2026' -> '2026-06-15' (data de referência do dia, para o dashboard)."""
    dia, mes, ano = nome_aba.replace("Insp_", "").split("_")
    return f"{ano}-{mes}-{dia}"


def ler_aba_diaria(ws, nome_aba: str) -> list[dict]:
    """Lê os registros de uma aba diária (cabeçalho na linha 3, dados a partir da linha 4)."""
    data_referencia = nome_aba_para_data(nome_aba)
    registros = []
    for linha_excel, linha in enumerate(ws.iter_rows(min_row=4, values_only=True), start=4):
        valores = dict(zip(COLUNAS_ENTRADA, (linha or ())[: len(COLUNAS_ENTRADA)]))
        if all(vazio(v) for v in valores.values()):
            continue  # linha em branco
        lote_id_bruto = valores.get("lote_id")
        if not vazio(lote_id_bruto) and str(lote_id_bruto).strip().lower().startswith("total"):
            continue  # linha de rodapé ("Total de registros: 25")
        valores["aba_origem"] = nome_aba
        valores["linha_planilha"] = linha_excel
        valores["data_referencia"] = data_referencia
        registros.append(valores)
    return registros


def consolidar_e_validar(caminho_entrada) -> list[RegistroValidado]:
    """
    Etapa 5.1: lê as 10 abas diárias, deduplica por Counter (por dia) e
    valida cada linha com validar_registro() (RN01-RN12).
    """
    wb = openpyxl.load_workbook(caminho_entrada, data_only=True)
    base_referencia = carregar_base_referencia(caminho_entrada)
    abas_diarias = [nome for nome in wb.sheetnames if nome != "Base_Referencia"]

    todos_validados: list[RegistroValidado] = []
    for nome_aba in abas_diarias:
        registros_do_dia = ler_aba_diaria(wb[nome_aba], nome_aba)

        # RN11: Counter reiniciado a cada dia (deduplicação é por execução/dia)
        contador = Counter()
        for registro in registros_do_dia:
            lote_id = registro.get("lote_id")
            if vazio(lote_id):
                ocorrencia = 1  # RN01 já classifica como Erro de Entrada
            else:
                chave = str(lote_id).strip()
                contador[chave] += 1
                ocorrencia = contador[chave]

            todos_validados.append(validar_registro(registro, ocorrencia, base_referencia))

    wb.close()
    return todos_validados


# ---------------------------------------------------------------------------
# Etapa 5.2 - Geração do relatório em Excel (6 abas)
# ---------------------------------------------------------------------------

RENOMEAR_COLUNAS = {
    "data_referencia": "Data",
    "lote_id": "Lote",
    "produto": "Produto",
    "linha": "Linha de Produção",
    "turno": "Turno",
    "status_normalizado": "Status",
    "responsavel": "Responsável",
    "observacao": "Observação",
    "classificacao": "Classificação",
    "regra_violada": "Regra",
    "motivo": "Motivo",
    "aba_origem": "Aba de Origem",
    "status_original": "Status Informado",
    "data_inspecao": "Data Informada",
    "linha_planilha": "Linha na Planilha",
}

COLUNAS_RELATORIO = [
    "data_referencia", "lote_id", "produto", "linha", "turno",
    "status_normalizado", "status_original", "responsavel",
    "observacao", "classificacao", "regra_violada", "motivo",
    "aba_origem", "linha_planilha",
]


def montar_dataframe(registros: list[RegistroValidado]) -> pd.DataFrame:
    df = pd.DataFrame([r.to_dict() for r in registros])
    df = df[COLUNAS_RELATORIO].rename(columns=RENOMEAR_COLUNAS)
    df = df.sort_values(["Data", "Lote"], na_position="last").reset_index(drop=True)
    return df


def montar_resumo(df_todos: pd.DataFrame) -> pd.DataFrame:
    total = len(df_todos)
    contagem = df_todos["Classificação"].value_counts()

    ordem = ["Válido", "Divergência", "Ambíguo", "Erro de Entrada"]
    linhas = [{"Indicador": "Total de registros processados", "Quantidade": total, "% do total": "100,0%"}]
    for categoria in ordem:
        qtd = int(contagem.get(categoria, 0))
        pct = (qtd / total * 100) if total else 0
        linhas.append({
            "Indicador": categoria + ("s" if categoria in ("Válido",) else ""),
            "Quantidade": qtd,
            "% do total": f"{pct:.1f}%".replace(".", ","),
        })
    return pd.DataFrame(linhas)


def formatar_aba(ws, cor_cabecalho="1F4E78"):
    """Formatação simples: cabeçalho em negrito, largura de coluna e congelamento da 1ª linha."""
    for celula in ws[1]:
        celula.font = Font(bold=True, color="FFFFFF")
        celula.fill = PatternFill(start_color=cor_cabecalho, end_color=cor_cabecalho, fill_type="solid")
    ws.freeze_panes = "A2"
    if ws.max_row > 1:
        ws.auto_filter.ref = ws.dimensions
    for coluna in ws.columns:
        maior = max((len(str(c.value)) for c in coluna if c.value is not None), default=10)
        letra = get_column_letter(coluna[0].column)
        ws.column_dimensions[letra].width = min(maior + 2, 50)


def gerar_relatorio_excel(registros: list[RegistroValidado], caminho_saida) -> Path:
    """
    Etapa 5.2: gera relatorio_conferencia_lotes.xlsx com as 6 abas exigidas,
    cada uma contendo apenas os registros da sua categoria.
    """
    df_todos = montar_dataframe(registros)
    df_validos = df_todos[df_todos["Classificação"] == "Válido"]
    df_divergencias = df_todos[df_todos["Classificação"] == "Divergência"]
    df_ambiguos = df_todos[df_todos["Classificação"] == "Ambíguo"]
    df_erros = df_todos[df_todos["Classificação"] == "Erro de Entrada"]
    df_resumo = montar_resumo(df_todos)

    caminho_saida = Path(caminho_saida)
    with pd.ExcelWriter(caminho_saida, engine="openpyxl") as writer:
        df_resumo.to_excel(writer, sheet_name="Resumo", index=False)
        df_todos.to_excel(writer, sheet_name="Todos", index=False)
        df_validos.to_excel(writer, sheet_name="Válidos", index=False)
        df_divergencias.to_excel(writer, sheet_name="Divergências", index=False)
        df_ambiguos.to_excel(writer, sheet_name="Ambíguos", index=False)
        df_erros.to_excel(writer, sheet_name="Erros de Entrada", index=False)

        for nome_aba in writer.sheets:
            formatar_aba(writer.sheets[nome_aba])

    return caminho_saida


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------

def main(caminho_entrada=ARQUIVO_ENTRADA, caminho_saida=ARQUIVO_SAIDA):
    registros = consolidar_e_validar(caminho_entrada)
    caminho_gerado = gerar_relatorio_excel(registros, caminho_saida)

    total = len(registros)
    contagem = Counter(r.classificacao for r in registros)
    print(f"Registros processados: {total}")
    for categoria in ["Válido", "Divergência", "Ambíguo", "Erro de Entrada"]:
        print(f"  {categoria}: {contagem.get(categoria, 0)}")
    print(f"Relatório gerado em: {caminho_gerado.resolve()}")

    return registros


if __name__ == "__main__":
    main()
