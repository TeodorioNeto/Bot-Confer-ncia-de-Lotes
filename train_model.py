"""Gera dataset ficticio e treina o classificador de lotes da Aula 24-A."""

from __future__ import annotations

import csv
from pathlib import Path

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

from api_ml.features import CLASSES, codificar_features


DATASET_PATH = Path("data/samples/lotes_historicos_ml.csv")
MODEL_PATH = Path("models/classificador_lotes.pkl")

STATUS_RAW = [
    "APROVADO",
    "OK",
    "PENDENTE",
    "EM ANALISE",
    "AJUSTE LINHA",
    "ESPECIFICACAO EM REVISAO",
    "REPROVADO",
    "NOK",
    "STATUS LIVRE",
]
TURNOS = ["MANHA", "TARDE", "NOITE"]


def gerar_dataset(total_amostras: int = 240) -> list[dict]:
    registros = []
    for indice in range(total_amostras):
        status_raw = STATUS_RAW[indice % len(STATUS_RAW)]
        turno = TURNOS[(indice // len(STATUS_RAW)) % len(TURNOS)]
        tem_obs = (indice % 4) in (0, 3)
        classe = regra_rotulagem(status_raw, turno, tem_obs)
        registros.append(
            {
                "lote_id": f"LG-2026-ML{indice + 1:04d}",
                "status_raw": status_raw,
                "turno": turno,
                "tem_obs": int(tem_obs),
                "classe": classe,
            }
        )
    return registros


def regra_rotulagem(status_raw: str, turno: str, tem_obs: bool) -> str:
    status = status_raw.upper()
    if status in {"APROVADO", "OK"}:
        return "válido_automático"
    if status in {"REPROVADO", "NOK"} and tem_obs:
        return "recusar_automático"
    if status == "AJUSTE LINHA" and turno == "NOITE":
        return "recusar_automático" if tem_obs else "revisar"
    if status in {"PENDENTE", "EM ANALISE", "ESPECIFICACAO EM REVISAO"}:
        return "revisar"
    return "revisar"


def salvar_dataset(registros: list[dict], caminho: Path = DATASET_PATH) -> Path:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(
            arquivo,
            fieldnames=["lote_id", "status_raw", "turno", "tem_obs", "classe"],
        )
        escritor.writeheader()
        escritor.writerows(registros)
    return caminho


def treinar_modelo(registros: list[dict], caminho_modelo: Path = MODEL_PATH) -> dict:
    x = [
        codificar_features(
            registro["status_raw"],
            registro["turno"],
            bool(int(registro["tem_obs"])),
        )
        for registro in registros
    ]
    y = [registro["classe"] for registro in registros]

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y,
    )
    modelo = RandomForestClassifier(
        n_estimators=120,
        random_state=42,
        max_depth=5,
        class_weight="balanced",
    )
    modelo.fit(x_train, y_train)
    acuracia = accuracy_score(y_test, modelo.predict(x_test))

    caminho_modelo.parent.mkdir(parents=True, exist_ok=True)
    pacote = {
        "model": modelo,
        "classes": CLASSES,
        "features": ["status_raw_codificado", "turno_codificado", "tem_obs"],
        "accuracy_holdout": acuracia,
    }
    joblib.dump(pacote, caminho_modelo)
    return pacote


def main() -> None:
    registros = gerar_dataset()
    caminho_dataset = salvar_dataset(registros)
    pacote = treinar_modelo(registros)
    print(f"Dataset gerado em: {caminho_dataset}")
    print(f"Modelo salvo em: {MODEL_PATH}")
    print(f"Acuracia holdout: {pacote['accuracy_holdout']:.3f}")


if __name__ == "__main__":
    main()
