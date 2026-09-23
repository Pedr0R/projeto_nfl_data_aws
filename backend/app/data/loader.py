"""Orquestração da camada de dados (F1).

Ponto único para (re)construir a camada normalizada + derivada. Idempotente:
usa CREATE OR REPLACE, então rodar de novo não duplica.

Uso via CLI:
    python -m app.data.loader          # constrói tudo
    python -m app.data.loader --stats  # constrói e imprime contagens
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .database import build_base_tables, get_connection, table_count
from .derived import build_derived_tables


def build_all(data_dir: Path | None = None) -> None:
    """Constrói tabelas base + derivadas."""
    build_base_tables(data_dir)
    build_derived_tables()


def stats() -> dict[str, int]:
    """Contagens das principais tabelas (sanidade)."""
    tables = ["games", "players", "plays", "pff", "player_play", "matchup", "player_season"]
    return {t: table_count(t) for t in tables}


def _table_exists(name: str) -> bool:
    con = get_connection()
    row = con.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?", [name]
    ).fetchone()
    return bool(row and row[0])


def ensure_built(data_dir: Path | None = None) -> None:
    """Constrói a camada se ainda não existir (usado na inicialização da API)."""
    if not _table_exists("player_season"):
        build_all(data_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Constrói a camada de dados (F1).")
    parser.add_argument("--stats", action="store_true", help="Imprime contagens ao final.")
    args = parser.parse_args()

    build_all()
    if args.stats:
        for table, count in stats().items():
            print(f"{table:>14}: {count:,}")


if __name__ == "__main__":
    main()
