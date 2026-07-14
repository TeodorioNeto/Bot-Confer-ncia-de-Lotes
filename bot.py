import argparse
import logging

from src.validacao import valida_campos_obrigatorios, valida_estrutura


def main():
    parser = argparse.ArgumentParser(description="Valida a planilha de conferencia de lotes.")
    parser.add_argument("arquivo", help="Caminho do arquivo .xlsx a ser validado")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    estrutura_ok = valida_estrutura(args.arquivo)
    campos_ok = valida_campos_obrigatorios(args.arquivo) if estrutura_ok else False

    if estrutura_ok and campos_ok:
        print("Planilha valida para RN01 e RN02.")
        return 0

    print("Planilha invalida para RN01/RN02.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
