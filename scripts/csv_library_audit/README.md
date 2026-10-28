# CSV Library Audit

`audit_csv_library.py` walks a folder tree, reads every `*.csv` with DuckDB, and
writes one row per file to `audit_reality.csv` — a ground-truth inventory of what
each file actually contains, as opposed to what its name suggests.

## Usage

Requires Python 3.10+.

```bash
pip install duckdb pandas

# Option A: edit the ROOT line at the top of the script, then:
python audit_csv_library.py

# Option B: pass paths on the command line
python audit_csv_library.py "C:\path\to\library" [output.csv]
```

The report is written UTF-8 with BOM (`utf-8-sig`) so Arabic opens correctly in
Excel by double-click.

## Output columns

| Column | Meaning |
| --- | --- |
| `file`, `folder`, `full_path`, `file_size_bytes` | Where the file is and how big |
| `rows`, `column_count` | Actual row and column counts (full scan, not a sample) |
| `columns_present` | JSON array of column names, in file order |
| `null_pct_by_column` | JSON object, percentage of NULLs per column |
| `approx_distinct_by_column` | JSON object, approximate distinct values per column (HyperLogLog) |
| `delimiter`, `has_header` | What DuckDB's sniffer detected |
| `encoding_used` | Which encoding actually parsed the file |
| `read_status`, `read_error` | `OK` or `READ_ERROR` plus the full DuckDB message |

## Reading the results

- **`has_header` is `False` on a file that clearly has a header** — the row shape is
  inconsistent (a data row with more fields than the header pushes DuckDB into
  positional `column0`, `column1`, … names). That file needs cleaning before use.
- **`rows = 0`** — the file is empty or header-only.
- **`read_status = READ_ERROR`** — the file never parsed. The error text is kept in
  full so the cause (encoding, quoting, truncation) is visible; these files are the
  point of the audit and must not be silently dropped.
- **`approx_distinct` = `rows`** on a column is a candidate key; `approx_distinct = 1`
  is a constant column carrying no information.

## Notes

- Every column is read as `VARCHAR` (`all_varchar = true`) so type inference never
  rejects a row; the audit measures shape and completeness, not types.
- `sample_size = -1` forces a full scan — the counts are exact, not estimates.
- Row counts come from `SUMMARIZE`'s own `count` column, so each file is scanned
  once rather than twice.
- A previous `audit_reality.csv` inside the tree is skipped, so re-runs stay
  idempotent instead of auditing their own output.
- Non-UTF-8 files are retried as UTF-16, then windows-1256 (Arabic). windows-1256
  needs DuckDB's `encodings` extension, downloaded on first use; without network
  access that retry is skipped and the file is reported as `READ_ERROR` with the
  encodings that were tried.
