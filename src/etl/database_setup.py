"""
database_setup.py — N100 Financial Intelligence Platform
Day 5: Loads all 12 processed CSVs into nifty100.db per schema.sql,
generates load_audit.csv, runs PRAGMA foreign_key_check.
"""

import pandas as pd
from sqlalchemy import create_engine, text
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROCESSED_PATH = BASE_DIR / "data" / "processed"
DB_PATH = BASE_DIR / "db"
SCHEMA_PATH = DB_PATH / "schema.sql"
OUTPUT_PATH = BASE_DIR / "output"
DB_PATH.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH / 'nifty100.db'}", echo=False)

TABLE_LOAD_ORDER = [
    ("companies", "companies"),
    ("profitandloss", "profitandloss"),
    ("balancesheet", "balancesheet"),
    ("cashflow", "cashflow"),
    ("analysis", "analysis"),
    ("documents", "documents"),
    ("prosandcons", "prosandcons"),
    ("sectors", "sectors"),
    ("stock_prices", "stock_prices"),
    ("market_cap", "market_cap"),
    ("financial_ratios", "financial_ratios"),
    ("peer_groups", "peer_groups"),
]


def create_schema():
    print("=" * 60)
    print("CREATING 12-TABLE SCHEMA")
    print("=" * 60)
    schema_sql = SCHEMA_PATH.read_text()
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys = ON"))
        for statement in schema_sql.strip().split(";"):
            statement = statement.strip()
            if statement and not statement.startswith("--"):
                conn.execute(text(statement))
        conn.commit()
    print("Schema created.\n")


def load_all_tables():
    print("=" * 60)
    print("LOADING ALL 12 TABLES — companies first (parent table)")
    print("=" * 60)

    audit_rows = []

    for csv_name, table_name in TABLE_LOAD_ORDER:
        csv_path = PROCESSED_PATH / f"{csv_name}.csv"

        if not csv_path.exists():
            print(f"-----> SKIPPED — {csv_path.name} not found")
            audit_rows.append({"table": table_name, "source_rows": 0, "loaded_rows": 0, "rejected": 0, "status": "FILE_MISSING"})
            continue

        df = pd.read_csv(csv_path)
        source_count = len(df)
        rejected = 0


        if "company_id" in df.columns and csv_name != "companies":
            valid_company_ids = set(pd.read_csv(PROCESSED_PATH / "companies.csv")["id"].astype(str).str.strip().str.upper())
            df["company_id"] = df["company_id"].astype(str).str.strip().str.upper()
            orphan_mask = ~df["company_id"].isin(valid_company_ids)
            rejected += orphan_mask.sum()
            df = df[~orphan_mask]

        if "company_id" in df.columns and "year" in df.columns:
            dupe_mask = df.duplicated(subset=["company_id", "year"], keep="first")
            rejected += dupe_mask.sum()
            df = df[~dupe_mask]

        # Drop rows with PARSE_ERROR year where applicable (rejected rows)
        if "year" in df.columns:
            bad = df["year"] == "PARSE_ERROR"
            rejected += bad.sum()
            df = df[~bad]

        df.to_sql(table_name, engine, if_exists="replace", index=False)
        loaded_count = pd.read_sql(f"SELECT COUNT(*) as cnt FROM {table_name}", engine).iloc[0]["cnt"]

        status = "OK" if loaded_count == (source_count - rejected) else "MISMATCH"
        print(f"  [{status}] {table_name}: {source_count} source -> {loaded_count} loaded ({rejected} rejected)")

        audit_rows.append({
            "table": table_name, "source_rows": source_count,
            "loaded_rows": loaded_count, "rejected": rejected, "status": status,
        })

    df_audit = pd.DataFrame(audit_rows)
    df_audit.to_csv(OUTPUT_PATH / "load_audit.csv", index=False)
    print(f"\nSaved: {OUTPUT_PATH / 'load_audit.csv'}")
    return df_audit


def run_fk_check():
    print("\n" + "=" * 60)
    print("FOREIGN KEY CHECK")
    print("=" * 60)
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys = ON"))
        result = conn.execute(text("PRAGMA foreign_key_check")).fetchall()

    if len(result) == 0:
        print(" --> PRAGMA foreign_key_check → 0 rows. All FKs valid.")
    else:
        print(f"----->  {len(result)} foreign key violations found:")
        for row in result[:10]:
            print(f"   {row}")
    return result


def verify_exit_criteria():
    print("\n" + "=" * 60)
    print("EXIT CRITERIA CHECK")
    print("=" * 60)
    company_count = pd.read_sql("SELECT COUNT(*) as cnt FROM companies", engine).iloc[0]["cnt"]
    print(f"  SELECT COUNT(*) FROM companies = {company_count}  (target: 92)  {'[DONE]' if company_count == 92 else '[ERROR]'}")


if __name__ == "__main__":
    create_schema()
    audit = load_all_tables()
    fk_result = run_fk_check()
    verify_exit_criteria()
    print("\n --> Day 5 full load complete.")