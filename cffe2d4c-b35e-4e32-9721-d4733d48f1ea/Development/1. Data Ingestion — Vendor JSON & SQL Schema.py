
import json
import pandas as pd

# ── Simulated vendor JSON payload (received daily) ───────────────────────────
vendor_json_raw = """
[
  {
    "loanNumber": "100012345",
    "borrowerName": "John Smith",
    "principalBalance": "315,442.87",
    "interestRate": "6.25%",
    "loanStatus": "Current",
    "origDate": "01/15/2020",
    "nextPaymentDue": "2026-07-01",
    "propertyState": "VA",
    "servicerName": "ABC Servicing",
    "ficoScore": 742
  }
]
"""

vendor_records = json.loads(vendor_json_raw)

# ── Target SQL schema definition ─────────────────────────────────────────────
sql_schema = {
    "LOAN_ID":            {"sql_type": "BIGINT",         "nullable": False},
    "BORROWER_NAME":      {"sql_type": "VARCHAR(100)",   "nullable": False},
    "CURRENT_UPB":        {"sql_type": "DECIMAL(18,2)",  "nullable": False},
    "INTEREST_RATE":      {"sql_type": "DECIMAL(6,4)",   "nullable": False},
    "LOAN_STATUS":        {"sql_type": "VARCHAR(20)",    "nullable": False},
    "ORIGINATION_DATE":   {"sql_type": "DATE",           "nullable": False},
    "NEXT_PAYMENT_DATE":  {"sql_type": "DATE",           "nullable": True},
    "PROPERTY_STATE":     {"sql_type": "CHAR(2)",        "nullable": True},
    "SERVICER":           {"sql_type": "VARCHAR(50)",    "nullable": True},
    "CREDIT_SCORE":       {"sql_type": "INT",            "nullable": True},
}

# Business rules for validation
business_rules = {
    "CREDIT_SCORE":    {"min": 300,  "max": 850},
    "INTEREST_RATE":   {"min": 0.0,  "max": 1.0},   # after percentage-to-decimal conversion
    "CURRENT_UPB":     {"min": 0.0,  "max": None},
}

vendor_fields = list(vendor_records[0].keys())

print("=" * 60)
print("VENDOR JSON — FIELD INVENTORY")
print("=" * 60)
for i, (k, v) in enumerate(vendor_records[0].items(), 1):
    print(f"  {i:2}. {k:<22}  =  {repr(v)}")

print(f"\nRecords received : {len(vendor_records)}")

print("\n" + "=" * 60)
print("TARGET SQL SCHEMA")
print("=" * 60)
_header = f"  {'Column':<22}  {'Type':<18}  {'Nullable'}"
print(_header)
print("  " + "-" * 50)
for col, meta in sql_schema.items():
    print(f"  {col:<22}  {meta['sql_type']:<18}  {meta['nullable']}")
