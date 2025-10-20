"""Combine multiple Parquet files into one.

Usage (PowerShell):
    python ./scripts/combine_parquet.py -o combined.parquet file1.parquet file2.parquet

Options:
    -o, --output       Output parquet filename (required)
    --dedupe           Deduplicate rows across files (default: False)
    --subset-cols COLS Comma-separated list of columns to keep in output
    --engine ENGINE    Parquet engine (pyarrow or fastparquet); default: pyarrow

This is intentionally dependency-light. It uses pandas for IO and simple
concatenation. For very large datasets, prefer a chunked/pyarrow-based solution.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List, Optional, Literal, cast

import pandas as pd


def combine_parquet_files(paths: Iterable[Path], output: Path, dedupe: bool = False, subset_cols: Optional[List[str]] = None, engine: str = "pyarrow") -> Path:
    """Read multiple parquet files, concatenate and write a single parquet.

    Returns the output Path on success.
    """
    dfs: List[pd.DataFrame] = []
    # Temporary mapping from column -> set of observed 'is_object' flags
    col_has_object: dict[str, bool] = {}

    for p in paths:
        if not p.exists():
            raise FileNotFoundError(f"Input file not found: {p}")
        df = pd.read_parquet(p, engine=cast(Literal["pyarrow", "fastparquet", "auto"], engine))
        # Record object-like presence per column
        for col, dtype in df.dtypes.items():
            try:
                is_obj = pd.api.types.is_object_dtype(dtype) or pd.api.types.is_string_dtype(dtype)
            except Exception:
                is_obj = True
            key = str(col)
            col_has_object[key] = col_has_object.get(key, False) or is_obj

        dfs.append(df)

    # For any column observed as object/string in at least one file, coerce that
    # column to string across all DataFrames to ensure consistent types for parquet.
    if col_has_object:
        for col, has_obj in col_has_object.items():
            if has_obj:
                for i, df in enumerate(dfs):
                    if col in df.columns:
                        try:
                            dfs[i][col] = df[col].astype(str)
                        except Exception:
                            dfs[i][col] = df[col].apply(lambda x: "" if pd.isna(x) else str(x))

    if not dfs:
        raise ValueError("No input files provided")

    combined = pd.concat(dfs, ignore_index=True)

    if subset_cols:
        combined = combined.loc[:, [c for c in subset_cols if c in combined.columns]]

    if dedupe:
        combined = combined.drop_duplicates()

    # Ensure output directory exists
    output.parent.mkdir(parents=True, exist_ok=True)

    combined.to_parquet(output, engine=cast(Literal["pyarrow", "fastparquet", "auto"], engine), index=False)

    return output


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Combine Parquet files into one")
    p.add_argument("files", nargs="+", help="Input parquet files to combine")
    p.add_argument("-o", "--output", required=True, help="Output parquet file path")
    p.add_argument("--dedupe", action="store_true", help="Drop duplicate rows in combined output")
    p.add_argument("--subset-cols", help="Comma-separated list of columns to keep in output")
    p.add_argument("--engine", default="pyarrow", help="Parquet engine to use: pyarrow or fastparquet")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    files = [Path(x) for x in args.files]
    output = Path(args.output)
    subset_cols = args.subset_cols.split(",") if args.subset_cols else None

    try:
        out = combine_parquet_files(files, output, dedupe=args.dedupe, subset_cols=subset_cols, engine=args.engine)
        print(f"Wrote combined parquet to: {out}")
        return 0
    except Exception as e:
        print(f"Failed to combine parquet files: {e}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
