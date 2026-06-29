
"""
Data Quality Report
─────────────────────────────────────────────────────────────────────────────
Produces three artefacts:
  1. dq_report_fig     — Executive DQ scorecard (metrics + gauge + issues)
  2. sql_dataset_fig   — Clean SQL-ready dataset rendered as a table
  3. Console print     — Full text summary for audit trail
"""

import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
from datetime import datetime

# ── Design tokens ─────────────────────────────────────────────────────────────
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

# ═══════════════════════════════════════════════════════════════════════════════
# ① DQ SCORECARD FIGURE
# ═══════════════════════════════════════════════════════════════════════════════
score = dq_summary["dq_score"]
score_color = GREEN if score >= 90 else (ORANGE if score >= 70 else CORAL)

dq_report_fig = plt.figure(figsize=(13, 9))
dq_report_fig.patch.set_facecolor(BG)

# ── Title bar ─────────────────────────────────────────────────────────────────
dq_report_fig.text(0.5, 0.97, "DATA QUALITY REPORT",
                   color=PRI, fontsize=14, fontweight="bold",
                   ha="center", va="top", fontfamily="monospace")
dq_report_fig.text(0.5, 0.94,
                   f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}  |  "
                   f"Source: Vendor JSON  |  Target: Enterprise SQL Schema",
                   color=SEC, fontsize=8, ha="center", va="top", fontfamily="monospace")

# ── KPI metric cards (top row) ────────────────────────────────────────────────
kpi_data = [
    ("Total Records",       dq_summary["total_records"],           BLUE),
    ("Successful Mappings", dq_summary["successful_mappings"],     GREEN),
    ("Ambiguous Mappings",  dq_summary["ambiguous_mappings"],      ORANGE),
    ("Missing Req. Fields", dq_summary["missing_required_fields"], CORAL),
    ("Invalid Values",      dq_summary["invalid_values"],          CORAL),
    ("Duplicate Records",   dq_summary["duplicate_records"],       CORAL),
    ("Biz Rule Violations", dq_summary["business_rule_violations"],CORAL),
]

card_w, card_h = 0.116, 0.12
start_x = 0.03
top_y   = 0.885

for n, (label, value, color) in enumerate(kpi_data):
    cx = start_x + n * (card_w + 0.018)
    ax_card = dq_report_fig.add_axes([cx, top_y - card_h, card_w, card_h])
    ax_card.set_facecolor(CARD)
    ax_card.set_xlim(0, 1); ax_card.set_ylim(0, 1); ax_card.axis("off")
    # Colored accent strip
    ax_card.add_patch(mpatches.FancyBboxPatch(
        (0, 0.85), 1.0, 0.15, boxstyle="square", facecolor=color, edgecolor="none"))
    ax_card.text(0.5, 0.50, str(value),
                 color=PRI, fontsize=16, fontweight="bold",
                 ha="center", va="center", fontfamily="monospace")
    ax_card.text(0.5, 0.15, label,
                 color=SEC, fontsize=6.0, ha="center", va="center",
                 fontfamily="monospace")

# ── DQ Score Gauge ────────────────────────────────────────────────────────────
import numpy as np

ax_gauge = dq_report_fig.add_axes([0.035, 0.32, 0.28, 0.38])
ax_gauge.set_facecolor(BG); ax_gauge.axis("off")
ax_gauge.set_xlim(-1.3, 1.3); ax_gauge.set_ylim(-0.4, 1.3)

# Gauge arc segments: danger → warning → ok
_theta = np.linspace(np.pi, 0, 300)
for start_deg, end_deg, col in [
    (180, 120, CORAL), (120, 60, ORANGE), (60, 0, GREEN)
]:
    _t = np.linspace(np.radians(start_deg), np.radians(end_deg), 100)
    _x_outer = np.cos(_t)
    _y_outer = np.sin(_t)
    _x_inner = 0.72 * np.cos(_t)
    _y_inner = 0.72 * np.sin(_t)
    _xs = np.concatenate([_x_outer, _x_inner[::-1]])
    _ys = np.concatenate([_y_outer, _y_inner[::-1]])
    ax_gauge.fill(_xs, _ys, color=col, alpha=0.35, zorder=1)

# Active arc (proportional to score)
_filled_angle = np.radians(180 - score * 1.8)   # 0→180 maps to 100→0
_t_fill = np.linspace(np.pi, _filled_angle, 200)
_x_fill_o = np.cos(_t_fill)
_y_fill_o = np.sin(_t_fill)
_x_fill_i = 0.72 * np.cos(_t_fill)
_y_fill_i = 0.72 * np.sin(_t_fill)
ax_gauge.fill(
    np.concatenate([_x_fill_o, _x_fill_i[::-1]]),
    np.concatenate([_y_fill_o, _y_fill_i[::-1]]),
    color=score_color, alpha=0.9, zorder=2
)

# Needle
_needle_angle = np.radians(180 - score * 1.8)
ax_gauge.annotate("",
    xy=(0.65 * np.cos(_needle_angle), 0.65 * np.sin(_needle_angle)),
    xytext=(0, 0),
    arrowprops=dict(arrowstyle="-|>", color=PRI, lw=2.0),
    zorder=5
)
ax_gauge.add_patch(plt.Circle((0, 0), 0.07, color=PRI, zorder=6))

# Labels
ax_gauge.text(0, -0.15, f"{score}",
              color=score_color, fontsize=28, fontweight="bold",
              ha="center", va="center", fontfamily="monospace", zorder=7)
ax_gauge.text(0, -0.32, "OVERALL DQ SCORE",
              color=SEC, fontsize=7.5, ha="center", va="center", fontfamily="monospace")
ax_gauge.text(-1.1, -0.05, "0", color=CORAL, fontsize=8, ha="center", fontfamily="monospace")
ax_gauge.text( 1.1, -0.05, "100", color=GREEN, fontsize=8, ha="center", fontfamily="monospace")
ax_gauge.text(0, 0.75, "DQ SCORE", color=SEC, fontsize=7, ha="center", fontfamily="monospace")

# ── DQ Metrics breakdown bar chart ───────────────────────────────────────────
ax_bar = dq_report_fig.add_axes([0.35, 0.32, 0.60, 0.38])
ax_bar.set_facecolor(BG)
for spine in ax_bar.spines.values():
    spine.set_visible(False)

categories = [
    "Successful\nMappings", "Ambiguous\nMappings",
    "Missing\nReq. Fields", "Invalid\nValues",
    "Biz Rule\nViolations", "Duplicate\nRecords"
]
values = [
    dq_summary["successful_mappings"],
    dq_summary["ambiguous_mappings"],
    dq_summary["missing_required_fields"],
    dq_summary["invalid_values"],
    dq_summary["business_rule_violations"],
    dq_summary["duplicate_records"],
]
bar_colors = [GREEN, ORANGE, CORAL, CORAL, CORAL, CORAL]

_y_pos = range(len(categories))
_bars = ax_bar.barh(list(_y_pos), values, color=bar_colors, height=0.55,
                    edgecolor="none")

# Add value labels
for bar, val in zip(_bars, values):
    ax_bar.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height() / 2,
                f"{val}", color=PRI, va="center", fontsize=9,
                fontfamily="monospace", fontweight="bold")

ax_bar.set_yticks(list(_y_pos))
ax_bar.set_yticklabels(categories, color=SEC, fontsize=8, fontfamily="monospace")
ax_bar.tick_params(axis="x", colors=SEC, labelsize=7)
ax_bar.set_xlim(0, max(max(values) + 2, 12))
ax_bar.xaxis.set_tick_params(color=SEC)
ax_bar.set_xlabel("Count", color=SEC, fontsize=8, fontfamily="monospace")
ax_bar.set_title("DQ Metrics Breakdown", color=PRI, fontsize=9,
                 fontfamily="monospace", pad=8)
ax_bar.tick_params(axis="both", which="both", length=0)
ax_bar.set_facecolor(BG)

# ── Issues log / Manual Review table ─────────────────────────────────────────
ax_iss = dq_report_fig.add_axes([0.03, 0.025, 0.94, 0.26])
ax_iss.set_facecolor(BG); ax_iss.axis("off")
ax_iss.set_xlim(0, 1); ax_iss.set_ylim(0, 1)

ax_iss.text(0.0, 0.97, "ISSUES LOG & RECOMMENDED MANUAL REVIEW ITEMS",
            color=LAVENDER, fontsize=8.5, fontweight="bold",
            va="top", fontfamily="monospace")

if dq_summary["issues_log"]:
    _iss_cols = ["#", "Field", "Issue Type", "Raw Value", "Message"]
    _col_xs   = [0.00, 0.04, 0.16, 0.32, 0.50]
    _col_ws   = [0.04, 0.12, 0.16, 0.18, 0.50]

    _row_h = 0.14
    _hdr_y = 0.82
    for label, xs in zip(_iss_cols, _col_xs):
        ax_iss.text(xs, _hdr_y, label,
                    color=LAVENDER, fontsize=7, fontweight="bold",
                    va="top", fontfamily="monospace")
    ax_iss.axhline(_hdr_y - 0.06, color=LAVENDER, lw=0.5, alpha=0.5)

    for n, iss in enumerate(dq_summary["issues_log"][:10]):
        _iy = _hdr_y - 0.08 - n * _row_h
        _row_bg = "#26262A" if n % 2 == 0 else "#222226"
        ax_iss.add_patch(mpatches.FancyBboxPatch(
            (0, _iy - 0.08), 1.0, _row_h,
            boxstyle="square", facecolor=_row_bg, edgecolor="none"))
        _vals = [
            str(iss["record_idx"] + 1),
            iss["field"],
            iss["issue_type"],
            str(iss["raw_value"])[:22],
            iss["message"][:55],
        ]
        _iss_color = CORAL if "VIOLATION" in iss["issue_type"] or "DUPLICATE" in iss["issue_type"] \
                     else ORANGE if "MISSING" in iss["issue_type"] else SEC
        for v, xs in zip(_vals, _col_xs):
            ax_iss.text(xs, _iy, v,
                        color=_iss_color if xs > 0 else SEC,
                        fontsize=6.2, va="top", fontfamily="monospace")
else:
    ax_iss.text(0.5, 0.50, "✓  No issues detected — dataset is clean and SQL-ready.",
                color=GREEN, fontsize=9, ha="center", va="center",
                fontfamily="monospace", fontweight="bold")

plt.close('all')

# ═══════════════════════════════════════════════════════════════════════════════
# ② SQL-READY DATASET FIGURE
# ═══════════════════════════════════════════════════════════════════════════════
_col_display = list(sql_ready_df.columns)
_n_cols_d    = len(_col_display)
_n_rows_d    = len(sql_ready_df)

_col_ws_d    = [1.4, 1.7, 1.5, 1.3, 1.3, 1.7, 1.7, 1.4, 1.8, 1.3]
_fig_w_d     = sum(_col_ws_d) + 0.4
_fig_h_d     = 0.65 * (_n_rows_d + 3) + 1.0

sql_dataset_fig, ax_ds = plt.subplots(figsize=(_fig_w_d, _fig_h_d))
sql_dataset_fig.patch.set_facecolor(BG)
ax_ds.set_facecolor(BG); ax_ds.axis("off")

# x positions
_xs_d = []
_xx = 0.0
for w in _col_ws_d:
    _xs_d.append(_xx)
    _xx += w
_total_w_d = _xx

ax_ds.set_xlim(0, _total_w_d)
ax_ds.set_ylim(-0.2, _fig_h_d)

ax_ds.text(_total_w_d / 2, _fig_h_d - 0.2,
           "CLEAN SQL-READY DATASET  —  Enterprise Schema",
           color=PRI, fontsize=10, fontweight="bold",
           ha="center", va="top", fontfamily="monospace")
ax_ds.text(_total_w_d / 2, _fig_h_d - 0.58,
           "Mapped  ·  Validated  ·  Transformed  ·  SQL-compatible types",
           color=SEC, fontsize=7.5, ha="center", va="top", fontfamily="monospace")

# Column headers
_hdr_y_d = _fig_h_d - 1.05
for label, xs, w in zip(_col_display, _xs_d, _col_ws_d):
    ax_ds.add_patch(mpatches.FancyBboxPatch(
        (xs, _hdr_y_d - 0.24), w - 0.06, 0.42,
        boxstyle="round,pad=0.02", facecolor=LAVENDER, edgecolor="none", zorder=2))
    # Wrap long header
    _lbl = label.replace("_", "\n") if len(label) > 12 else label
    ax_ds.text(xs + 0.08, _hdr_y_d - 0.03, _lbl,
               color=BG, fontsize=6.5, fontweight="bold",
               va="top", fontfamily="monospace")

# SQL type sub-header
_type_y = _hdr_y_d - 0.38
_sql_types = [sql_schema[c]["sql_type"] for c in _col_display]
for t, xs in zip(_sql_types, _xs_d):
    ax_ds.text(xs + 0.08, _type_y, t,
               color=BLUE, fontsize=5.5, va="top", fontfamily="monospace")

# Data rows
for r_idx, (_, row) in enumerate(sql_ready_df.iterrows()):
    _ry = _type_y - 0.20 - r_idx * 0.55
    _row_bg_d = "#26262A" if r_idx % 2 == 0 else "#222226"
    ax_ds.add_patch(mpatches.FancyBboxPatch(
        (0, _ry - 0.22), _total_w_d - 0.06, 0.42,
        boxstyle="round,pad=0.02", facecolor=_row_bg_d, edgecolor="none", zorder=1))
    for val, xs, col_name in zip(row.values, _xs_d, _col_display):
        _disp = str(val) if val is not None else "NULL"
        ax_ds.text(xs + 0.08, _ry, _disp[:20],
                   color=PRI if val is not None else CORAL,
                   fontsize=6.8, va="center", fontfamily="monospace")

plt.close('all')

# ── Console print ─────────────────────────────────────────────────────────────
print("=" * 65)
print("  EXECUTIVE DATA QUALITY REPORT")
print("=" * 65)
print(f"  Report Date        : {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
print(f"  Source             : Vendor JSON (daily feed)")
print(f"  Target Schema      : Enterprise SQL — loan_portfolio table")
print()
print(f"  ┌─────────────────────────────────────────────────────┐")
print(f"  │  METRIC                          VALUE              │")
print(f"  ├─────────────────────────────────────────────────────┤")
print(f"  │  Total Records Processed         {dq_summary['total_records']:<18}   │")
print(f"  │  Successful Field Mappings        {dq_summary['successful_mappings']:<18}  │")
print(f"  │  Ambiguous Mappings               {dq_summary['ambiguous_mappings']:<18}  │")
print(f"  │  Missing Required Fields          {dq_summary['missing_required_fields']:<18}  │")
print(f"  │  Invalid Values                   {dq_summary['invalid_values']:<18}  │")
print(f"  │  Business Rule Violations         {dq_summary['business_rule_violations']:<18}  │")
print(f"  │  Duplicate Records                {dq_summary['duplicate_records']:<18}  │")
print(f"  │  Overall DQ Score                 {dq_summary['dq_score']:<18}  │")
print(f"  └─────────────────────────────────────────────────────┘")
print()
if dq_summary["manual_review_items"]:
    print("  RECOMMENDED MANUAL REVIEW ITEMS:")
    for item in dq_summary["manual_review_items"]:
        print(f"    • [Rec {item['record_idx']+1}] {item['field']}: {item['message']}")
else:
    print("  ✓ No manual review items — all checks passed.")
print()
print("  SQL-READY DATASET:")
print(sql_ready_df.to_string(index=False))
