import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from datetime import datetime

# ── Inputs from upstream ─────────────────────────────────────────
# dq_summary, sql_ready_df, issues_log, sql_schema

# ── Zerve palette ────────────────────────────────────────────────
BG       = "#1D1D20"
CARD     = "#26262A"
PRI      = "#fbfbff"
SEC      = "#909094"
GREEN    = "#8DE5A1"
ORANGE   = "#FFB482"
CORAL    = "#FF9F9B"
LAVENDER = "#D0BBFF"
BLUE     = "#A1C9F4"
GOLD     = "#ffd400"

score       = dq_summary["dq_score"]
score_color = GREEN if score >= 90 else (ORANGE if score >= 75 else CORAL)

# ═══════════════════════════════════════════════════════════════
# FIGURE 1 — Executive DQ Dashboard
# ═══════════════════════════════════════════════════════════════
dq_report_fig = plt.figure(figsize=(18, 14))
dq_report_fig.patch.set_facecolor(BG)

# ── KPI Cards (top row) ──────────────────────────────────────────
kpi_data = [
    ("Total Records",        dq_summary["total_records"],          BLUE),
    ("Field Mappings",       f"{dq_summary['successful_mappings']}/10", GREEN),
    ("Ambiguous Mappings",   dq_summary["ambiguous_mappings"],     ORANGE if dq_summary["ambiguous_mappings"] else GREEN),
    ("Missing Required",     dq_summary["missing_required"],       CORAL  if dq_summary["missing_required"]  else GREEN),
    ("Invalid Values",       dq_summary["invalid_values"],         CORAL  if dq_summary["invalid_values"]    else GREEN),
    ("Duplicate Records",    dq_summary["duplicate_records"],      CORAL  if dq_summary["duplicate_records"] else GREEN),
    ("Biz Rule Violations",  dq_summary["business_rule_violations"],ORANGE if dq_summary["business_rule_violations"] else GREEN),
]

card_w   = 1 / 7
card_h   = 0.13
start_x  = 0.0
top_y    = 0.96

for n, (label, val, color) in enumerate(kpi_data):
    cx = start_x + n * card_w + card_w / 2
    ax_card = dq_report_fig.add_axes([start_x + n * card_w + 0.004, top_y - card_h, card_w - 0.008, card_h])
    ax_card.set_facecolor(CARD)
    ax_card.set_xlim(0, 1); ax_card.set_ylim(0, 1)
    for sp in ax_card.spines.values(): sp.set_visible(False)
    ax_card.set_xticks([]); ax_card.set_yticks([])
    ax_card.text(0.5, 0.62, str(val), ha="center", va="center",
                 fontsize=22, fontweight="bold", color=color, fontfamily="monospace")
    ax_card.text(0.5, 0.22, label, ha="center", va="center",
                 fontsize=8.5, color=SEC, fontfamily="monospace")

# ── DQ Score Gauge ───────────────────────────────────────────────
ax_gauge = dq_report_fig.add_axes([0.03, 0.60, 0.26, 0.28])
ax_gauge.set_facecolor(BG)
ax_gauge.set_xlim(-1.2, 1.2); ax_gauge.set_ylim(-0.2, 1.2)
ax_gauge.axis("off")

theta   = np.linspace(np.pi, 0, 300)
x_outer = np.cos(theta)
y_outer = np.sin(theta)

# Background arc (grey)
ax_gauge.fill_between(np.cos(theta), 0.0 * np.sin(theta), np.sin(theta),
                      color=CARD, zorder=1)
# Coloured fill up to score
fill_end   = np.pi - (score / 100) * np.pi
theta_fill = np.linspace(np.pi, fill_end, 200)
ax_gauge.fill_between(np.cos(theta_fill), 0.0 * np.sin(theta_fill),
                      np.sin(theta_fill), color=score_color, alpha=0.85, zorder=2)

ax_gauge.text(0, 0.25, f"{score}", ha="center", va="center",
              fontsize=32, fontweight="bold", color=score_color, fontfamily="monospace")
ax_gauge.text(0, -0.05, "/ 100", ha="center", va="center",
              fontsize=14, color=SEC, fontfamily="monospace")
ax_gauge.text(0, 0.95, "Overall DQ Score", ha="center", va="center",
              fontsize=10, color=PRI, fontfamily="monospace")
ax_gauge.text(-1.05, -0.12, "0", ha="center", fontsize=9, color=SEC)
ax_gauge.text( 1.05, -0.12, "100", ha="center", fontsize=9, color=SEC)

# ── Issue Distribution Bar Chart ─────────────────────────────────
ax_bar = dq_report_fig.add_axes([0.35, 0.60, 0.30, 0.28])
ax_bar.set_facecolor(BG)
for sp in ax_bar.spines.values(): sp.set_color(SEC)

categories  = ["Duplicates", "Missing\nRequired", "Invalid\nValues", "Biz Rule\nViolations"]
values      = [
    dq_summary["duplicate_records"],
    dq_summary["missing_required"],
    dq_summary["invalid_values"],
    dq_summary["business_rule_violations"],
]
bar_colors  = [CORAL, ORANGE, LAVENDER, BLUE]

bars = ax_bar.barh(categories, values, color=bar_colors, height=0.55, zorder=2)
ax_bar.set_facecolor(BG)
ax_bar.grid(axis="x", color=CARD, linewidth=0.8, zorder=1)
ax_bar.tick_params(colors=SEC, labelsize=9)
ax_bar.set_xlabel("Issue Count", color=SEC, fontsize=9)
ax_bar.set_title("Issues by Type", color=PRI, fontsize=10, fontfamily="monospace", pad=8)
ax_bar.xaxis.label.set_color(SEC)
for bar, val in zip(bars, values):
    ax_bar.text(val + 0.15, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=9, color=PRI)

# ── Issues by Field ───────────────────────────────────────────────
ax_field = dq_report_fig.add_axes([0.68, 0.60, 0.30, 0.28])
ax_field.set_facecolor(BG)
for sp in ax_field.spines.values(): sp.set_color(SEC)

field_names   = list(dq_summary["issues_by_field"].keys())[:8]
field_counts  = list(dq_summary["issues_by_field"].values())[:8]
field_colors  = [CORAL, LAVENDER, ORANGE, BLUE, GREEN, GOLD, CORAL, LAVENDER][:len(field_names)]

bars2 = ax_field.barh(field_names, field_counts, color=field_colors, height=0.55, zorder=2)
ax_field.set_facecolor(BG)
ax_field.grid(axis="x", color=CARD, linewidth=0.8, zorder=1)
ax_field.tick_params(colors=SEC, labelsize=8)
ax_field.set_xlabel("Issue Count", color=SEC, fontsize=9)
ax_field.set_title("Issues by Field", color=PRI, fontsize=10, fontfamily="monospace", pad=8)
for bar, val in zip(bars2, field_counts):
    ax_field.text(val + 0.05, bar.get_y() + bar.get_height() / 2,
                  str(val), va="center", fontsize=9, color=PRI)

# ── Validation Trend Chart ────────────────────────────────────────
ax_trend = dq_report_fig.add_axes([0.03, 0.27, 0.94, 0.26])
ax_trend.set_facecolor(BG)
for sp in ax_trend.spines.values(): sp.set_color(SEC)

ibd        = dq_summary["issues_by_date"]
dates_raw  = sorted(ibd.keys())
counts     = [ibd[d] for d in dates_raw]
x_pos      = list(range(len(dates_raw)))

ax_trend.fill_between(x_pos, counts, color=LAVENDER, alpha=0.25)
ax_trend.plot(x_pos, counts, color=LAVENDER, linewidth=2, marker="o", markersize=4, zorder=3)
ax_trend.set_facecolor(BG)
ax_trend.grid(axis="y", color=CARD, linewidth=0.8, zorder=1)
ax_trend.tick_params(colors=SEC, labelsize=7.5)
ax_trend.set_ylabel("Issues", color=SEC, fontsize=9)
ax_trend.set_title("Daily Validation Issue Trend — June 2026", color=PRI, fontsize=10,
                   fontfamily="monospace", pad=8)

# Pre-compute tick labels (no formatters)
step        = max(1, len(dates_raw) // 12)
tick_pos    = x_pos[::step]
tick_labels = [d[5:] for d in dates_raw[::step]]   # "MM-DD"
ax_trend.set_xticks(tick_pos)
ax_trend.set_xticklabels(tick_labels, rotation=45, ha="right", fontsize=7.5)

avg_line = sum(counts) / len(counts) if counts else 0
ax_trend.axhline(y=avg_line, color=GOLD, linewidth=1.2, linestyle="--", alpha=0.7)
ax_trend.text(x_pos[-1] * 0.99, avg_line + 0.1, f"avg {avg_line:.1f}", color=GOLD, fontsize=8, ha="right")

# ── Issues Log Table ──────────────────────────────────────────────
ax_log = dq_report_fig.add_axes([0.03, 0.02, 0.94, 0.22])
ax_log.set_facecolor(BG)
ax_log.axis("off")

log_cols   = ["Rec#", "Loan ID", "Field", "Issue Type", "Detail"]
log_sample = issues_log[:12]

log_col_w  = [0.06, 0.10, 0.16, 0.20, 0.48]
log_x      = [sum(log_col_w[:j]) for j in range(len(log_col_w))]
log_x_mid  = [log_x[j] + log_col_w[j] / 2 for j in range(len(log_col_w))]

header_y_log = 0.93
for j, col_name in enumerate(log_cols):
    ax_log.text(log_x_mid[j], header_y_log, col_name,
                transform=ax_log.transAxes, ha="center", va="center",
                fontsize=8.5, fontweight="bold", color=BLUE, fontfamily="monospace")

ax_log.plot([0, 1], [header_y_log - 0.04, header_y_log - 0.04],
            color=SEC, linewidth=0.5, transform=ax_log.transAxes)

row_gap = 0.72 / max(len(log_sample), 1)
for i, issue in enumerate(log_sample):
    ry     = header_y_log - 0.10 - i * row_gap
    bg_col = "#26262A" if i % 2 == 0 else BG
    rect   = mpatches.FancyBboxPatch((0, ry - row_gap * 0.4), 1.0, row_gap * 0.85,
                                     boxstyle="square,pad=0", linewidth=0,
                                     facecolor=bg_col, transform=ax_log.transAxes, clip_on=False)
    ax_log.add_patch(rect)

    type_color = {"Duplicate Record": CORAL, "Missing Required Field": ORANGE,
                  "Invalid Value": LAVENDER, "Business Rule Violation": GOLD}.get(issue["issue_type"], PRI)
    row_vals = [
        str(issue["record_idx"]),
        str(issue["loan_id"])[:12],
        issue["field"],
        issue["issue_type"],
        issue["detail"][:65],
    ]
    for j, v in enumerate(row_vals):
        ax_log.text(log_x_mid[j], ry, v,
                    transform=ax_log.transAxes, ha="center", va="center",
                    fontsize=7.5, color=type_color if j == 3 else PRI, fontfamily="monospace")

ax_log.set_title(f"Issues Log (first {len(log_sample)} of {len(issues_log)} total)",
                 color=PRI, fontsize=9.5, fontfamily="monospace", pad=6)

# ── Main title ────────────────────────────────────────────────────
dq_report_fig.suptitle(
    f"Executive Data Quality Report  |  Batch: June 2026  |  Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
    fontsize=12, color=PRI, fontfamily="monospace", y=0.995
)

plt.close('all')

# ═══════════════════════════════════════════════════════════════
# FIGURE 2 — SQL-Ready Dataset Table (first 20 rows)
# ═══════════════════════════════════════════════════════════════
preview_df = sql_ready_df.head(20).copy()
preview_df["CURRENT_UPB"] = preview_df["CURRENT_UPB"].apply(
    lambda x: f"${x:,.2f}" if pd.notna(x) else "NULL")
preview_df["INTEREST_RATE"] = preview_df["INTEREST_RATE"].apply(
    lambda x: f"{x:.4f}" if pd.notna(x) else "NULL")
preview_df = preview_df.fillna("NULL")

col_w_ds = [1.4, 2.2, 1.6, 1.5, 1.5, 1.7, 1.7, 1.5, 2.0, 1.3]
fig_w_ds = sum(col_w_ds) + 0.4

sql_dataset_fig = plt.figure(figsize=(fig_w_ds, 1.0 + len(preview_df) * 0.42 + 0.5))
sql_dataset_fig.patch.set_facecolor(BG)
ax_ds = sql_dataset_fig.add_axes([0.01, 0.01, 0.98, 0.98])
ax_ds.set_facecolor(BG)
ax_ds.axis("off")

cols_ds    = list(preview_df.columns)
types_ds   = [sql_schema[c]["type"] for c in cols_ds]
total_w_ds = sum(col_w_ds)
xs_ds      = [sum(col_w_ds[:j]) / total_w_ds for j in range(len(col_w_ds))]
ws_ds      = [cw / total_w_ds for cw in col_w_ds]

n_rows_ds  = len(preview_df)
row_h_ds   = 0.88 / (n_rows_ds + 2)

hy = 0.95
for j, (col_name, typ) in enumerate(zip(cols_ds, types_ds)):
    cx = xs_ds[j] + ws_ds[j] / 2
    ax_ds.text(cx, hy, col_name, transform=ax_ds.transAxes,
               ha="center", va="center", fontsize=8.5, fontweight="bold",
               color=BLUE, fontfamily="monospace")
    ax_ds.text(cx, hy - row_h_ds * 0.65, typ, transform=ax_ds.transAxes,
               ha="center", va="center", fontsize=6.5, color=SEC, fontfamily="monospace")

ax_ds.plot([0, 1], [hy - row_h_ds * 1.1, hy - row_h_ds * 1.1],
           color=SEC, linewidth=0.5, transform=ax_ds.transAxes)

for r_idx, (_, data_row) in enumerate(preview_df.iterrows()):
    ry     = hy - row_h_ds * 1.5 - r_idx * row_h_ds
    bg_col = "#26262A" if r_idx % 2 == 0 else BG
    rect   = mpatches.FancyBboxPatch((0, ry - row_h_ds * 0.45), 1.0, row_h_ds * 0.90,
                                     boxstyle="square,pad=0", linewidth=0,
                                     facecolor=bg_col, transform=ax_ds.transAxes, clip_on=False)
    ax_ds.add_patch(rect)

    for j, col_name in enumerate(cols_ds):
        cx    = xs_ds[j] + ws_ds[j] / 2
        t     = str(data_row[col_name])
        color = CORAL if t == "NULL" else PRI
        ax_ds.text(cx, ry, t, transform=ax_ds.transAxes,
                   ha="center", va="center", fontsize=7.5,
                   color=color, fontfamily="monospace")

ax_ds.set_title(f"SQL-Ready Dataset — First 20 of {len(sql_ready_df)} Records (Enterprise Schema)",
                color=PRI, fontsize=10, fontfamily="monospace", pad=8)

plt.close('all')

print("=" * 65)
print("  EXECUTIVE DATA QUALITY REPORT")
print("=" * 65)
print(f"  Report Date        : {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")
print(f"  Total Records      : {dq_summary['total_records']}")
print(f"  Total Issues       : {dq_summary['total_issues']}")
print(f"  DQ Score           : {dq_summary['dq_score']} / 100")
print(f"  Clean Records      : {dq_summary['total_records'] - len(set(i['record_idx'] for i in issues_log))}")
print("=" * 65)
