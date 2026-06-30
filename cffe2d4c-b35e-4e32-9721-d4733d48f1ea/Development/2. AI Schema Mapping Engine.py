import re
import pandas as pd
from difflib import SequenceMatcher

# ── Inputs from upstream ─────────────────────────────────────────
# vendor_fields, sql_schema inherited from Block 1

# ── Semantic synonym table ───────────────────────────────────────
SYNONYMS = {
    # loanNumber → LOAN_ID
    "loannumber":   "LOAN_ID",
    "loanid":       "LOAN_ID",
    "loan_no":      "LOAN_ID",
    "loanno":       "LOAN_ID",

    # borrowerName → BORROWER_NAME
    "borrowername": "BORROWER_NAME",
    "borrower":     "BORROWER_NAME",
    "clientname":   "BORROWER_NAME",
    "customername": "BORROWER_NAME",

    # principalBalance → CURRENT_UPB
    "principalbalance": "CURRENT_UPB",
    "upb":              "CURRENT_UPB",
    "currentbalance":   "CURRENT_UPB",
    "outstandingbalance":"CURRENT_UPB",
    "balance":          "CURRENT_UPB",

    # interestRate → INTEREST_RATE
    "interestrate": "INTEREST_RATE",
    "rate":         "INTEREST_RATE",
    "couponrate":   "INTEREST_RATE",
    "noterate":     "INTEREST_RATE",

    # loanStatus → LOAN_STATUS
    "loanstatus":   "LOAN_STATUS",
    "status":       "LOAN_STATUS",
    "loanstate":    "LOAN_STATUS",

    # origDate → ORIGINATION_DATE
    "origdate":         "ORIGINATION_DATE",
    "originationdate":  "ORIGINATION_DATE",
    "fundingdate":      "ORIGINATION_DATE",
    "closedate":        "ORIGINATION_DATE",
    "loandate":         "ORIGINATION_DATE",

    # nextPaymentDue → NEXT_PAYMENT_DATE
    "nextpaymentdue":   "NEXT_PAYMENT_DATE",
    "nextpaymentdate":  "NEXT_PAYMENT_DATE",
    "nextduedate":      "NEXT_PAYMENT_DATE",
    "paymentduedate":   "NEXT_PAYMENT_DATE",

    # propertyState → PROPERTY_STATE
    "propertystate":    "PROPERTY_STATE",
    "state":            "PROPERTY_STATE",
    "propstate":        "PROPERTY_STATE",

    # servicerName → SERVICER
    "servicername": "SERVICER",
    "servicer":     "SERVICER",
    "servicingco":  "SERVICER",
    "loanservicer": "SERVICER",

    # ficoScore → CREDIT_SCORE
    "ficoscore":    "CREDIT_SCORE",
    "fico":         "CREDIT_SCORE",
    "creditscore":  "CREDIT_SCORE",
    "creditrating": "CREDIT_SCORE",
}

# Type-hint signals: if vendor field name contains keyword → prefer sql col
TYPE_HINTS = {
    "date":    ["ORIGINATION_DATE","NEXT_PAYMENT_DATE"],
    "rate":    ["INTEREST_RATE"],
    "balance": ["CURRENT_UPB"],
    "score":   ["CREDIT_SCORE"],
    "state":   ["PROPERTY_STATE"],
    "status":  ["LOAN_STATUS"],
}

sql_cols = [c for c in sql_schema.keys()]

def token_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

mapping_rows = []

for json_field in [f for f in vendor_fields if f != "ingestion_date"]:
    norm = re.sub(r"[_\s]", "", json_field).lower()
    synonyms_norm = {re.sub(r"[_\s]","","").lower(): v for k,v in SYNONYMS.items() for _ in [k]}
    synonyms_norm = {re.sub(r"[_\s]","",k).lower(): v for k,v in SYNONYMS.items()}

    # 1. Direct synonym lookup (highest priority)
    if norm in synonyms_norm:
        best_col   = synonyms_norm[norm]
        best_score = 0.97
        reason     = "Direct semantic synonym match"
    else:
        # 2. Token similarity against all SQL column names
        scores = {}
        for col in sql_cols:
            col_norm = re.sub(r"[_\s]","",col).lower()
            sim = token_similarity(norm, col_norm)
            # Apply type-hint bonus
            for keyword, preferred_cols in TYPE_HINTS.items():
                if keyword in norm and col in preferred_cols:
                    sim = min(1.0, sim + 0.12)
            scores[col] = sim

        sorted_cols = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_col, best_score = sorted_cols[0]
        second_score = sorted_cols[1][1] if len(sorted_cols) > 1 else 0

        # Ambiguity: top two candidates within 0.15 of each other
        gap = best_score - second_score
        if gap < 0.15:
            reason = f"Similarity match ({best_score:.2f}); ambiguous — gap to runner-up only {gap:.2f}"
        else:
            reason = f"Token similarity match (score {best_score:.2f})"

    all_score_vals = list(scores.values()) if best_score < 0.97 else []
    ambig = (best_score < 0.97) and (len(all_score_vals) >= 2) and (
        (sorted(all_score_vals, reverse=True)[0] - sorted(all_score_vals, reverse=True)[1]) < 0.15
    )

    if best_score >= 0.90:
        conf, conf_label = best_score, "High"
    elif best_score >= 0.75:
        conf, conf_label = best_score, "Medium"
    else:
        conf, conf_label = best_score, "Low"

    mapping_rows.append({
        "JSON Field":       json_field,
        "SQL Column":       best_col,
        "Confidence":       round(conf, 2),
        "Confidence Label": conf_label,
        "Ambiguous":        ambig or conf_label in ("Medium","Low"),
        "Reasoning":        reason,
        "Analyst Review":   "Required" if (ambig or conf_label in ("Medium","Low")) else "Not required",
    })

ai_mapping_df = pd.DataFrame(mapping_rows)

# Summarise mapped vs missing SQL columns
mapped_sql_cols   = set(ai_mapping_df["SQL Column"].tolist())
missing_sql_cols  = [c for c in sql_cols if c not in mapped_sql_cols]

n_high   = (ai_mapping_df["Confidence Label"] == "High").sum()
n_medium = (ai_mapping_df["Confidence Label"] == "Medium").sum()
n_ambig  = ai_mapping_df["Ambiguous"].sum()

print("=" * 90)
print("  AI SCHEMA MAPPING REPORT")
print("=" * 90)
print(f"  {'JSON Field':<26} {'SQL Column':<22} {'Conf':>5}  {'Level':<8} {'Review'}")
print("-" * 90)
for _, row in ai_mapping_df.iterrows():
    flag = "⚠" if row["Ambiguous"] else "✓"
    print(f"  {flag} {row['JSON Field']:<24} {row['SQL Column']:<22} {row['Confidence']:>5.2f}  {row['Confidence Label']:<8} {row['Analyst Review']}")
print("=" * 90)
print(f"  High confidence : {n_high}    Medium : {n_medium}    Ambiguous : {n_ambig}")
print(f"  Missing SQL cols: {missing_sql_cols if missing_sql_cols else 'None'}")
print("=" * 90)
