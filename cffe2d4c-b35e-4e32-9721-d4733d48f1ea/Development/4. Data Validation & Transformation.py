
"""
Data Validation & Transformation
─────────────────────────────────────────────────────────────────────────────
Applies approved field mappings and performs all required transformations:
  1. Remove commas from numeric strings
  2. Strip % and convert to decimal (e.g. 6.25% → 0.0625)
  3. Standardize mixed date formats → ISO 8601 (YYYY-MM-DD)
  4. Cast to SQL-compatible Python types (int, float, str, date-string)
  5. Detect missing required fields
  6. Detect duplicate records (by LOAN_ID)
  7. Evaluate business rules (FICO range, rate range, positive balance)

Outputs:
  • sql_ready_df   — clean DataFrame aligned to SQL schema column order
  • dq_summary     — structured dict used by the DQ Report block
  • issues_log     — list of per-record per-field issue dicts
"""

import re
import pandas as pd
from datetime import datetime
from copy import deepcopy

# ─────────────────────────────────────────────────────────────────────────────
# 1.  Apply field mapping (rename JSON keys → SQL column names)
# ─────────────────────────────────────────────────────────────────────────────
raw_records = deepcopy(vendor_records)

renamed_records = []
for rec in raw_records:
    new_rec = {}
    for json_key, value in rec.items():
        sql_col = field_map.get(json_key)
        if sql_col:
            new_rec[sql_col] = value
        # unmapped fields are dropped (or could be routed to a staging column)
    renamed_records.append(new_rec)

# ─────────────────────────────────────────────────────────────────────────────
# 2.  Transformation helpers
# ─────────────────────────────────────────────────────────────────────────────
def parse_numeric(value) -> tuple[float | None, str | None]:
    """Strip commas, currency symbols, whitespace → float. Returns (val, error)."""
    if value is None or str(value).strip() == "":
        return None, "NULL_VALUE"
    cleaned = re.sub(r"[,$\s]", "", str(value))
    try:
        return float(cleaned), None
    except ValueError:
        return None, f"NON_NUMERIC: {value!r}"


def parse_percent(value) -> tuple[float | None, str | None]:
    """'6.25%' → 0.0625. Also handles plain floats already in decimal form."""
    if value is None or str(value).strip() == "":
        return None, "NULL_VALUE"
    s = str(value).strip()
    if s.endswith("%"):
        try:
            return round(float(s[:-1]) / 100, 6), None
        except ValueError:
            return None, f"INVALID_PERCENT: {value!r}"
    try:
        v = float(s)
        # Heuristic: if value > 1 it was probably given as a whole number (e.g. 6.25)
        return round(v / 100, 6) if v > 1 else round(v, 6), None
    except ValueError:
        return None, f"INVALID_PERCENT: {value!r}"


DATE_FORMATS = ["%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y", "%Y/%m/%d"]

def parse_date(value) -> tuple[str | None, str | None]:
    """Try multiple date formats → ISO 8601 string. Returns (val, error)."""
    if value is None or str(value).strip() == "":
        return None, "NULL_VALUE"
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(str(value).strip(), fmt).strftime("%Y-%m-%d"), None
        except ValueError:
            continue
    return None, f"UNPARSEABLE_DATE: {value!r}"


# ─────────────────────────────────────────────────────────────────────────────
# 3.  Per-record transformation + validation
# ─────────────────────────────────────────────────────────────────────────────
transformed_records = []
issues_log = []   # {record_idx, field, issue_type, raw_value, message}

for rec_idx, rec in enumerate(renamed_records):
    out = {}
    _issues = []

    def log_issue(field, issue_type, raw_value, message):
        _issues.append({
            "record_idx":  rec_idx,
            "field":       field,
            "issue_type":  issue_type,
            "raw_value":   raw_value,
            "message":     message,
        })

    # LOAN_ID — string-to-BIGINT
    raw = rec.get("LOAN_ID")
    val, err = parse_numeric(raw)
    if err:
        log_issue("LOAN_ID", "INVALID_TYPE", raw, err)
        out["LOAN_ID"] = None
    else:
        out["LOAN_ID"] = int(val)

    # BORROWER_NAME — VARCHAR(100)
    raw = rec.get("BORROWER_NAME")
    if not raw or str(raw).strip() == "":
        log_issue("BORROWER_NAME", "MISSING_REQUIRED", raw, "Borrower name is blank")
        out["BORROWER_NAME"] = None
    else:
        name = str(raw).strip()
        if len(name) > 100:
            log_issue("BORROWER_NAME", "TRUNCATION_RISK", raw, f"Length {len(name)} exceeds VARCHAR(100)")
        out["BORROWER_NAME"] = name[:100]

    # CURRENT_UPB — DECIMAL(18,2)
    raw = rec.get("CURRENT_UPB")
    val, err = parse_numeric(raw)
    if err:
        log_issue("CURRENT_UPB", "INVALID_VALUE", raw, err)
        out["CURRENT_UPB"] = None
    else:
        out["CURRENT_UPB"] = round(val, 2)
        rule = business_rules.get("CURRENT_UPB", {})
        if rule.get("min") is not None and val < rule["min"]:
            log_issue("CURRENT_UPB", "BUSINESS_RULE_VIOLATION", raw,
                      f"Balance {val} is below minimum {rule['min']}")

    # INTEREST_RATE — DECIMAL(6,4) — stored as decimal (not %)
    raw = rec.get("INTEREST_RATE")
    val, err = parse_percent(raw)
    if err:
        log_issue("INTEREST_RATE", "INVALID_VALUE", raw, err)
        out["INTEREST_RATE"] = None
    else:
        out["INTEREST_RATE"] = round(val, 4)
        rule = business_rules.get("INTEREST_RATE", {})
        if not (rule["min"] <= val <= rule["max"]):
            log_issue("INTEREST_RATE", "BUSINESS_RULE_VIOLATION", raw,
                      f"Rate {val} outside valid range [{rule['min']}, {rule['max']}]")

    # LOAN_STATUS — VARCHAR(20)
    raw = rec.get("LOAN_STATUS")
    valid_statuses = {"Current", "Delinquent", "Default", "Paid Off", "In Foreclosure"}
    if not raw:
        log_issue("LOAN_STATUS", "MISSING_REQUIRED", raw, "Loan status is missing")
        out["LOAN_STATUS"] = None
    else:
        status = str(raw).strip()
        if status not in valid_statuses:
            log_issue("LOAN_STATUS", "INVALID_VALUE", raw,
                      f"'{status}' not in allowed set {valid_statuses}")
        out["LOAN_STATUS"] = status[:20]

    # ORIGINATION_DATE — DATE
    raw = rec.get("ORIGINATION_DATE")
    val, err = parse_date(raw)
    if err:
        log_issue("ORIGINATION_DATE", "INVALID_DATE", raw, err)
        out["ORIGINATION_DATE"] = None
    else:
        out["ORIGINATION_DATE"] = val

    # NEXT_PAYMENT_DATE — DATE (nullable)
    raw = rec.get("NEXT_PAYMENT_DATE")
    val, err = parse_date(raw)
    if err and raw is not None:
        log_issue("NEXT_PAYMENT_DATE", "INVALID_DATE", raw, err)
        out["NEXT_PAYMENT_DATE"] = None
    else:
        out["NEXT_PAYMENT_DATE"] = val

    # PROPERTY_STATE — CHAR(2)
    raw = rec.get("PROPERTY_STATE")
    if raw and len(str(raw).strip()) != 2:
        log_issue("PROPERTY_STATE", "INVALID_VALUE", raw,
                  f"State code '{raw}' should be exactly 2 characters")
    out["PROPERTY_STATE"] = str(raw).strip().upper() if raw else None

    # SERVICER — VARCHAR(50)
    raw = rec.get("SERVICER")
    if raw and len(str(raw)) > 50:
        log_issue("SERVICER", "TRUNCATION_RISK", raw, f"Length {len(str(raw))} exceeds VARCHAR(50)")
    out["SERVICER"] = str(raw).strip()[:50] if raw else None

    # CREDIT_SCORE — INT
    raw = rec.get("CREDIT_SCORE")
    val, err = parse_numeric(raw)
    if err:
        log_issue("CREDIT_SCORE", "INVALID_VALUE", raw, err)
        out["CREDIT_SCORE"] = None
    else:
        out["CREDIT_SCORE"] = int(val)
        rule = business_rules.get("CREDIT_SCORE", {})
        if not (rule["min"] <= int(val) <= rule["max"]):
            log_issue("CREDIT_SCORE", "BUSINESS_RULE_VIOLATION", raw,
                      f"FICO {int(val)} outside valid range [{rule['min']}, {rule['max']}]")

    issues_log.extend(_issues)
    transformed_records.append(out)

# ─────────────────────────────────────────────────────────────────────────────
# 4.  Assemble SQL-ready DataFrame in schema column order
# ─────────────────────────────────────────────────────────────────────────────
sql_col_order = list(sql_schema.keys())
sql_ready_df = pd.DataFrame(transformed_records, columns=sql_col_order)

# ─────────────────────────────────────────────────────────────────────────────
# 5.  Duplicate detection (by LOAN_ID)
# ─────────────────────────────────────────────────────────────────────────────
_dup_mask   = sql_ready_df.duplicated(subset=["LOAN_ID"], keep=False)
duplicate_count = _dup_mask.sum()
if duplicate_count:
    for idx in sql_ready_df[_dup_mask].index:
        issues_log.append({
            "record_idx": idx,
            "field":      "LOAN_ID",
            "issue_type": "DUPLICATE_RECORD",
            "raw_value":  sql_ready_df.at[idx, "LOAN_ID"],
            "message":    "Duplicate LOAN_ID detected",
        })

# ─────────────────────────────────────────────────────────────────────────────
# 6.  Missing required field check
# ─────────────────────────────────────────────────────────────────────────────
required_cols = [col for col, m in sql_schema.items() if not m["nullable"]]
missing_required_count = 0
for col in required_cols:
    n_null = sql_ready_df[col].isna().sum()
    if n_null > 0:
        missing_required_count += n_null

# ─────────────────────────────────────────────────────────────────────────────
# 7.  DQ Summary
# ─────────────────────────────────────────────────────────────────────────────
_total = len(sql_ready_df)
_successful_maps  = len(field_map)
_ambiguous_maps   = len(pending_map)
_invalid_vals     = sum(1 for i in issues_log if i["issue_type"] in
                        ("INVALID_VALUE", "INVALID_TYPE", "INVALID_DATE", "NON_NUMERIC"))
_biz_violations   = sum(1 for i in issues_log if i["issue_type"] == "BUSINESS_RULE_VIOLATION")
_missing_req      = missing_required_count
_duplicates       = duplicate_count

# DQ score: penalise for each class of issue (per record)
_penalties = (
    (_invalid_vals     * 5) +
    (_biz_violations   * 3) +
    (_missing_req      * 10) +
    (_duplicates       * 5) +
    (_ambiguous_maps   * 2)
)
_dq_score = max(0, round(100 - (_penalties / max(_total, 1)), 1))

dq_summary = {
    "total_records":          _total,
    "successful_mappings":    _successful_maps,
    "ambiguous_mappings":     _ambiguous_maps,
    "missing_required_fields":_missing_req,
    "invalid_values":         _invalid_vals,
    "business_rule_violations":_biz_violations,
    "duplicate_records":      _duplicates,
    "dq_score":               _dq_score,
    "issues_log":             issues_log,
    "manual_review_items":    [i for i in issues_log
                               if i["issue_type"] in
                               ("BUSINESS_RULE_VIOLATION", "AMBIGUOUS_MAPPING",
                                "DUPLICATE_RECORD", "MISSING_REQUIRED")],
}

# ─────────────────────────────────────────────────────────────────────────────
# 8.  Print transformation summary
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 65)
print("  DATA VALIDATION & TRANSFORMATION SUMMARY")
print("=" * 65)
print(f"  Records processed       : {_total}")
print(f"  Successful mappings     : {_successful_maps} / {len(sql_schema)}")
print(f"  Invalid values          : {_invalid_vals}")
print(f"  Business rule violations: {_biz_violations}")
print(f"  Missing required fields : {_missing_req}")
print(f"  Duplicate records       : {_duplicates}")
print(f"  Overall DQ Score        : {_dq_score} / 100")

if issues_log:
    print(f"\n  Issues detected ({len(issues_log)}):")
    for iss in issues_log:
        print(f"    [rec {iss['record_idx']}] {iss['field']:<22} "
              f"  {iss['issue_type']:<28}  {iss['message']}")
else:
    print("\n  ✓ No issues detected — all records passed all checks.")

print("\n  TRANSFORMATIONS APPLIED:")
_transforms = [
    ("loanNumber",       "string → BIGINT  (stripped non-numeric chars)"),
    ("principalBalance", "string → DECIMAL (removed comma separator)"),
    ("interestRate",     "6.25%  → 0.0625  (% stripped, divided by 100)"),
    ("origDate",         "MM/DD/YYYY → YYYY-MM-DD  (ISO 8601)"),
    ("nextPaymentDue",   "YYYY-MM-DD (already ISO, validated format)"),
    ("propertyState",    "uppercased, length validated (CHAR 2)"),
    ("ficoScore",        "numeric → INT"),
]
for src, desc in _transforms:
    print(f"    {src:<22}  {desc}")
