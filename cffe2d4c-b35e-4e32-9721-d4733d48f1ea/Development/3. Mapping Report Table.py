
"""
Mapping Report Table
─────────────────────────────────────────────────────────────────────────────
Renders the AI Mapping Report in a clean, publication-ready styled table
and exports the approved field_map dict for use in transformation blocks.
"""

import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import to_rgba

# ── Build approved mapping dict (analyst would override ambiguous rows here) ──
# For this demo all mappings are High-confidence → auto-approved.
# A Medium/Low row would appear in the PENDING dict for human review.
approved_map = {}    # json_field → sql_column  (auto-approved)
pending_map  = {}    # json_field → sql_column  (needs review)

for _, row in ai_mapping_df.iterrows():
    if row["SQL_COLUMN"] == "NO_MATCH":
        pending_map[row["JSON_FIELD"]] = row["SQL_COLUMN"]
    elif row["AMBIGUOUS"] == "YES" or row["CONFIDENCE"] in ("Low",):
        pending_map[row["JSON_FIELD"]] = row["SQL_COLUMN"]
    else:
        approved_map[row["JSON_FIELD"]] = row["SQL_COLUMN"]

# field_map is the final mapping used by downstream transformation
field_map = {**approved_map}   # only auto-approved fields transform

print("Approved field_map:")
for k, v in field_map.items():
    print(f"  {k:<22}  →  {v}")

if pending_map:
    print("\n⚠  Pending analyst review:")
    for k, v in pending_map.items():
        print(f"  {k:<22}  →  {v}")

# ── Visual Mapping Report table ───────────────────────────────────────────────
BG         = "#1D1D20"
TEXT_PRI   = "#fbfbff"
TEXT_SEC   = "#909094"
GREEN      = "#8DE5A1"
ORANGE     = "#FFB482"
CORAL      = "#FF9F9B"
LAVENDER   = "#D0BBFF"
BLUE       = "#A1C9F4"

conf_color = {"High": GREEN, "Medium": ORANGE, "Low": CORAL}
ambig_color = {"YES": CORAL, "NO": GREEN}

display_df = ai_mapping_df[["JSON_FIELD", "SQL_COLUMN", "RAW_SCORE", "CONFIDENCE", "AMBIGUOUS", "REASONING"]].copy()
display_df["RAW_SCORE"] = display_df["RAW_SCORE"].apply(lambda x: f"{x:.3f}")

n_rows = len(display_df)
col_widths = [1.8, 2.0, 0.9, 0.9, 0.85, 5.6]
fig_width  = sum(col_widths) + 0.4
fig_height = 0.55 * (n_rows + 2) + 0.6

mapping_report_fig, ax = plt.subplots(figsize=(fig_width, fig_height))
mapping_report_fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)
ax.axis("off")

col_labels = ["JSON Field", "SQL Column", "Score", "Confidence", "Ambiguous", "Reasoning"]
n_cols = len(col_labels)

# Compute x positions from cumulative widths
x_starts = []
_x = 0.0
for w in col_widths:
    x_starts.append(_x)
    _x += w
total_w = _x

# Title
ax.text(total_w / 2, fig_height - 0.25, "AI SCHEMA MAPPING REPORT",
        color=TEXT_PRI, fontsize=11, fontweight="bold", ha="center", va="top",
        fontfamily="monospace")

# Header row
header_y = fig_height - 0.75
for j, (label, xs, w) in enumerate(zip(col_labels, x_starts, col_widths)):
    ax.add_patch(mpatches.FancyBboxPatch(
        (xs, header_y - 0.22), w - 0.06, 0.38,
        boxstyle="round,pad=0.02", facecolor=LAVENDER, edgecolor="none", zorder=2
    ))
    ax.text(xs + 0.06, header_y, label,
            color=BG, fontsize=7.5, fontweight="bold", va="center", fontfamily="monospace")

# Data rows
for i, (_, row) in enumerate(display_df.iterrows()):
    row_y = header_y - 0.52 * (i + 1)
    row_bg = "#26262A" if i % 2 == 0 else "#222226"

    ax.add_patch(mpatches.FancyBboxPatch(
        (0, row_y - 0.22), total_w - 0.06, 0.38,
        boxstyle="round,pad=0.02", facecolor=row_bg, edgecolor="none", zorder=1
    ))

    vals = [
        row["JSON_FIELD"], row["SQL_COLUMN"], row["RAW_SCORE"],
        row["CONFIDENCE"], row["AMBIGUOUS"], row["REASONING"]
    ]
    for j, (val, xs, w) in enumerate(zip(vals, x_starts, col_widths)):
        text_color = TEXT_PRI
        if j == 3:   # Confidence
            text_color = conf_color.get(str(val), TEXT_PRI)
        elif j == 4:  # Ambiguous
            text_color = ambig_color.get(str(val), TEXT_PRI)

        # Truncate reasoning for display
        disp_val = str(val)
        if j == 5 and len(disp_val) > 68:
            disp_val = disp_val[:65] + "…"

        ax.text(xs + 0.06, row_y, disp_val,
                color=text_color, fontsize=6.5, va="center",
                fontfamily="monospace", clip_on=True)

# Legend
legend_y = row_y - 0.52
for label, color in [("High confidence", GREEN), ("Medium confidence", ORANGE),
                     ("Low / Ambiguous", CORAL)]:
    ax.add_patch(mpatches.Circle((x_starts[0] + 0.08, legend_y), 0.07,
                                  color=color, zorder=3))
    ax.text(x_starts[0] + 0.22, legend_y, label,
            color=TEXT_SEC, fontsize=6, va="center", fontfamily="monospace")
    x_starts[0] += 1.6

ax.set_xlim(0, total_w)
ax.set_ylim(legend_y - 0.4, fig_height)
plt.tight_layout(pad=0.1)
plt.close('all')

print(f"\nMapping report rendered: {len(approved_map)} auto-approved, {len(pending_map)} pending review.")
