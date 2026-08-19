"""
loader.py — N100 Financial Intelligence Platform
Day 2: Loads all 12 raw Excel files, applies normalization, returns clean DataFrames.
"""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_PATH = BASE_DIR / "data" / "raw"
SUPPORTING_PATH = RAW_PATH / "supporting datasets"
PROCESSED_PATH = BASE_DIR / "data" / "processed"
PROCESSED_PATH.mkdir(parents=True, exist_ok=True)

# Core files: banner row at index 0, real header at index 1
CORE_FILES = {
    "companies": "companies.xlsx",
    "profitandloss": "profitandloss.xlsx",
    "balancesheet": "balancesheet.xlsx",
    "cashflow": "cashflow.xlsx",
    "documents": "documents.xlsx",
    "analysis": "analysis.xlsx",
    "prosandcons": "prosandcons.xlsx",
}

# Supporting files: header at index 0, no banner row
SUPPORTING_FILES = {
    "sectors": "sectors.xlsx",
    "stock_prices": "stock_prices.xlsx",
    "financial_ratios": "financial_ratios.xlsx",
    "peer_groups": "peer_groups.xlsx",
    "market_cap": "market_cap.xlsx",
}


def normalize_year(value) -> int | None:
    """
    Normalize inconsistent year formats into a 4-digit int.
    Handles: 2023, '2023', 'FY23', 'FY2023', 'Mar 2023', 'Dec 2012', 2023.0
    """
    if pd.isna(value):
        return None

    if isinstance(value, (int, float)):
        year = int(value)
        return year if 1990 <= year <= 2035 else None

    text = str(value).strip()

    # 'FY23' or 'FY2023' style
    if text.upper().startswith("FY"):
        digits = "".join(c for c in text if c.isdigit())
        if len(digits) == 2:
            return 2000 + int(digits)
        if len(digits) == 4:
            return int(digits)

    # 'Mar 2023', 'Dec 2012' style 
    digits_only = "".join(c for c in text if c.isdigit())
    if len(digits_only) >= 4:
        year = int(digits_only[-4:])
        return year if 1990 <= year <= 2035 else None

    return None


def normalize_ticker(value) -> str | None:
    """
    Normalize ticker symbols to a consistent uppercase, stripped format.
    Handles: ' abb ', 'ABB.NS', 'abb', None
    """
    if pd.isna(value):
        return None

    text = str(value).strip().upper()
    # Remove common exchange suffixes
    for suffix in [".NS", ".BO", ".NSE", ".BSE"]:
        if text.endswith(suffix):
            text = text[: -len(suffix)]

    return text if text else None


def load_core_file(name: str, filename: str) -> pd.DataFrame:
    """Load a core file (banner row at 0, header at 1)."""
    df = pd.read_excel(RAW_PATH / filename, header=1)
    return df


def load_supporting_file(name: str, filename: str) -> pd.DataFrame:
    """Load a supporting file (header at row 0, no banner)."""
    df = pd.read_excel(SUPPORTING_PATH / filename, header=0)
    return df


def load_all_raw() -> dict:
    """Load all 12 raw files into a dict of DataFrames."""
    print("=" * 60)
    print("LOADING RAW FILES")
    print("=" * 60)

    dataframes = {}

    for name, filename in CORE_FILES.items():
        df = load_core_file(name, filename)
        dataframes[name] = df
        print(f"[core]       {filename:<25} -> {df.shape[0]} rows, {df.shape[1]} cols")

    for name, filename in SUPPORTING_FILES.items():
        df = load_supporting_file(name, filename)
        dataframes[name] = df
        print(f"[supporting] {filename:<25} -> {df.shape[0]} rows, {df.shape[1]} cols")

    print("\nAll 12 files loaded.\n")
    return dataframes


def apply_normalization(dataframes: dict) -> dict:
    """Apply normalize_year and normalize_ticker across relevant tables."""
    print("=" * 60)
    print("NORMALIZING")
    print("=" * 60)

    # Normalize ticker on companies table
    if "ticker" in dataframes["companies"].columns:
        dataframes["companies"]["ticker"] = dataframes["companies"]["ticker"].apply(normalize_ticker)
    elif "company_id" in dataframes["companies"].columns:
        # some datasets use company_id as the ticker itself
        dataframes["companies"]["company_id"] = dataframes["companies"]["company_id"].apply(normalize_ticker)

    # Normalize year across all tables that have a 'year' or 'Year' column
    for name, df in dataframes.items():
        for col in df.columns:
            if str(col).strip().lower() == "year":
                df[col] = df[col].apply(normalize_year)
                print(f"  normalized year in: {name}.{col}")

    print("\nNormalization complete.\n")
    return dataframes


def save_processed(dataframes: dict) -> None:
    """Save all normalized DataFrames to data/processed/ as CSV."""
    for name, df in dataframes.items():
        out_path = PROCESSED_PATH / f"{name}.csv"
        df.to_csv(out_path, index=False)
        print(f"  saved: {out_path.name} ({len(df)} rows)")


if __name__ == "__main__":
    raw = load_all_raw()
    normalized = apply_normalization(raw)
    save_processed(normalized)
    print("\n Day 2 loading + normalization complete.")