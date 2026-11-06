import json, os, re, sys, unicodedata
from datetime import datetime
from openpyxl import Workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

HEADERS = ["ชื่อเรื่อง", "ประเภท", "Streaming Platform", "Season / Part",
           "รูปแบบการรับชม", "สถานะในไทย", "ลิงก์"]
STATUS_FILL = {                      # (light background, dark bold text of the same color)
    "มี": ("C6EFCE", "006100"),                 # green
    "ไม่มี": ("FFC7CE", "9C0006"),               # red
    "ไม่พบข้อมูล": ("E7E6E6", "3A3838"),          # gray
}
# Watch links must open the title's own page on the platform, never an aggregator or search page
NOT_WATCH_PAGES = ("justwatch.", "wheretowatch.", "themoviedb.", "letsfindmovie.", "google.com/search")


def check_watch_link(url, platform):
    if url and any(d in url for d in NOT_WATCH_PAGES):
        raise ValueError(f"{platform}: link must be the platform's title page, not {url}")
    return url

HEADER_FILL = PatternFill("solid", fgColor="1F3864")   # dark blue
HEADER_FONT = Font(bold=True, color="FFFFFF")
LINK_FONT = Font(color="0563C1", underline="single")
RECOMMEND_FILL = PatternFill("solid", fgColor="E2EFDA")   # light green: recommended platform cell
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(vertical="top", wrap_text=True)


def text_width(value):
    """Visible width: Thai vowel/tone marks (combining) take no space."""
    s = "" if value is None else str(value)
    return sum(0 if unicodedata.combining(c) or unicodedata.category(c) == "Mn" else 1 for c in s)


def merged_cells(ws):
    return {(r, c) for rng in ws.merged_cells.ranges
            for r in range(rng.min_row, rng.max_row + 1) for c in range(rng.min_col, rng.max_col + 1)}


def fit_columns(ws, min_w=8, max_w=60):
    """Width: fit the longest text in each column (merged cells are skipped)."""
    skip, widths = merged_cells(ws), {}
    for row in ws.iter_rows():
        for c in row:
            if (c.row, c.column) in skip:
                continue
            w = max((text_width(line) for line in str(c.value or "").split("\n")), default=0)
            widths[c.column_letter] = max(widths.get(c.column_letter, 0), w)
    for col, w in widths.items():
        ws.column_dimensions[col].width = max(min_w, min(max_w, w * 1.15 + 3))


def fit_rows(ws, line_h=17, pad=6):
    """Height: enough lines for wrapped text in every cell (merged cells are skipped)."""
    skip = merged_cells(ws)
    for row in ws.iter_rows():
        lines = 1
        for c in row:
            if (c.row, c.column) in skip or c.value is None:
                continue
            col_w = ws.column_dimensions[c.column_letter].width or 10
            usable = max(1, col_w - 2)
            n = sum(max(1, -(-int(text_width(t)) // int(usable))) for t in str(c.value).split("\n"))
            lines = max(lines, n)
        ws.row_dimensions[row[0].row].height = line_h * lines + pad


def header_row(ws, row, values):
    for i, v in enumerate(values, 1):
        c = ws.cell(row=row, column=i, value=v)
        c.fill, c.font, c.border = HEADER_FILL, HEADER_FONT, BORDER
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def join_th(items):
    """['A','B','C'] -> A, B และ C (as (text, bold) parts, platform names bold)."""
    parts = []
    for i, (name, kind) in enumerate(items):
        if i:
            parts.append((" และ " if i == len(items) - 1 else ", ", False))
        parts.append((name, True))
        if kind:
            parts.append((f" ({kind})", False))
    return parts


def summary_parts(t, checked):
    """Build the Thai summary sentence from the table rows, as (text, bold) parts."""
    watch, rent = {}, []
    for row in t["rows"]:
        if row["status"] != "มี":
            continue
        kinds = [k.strip().split(" (")[0] for k in (row.get("viewing_type") or "").split("/")]
        stream = [k for k in kinds if k in ("Subscription", "Free")]
        if stream:
            watch.setdefault(row["platform"], [])
            watch[row["platform"]] += [k for k in stream if k not in watch[row["platform"]]]
        if any(k in ("Rent", "Buy") for k in kinds) and row["platform"] not in rent:
            rent.append(row["platform"])
    when = f" (ตรวจสอบเมื่อ {checked:%Y-%m-%d %H:%M} น.)"
    if not watch and not rent:
        return [("ตรวจสอบแล้ว ไม่พบ Platform ที่ให้บริการเรื่องนี้ในประเทศไทย" + when, False)]
    parts = []
    if watch:
        parts += [("เรื่องนี้สามารถรับชมได้บน ", False)]
        parts += join_th([(p, " / ".join(k)) for p, k in watch.items()])
        parts += [(" ในประเทศไทย", False)]
        if rent:
            parts += [(" และสามารถเช่าหรือซื้อผ่าน ", False)] + join_th([(p, "") for p in rent])
    else:
        parts += [("เรื่องนี้ไม่มีให้รับชมแบบ Subscription หรือ Free ในประเทศไทย แต่สามารถเช่าหรือซื้อผ่าน ", False)]
        parts += join_th([(p, "") for p in rent])
    return parts + [(when, False)]


def summary_box(ws, top, label, parts, ncols=7):
    """Two-row box under the table: blue 'สรุป' label row + summary text row."""
    box_side = Side(style="thin", color="B4C6E7")
    for row in (top, top + 1):
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=ncols)
        for col in range(1, ncols + 1):
            ws.cell(row=row, column=col).border = Border(
                left=box_side if col == 1 else None, right=box_side if col == ncols else None,
                top=box_side if row == top else None, bottom=box_side if row == top + 1 else None)
    h = ws.cell(row=top, column=1, value=label)
    h.font = Font(bold=True, size=12, color="2F5597")
    h.fill = PatternFill("solid", fgColor="EEF3FB")
    h.alignment = Alignment(vertical="center", indent=1)
    ws.row_dimensions[top].height = 24
    rich = CellRichText([TextBlock(InlineFont(b=bold), text) for text, bold in parts])
    c = ws.cell(row=top + 1, column=1, value=rich)
    c.alignment = Alignment(vertical="center", wrap_text=True, indent=1)
    total_w = sum(ws.column_dimensions[get_column_letter(i)].width or 10 for i in range(1, ncols + 1))
    lines = max(1, -(-text_width("".join(p for p, _ in parts)) * 1.1 // total_w))
    ws.row_dimensions[top + 1].height = 18 * lines + 14


def viewing_text(row):
    """รูปแบบการรับชม: adds the package name and price to Subscription, e.g. Subscription (Standard 1,390 บาท/ปี ขึ้นไป)."""
    base = row.get("viewing_type") or "–"
    if "Subscription" not in base or "(" in base:
        return base
    pkg = row.get("package")
    if pkg and pkg.get("name") and pkg.get("price") is not None:
        text = f'{pkg["name"]} {pkg["price"]:,.0f} บาท/{pkg.get("per", "เดือน")}'
        text += " ขึ้นไป" if pkg.get("or_higher") else ""
    elif pkg and pkg.get("name"):
        text = f'{pkg["name"]}, ไม่พบข้อมูลราคา'
    else:
        text = "ไม่พบข้อมูลแพ็กเกจ"
    return base.replace("Subscription", f"Subscription ({text})", 1)


def not_found_note(ws, top, rows, ncols=7):
    """'Note:' box under the summary: explains every ไม่พบข้อมูล row, one bullet per row. Returns rows used."""
    missing = [x for x in rows if x["status"] == "ไม่พบข้อมูล"]
    if not missing:
        return 0
    for x in missing:
        if not x.get("reason"):
            raise ValueError(f'{x["platform"]}: a ไม่พบข้อมูล row needs a "reason"')
    lines = [("Note:", True), ("ไม่พบข้อมูล คือ ระบบค้นหาแล้วไม่เจอข้อมูล เนื่องจาก", False)]
    lines += [(f'• {x["platform"]}: {x["reason"]}', False) for x in missing]
    side = Side(style="thin", color="BFBFBF")
    total_w = sum(ws.column_dimensions[get_column_letter(i)].width or 10 for i in range(1, ncols + 1))
    for i, (text, bold) in enumerate(lines):
        row = top + i
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=ncols)
        for col in range(1, ncols + 1):
            ws.cell(row=row, column=col).border = Border(
                left=side if col == 1 else None, right=side if col == ncols else None,
                top=side if i == 0 else None, bottom=side if i == len(lines) - 1 else None)
        c = ws.cell(row=row, column=1, value=text)
        c.font = Font(bold=bold, color="3A3838")
        c.fill = PatternFill("solid", fgColor="F2F2F2")
        c.alignment = Alignment(vertical="center", wrap_text=True, indent=1)
        n = max(1, -(-int(text_width(text) * 1.1) // int(total_w)))
        ws.row_dimensions[row].height = 17 * n + 6
    return len(lines)


def file_title(titles):
    """[ชื่อหนัง] part of the file name: spaces → _, characters Windows does not allow are removed."""
    name = titles[0]["title"] if len(titles) == 1 else f'{titles[0]["title"]}_and_{len(titles) - 1}_more'
    name = re.sub(r'[\\/:*?"<>|(),]', "", name)
    name = re.sub(r"\s+", "_", name.strip())
    return name[:80] or "Untitled"


def build(json_path):
    data = json.load(open(json_path, encoding="utf-8"))
    checked = datetime.strptime(data["checked_at"], "%Y-%m-%d %H:%M")
    wb = Workbook()

    # ---- Sheet 1: Results ----
    ws = wb.active
    ws.title = "Results"
    header_row(ws, 1, HEADERS)
    ws.freeze_panes = "A2"
    r = 2
    for t in data["titles"]:
        for row in t["rows"]:
            status = row["status"]
            if status not in STATUS_FILL:
                raise ValueError(f"Invalid status: {status}")
            values = [t["title"], t["type"], row["platform"], row.get("season") or "–",
                      viewing_text(row), status, None]
            for i, v in enumerate(values, 1):
                c = ws.cell(row=r, column=i, value=v)
                c.alignment, c.border = WRAP, BORDER
            if row.get("recommended") and status == "มี":     # recommended: ⭐ name + small "(แนะนำ)" line, light green cell
                pc = ws.cell(row=r, column=3)
                pc.value = CellRichText([TextBlock(InlineFont(b=True), f'⭐ {row["platform"]}'),
                                         TextBlock(InlineFont(sz=9, color="375623"), "\n(แนะนำ)")])
                pc.fill = RECOMMEND_FILL
                pc.alignment = Alignment(vertical="top", wrap_text=True)
            sc = ws.cell(row=r, column=6)
            bg, fg = STATUS_FILL[status]
            sc.fill = PatternFill("solid", fgColor=bg)
            sc.font = Font(bold=True, color=fg)
            sc.alignment = Alignment(horizontal="center", vertical="top")
            lc = ws.cell(row=r, column=7)
            links = row.get("links") or []
            link = check_watch_link(row.get("link") or (links[0]["url"] if links else None), row["platform"])
            for x in links:
                check_watch_link(x["url"], row["platform"])
            if link:
                lc.value, lc.hyperlink, lc.font = "ลิงก์", link, LINK_FONT
            else:
                lc.value = "–"
            r += 1
    fit_columns(ws)
    ws.column_dimensions["G"].width = 10
    fit_rows(ws)
    for rr in range(2, ws.max_row + 1):                  # recommended cell has 2 lines: fixed row height
        if isinstance(ws.cell(row=rr, column=3).value, CellRichText):
            ws.row_dimensions[rr].height = 34
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True

    # Summary box ("สรุป") under the table, one per title
    r += 1
    for t in data["titles"]:
        label = "สรุป" if len(data["titles"]) == 1 else f'สรุป — {t["title"]}'
        summary_box(ws, r, label, summary_parts(t, checked))
        r += 2
        r += not_found_note(ws, r, t["rows"])   # "Note:" box right under the summary, only if there are ไม่พบข้อมูล rows
        r += 1

    # ---- Sheet 2: Summary ----
    sm = wb.create_sheet("Summary")
    sm["A1"] = "Streaming Platform Search — Summary"
    sm["A1"].font = Font(bold=True, size=14, color="1F3864")
    sm.merge_cells("A1:C1")                       # title does not affect column widths

    def info_row(row, label, value, fmt=None):
        a = sm.cell(row=row, column=1, value=label)
        a.font, a.fill, a.border, a.alignment = Font(bold=True, color="1F3864"), PatternFill("solid", fgColor="EEF3FB"), BORDER, WRAP
        b = sm.cell(row=row, column=2, value=value)
        b.border, b.alignment = BORDER, Alignment(horizontal="left", vertical="top", wrap_text=True)
        if fmt:
            b.number_format = fmt

    info_row(3, "Checked at (UTC+7)", checked, "yyyy-mm-dd hh:mm")
    r = 5
    for t in data["titles"]:
        rec = next((x for x in t["rows"] if x.get("recommended") and x["status"] == "มี"), None)
        items = [("ชื่อเรื่อง", f'{t["title"]} ({t["type"]}, {t.get("year", "")})'.replace(", )", ")")),
                 ("สรุป", "".join(p for p, _ in summary_parts(t, checked))),
                 ("Recommended", f'{rec["platform"]} — {t.get("recommendation_reason", "")}' if rec else "–"),
                 ]
        for label, val in items:
            info_row(r, label, val)
            r += 1
        # Notes: one bullet per row, listed downwards (label cell merged down the left)
        notes = t.get("notes") or []
        notes = notes if isinstance(notes, list) else [notes]
        notes = notes or ["None"]
        first = r
        for n in notes:
            info_row(r, "Notes" if r == first else None, f"• {n}" if n != "None" else n)
            r += 1
        if len(notes) > 1:
            sm.merge_cells(start_row=first, start_column=1, end_row=r - 1, end_column=1)
        r += 1
    # Watch links: one row per part, so every part has its own clickable page
    watch = [(t["title"], row["platform"], x["part"], x["url"]) for t in data["titles"]
             for row in t["rows"] if row["status"] == "มี" for x in (row.get("links") or [])]
    if watch:
        sm.cell(row=r, column=1, value="Watch links").font = Font(bold=True, size=12, color="1F3864")
        r += 1
        header_row(sm, r, ["Streaming Platform", "Season / Part", "Watch link"])
        r += 1
        for title, platform, part, url in watch:
            a = sm.cell(row=r, column=1, value=platform)
            a.border, a.alignment = BORDER, WRAP
            b = sm.cell(row=r, column=2, value=part)
            b.border, b.alignment = BORDER, WRAP
            c = sm.cell(row=r, column=3, value=f"ดู {part} บน {platform}")
            c.hyperlink, c.font, c.border, c.alignment = url, LINK_FONT, BORDER, WRAP
            r += 1
        r += 1
    sm.cell(row=r, column=1, value="Sources").font = Font(bold=True, size=12, color="1F3864")
    r += 1
    header_row(sm, r, ["Source", "URL", "Checked at (UTC+7)"])
    r += 1
    for s in data["sources"]:
        n = sm.cell(row=r, column=1, value=s["name"])
        n.border, n.alignment = BORDER, WRAP
        u = sm.cell(row=r, column=2, value=s["url"])
        u.hyperlink, u.font, u.border, u.alignment = s["url"], LINK_FONT, BORDER, WRAP
        d = sm.cell(row=r, column=3, value=datetime.strptime(s["checked_at"], "%Y-%m-%d %H:%M"))
        d.number_format, d.border = "yyyy-mm-dd hh:mm", BORDER
        d.alignment = Alignment(horizontal="left", vertical="top")
        r += 1
    fit_columns(sm, min_w=10, max_w=80)          # width fits the text every time
    sm.column_dimensions["A"].width = min(sm.column_dimensions["A"].width, 40)  # labels/source names wrap past 40
    fit_rows(sm)                                  # height fits wrapped text every time
    sm.row_dimensions[1].height = 26
    sm.page_setup.orientation = "landscape"
    sm.page_setup.fitToWidth, sm.page_setup.fitToHeight = 1, 0
    sm.sheet_properties.pageSetUpPr.fitToPage = True

    # ---- Save with dated file name ----
    os.makedirs("output", exist_ok=True)
    name = file_title(data["titles"])
    out = f'output/{name}_Streaming_Platform_{checked:%Y-%m-%d}.xlsx'
    if os.path.exists(out):
        out = f'output/{name}_Streaming_Platform_{checked:%Y-%m-%d_%H%M}.xlsx'
    wb.save(out)
    print(out)


if __name__ == "__main__":
    build(sys.argv[1])
