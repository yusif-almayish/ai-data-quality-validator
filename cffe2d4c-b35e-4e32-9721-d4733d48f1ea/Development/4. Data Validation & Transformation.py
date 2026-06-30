import re
import pandas as pd
from datetime import datetime

# ── Inputs from upstream ─────────────────────────────────────────
# vendor_records, sql_schema, business_rules, field_map, pending_map

VALID_STATES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA",
    "ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK",
    "OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC",
}

DATE_FORMATS = ["%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y", "%m-%d-%Y", "%Y/%m/%d"]

# ────────────────────────────────────────────────────────────────
# Helper functions
# ────────────────────────────────────────────────────────────────
def parse_numeric(val):
    if val is None or str(val).strip() == "":
        return None, "Missing value"
    s = re.sub(r"[,$\s]", "", str(val))
    # Replace letter O with 0 (common OCR error)
    s = s.replace("O", "0")
    try:
        return float(s), None
    except ValueError:
        return None, f"Cannot parse numeric: '{val}'"

def parse_percent(val):
    if val is None or str(val).strip() == "":
        return None, "Missing value"
    s = str(val).strip().rstrip("%").strip()
    try:
        f = float(s)
        # Convert to decimal if it looks like a percentage
        if f > 1.0:
            f = round(f / 100.0, 6)
        return f, None
    except ValueError:
        return None, f"Cannot parse rate: '{val}'"

def parse_date(val):
    if val is None or str(val).strip() == "":
        return None, "Missing value"
    s = str(val).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d"), None
        except ValueError:
            continue
    return None, f"Unrecognised date format: '{val}'"

def log_issue(log, rec_idx, loan_id, field, issue_type, detail):
    log.append({
        "record_idx":  rec_idx,
        "loan_id":     loan_id,
        "field":       field,
        "issue_type":  issue_type,
        "detail":      detail,
    })

# ────────────────────────────────────────────────────────────────
# Step 1: Rename vendor fields → SQL columns
# ────────────────────────────────────────────────────────────────
renamed_records = []
for rec in vendor_records:
    new_rec = {}
    for json_key, value in rec.items():
        if json_key == "ingestion_date":
            new_rec["ingestion_date"] = value
            continue
        sql_col = field_map.get(json_key)
        if sql_col:
            new_rec[sql_col] = value
        # pending fields are excluded until analyst approves
    renamed_records.append(new_rec)

# ────────────────────────────────────────────────────────────────
# Step 2: Transform & validate each record
# ────────────────────────────────────────────────────────────────
issues_log       = []
transformed_records = []
seen_loan_ids    = {}   # loan_id → first record index
required_cols    = [c for c, m in sql_schema.items() if not m["nullable"]]

for rec_idx, rec in enumerate(renamed_records):
    out = {}
    raw_loan_id = str(rec.get("LOAN_ID", "")).strip()

    # ── LOAN_ID ──────────────────────────────────────────────────
    val, err = parse_numeric(raw_loan_id)
    if err:
        log_issue(issues_log, rec_idx, raw_loan_id, "LOAN_ID", "Invalid Value", err)
        out["LOAN_ID"] = None
    else:
        out["LOAN_ID"] = int(val)

    # ── Duplicate detection ──────────────────────────────────────
    if out["LOAN_ID"] is not None:
        if out["LOAN_ID"] in seen_loan_ids:
            log_issue(issues_log, rec_idx, out["LOAN_ID"], "LOAN_ID", "Duplicate Record",
                      f"Duplicate of record at index {seen_loan_ids[out['LOAN_ID']]}")
        else:
            seen_loan_ids[out["LOAN_ID"]] = rec_idx

    # ── BORROWER_NAME ─────────────────────────────────────────────
    name = rec.get("BORROWER_NAME")
    if not name or str(name).strip() == "":
        log_issue(issues_log, rec_idx, raw_loan_id, "BORROWER_NAME", "Missing Required Field", "Null/empty borrower name")
        out["BORROWER_NAME"] = None
    else:
        name = str(name).strip()
        if sql_schema["BORROWER_NAME"]["max_len"] and len(name) > sql_schema["BORROWER_NAME"]["max_len"]:
            log_issue(issues_log, rec_idx, raw_loan_id, "BORROWER_NAME", "Invalid Value",
                      f"Exceeds VARCHAR(100): length {len(name)}")
        out["BORROWER_NAME"] = name[:100]

    # ── CURRENT_UPB ──────────────────────────────────────────────
    val, err = parse_numeric(rec.get("CURRENT_UPB"))
    if err:
        log_issue(issues_log, rec_idx, raw_loan_id, "CURRENT_UPB", "Invalid Value", err)
        out["CURRENT_UPB"] = None
    else:
        if val < 0:
            log_issue(issues_log, rec_idx, raw_loan_id, "CURRENT_UPB", "Business Rule Violation",
                      f"Negative balance: {val}")
        out["CURRENT_UPB"] = round(val, 2)

    # ── INTEREST_RATE ─────────────────────────────────────────────
    rate, err = parse_percent(rec.get("INTEREST_RATE"))
    if err:
        log_issue(issues_log, rec_idx, raw_loan_id, "INTEREST_RATE", "Invalid Value", err)
        out["INTEREST_RATE"] = None
    else:
        rule = business_rules["INTEREST_RATE"]
        if not (rule["min"] <= rate <= rule["max"]):
            log_issue(issues_log, rec_idx, raw_loan_id, "INTEREST_RATE", "Business Rule Violation",
                      f"Rate {rate:.4f} outside [{rule['min']}, {rule['max']}]")
            out["INTEREST_RATE"] = None
        else:
            out["INTEREST_RATE"] = round(rate, 6)

    # ── LOAN_STATUS ───────────────────────────────────────────────
    status = str(rec.get("LOAN_STATUS", "")).strip()
    allowed = business_rules["LOAN_STATUS"]["allowed"]
    if status not in allowed:
        log_issue(issues_log, rec_idx, raw_loan_id, "LOAN_STATUS", "Business Rule Violation",
                  f"'{status}' not in allowed set {allowed}")
        out["LOAN_STATUS"] = None
    else:
        out["LOAN_STATUS"] = status

    # ── ORIGINATION_DATE ─────────────────────────────────────────
    d, err = parse_date(rec.get("ORIGINATION_DATE"))
    if err:
        log_issue(issues_log, rec_idx, raw_loan_id, "ORIGINATION_DATE", "Invalid Value", err)
        out["ORIGINATION_DATE"] = None
    else:
        out["ORIGINATION_DATE"] = d

    # ── NEXT_PAYMENT_DATE ─────────────────────────────────────────
    d, err = parse_date(rec.get("NEXT_PAYMENT_DATE"))
    if err:
        log_issue(issues_log, rec_idx, raw_loan_id, "NEXT_PAYMENT_DATE", "Invalid Value", err)
        out["NEXT_PAYMENT_DATE"] = None
    else:
        out["NEXT_PAYMENT_DATE"] = d

    # ── PROPERTY_STATE ────────────────────────────────────────────
    state = str(rec.get("PROPERTY_STATE", "")).strip().upper()
    if state not in VALID_STATES:
        log_issue(issues_log, rec_idx, raw_loan_id, "PROPERTY_STATE", "Invalid Value",
                  f"'{rec.get('PROPERTY_STATE')}' is not a valid 2-char state code")
        out["PROPERTY_STATE"] = None
    else:
        out["PROPERTY_STATE"] = state

    # ── SERVICER ─────────────────────────────────────────────────
    svc = rec.get("SERVICER")
    if svc and len(str(svc)) > 50:
        log_issue(issues_log, rec_idx, raw_loan_id, "SERVICER", "Invalid Value",
                  f"Exceeds VARCHAR(50): length {len(str(svc))}")
    out["SERVICER"] = str(svc)[:50] if svc else None

    # ── CREDIT_SCORE ─────────────────────────────────────────────
    cs_val, err = parse_numeric(rec.get("CREDIT_SCORE"))
    if err:
        log_issue(issues_log, rec_idx, raw_loan_id, "CREDIT_SCORE", "Invalid Value", err)
        out["CREDIT_SCORE"] = None
    else:
        cs_int = int(cs_val)
        rule   = business_rules["CREDIT_SCORE"]
        if not (rule["min"] <= cs_int <= rule["max"]):
            log_issue(issues_log, rec_idx, raw_loan_id, "CREDIT_SCORE", "Business Rule Violation",
                      f"FICO {cs_int} outside [{rule['min']}, {rule['max']}]")
            out["CREDIT_SCORE"] = None
        else:
            out["CREDIT_SCORE"] = cs_int

    transformed_records.append(out)

# ────────────────────────────────────────────────────────────────
# Step 3: Build SQL-ready DataFrame
# ────────────────────────────────────────────────────────────────
sql_col_order = list(sql_schema.keys())
sql_ready_df  = pd.DataFrame(transformed_records)[sql_col_order]

# ────────────────────────────────────────────────────────────────
# Step 4: Compute DQ summary
# ────────────────────────────────────────────────────────────────
issues_df = pd.DataFrame(issues_log) if issues_log else pd.DataFrame(
    columns=["record_idx","loan_id","field","issue_type","detail"])

n_total        = len(vendor_records)
n_dups         = (issues_df["issue_type"] == "Duplicate Record").sum()        if len(issues_df) else 0
n_missing      = (issues_df["issue_type"] == "Missing Required Field").sum()  if len(issues_df) else 0
n_invalid      = (issues_df["issue_type"] == "Invalid Value").sum()           if len(issues_df) else 0
n_biz          = (issues_df["issue_type"] == "Business Rule Violation").sum() if len(issues_df) else 0
n_ambig        = len(pending_map)
n_mapped       = len(field_map)
n_total_issues = n_dups + n_missing + n_invalid + n_biz

# DQ Score: start at 100, deduct per issue type (per record)
score = 100.0
score -= n_missing * (10 / n_total) * 100 / 100
score -= n_invalid * (5  / n_total) * 100 / 100
score -= n_biz     * (3  / n_total) * 100 / 100
score -= n_dups    * (5  / n_total) * 100 / 100
score -= n_ambig   * 2
dq_score = max(0.0, round(score, 1))

# Issues by field
issues_by_field = (issues_df.groupby("field")["issue_type"].count().sort_values(ascending=False).to_dict()
                   if len(issues_df) else {})

# Issues by date (for trend chart)
if len(issues_df) and len(renamed_records):
    date_map = {i: renamed_records[i].get("ingestion_date","") for i in range(len(renamed_records))}
    issues_df["ingestion_date"] = issues_df["record_idx"].map(date_map)
    issues_by_date = issues_df.groupby("ingestion_date")["issue_type"].count().sort_index().to_dict()
else:
    issues_by_date = {}

dq_summary = {
    "total_records":         n_total,
    "successful_mappings":   n_mapped,
    "ambiguous_mappings":    n_ambig,
    "missing_required":      int(n_missing),
    "invalid_values":        int(n_invalid),
    "duplicate_records":     int(n_dups),
    "business_rule_violations": int(n_biz),
    "total_issues":          int(n_total_issues),
    "dq_score":              dq_score,
    "issues_by_field":       issues_by_field,
    "issues_by_date":        issues_by_date,
    "batch_start":           vendor_records[0].get("ingestion_date","") if vendor_records else "",
    "batch_end":             vendor_records[-1].get("ingestion_date","") if vendor_records else "",
}

print("=" * 65)
print("  DATA VALIDATION & TRANSFORMATION SUMMARY")
print("=" * 65)
print(f"  Records processed         : {n_total}")
print(f"  Successful field mappings : {n_mapped} / {len(sql_schema)}")
print(f"  Ambiguous mappings        : {n_ambig}")
print(f"  ─────────────────────────────────────────────────")
print(f"  Duplicate records         : {n_dups}")
print(f"  Missing required fields   : {n_missing}")
print(f"  Invalid values            : {n_invalid}")
print(f"  Business rule violations  : {n_biz}")
print(f"  Total issues              : {n_total_issues}")
print(f"  ─────────────────────────────────────────────────")
print(f"  Overall DQ Score          : {dq_score} / 100")
print("=" * 65)
print(f"\n  Issues by field:")
for field, cnt in list(issues_by_field.items())[:10]:
    print(f"    {field:<22} : {cnt}")
print(f"\n  SQL-ready dataset shape : {sql_ready_df.shape}")
print(f"  Clean records (0 issues): {n_total - len(issues_df['record_idx'].unique()) if len(issues_df) else n_total}")
