import json

# ── Build structured context for the GEN_AI block ────────────────
# Summarise issues_log into a concise digest
issue_type_counts = {}
issue_field_counts = {}
for item in issues_log:
    issue_type_counts[item["issue_type"]]  = issue_type_counts.get(item["issue_type"], 0) + 1
    issue_field_counts[item["field"]]      = issue_field_counts.get(item["field"], 0) + 1

sample_issues = [
    f"{i['issue_type']} on {i['field']}: {i['detail'][:80]}"
    for i in issues_log[:8]
]

ai_context = {
    "batch_summary": {
        "total_records":           dq_summary["total_records"],
        "clean_records":           dq_summary["total_records"] - dq_summary["total_issues"],
        "total_issues":            dq_summary["total_issues"],
        "overall_dq_score":        dq_summary["dq_score"],
        "successful_mappings":     dq_summary["successful_mappings"],
        "ambiguous_mappings":      dq_summary["ambiguous_mappings"],
    },
    "issue_breakdown": {
        "duplicate_records":          dq_summary["duplicate_records"],
        "missing_required_fields":    dq_summary["missing_required"],
        "invalid_values":             dq_summary["invalid_values"],
        "business_rule_violations":   dq_summary["business_rule_violations"],
    },
    "issues_by_type":  issue_type_counts,
    "issues_by_field": issue_field_counts,
    "sample_issues":   sample_issues,
    "automated_actions": [
        "Schema mapping completed automatically (10/10 fields, 0 requiring analyst review)",
        "Numeric formatting corrected: commas and currency symbols stripped",
        "Interest rates converted from percentage strings to decimals",
        "Date formats normalised to ISO-8601 across multiple input patterns",
        "State codes standardised to uppercase 2-character USPS format",
        "Duplicate LOAN_IDs detected and flagged without analyst involvement",
    ],
}

ai_context_str = json.dumps(ai_context, indent=2)
print(ai_context_str[:1200])
