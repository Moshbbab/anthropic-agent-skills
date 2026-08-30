"""Audit every CSV in a folder tree with DuckDB and write one row per file.

Usage:
    python audit_csv_library.py                 # uses ROOT below
    python audit_csv_library.py <root> [out]    # or pass paths on the command line

Output columns per file: row count, column names, null percentage and approximate
distinct count per column, plus the sniffed delimiter / header flag / encoding and
a read status so unreadable files stay visible instead of disappearing.
"""

import glob
import json
import sys
from pathlib import Path

import duckdb
import pandas as pd

# --- edit this line only -------------------------------------------------
ROOT = r"C:\<مسار مكتبة السوق>"
# -------------------------------------------------------------------------

OUTPUT_NAME = "audit_reality.csv"

# Tried in order. The first one that parses the file wins and is recorded in
# `encoding_used`. windows-1256 (Arabic) needs DuckDB's `encodings` extension,
# which is downloaded on first use and skipped silently when unavailable.
ENCODINGS = ["utf-8", "utf-16", "windows-1256"]
CORE_ENCODINGS = {"utf-8", "utf-16", "latin-1"}  # built in, no extension needed


def find_csv_files(root: Path, output: Path) -> list[Path]:
    """Every *.csv under root, case-insensitive, excluding the audit output itself."""
    seen: dict[str, Path] = {}
    # Character classes rather than "*.csv" + "*.CSV": glob is case-sensitive on
    # Linux/macOS, so .Csv and .cSV would otherwise be missed.
    for hit in glob.glob(str(root / "**" / "*.[cC][sS][vV]"), recursive=True):
        path = Path(hit)
        if not path.is_file():
            continue
        # A previous run's output lives inside the tree; auditing it would grow
        # the report with rows about itself on every re-run.
        if path.name == output.name or path.resolve() == output.resolve():
            continue
        seen.setdefault(str(path.resolve()).lower(), path)
    return sorted(seen.values(), key=lambda p: str(p).lower())


def relation(path: Path, encoding: str) -> str:
    quoted = path.as_posix().replace("'", "''")
    encoding_arg = f", encoding = '{encoding}'" if encoding != "utf-8" else ""
    return (
        "read_csv("
        f"'{quoted}', all_varchar = true, sample_size = -1{encoding_arg}"
        ")"
    )


def summarize(con: duckdb.DuckDBPyConnection, path: Path) -> tuple[pd.DataFrame, str]:
    """SUMMARIZE the file, retrying the encoding list. Returns (summary, encoding).

    A failed query leaves the connection in an aborted transaction, so each
    attempt runs on its own cursor; otherwise every retry fails with
    "Current transaction is aborted" and hides the real parse error.
    """
    first_error: Exception | None = None
    tried: list[str] = []
    for encoding in ENCODINGS:
        if encoding not in CORE_ENCODINGS and not load_encodings_extension(con):
            continue
        tried.append(encoding)
        cursor = con.cursor()
        try:
            return cursor.sql(f"SUMMARIZE SELECT * FROM {relation(path, encoding)}").df(), encoding
        except Exception as exc:  # noqa: BLE001 - recorded per file, never fatal
            first_error = first_error or exc
        finally:
            cursor.close()
    if first_error is None:
        raise RuntimeError("no encoding attempted")
    raise RuntimeError(f"{type(first_error).__name__}: {first_error} [encodings tried: {', '.join(tried)}]")


def load_encodings_extension(con: duckdb.DuckDBPyConnection) -> bool:
    """Load DuckDB's `encodings` extension once; False when it is unavailable."""
    if not hasattr(load_encodings_extension, "_ok"):
        cursor = con.cursor()
        try:
            cursor.sql("INSTALL encodings")
            cursor.sql("LOAD encodings")
            load_encodings_extension._ok = True
        except Exception:  # noqa: BLE001 - offline or unsupported build
            load_encodings_extension._ok = False
        finally:
            cursor.close()
    return load_encodings_extension._ok


def sniff(con: duckdb.DuckDBPyConnection, path: Path, encoding: str) -> tuple:
    """Delimiter and header flag from DuckDB's sniffer (reads a sample only).

    A False header flag on a file that visibly has one means the shape is
    inconsistent — ragged rows push DuckDB into positional column0/column1 names.
    """
    quoted = path.as_posix().replace("'", "''")
    encoding_arg = f", encoding = '{encoding}'" if encoding != "utf-8" else ""
    cursor = con.cursor()
    try:
        row = cursor.sql(
            f"SELECT Delimiter, HasHeader FROM sniff_csv('{quoted}'{encoding_arg})"
        ).fetchone()
        return (row[0], bool(row[1])) if row else (None, None)
    except Exception:  # noqa: BLE001 - sniffing is best effort
        return (None, None)
    finally:
        cursor.close()


def audit_file(con: duckdb.DuckDBPyConnection, path: Path) -> dict:
    row = {
        "file": path.name,
        "folder": path.parent.name,
        "full_path": str(path),
        "file_size_bytes": path.stat().st_size if path.exists() else None,
        "rows": None,
        "column_count": None,
        "columns_present": None,
        "null_pct_by_column": None,
        "approx_distinct_by_column": None,
        "delimiter": None,
        "has_header": None,
        "encoding_used": None,
        "read_status": "READ_ERROR",
        "read_error": None,
    }

    try:
        summary, encoding = summarize(con, path)
    except Exception as exc:  # noqa: BLE001 - one bad file must not stop the audit
        row["read_error"] = str(exc).replace("\n", " ")[:1000]
        return row

    columns = summary["column_name"].astype(str).tolist()
    # SUMMARIZE's `count` is the total row count per column (nulls included), so
    # it replaces a second full scan for SELECT COUNT(*).
    row_count = int(summary["count"].max()) if len(summary) else 0

    row.update(
        rows=row_count,
        column_count=len(columns),
        columns_present=json.dumps(columns, ensure_ascii=False),
        null_pct_by_column=json.dumps(
            {
                str(r["column_name"]): (
                    None if pd.isna(r["null_percentage"]) else round(float(r["null_percentage"]), 4)
                )
                for _, r in summary.iterrows()
            },
            ensure_ascii=False,
        ),
        approx_distinct_by_column=json.dumps(
            {
                str(r["column_name"]): (
                    None if pd.isna(r["approx_unique"]) else int(r["approx_unique"])
                )
                for _, r in summary.iterrows()
            },
            ensure_ascii=False,
        ),
        encoding_used=encoding,
        read_status="OK",
    )
    row["delimiter"], row["has_header"] = sniff(con, path, encoding)
    return row


def main(argv: list[str]) -> int:
    root = Path(argv[1] if len(argv) > 1 else ROOT)
    output = Path(argv[2]) if len(argv) > 2 else root / OUTPUT_NAME

    if not root.is_dir():
        print(f"Root folder not found: {root}", file=sys.stderr)
        return 1

    files = find_csv_files(root, output)
    if not files:
        print(f"No CSV files found under: {root}", file=sys.stderr)
        return 1

    out = []
    with duckdb.connect() as con:
        for index, path in enumerate(files, start=1):
            print(f"[{index}/{len(files)}] {path.name}", flush=True)
            out.append(audit_file(con, path))

    audit = pd.DataFrame(out)
    output.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(output, index=False, encoding="utf-8-sig")

    print(f"\n{len(audit)} file rows written to: {output}")
    print(audit["read_status"].value_counts(dropna=False).to_string())

    unreadable = audit[audit["read_status"] != "OK"]
    if len(unreadable):
        print("\nUnreadable files:")
        for _, r in unreadable.iterrows():
            print(f"  {r['full_path']}: {r['read_error']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
