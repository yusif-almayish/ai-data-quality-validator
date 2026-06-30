import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import to_rgba

# ── Inputs from upstream ─────────────────────────────────────────
# ai_mapping_df inherited

# ── Approve / pend mappings ──────────────────────────────────────
approved_map = {}
pending_map  = {}
for _, row in ai_mapping_df.iterrows():
    if row["Analyst Review"] == "Not required":
        approved_map[row["JSON Field"]] = row["SQL Column"]
    else:
        pending_map[row["JSON Field"]]  = row["SQL Column"]

field_map = approved_map.copy()

# ── Zerve palette ────────────────────────────────────────────────
BG       = "#1D1D20"
TEXT_PRI = "#fbfbff"
TEXT_SEC = "#909094"
GREEN    = "#8DE5A1"
ORANGE   = "#FFB482"
CORAL    = "#FF9F9B"
LAVENDER = "#D0BBFF"
BLUE     = "#A1C9F4"

def conf_color(label):
    return {"High": GREEN, "Medium": ORANGE, "Low": CORAL}.get(label, TEXT_SEC)

def ambig_color(is_ambig):
    return CORAL if is_ambig else GREEN

# ── Build display DataFrame ──────────────────────────────────────
display_df = ai_mapping_df[[
    "JSON Field","SQL Column","Confidence","Confidence Label","Ambiguous","Analyst Review","Reasoning"
]].copy()
display_df["Confidence"] = display_df["Confidence"].apply(lambda x: f"{x:.2f}")
display_df["Ambiguous"]  = display_df["Ambiguous"].apply(lambda x: "⚠  Yes" if x else "✓  No")

# ── Render table ─────────────────────────────────────────────────
n_rows      = len(display_df)
col_widths  = [2.4, 2.4, 1.4, 1.5, 1.4, 2.0, 5.0]
fig_width   = sum(col_widths) + 0.4
fig_height  = 1.0 + n_rows * 0.52 + 0.4

mapping_report_fig, ax = plt.subplots(figsize=(fig_width, fig_height))
mapping_report_fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)
ax.axis("off")

col_labels = ["JSON Field","SQL Column","Conf","Level","Ambiguous","Review","Reasoning"]
n_cols     = len(col_labels)

total_w  = sum(col_widths)
x_starts = [sum(col_widths[:j]) / total_w for j in range(n_cols)]
w        = [cw / total_w for cw in col_widths]

header_y = 1.0 - 0.3 / fig_height

# Header row
for j, label in enumerate(col_labels):
    xs = x_starts[j] + w[j] / 2
    ax.text(xs, header_y, label,
            transform=ax.transAxes,
            ha="center", va="center",
            fontsize=9, fontweight="bold",
            color=BLUE, fontfamily="monospace")

# Divider line under header
ax.plot([0, 1], [header_y - 0.025, header_y - 0.025],
        color=TEXT_SEC, linewidth=0.6, transform=ax.transAxes)

row_h = 0.52 / fig_height

for i, (_, data_row) in enumerate(display_df.iterrows()):
    row_y   = header_y - 0.06 - i * row_h - row_h / 2
    row_bg  = "#26262A" if i % 2 == 0 else BG

    rect = mpatches.FancyBboxPatch(
        (0.0, row_y - row_h * 0.45), 1.0, row_h * 0.90,
        boxstyle="square,pad=0", linewidth=0,
        facecolor=row_bg, transform=ax.transAxes, clip_on=False
    )
    ax.add_patch(rect)

    vals = [
        data_row["JSON Field"],
        data_row["SQL Column"],
        data_row["Confidence"],
        data_row["Confidence Label"],
        data_row["Ambiguous"],
        data_row["Analyst Review"],
        data_row["Reasoning"],
    ]

    for j, val in enumerate(vals):
        xs = x_starts[j] + w[j] / 2
        if j == 3:
            text_color = conf_color(val)
        elif j == 4:
            text_color = CORAL if "⚠" in str(val) else GREEN
        elif j == 5:
            text_color = ORANGE if "Required" in str(val) else TEXT_SEC
        elif j in (0, 1):
            text_color = TEXT_PRI
        else:
            text_color = TEXT_SEC

        ax.text(xs, row_y, str(val),
                transform=ax.transAxes,
                ha="center" if j not in (0, 1, 6) else "left",
                va="center",
                fontsize=8,
                color=text_color,
                fontfamily="monospace")

# Legend
legend_y = 0.015
legend_items = [
    (GREEN, "High confidence — Auto-approved"),
    (ORANGE, "Medium confidence — Analyst review"),
    (CORAL, "Low / Ambiguous — Analyst review"),
]
lx = 0.01
for color, label in legend_items:
    patch = mpatches.Patch(facecolor=color, label=label)
    ax.text(lx, legend_y, "■", transform=ax.transAxes, fontsize=10, color=color, va="center")
    ax.text(lx + 0.025, legend_y, label, transform=ax.transAxes, fontsize=7.5, color=TEXT_SEC, va="center")
    lx += 0.32

ax.set_title("AI Schema Mapping Report — Vendor → Enterprise SQL",
             fontsize=11, fontweight="bold", color=TEXT_PRI, pad=10,
             fontfamily="monospace")

plt.tight_layout(pad=0.3)
plt.close('all')

print(f"Approved field_map ({len(approved_map)} fields):")
for k, v in approved_map.items():
    print(f"  {k:<26} →  {v}")
if pending_map:
    print(f"\nPending analyst review ({len(pending_map)} fields):")
    for k, v in pending_map.items():
        print(f"  {k:<26} →  {v}  ⚠")
