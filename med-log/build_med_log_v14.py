"""Medication Log v14 — Md and Pg shifted 4 hours earlier per Michael's
instruction (Aug 8 2026): Md now 4am/noon/8pm (was 8am/4pm/midnight),
Pg now 4am/4pm (was 8am/8pm). Av column cleared to blank.
Base geometry replicated from approved v13 (fetched from GitHub)."""
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

W, H = letter  # 612 x 792
MARGIN = 36.0
TBL_L, TBL_R = 36.0, 576.0
TBL_TOP_Y = 792 - 66.0     # top of table (pdf coords, y up)
TBL_BOT_Y = 792 - 687.0
HR_W = 32.0
ROW_H = 24.5
N_ROWS = 24
DAY_HDR_H = 18.0   # 66 -> 84
MED_HDR_H = 15.0   # 84 -> 99
GRID_TOP_Y = 792 - 99.0  # top of hour rows

# Lightened greys (v12: shade DFDFDF, lines 0.60 grey)
SHADE = (0.925, 0.925, 0.925)      # ECECEC
GRID_GREY = 0.78                    # was 0.60

MEDS = ["Pa", "Md", "H", "Pg", "Av"]
# Shaded rows per med (1-indexed hour rows; 4=4am, 8=8am, 12=noon, 16=4pm, 20=8pm, 24=midnight)
SHADED = {
    "Pa": [],
    "Md": [4, 12, 20],   # shifted 4h earlier: was 8am/4pm/midnight -> 4am/noon/8pm
    "H":  [4, 8, 12, 16, 20, 24],
    "Pg": [4, 16],       # shifted 4h earlier: was 8am/8pm -> 4am/4pm
    "Av": [],            # cleared per Michael's instruction (Aug 8 2026)
}
HOURS = [str(i) for i in range(1, 12)] + ["Noon"] + [str(i) for i in range(1, 12)] + ["12"]
LEGEND = ("Pa = Pain   Md = Methadone (8h)   H = Hydromorphone (4h)   "
          "Pg = Pregabalin (12h)   Av = Advil (8h)   Grey = scheduled dose time")


def day_columns(n_days):
    """Return per-day med column x-offsets and widths.
    Existing 4 columns narrowed 25%; Av takes the freed space (original width)."""
    day_w = (TBL_R - TBL_L - 2 * HR_W) / n_days
    w = day_w / 5.0
    return day_w, [w, w, w, w, w]


def draw_page(c, title, days):
    n = len(days)
    day_w, med_ws = day_columns(n)

    # Title
    c.setFont("Helvetica-Bold", 18)
    c.setFillColorRGB(0, 0, 0)
    c.drawCentredString(W / 2, 792 - 37.7 - 18 * 0.75, title)

    # --- shading first (under grid) ---
    c.setFillColorRGB(*SHADE)
    for d in range(n):
        day_x = TBL_L + HR_W + d * day_w
        x = day_x
        for mi, med in enumerate(MEDS):
            w = med_ws[mi]
            for row in SHADED[med]:
                y_top = GRID_TOP_Y - (row - 1) * ROW_H
                c.rect(x, y_top - ROW_H, w, ROW_H, stroke=0, fill=1)
            x += w

    # --- grid lines ---
    # internal grey lines
    c.setStrokeColorRGB(GRID_GREY, GRID_GREY, GRID_GREY)
    c.setLineWidth(0.5)
    # horizontal row lines (between hour rows, not table borders)
    for r in range(1, N_ROWS):
        y = GRID_TOP_Y - r * ROW_H
        c.line(TBL_L, y, TBL_R, y)
    # vertical med-column lines within each day (grey)
    for d in range(n):
        day_x = TBL_L + HR_W + d * day_w
        x = day_x
        for w in med_ws[:-1]:
            x += w
            c.line(x, TBL_BOT_Y, x, GRID_TOP_Y + MED_HDR_H)

    # black structural lines
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1)
    c.rect(TBL_L, TBL_BOT_Y, TBL_R - TBL_L, TBL_TOP_Y - TBL_BOT_Y, stroke=1, fill=0)
    # day separators + Hr column separators (full height)
    for d in range(n + 1):
        x = TBL_L + HR_W + d * day_w
        c.line(x, TBL_BOT_Y, x, TBL_TOP_Y)
    # header separators
    c.line(TBL_L, TBL_TOP_Y - DAY_HDR_H, TBL_R, TBL_TOP_Y - DAY_HDR_H)
    c.line(TBL_L, GRID_TOP_Y, TBL_R, GRID_TOP_Y)
    # Noon emphasis line (mid-table) — grey in v12? keep grey
    # (v12 had no special noon line; skip)

    # --- header text ---
    c.setFillColorRGB(0, 0, 0)  # reset after shading fill
    # "Hr" headers span both header bands, centered
    c.setFont("Helvetica-Bold", 11)
    hdr_mid_y = TBL_TOP_Y - (DAY_HDR_H + MED_HDR_H) / 2 - 4
    c.drawCentredString(TBL_L + HR_W / 2, hdr_mid_y, "Hr")
    c.drawCentredString(TBL_R - HR_W / 2, hdr_mid_y, "Hr")
    # day names
    c.setFont("Helvetica-Bold", 13)
    for d, name in enumerate(days):
        cx = TBL_L + HR_W + d * day_w + day_w / 2
        c.drawCentredString(cx, TBL_TOP_Y - DAY_HDR_H + 4.5, name)
    # med abbreviations
    c.setFont("Helvetica-Bold", 11)
    for d in range(n):
        x = TBL_L + HR_W + d * day_w
        for mi, med in enumerate(MEDS):
            w = med_ws[mi]
            c.drawCentredString(x + w / 2, GRID_TOP_Y + 3.5, med)
            x += w

    # --- hour labels (both Hr columns) ---
    c.setFont("Helvetica-Bold", 10)
    for r, label in enumerate(HOURS):
        y = GRID_TOP_Y - r * ROW_H - ROW_H / 2 - 3.5
        c.drawCentredString(TBL_L + HR_W / 2, y, label)
        c.drawCentredString(TBL_R - HR_W / 2, y, label)

    # --- legend ---
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(W / 2, TBL_BOT_Y - 14, LEGEND)


c = canvas.Canvas("/mnt/user-data/outputs/Medication_Log_v14.pdf", pagesize=letter)
draw_page(c, "Medication Log — Mon–Thu", ["Monday", "Tuesday", "Wednesday", "Thursday"])
c.showPage()
draw_page(c, "Medication Log — Fri–Sun", ["Friday", "Saturday", "Sunday"])
c.showPage()
c.save()
print("built")
