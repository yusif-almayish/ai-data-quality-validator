import sqlite3
import pandas as pd
from datetime import date

# ── Configuration — adjust date range for each daily batch ───────
BATCH_START = "2026-06-01"
BATCH_END   = "2026-06-30"
DB_PATH     = "loan_portfolio.db"
TABLE_NAME  = "vendor_loan_data"

# ── Connect & load records for the configured date range ─────────
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

query = f"""
    SELECT *
    FROM   {TABLE_NAME}
    WHERE  ingestion_date BETWEEN '{BATCH_START}' AND '{BATCH_END}'
    ORDER  BY ingestion_date, loanNumber
"""

cursor = conn.execute(query)
rows   = cursor.fetchall()
conn.close()

vendor_records = [dict(r) for r in rows]

# ── Enterprise SQL schema (target) ──────────────────────────────
sql_schema = {
    "LOAN_ID":           {"type": "BIGINT",       "nullable": False, "max_len": None},
    "BORROWER_NAME":     {"type": "VARCHAR(100)",  "nullable": False, "max_len": 100},
    "CURRENT_UPB":       {"type": "DECIMAL(18,2)", "nullable": False, "max_len": None},
    "INTEREST_RATE":     {"type": "DECIMAL(6,4)",  "nullable": False, "max_len": None},
    "LOAN_STATUS":       {"type": "VARCHAR(20)",   "nullable": False, "max_len": 20},
    "ORIGINATION_DATE":  {"type": "DATE",          "nullable": False, "max_len": None},
    "NEXT_PAYMENT_DATE": {"type": "DATE",          "nullable": True,  "max_len": None},
    "PROPERTY_STATE":    {"type": "CHAR(2)",        "nullable": False, "max_len": 2},
    "SERVICER":          {"type": "VARCHAR(50)",   "nullable": True,  "max_len": 50},
    "CREDIT_SCORE":      {"type": "INT",           "nullable": True,  "max_len": None},
}

# ── Business rules ───────────────────────────────────────────────
business_rules = {
    "CREDIT_SCORE":   {"min": 300, "max": 850,  "desc": "FICO score must be 300–850"},
    "INTEREST_RATE":  {"min": 0.0, "max": 1.0,  "desc": "Rate must be 0.0–1.0 after pct conversion"},
    "CURRENT_UPB":    {"min": 0.0, "max": None, "desc": "Balance must be non-negative"},
    "LOAN_STATUS":    {"allowed": ["Current","Delinquent","Paid Off","Foreclosure","Forbearance"],
                       "desc": "Status must match approved values"},
    "PROPERTY_STATE": {"length": 2, "desc": "Must be a 2-character state code"},
}

# ── Ingestion summary ────────────────────────────────────────────
vendor_fields = list(vendor_records[0].keys()) if vendor_records else []

print("=" * 65)
print("  LOAN PORTFOLIO — DATABASE INGESTION SUMMARY")
print("=" * 65)
print(f"  Source database  : {DB_PATH}")
print(f"  Source table     : {TABLE_NAME}")
print(f"  Batch window     : {BATCH_START}  →  {BATCH_END}")
print(f"  Records loaded   : {len(vendor_records)}")
print(f"  Fields per record: {len(vendor_fields)}")
print()
print("  Vendor Field Inventory (first record sample):")
sample = vendor_records[0]
for k, v in sample.items():
    if k == "ingestion_date":
        continue
    print(f"    {k:<25} = {repr(v)}")
print("=" * 65)
