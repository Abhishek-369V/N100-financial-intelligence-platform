"""
Day 2: Loads all 12 raw Excel files, normalizes year/ticker.
"""

import pandas as pd
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # src/etl/ -> project root
RAW_PATH = BASE_DIR / "data" / "raw"
SUPPORTING_PATH = RAW_PATH / "supporting datasets"
PROCESSED_PATH = BASE_DIR / "data" / "processed"
PROCESSED_PATH.mkdir(parents=True, exist_ok=True)

CORE_FILES = {
    "companies": "companies.xlsx",
    "profitandloss": "profitandloss.xlsx",
    "balancesheet": "balancesheet.xlsx",
    "cashflow": "cashflow.xlsx",
    "documents": "documents.xlsx",
    "analysis": "analysis.xlsx",
    "prosandcons": "prosandcons.xlsx",
}

SUPPORTING_FILES = {
    "sectors": "sectors.xlsx",
    "stock_prices": "stock_prices.xlsx",
    "market_cap": "market_cap.xlsx",
    "financial_ratios": "financial_ratios.xlsx",
    "peer_groups": "peer_groups.xlsx",
}

MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
    "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    "january": "01", "february": "02", "march": "03", "april": "04", "june": "06",
    "july": "07", "august": "08", "september": "09", "october": "10",
    "november": "11", "december": "12",
}


def normalize_year(value):
    """
    Normalize year values to 'YYYY-MM' string per PDF spec (page 37).
    Handles: 'Mar-23', 'Mar 23', 'March-2023', 2023 (int), 'FY23',
             'Dec-22', 'Jun-23', '2023-03' (pass-through).
    Returns 'PARSE_ERROR' string for unparseable input (per spec — not None).
    """
    if pd.isna(value):
        return "PARSE_ERROR"

    # Already normalized: 'YYYY-MM'
    if isinstance(value, str) and re.match(r"^\d{4}-\d{2}$", value.strip()):
        return value.strip()

    # Plain integer/float year -> assume March FY close
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        year = int(value)
        if 1990 <= year <= 2035:
            return f"{year}-03"
        return "PARSE_ERROR"

    text = str(value).strip()

    # FY23 / FY2023
    fy_match = re.match(r"^FY\s*(\d{2,4})$", text, re.IGNORECASE)
    if fy_match:
        digits = fy_match.group(1)
        year = 2000 + int(digits) if len(digits) == 2 else int(digits)
        return f"{year}-03"

    # 'Mar-23', 'Mar 23', 'Dec-22', 'Jun-23' (3-letter month + 2-digit year)
    short_match = re.match(r"^([A-Za-z]{3,9})[\s\-]+(\d{2,4})$", text)
    if short_match:
        month_str = short_match.group(1).lower()
        year_str = short_match.group(2)
        if month_str in MONTH_MAP:
            year = 2000 + int(year_str) if len(year_str) == 2 else int(year_str)
            if 1990 <= year <= 2035:
                return f"{year}-{MONTH_MAP[month_str]}"

    # Plain 4-digit year embedded in text, no month found
    digits_only = re.sub(r"\D", "", text)
    if len(digits_only) == 4:
        year = int(digits_only)
        if 1990 <= year <= 2035:
            return f"{year}-03"

    return "PARSE_ERROR"


def normalize_ticker(value):
    """Normalize ticker: strip whitespace, uppercase. Preserve hyphens/ampersands (valid NSE tickers)."""
    if pd.isna(value):
        return None
    text = str(value).strip().upper()
    return text if text else None


def load_core_file(filename):
    """Core files: banner row at 0, real header at row 1 (PDF page 10 load note)."""
    return pd.read_excel(RAW_PATH / filename, header=1)


def load_supporting_file(filename):
    """Supporting files: header at row 0, no banner (PDF page 10 load note)."""
    return pd.read_excel(SUPPORTING_PATH / filename, header=0)


def load_all_raw():
    print("=" * 60)
    print("LOADING RAW FILES")
    print("=" * 60)
    dataframes = {}
    for name, filename in CORE_FILES.items():
        df = load_core_file(filename)
        dataframes[name] = df
        print(f"[core]       {filename:<25} -> {df.shape[0]} rows, {df.shape[1]} cols")
    for name, filename in SUPPORTING_FILES.items():
        df = load_supporting_file(filename)
        dataframes[name] = df
        print(f"[supporting] {filename:<25} -> {df.shape[0]} rows, {df.shape[1]} cols")
    print("\nAll 12 files loaded.\n")
    return dataframes


def apply_normalization(dataframes):
    print("=" * 60)
    print("NORMALIZING (year -> YYYY-MM, ticker -> upper/stripped)")
    print("=" * 60)

    parse_failures = []

    # Ticker normalization on company_id / id columns
    for name, df in dataframes.items():
        for col in df.columns:
            if str(col).strip().lower() in ("company_id", "id") and df[col].dtype == object:
                if name == "companies" and str(col).strip().lower() == "id":
                    df[col] = df[col].apply(normalize_ticker)
                elif str(col).strip().lower() == "company_id":
                    df[col] = df[col].apply(normalize_ticker)

    # Year normalization -> YYYY-MM, log PARSE_ERROR rows
    for name, df in dataframes.items():
        for col in df.columns:
            col_clean = str(col).strip().lower()
            if col_clean in ("year",):
                original = df[col].copy()
                df[col] = df[col].apply(normalize_year)
                errors = df[df[col] == "PARSE_ERROR"]
                for idx in errors.index:
                    parse_failures.append({
                        "table": name, "row_index": idx,
                        "raw_value": original.loc[idx], "column": col
                    })
                print(f"  normalized year in: {name}.{col} ({len(errors)} parse errors)")

    if parse_failures:
        pd.DataFrame(parse_failures).to_csv(PROCESSED_PATH / "parse_failures.csv", index=False)
        print(f"\n  {len(parse_failures)} PARSE_ERROR rows logged to parse_failures.csv")

    print("\nNormalization complete.\n")
    return dataframes


def save_processed(dataframes):
    for name, df in dataframes.items():
        out_path = PROCESSED_PATH / f"{name}.csv"
        df.to_csv(out_path, index=False)
        print(f"  saved: {out_path.name} ({len(df)} rows)")


if __name__ == "__main__":
    raw = load_all_raw()
    normalized = apply_normalization(raw)
    save_processed(normalized)
    print("\n Day 2 loading + normalization complete.")