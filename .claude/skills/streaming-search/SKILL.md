---
name: streaming-search
description: Find which streaming platforms in Thailand offer a movie, series, or anime the user names, with viewing type, package, season/part, status, links, and sources, then build the Excel report. Use when the user asks "Where can I watch X?" or an equivalent question.
---

# Skill: streaming-search

## Input
One or more titles from the user (optionally with type / year / season). Thai or English titles are both accepted.

| ประเภท | ชื่อเรื่อง |
|---|---|
| Movie | Avengers: Endgame |
| Series | Stranger Things |
| Anime | Attack on Titan |
| Anime | One Piece |

---

## Step 0 — Load memory
1. `memory/MEMORY.md`, `user-preferences.md`, `thai-platforms.md`, and `lessons.md` are already imported by CLAUDE.md.
2. Open `memory/search-log.md` and check for a previous search of this title. Use it only as a **hint for where to look first**. Always re-verify.

## Step 1 — Identify the title (disambiguation)
Check whether each title has multiple versions. If so → **stop and ask the user** before searching. Do not create the Excel file yet.

Cases that require asking:
- **One Piece** → anime (1999–) / live-action series / anime movies (several)
- **Attack on Titan** → TV anime / live-action movie / anime movie (The Last Attack)
- **Spider-Man** → several different film series (Tobey Maguire / Andrew Garfield / Tom Holland / Spider-Verse)
- Titles shared with remakes or foreign versions (e.g. Korean original vs. Thai remake)

No need to ask when: the user already gave the type/year/edition, or the title clearly has a single version (e.g. Avengers: Endgame).

**Do not ask — movie series without a part:** e.g. `Harry Potter`, `The Lord of the Rings`.
1. List the films of the main movie series in release order and number them, e.g. for Harry Potter:
   ภาค 1 Philosopher's Stone (2001), ภาค 2 Chamber of Secrets (2002), ภาค 3 Prisoner of Azkaban (2004),
   ภาค 4 Goblet of Fire (2005), ภาค 5 Order of the Phoenix (2007), ภาค 6 Half-Blood Prince (2009),
   ภาค 7 Deathly Hallows – Part 1 (2010), ภาค 8 Deathly Hallows – Part 2 (2011).
2. Use these numbers in `Season / Part` and put the list in `notes`, one item per part.
3. Other versions (e.g. a TV series) go in `notes` only; do not add rows for them.

Once clear, record: official English title, Thai title (if any), Japanese/romaji title (for anime), year, type.
→ Search using every name, because Thai platforms often list titles under their Thai or localized names.

## Step 2 — Search
Source reliability, highest first:

1. **The platform's official title page (Thailand region)**
2. **JustWatch Thailand** (`justwatch.com/th`): aggregator split by Stream / Rent / Buy / Free
3. **Official announcements** from the platform or the Thai license holder
4. **Reputable news outlets**: supporting evidence only

Suggested queries (run several, one per query):
- `"<title>" JustWatch Thailand`
- `"<title>" where to watch Thailand`
- `"<Thai title>" <platform name>`
- `"<title>" site:<platform domain>`
- `รับชม "<Thai title>"` (finds platform title pages in Thai, e.g. Disney+ / HBO Max)
- For anime, add: `Thai license`, `Thai subtitles`, `Thai dub`

Check every platform in `memory/thai-platforms.md`. A platform that was not checked must never be reported as `ไม่มี`.

## Step 3 — Verify
For each platform:
- **Open the actual page** (WebFetch / browser). Do not rely on search snippets alone.
- Confirm it is the **Thailand region** (URL contains `/th`, prices in THB, or the page states the country).
- A "not available in your country" message refers to **your own location**, not Thailand. It is not evidence for Thailand.
- Confirm it is the **same title/version** (year, type, director/studio).
- If two sources conflict → favor the official page; if still unclear, mark `ไม่พบข้อมูล` and explain the conflict in `notes`.
- If a platform page requires login → never log in on the user's behalf; use another source or mark `ไม่พบข้อมูล`.
- For a movie series, check each film on each platform. A part that is not confirmed is left out of the list, never guessed.
- Keep the URL of each title page you find: it becomes the watch link (Step 4).

## Step 4 — Extract details
Per platform, collect:

| Field | Rule |
|---|---|
| Streaming Platform | Official name of a real platform found in this search |
| Season / Part | Only what is **shown on the actual page**, e.g. `Season 1–3`, `The Final Season Part 1–2` · single movie or status not `มี` → `–` · movie series → only the parts on that platform, e.g. `ภาค 1–3`, `ภาค 2–7`, `ภาค 1–3, 5` |
| รูปแบบการรับชม | `Subscription` / `Rent` / `Buy` / `Free`, joined with ` / ` · package in brackets: `Subscription (Premium)` · unknown package → `Subscription (ไม่พบข้อมูลแพ็กเกจ)` |
| ลิงก์ | The platform's **own page for that title** (play / rent / buy). Never an aggregator, search, or category page. None found → `–` |
| Source + time | Source used to verify + timestamp (UTC+7) |
| สถานะในไทย | `มี` / `ไม่มี` / `ไม่พบข้อมูล` |

## Step 5 — Decide the status
```
Title page found on the platform, Thailand region             → มี
Listed on JustWatch Thailand + no conflicting evidence        → มี (cite JustWatch; link stays – unless a title page is found)
Checked platform/JustWatch Thailand, not in the catalog       → ไม่มี
Nothing found / page could not be opened                      → ไม่พบข้อมูล
Conflicting data / other region / data older than 30 days     → ไม่พบข้อมูล (explain in notes)
```

## Step 6 — Pick the recommended platform
One per title (set `"recommended": true` on that row). It is written in the Summary sheet; the table row is **not** highlighted.
Among `มี` rows, pick the first match:
1. A platform the user already has (from `user-preferences.md`) with the most seasons/parts
2. `Free` with the most seasons/parts
3. `Subscription` with the most seasons/parts
4. `Rent / Buy`

If no row is `มี`, there is no recommendation.

**Row order in the table:** recommended → other `มี` (Free → Subscription → Rent/Buy) → `ไม่พบข้อมูล` → `ไม่มี` (major platforms only).

## Step 7 — Save the results as JSON
Write the verified results to `output/results_YYYY-MM-DD_HHMM.json`. This JSON is the single source for both the chat answer and the Excel file, so they always match.

```json
{
  "checked_at": "2026-11-05 13:00",
  "titles": [
    {
      "title": "Spider-Man (Tom Holland, MCU)",
      "type": "Movie",
      "year": "2017–2026",
      "rows": [
        {"platform": "Disney+", "season": "ภาค 1–3", "viewing_type": "Subscription (ไม่พบข้อมูลแพ็กเกจ)",
         "status": "มี", "recommended": true,
         "links": [{"part": "ภาค 1", "url": "https://www.disneyplus.com/th-th/browse/entity-..."},
                   {"part": "ภาค 2", "url": "https://www.disneyplus.com/th-th/browse/entity-..."},
                   {"part": "ภาค 3", "url": "https://www.disneyplus.com/th-th/browse/entity-..."}]},
        {"platform": "Netflix", "season": "–", "viewing_type": "–", "status": "ไม่พบข้อมูล", "link": null}
      ],
      "recommendation_reason": "Subscription with the most parts",
      "notes": [
        "ภาค 1 = Spider-Man: Homecoming (2017)",
        "ภาค 2 = Spider-Man: Far From Home (2019)",
        "ภาค 3 = Spider-Man: No Way Home (2021)",
        "Netflix: Thailand availability could not be confirmed (check ran from outside Thailand)"
      ]
    }
  ],
  "sources": [
    {"name": "Disney+ TH — Spider-Man movies", "url": "https://...", "checked_at": "2026-11-05 13:00"}
  ]
}
```
- `checked_at` uses `YYYY-MM-DD HH:MM` in Thailand time (UTC+7).
- `status` must be `มี`, `ไม่มี`, or `ไม่พบข้อมูล` exactly. The script stops with an error otherwise.
- Use `link` for a single title page, or `links` (one item per part) for a movie series. The table links to the first one;
  the Summary sheet lists every part under "Watch links". Use `null` / omit when there is no title page.
- The script stops with an error if a link points to an aggregator (JustWatch, wheretowatch, TMDB) — put those in `sources` only.
- `notes` is a list: one item per point (one per part, one per platform note). Each item becomes its own bullet row.
- Do not write a summary sentence in the JSON. The script builds the "สรุป" sentence from the rows, so it always matches the table.

## Step 8 — Build the Excel file
1. If `output/build_excel.py` does not exist, create it with **exactly** the code below. Do not rewrite or "improve" it, so every report has the same format.
2. Install the library if needed: `pip install openpyxl`
3. Run: `python output/build_excel.py output/results_YYYY-MM-DD_HHMM.json`
4. The script prints the file path, e.g. `output/Harry_Potter_Streaming_Platform_2026-11-05.xlsx`.

What the script does (maps to the Excel criteria in CLAUDE.md):

| Criterion | How |
|---|---|
| 1. Dark blue header, frozen | Header fill `1F3864`, white bold text, freeze panes at `A2` |
| 2. Widths and heights fit | On both sheets, every time: column width from the longest text (Thai vowel/tone marks not counted, max 60 on Results / 80 on Summary), wrap text, and row height from the number of wrapped lines |
| 3. Number formats | Check time `yyyy-mm-dd hh:mm` |
| 4. Status colors | Light fill + bold dark text of the same color: `มี` green, `ไม่มี` red, `ไม่พบข้อมูล` gray |
| 5. Hyperlinks | `ลิงก์` column opens the title's watch page; Watch links and source URLs are clickable; aggregator links are rejected |
| 6. Recommendation | No row highlight; `Recommended` row on the Summary sheet |
| 7. Summary | "สรุป" box under the table on `Results` (platform names in bold) + `Summary` sheet: check time, summary, recommendation, Notes (one bullet per row), Watch links (one row per part), sources |
| 8. File name | `[ชื่อหนัง]_Streaming_Platform_YYYY-MM-DD.xlsx` (spaces → `_`, invalid characters removed, `_HHMM` added if the file exists) |

```python
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
                      row.get("viewing_type") or "–", status, None]
            for i, v in enumerate(values, 1):
                c = ws.cell(row=r, column=i, value=v)
                c.alignment, c.border = WRAP, BORDER
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
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True

    # Summary box ("สรุป") under the table, one per title
    r += 1
    for t in data["titles"]:
        label = "สรุป" if len(data["titles"]) == 1 else f'สรุป — {t["title"]}'
        summary_box(ws, r, label, summary_parts(t, checked))
        r += 3

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
```

## Step 9 — Answer in chat
Show the same data as the JSON, in the chat format from CLAUDE.md:
1. The table with the 7 exact column headers
2. **สรุป**: the same sentence the script writes in the Excel summary box, with platform names in bold:
   - `เรื่องนี้สามารถรับชมได้บน **A** (Subscription) และ **B** (Free) ในประเทศไทย และสามารถเช่าหรือซื้อผ่าน **C** (ตรวจสอบเมื่อ YYYY-MM-DD HH:MM น.)`
   - Only Rent/Buy: `เรื่องนี้ไม่มีให้รับชมแบบ Subscription หรือ Free ในประเทศไทย แต่สามารถเช่าหรือซื้อผ่าน **C** (ตรวจสอบเมื่อ ...)`
   - Nothing: `ตรวจสอบแล้ว ไม่พบ Platform ที่ให้บริการเรื่องนี้ในประเทศไทย (ตรวจสอบเมื่อ ...)`
3. **Sources** with check times
4. **Notes** as bullet points, one per line (same items as `notes` in the JSON)
5. **Excel file:** the path printed by the script

If no platform in Thailand offers the title, use the "Nothing" sentence above and list the sources checked.

## Step 10 — Update memory
- Add one entry to `memory/search-log.md` (format is in the file). Keep the 50 most recent entries.
- New legal Thai platform found that is not on the list → add it to `thai-platforms.md` with the date.
- User states which platforms they subscribe to → record it in `user-preferences.md`.
- A mistake happened or the user corrected an answer → record it in `lessons.md`.

---

## Example 1 — ambiguous title (ask first)

**User:** Where can I watch Attack on Titan?

**Agent (Step 1):** "Attack on Titan" has several versions. Which one do you mean?
1) TV anime (2013–2023) 2) Live-action movie (2015) 3) Anime movie: The Last Attack

## Example 2 — movie series (from a real search on 2026-11-05; re-check before reuse)

**User:** Spider-Man → asked back → **User:** Tom Holland (MCU)

**Agent (Step 9):**

| ชื่อเรื่อง | ประเภท | Streaming Platform | Season / Part | รูปแบบการรับชม | สถานะในไทย | ลิงก์ |
|---|---|---|---|---|---|---|
| Spider-Man (Tom Holland, MCU) | Movie | Disney+ | ภาค 1–3 | Subscription (ไม่พบข้อมูลแพ็กเกจ) | มี | [ลิงก์](https://www.disneyplus.com/th-th/browse/entity-d285316b-e1ea-4b50-933a-bb5fd13549c1) |
| Spider-Man (Tom Holland, MCU) | Movie | Prime Video (Amazon Video) | ภาค 4 | Rent / Buy | มี | [ลิงก์](https://www.primevideo.com/-/th/detail/0MH84EJKE2M4I598UISANJRS1X) |
| Spider-Man (Tom Holland, MCU) | Movie | Apple TV | ภาค 4 | Rent / Buy | มี | – |
| Spider-Man (Tom Holland, MCU) | Movie | Netflix | – | – | ไม่พบข้อมูล | – |

**สรุป:** เรื่องนี้สามารถรับชมได้บน **Disney+** (Subscription) ในประเทศไทย และสามารถเช่าหรือซื้อผ่าน **Prime Video (Amazon Video)** และ **Apple TV** (ตรวจสอบเมื่อ 2026-11-05 13:00 น.)

**Notes:**
- ภาค 1 = Spider-Man: Homecoming (2017)
- ภาค 2 = Spider-Man: Far From Home (2019)
- ภาค 3 = Spider-Man: No Way Home (2021)
- ภาค 4 = Spider-Man: Brand New Day (2026)
- Apple TV: listed by JustWatch for Thailand, but no title page link was found, so the link is –
- Netflix: Thailand availability could not be confirmed (check ran from outside Thailand)

**Excel file:** `output/Spider-Man_Tom_Holland_MCU_Streaming_Platform_2026-11-05.xlsx`

---

## Checklist before answering
- [ ] Title/version is clear (asked back if ambiguous; movie series without a part → searched all parts)
- [ ] Every row comes from this session's online search, not from memory or model knowledge
- [ ] Every platform name is a real platform found in this search (no placeholders)
- [ ] Every row is Thailand-region data
- [ ] Only the three statuses are used: `มี` / `ไม่มี` / `ไม่พบข้อมูล`
- [ ] No guessed seasons, parts, packages, or prices
- [ ] Every `ลิงก์` opens the platform's page for that title (not an aggregator, search, or category page)
- [ ] Movie series: parts listed per platform, part list in Notes, every part in Watch links
- [ ] Notes written as a list (one bullet per row in Excel)
- [ ] One recommended platform per title in the Summary sheet (or `–` if nothing is `มี`); no row highlight
- [ ] Chat table and Excel file show the same data
- [ ] Excel built with the script above; file named `[ชื่อหนัง]_Streaming_Platform_YYYY-MM-DD.xlsx`
- [ ] Sources and check time included
- [ ] Memory updated
