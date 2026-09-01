"""Sistema desktop legado simulado para a demonstracao do Capstone.

A aplicacao nao expoe API. O bot interage por teclado com a janela e usa o
atalho Ctrl+E para solicitar a exportacao exibida ao operador.
"""

from __future__ import annotations

import argparse
import json
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from src.capstone_collectors import load_inventory_from_reference


class EstoqueDesktopApp:
    def __init__(self, root: tk.Tk, *, source_path, export_path):
        self.root = root
        self.source_path = Path(source_path)
        self.export_path = Path(export_path)
        self.records = load_inventory_from_reference(self.source_path)

        root.title("LG - Controle de Estoque Legado")
        root.geometry("900x520")
        root.minsize(760, 420)
        root.bind("<Control-e>", self.export_records)

        header = ttk.Frame(root, padding=16)
        header.pack(fill="x")
        ttk.Label(
            header,
            text="Controle de Estoque - Sistema Legado",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            header,
            text="Consulte um lote e pressione Ctrl+E para exportar a grade.",
        ).pack(anchor="w", pady=(4, 0))

        search_frame = ttk.Frame(root, padding=(16, 0, 16, 10))
        search_frame.pack(fill="x")
        ttk.Label(search_frame, text="Lote:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=32,
        )
        self.search_entry.pack(side="left", padx=8)
        self.search_entry.bind("<Return>", self.apply_filter)
        ttk.Button(search_frame, text="Consultar", command=self.apply_filter).pack(
            side="left"
        )
        ttk.Button(
            search_frame,
            text="Exportar grade (Ctrl+E)",
            command=self.export_records,
        ).pack(side="right")

        columns = (
            "lote_id",
            "produto",
            "descricao_produto",
            "status_estoque",
            "quantidade_estoque",
        )
        self.grid = ttk.Treeview(root, columns=columns, show="headings")
        headings = {
            "lote_id": "Lote",
            "produto": "Produto",
            "descricao_produto": "Descricao",
            "status_estoque": "Cadastro",
            "quantidade_estoque": "Quantidade",
        }
        widths = {
            "lote_id": 145,
            "produto": 120,
            "descricao_produto": 330,
            "status_estoque": 100,
            "quantidade_estoque": 90,
        }
        for column in columns:
            self.grid.heading(column, text=headings[column])
            self.grid.column(column, width=widths[column], anchor="w")
        self.grid.pack(fill="both", expand=True, padx=16)

        self.status_var = tk.StringVar(value=f"{len(self.records)} registros carregados")
        ttk.Label(root, textvariable=self.status_var, padding=16).pack(anchor="w")
        self._render(self.records)
        self.search_entry.focus_set()

    def apply_filter(self, _event=None):
        query = self.search_var.get().strip().lower()
        filtered = [
            record
            for record in self.records
            if not query or query in str(record.get("lote_id") or "").lower()
        ]
        self._render(filtered)
        self.status_var.set(f"{len(filtered)} registro(s) encontrado(s)")

    def export_records(self, _event=None):
        self.export_path.parent.mkdir(parents=True, exist_ok=True)
        self.export_path.write_text(
            json.dumps(self.records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.status_var.set(f"Exportacao concluida: {self.export_path.name}")

    def _render(self, records):
        for item in self.grid.get_children():
            self.grid.delete(item)
        for record in records:
            self.grid.insert(
                "",
                "end",
                values=(
                    record.get("lote_id"),
                    record.get("produto"),
                    record.get("descricao_produto"),
                    record.get("status_estoque"),
                    record.get("quantidade_estoque"),
                ),
            )


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--export", required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    root = tk.Tk()
    EstoqueDesktopApp(root, source_path=args.source, export_path=args.export)
    root.mainloop()


if __name__ == "__main__":
    main()
