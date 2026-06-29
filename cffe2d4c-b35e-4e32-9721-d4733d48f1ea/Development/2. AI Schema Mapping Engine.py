
"""
AI Schema Mapping Engine
─────────────────────────────────────────────────────────────────────────────
Simulates an LLM-style field mapping agent using:
  • Token overlap scoring  (fuzzy name similarity)
  • Semantic synonym tables (domain knowledge)
  • Type-compatibility signals
  • Confidence calibration with ambiguity flagging

This approach keeps all data internal — no external API call required.
"""

import re
import pandas as pd
from difflib import SequenceMatcher

# ── Synonym / semantic knowledge base ────────────────────────────────────────
SYNONYMS = {
    "LOAN_ID": [
        "loannumber", "loanid", "loan_num", "loan_no", "accountnumber",
        "accountid", "loanref", "loanreference"
    ],
    "BORROWER_NAME": [
        "borrowername", "borrower", "clientname", "customername",
        "applicantname", "fullname", "name"
    ],
    "CURRENT_UPB": [
        "principalbalance", "upb", "currentbalance", "outstandingbalance",
        "balance", "currentupb", "principal", "loanbalance"
    ],
    "INTEREST_RATE": [
        "interestrate", "rate", "couponrate", "noteratepercent",
        "intrate", "annualrate"
    ],
    "LOAN_STATUS": [
        "loanstatus", "status", "loancondition", "loanstate",
        "delinquencystatus"
    ],
    "ORIGINATION_DATE": [
        "origdate", "originationdate", "loanorigdate", "dateoriginated",
        "fundingdate", "opendate", "startdate"
    ],
    "NEXT_PAYMENT_DATE": [
        "nextpaymentdue", "nextpaymentdate", "nextduedate", "duedatenext",
        "schedulednextpayment"
    ],
    "PROPERTY_STATE": [
        "propertystate", "state", "propstate", "collateralstate",
        "stateabbr"
    ],
    "SERVICER": [
        "servicername", "servicer", "servicingcompany", "servicingentity",
        "loanservicer"
    ],
    "CREDIT_SCORE": [
        "ficoscore", "creditscore", "fico", "creditrating",
        "borrowercreditscore", "vantagescore"
    ],
}

# ── Type-compatibility hints ──────────────────────────────────────────────────
TYPE_HINTS = {
    "BIGINT":       ["number", "id", "num", "code", "count"],
    "DECIMAL":      ["balance", "rate", "amount", "price", "value", "upb"],
    "VARCHAR":      ["name", "status", "servicer", "state", "text", "description"],
    "DATE":         ["date", "due", "orig", "payment"],
    "INT":          ["score", "fico", "credit", "rating", "age"],
    "CHAR":         ["state", "code", "abbr"],
}


def _normalise(s: str) -> str:
    """Lowercase, strip non-alpha."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _token_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalise(a), _normalise(b)).ratio()


def _type_signal(json_field: str, sql_type: str) -> float:
    """Bonus score if field name tokens align with SQL type group."""
    base_type = sql_type.split("(")[0].upper()
    hints = TYPE_HINTS.get(base_type, [])
    norm = _normalise(json_field)
    return 0.1 if any(h in norm for h in hints) else 0.0


def score_mapping(json_field: str, sql_col: str, sql_type: str) -> float:
    """Composite similarity score [0, 1]."""
    norm_field = _normalise(json_field)
    # Exact synonym match → high base
    synonyms = [_normalise(s) for s in SYNONYMS.get(sql_col, [])]
    if norm_field in synonyms:
        return min(1.0, 0.85 + _type_signal(json_field, sql_type))
    # Token similarity
    token_score = max(
        _token_similarity(json_field, sql_col),
        max((_token_similarity(json_field, s) for s in SYNONYMS.get(sql_col, [])), default=0),
    )
    return min(1.0, token_score + _type_signal(json_field, sql_type))


def confidence_label(score: float) -> str:
    if score >= 0.80:
        return "High"
    if score >= 0.55:
        return "Medium"
    return "Low"


def is_ambiguous(score: float, all_scores: list[float]) -> bool:
    """Ambiguous if best score < 0.80 OR two candidates are within 0.15 of each other."""
    sorted_scores = sorted(all_scores, reverse=True)
    if score < 0.80:
        return True
    if len(sorted_scores) > 1 and (sorted_scores[0] - sorted_scores[1]) < 0.15:
        return True
    return False


# ── Run mapping for every vendor field ───────────────────────────────────────
mapping_rows = []

for json_field in vendor_fields:
    scores = {
        sql_col: score_mapping(json_field, sql_col, meta["sql_type"])
        for sql_col, meta in sql_schema.items()
    }
    best_col = max(scores, key=scores.get)
    best_score = scores[best_col]
    all_score_vals = list(scores.values())

    ambig = is_ambiguous(best_score, all_score_vals)
    conf = confidence_label(best_score)

    # Build human-readable reasoning
    norm = _normalise(json_field)
    synonyms_norm = [_normalise(s) for s in SYNONYMS.get(best_col, [])]
    if norm in synonyms_norm:
        reason = f"'{json_field}' is a known synonym for {best_col}; type conversion may be required."
    elif best_score >= 0.80:
        reason = f"Strong token overlap between '{json_field}' and '{best_col}'; minor format transform expected."
    elif best_score >= 0.55:
        reason = f"Partial name similarity to '{best_col}'; recommend analyst confirmation before production use."
    else:
        reason = f"Weak signal — no strong match found; manual mapping required."

    mapping_rows.append({
        "JSON_FIELD":   json_field,
        "SQL_COLUMN":   best_col if best_score >= 0.35 else "NO_MATCH",
        "RAW_SCORE":    round(best_score, 3),
        "CONFIDENCE":   conf,
        "AMBIGUOUS":    "YES" if ambig else "NO",
        "REASONING":    reason,
    })

ai_mapping_df = pd.DataFrame(mapping_rows)

# ── Identify unmapped SQL columns ─────────────────────────────────────────────
mapped_sql_cols = set(ai_mapping_df["SQL_COLUMN"].tolist())
missing_sql_cols = [col for col in sql_schema if col not in mapped_sql_cols]

# ── Print AI Mapping Report ───────────────────────────────────────────────────
print("=" * 90)
print("  AI SCHEMA MAPPING REPORT")
print("=" * 90)
_hdr = f"  {'JSON Field':<22} {'SQL Column':<22} {'Score':>6}  {'Conf':<8} {'Ambig':<7} Reasoning"
print(_hdr)
print("  " + "─" * 86)
for _, row in ai_mapping_df.iterrows():
    flag = "⚠" if row["AMBIGUOUS"] == "YES" else " "
    print(
        f"  {flag}{row['JSON_FIELD']:<21} {row['SQL_COLUMN']:<22} "
        f"{row['RAW_SCORE']:>6.3f}  {row['CONFIDENCE']:<8} {row['AMBIGUOUS']:<7} "
        f"{row['REASONING']}"
    )

print(f"\n  ⚠  = Flagged for analyst review")

if missing_sql_cols:
    print(f"\n  SQL COLUMNS WITH NO VENDOR MAPPING:")
    for c in missing_sql_cols:
        print(f"    • {c}  [{sql_schema[c]['sql_type']}]  nullable={sql_schema[c]['nullable']}")

# Summary stats
n_high   = (ai_mapping_df["CONFIDENCE"] == "High").sum()
n_medium = (ai_mapping_df["CONFIDENCE"] == "Medium").sum()
n_ambig  = (ai_mapping_df["AMBIGUOUS"] == "YES").sum()
print(f"\n  Mappings: {len(ai_mapping_df)} total  |  "
      f"High={n_high}  Medium={n_medium}  "
      f"Low={(ai_mapping_df['CONFIDENCE']=='Low').sum()}  |  "
      f"Ambiguous={n_ambig}")
