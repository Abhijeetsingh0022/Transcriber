"""
Document Exporters for TXT, CSV, JSON, and DOCX formats.
"""

import json
import csv
import io
from typing import Dict, Any, List, Optional
from pathlib import Path
import base64
from engine.exporters.subtitles import format_timestamp_vtt


from engine.exporters.script import group_segments_into_dialogue_turns, format_speaker_name


def get_tmux_logo_path() -> Optional[Path]:
    """Finds the TMUX logo image file across backend assets or frontend public directories."""
    base_dir = Path(__file__).resolve().parents[2]  # backend directory
    candidates = [
        base_dir / "assets" / "tmux-logo.png",
        base_dir.parent / "frontend" / "public" / "tmux-logo.png",
        base_dir / "assets" / "tmux.png",
        base_dir.parent / "frontend" / "public" / "tmux.png",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def get_tmux_logo_base64() -> str:
    """Returns data:image/png;base64,... string for inline standalone HTML exports."""
    logo_path = get_tmux_logo_path()
    if logo_path and logo_path.is_file():
        try:
            with open(logo_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            return f"data:image/png;base64,{b64}"
        except Exception:
            pass
    return ""


def generate_txt(transcript: Dict[str, Any], include_timestamps: bool = True) -> str:
    """Generates plain text transcript with optional speaker and timestamp headers."""
    segments = transcript.get("segments", [])
    speaker_map = {
        s["speaker_label"]: format_speaker_name(s["speaker_label"], s.get("display_name"))
        for s in transcript.get("speakers", [])
    }
    lines = []

    for seg in segments:
        text = seg.get("text", "").strip()
        if not text:
            continue

        if include_timestamps:
            start_str = format_timestamp_vtt(seg["start_time"])
            raw_speaker = seg.get("speaker_label", "SPEAKER_00")
            speaker = speaker_map.get(raw_speaker, format_speaker_name(raw_speaker))
            lines.append(f"[{start_str}] {speaker}: {text}")
        else:
            lines.append(text)

    return "\n\n".join(lines)


import re


def _sanitize_csv_cell(value: Any) -> Any:
    """Neutralizes CSV formula injection (CWE-1236) by prepending a single quote to formula characters."""
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return f"'{value}"
    return value


def _safe_hex_color(hex_str: Optional[str], default: str = "#2563EB") -> str:
    """Validates 6-digit hex color format (#RRGGBB) to prevent invalid ReportLab/XML rendering."""
    if hex_str and isinstance(hex_str, str):
        cleaned = hex_str.strip()
        if re.match(r"^#[0-9a-fA-F]{6}$", cleaned):
            return cleaned
    return default


def generate_csv(segments: List[Dict[str, Any]], speakers: Optional[List[Dict[str, Any]]] = None) -> str:
    """Generates comma-separated values (CSV) string containing tabular timestamps."""
    speaker_map = {
        s["speaker_label"]: format_speaker_name(s["speaker_label"], s.get("display_name"))
        for s in (speakers or [])
    }
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Segment Index", "Start Time (s)", "End Time (s)", "Speaker", "Addressed To", "Intent", "Text"])

    for idx, seg in enumerate(segments):
        raw_speaker = seg.get("speaker_label", "")
        spk_name = speaker_map.get(raw_speaker, format_speaker_name(raw_speaker) if raw_speaker else "")
        writer.writerow([
            idx + 1,
            round(seg["start_time"], 3),
            round(seg["end_time"], 3),
            _sanitize_csv_cell(spk_name),
            _sanitize_csv_cell(seg.get("addressed_to") or ""),
            _sanitize_csv_cell(seg.get("turn_intent") or ""),
            _sanitize_csv_cell(seg.get("text", "").strip())
        ])

    return output.getvalue()


def generate_json(transcript: Dict[str, Any]) -> str:
    """Serializes complete transcript AST into formatted JSON."""
    return json.dumps(transcript, indent=2, ensure_ascii=False)


def hex_to_rgb(hex_str: str):
    """Converts hex color string (#2563EB) to python-docx RGBColor."""
    from docx.shared import RGBColor
    clean = hex_str.lstrip("#")
    if len(clean) == 6:
        try:
            return RGBColor(int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16))
        except ValueError:
            pass
    return RGBColor(37, 99, 235)


def set_cell_background(cell, hex_color: str):
    """Applies solid background color shading to a docx table cell."""
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls
    clean = hex_color.lstrip("#")
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{clean}"/>')
    cell._tc.get_or_add_tcPr().append(shd)


def set_cell_margins(cell, top: int = 120, bottom: int = 120, left: int = 150, right: int = 150):
    """Sets internal cell margins in dxa (1 pt = 20 dxa)."""
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    cell._tc.get_or_add_tcPr().append(tcMar)


def set_table_borders(table, color: str = "E2E8F0"):
    """Applies modern subtle horizontal borders and removes heavy vertical borders."""
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls
    clean = color.lstrip("#")
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="6" w:space="0" w:color="{clean}"/>'
        f'<w:bottom w:val="single" w:sz="6" w:space="0" w:color="{clean}"/>'
        f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="{clean}"/>'
        f'<w:left w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'<w:insideV w:val="none"/>'
        f'</w:tblBorders>'
    )
    table._tbl.tblPr.append(borders)


def set_row_header(row):
    """Marks a table row to repeat as a header on each page break."""
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls
    ns = nsdecls("w")
    trPr = row._tr.get_or_add_trPr()
    trPr.append(parse_xml(f'<w:tblHeader {ns}/>'))
    trPr.append(parse_xml(f'<w:cantSplit {ns}/>'))


def set_row_cant_split(row):
    """Prevents a table row from splitting across a page break."""
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls
    ns = nsdecls("w")
    trPr = row._tr.get_or_add_trPr()
    trPr.append(parse_xml(f'<w:cantSplit {ns}/>'))


def add_page_number_to_run(run):
    """Appends Word PAGE dynamic field to a run."""
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls
    ns = nsdecls("w")
    fld1 = parse_xml(f'<w:fldChar {ns} w:fldCharType="begin"/>')
    instr1 = parse_xml(f'<w:instrText {ns} xml:space="preserve"> PAGE </w:instrText>')
    fld2 = parse_xml(f'<w:fldChar {ns} w:fldCharType="separate"/>')
    fld3 = parse_xml(f'<w:fldChar {ns} w:fldCharType="end"/>')
    run._r.append(fld1)
    run._r.append(instr1)
    run._r.append(fld2)
    run._r.append(fld3)


def add_numpages_to_run(run):
    """Appends Word NUMPAGES dynamic field to a run."""
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls
    ns = nsdecls("w")
    fld1 = parse_xml(f'<w:fldChar {ns} w:fldCharType="begin"/>')
    instr1 = parse_xml(f'<w:instrText {ns} xml:space="preserve"> NUMPAGES </w:instrText>')
    fld2 = parse_xml(f'<w:fldChar {ns} w:fldCharType="separate"/>')
    fld3 = parse_xml(f'<w:fldChar {ns} w:fldCharType="end"/>')
    run._r.append(fld1)
    run._r.append(instr1)
    run._r.append(fld2)
    run._r.append(fld3)


LANGUAGE_MAP = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "hi": "Hindi",
    "ar": "Arabic",
    "nl": "Dutch",
    "tr": "Turkish",
    "pl": "Polish",
    "sv": "Swedish",
    "id": "Indonesian",
    "uk": "Ukrainian",
    "vi": "Vietnamese",
    "th": "Thai",
    "ta": "Tamil",
    "te": "Telugu",
    "bn": "Bengali",
    "mr": "Marathi",
    "ur": "Urdu",
    "gu": "Gujarati",
}


def generate_docx(
    transcript: Dict[str, Any],
    output_path: str,
    job: Optional[Dict[str, Any]] = None
):
    """
    Generates a production-grade executive Microsoft Word transcript document (.docx).
    Features:
      - Executive title banner with recording metadata
      - Key Metrics Overview 2x3 summary card table
      - Speaker Roster & Conversational Share table with talk time, words, and WPM pace
      - Complete 3-Column Dialogue Transcript table (Time Interval, Speaker, Dialogue Content)
      - Alternating row zebra fills, speaker brand colors, monospace timecodes
      - Multi-page repeating headers (w:tblHeader) and row integrity (w:cantSplit)
      - Professional header & footer with dynamic page numbers (Page X of Y)
    """
    try:
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor
        from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from datetime import datetime
        from engine.exporters.script import group_segments_into_dialogue_turns, format_time_code
    except ImportError:
        # Fallback to plain text if python-docx is not installed
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(generate_txt(transcript))
        return

    doc = Document()

    # 1. Page Margins (0.75 in all sides for wide readable 7.0-inch tables)
    section = doc.sections[0]
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(0.75)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)

    # 2. Running Header and Footer
    title = job.get("filename", "Audio/Video Recording") if job else "Transcription Script"

    header_p = section.header.paragraphs[0]
    header_p.paragraph_format.space_after = Pt(4)
    run_hdr = header_p.add_run(f"TMUX Workstation  •  Executive Transcription Report  •  {title}")
    run_hdr.font.size = Pt(8.5)
    run_hdr.font.color.rgb = RGBColor(148, 163, 184)  # Slate-400

    footer_p = section.footer.paragraphs[0]
    footer_p.paragraph_format.space_before = Pt(8)
    run_ftr_l = footer_p.add_run(f"TMUX AI Engine  •  Source File: {title}  •  Confidential  •  Page ")
    run_ftr_l.font.size = Pt(8.5)
    run_ftr_l.font.color.rgb = RGBColor(148, 163, 184)
    add_page_number_to_run(footer_p.add_run())
    run_ftr_mid = footer_p.add_run(" of ")
    run_ftr_mid.font.size = Pt(8.5)
    run_ftr_mid.font.color.rgb = RGBColor(148, 163, 184)
    add_numpages_to_run(footer_p.add_run())

    # 3. Document Title Banner & Logo
    logo_path = get_tmux_logo_path()
    if logo_path:
        logo_p = doc.add_paragraph()
        logo_p.paragraph_format.space_before = Pt(0)
        logo_p.paragraph_format.space_after = Pt(6)
        logo_run = logo_p.add_run()
        logo_run.add_picture(str(logo_path), width=Inches(1.8))

    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(2)
    run_title = title_p.add_run("TRANSCRIPTION SCRIPT & EXECUTIVE REPORT")
    run_title.font.name = "Calibri"
    run_title.font.size = Pt(20)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(15, 23, 42)  # Slate-900

    turns = group_segments_into_dialogue_turns(transcript)
    total_words = transcript.get("word_count") or sum(t.get("word_count", 0) for t in turns)
    raw_lang = (transcript.get("detected_language") or "en").lower()
    lang_full = LANGUAGE_MAP.get(raw_lang, raw_lang.upper())
    lang_display = f"{lang_full} ({raw_lang.upper()})"
    total_duration = turns[-1]["end_time"] if turns else (job.get("duration_seconds") or 0.0)
    duration_str = format_time_code(total_duration, include_hours=True)

    # Prominent Source Media File Callout Card (1 row x 1 col)
    callout_table = doc.add_table(rows=1, cols=1)
    callout_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    callout_table.autofit = False
    set_table_borders(callout_table, "BFDBFE")
    c_cell = callout_table.rows[0].cells[0]
    c_cell.width = Inches(7.0)
    set_cell_background(c_cell, "EFF6FF")
    set_cell_margins(c_cell, top=100, bottom=100, left=140, right=140)

    p_callout = c_cell.paragraphs[0]
    p_callout.paragraph_format.space_after = Pt(2)
    r_c_lbl = p_callout.add_run(f"SOURCE MEDIA FILE: {title}\n")
    r_c_lbl.font.size = Pt(11)
    r_c_lbl.font.bold = True
    r_c_lbl.font.color.rgb = RGBColor(30, 64, 175)  # Blue-800

    r_c_sub = p_callout.add_run(
        f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}  •  "
        f"Duration: {duration_str} ({total_duration:.1f}s)  •  "
        f"Language: {lang_display}  •  "
        f"Local AI Workstation"
    )
    r_c_sub.font.size = Pt(8.5)
    r_c_sub.font.color.rgb = RGBColor(71, 85, 105)  # Slate-600

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # 4. Section 1: Key Metrics Summary Cards Table (2 rows x 3 columns)
    h1 = doc.add_paragraph()
    h1.paragraph_format.space_before = Pt(4)
    h1.paragraph_format.space_after = Pt(4)
    r_h1 = h1.add_run("1. RECORDING OVERVIEW & METRICS")
    r_h1.font.size = Pt(11)
    r_h1.font.bold = True
    r_h1.font.color.rgb = RGBColor(15, 23, 42)

    metrics_table = doc.add_table(rows=2, cols=3)
    metrics_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    metrics_table.autofit = False
    set_table_borders(metrics_table, "CBD5E1")

    avg_pace = int(round(total_words / max(total_duration / 60.0, 0.01))) if total_duration > 0 else 0
    pace_desc = "Normal pace" if avg_pace < 160 else "Fast pace" if avg_pace > 190 else "Conversational"

    # Extract distinct speakers
    speakers = list(transcript.get("speakers") or [])
    if not speakers and turns:
        seen = {}
        for t in turns:
            lbl = t.get("speaker_label", "SPEAKER_00")
            if lbl not in seen:
                seen[lbl] = {
                    "speaker_label": lbl,
                    "display_name": t.get("display_name") or lbl,
                    "color_hex": t.get("color_hex", "#2563eb"),
                }
        speakers = list(seen.values())

    metrics_data = [
        [
            ("RECORDED DURATION", f"{duration_str} ({total_duration:.1f}s)"),
            ("DETECTED LANGUAGE", lang_display),
            ("TOTAL WORDS", f"{total_words:,} words"),
        ],
        [
            ("DIALOGUE TURNS", f"{len(turns)} turns"),
            ("IDENTIFIED SPEAKERS", f"{len(speakers) or 1} speakers"),
            ("SPEAKING PACE", f"{avg_pace} WPM • {pace_desc}"),
        ],
    ]

    for row_idx, row in enumerate(metrics_table.rows):
        set_row_cant_split(row)
        for col_idx, cell in enumerate(row.cells):
            cell.width = Inches(2.333)
            set_cell_background(cell, "F8FAFC")
            set_cell_margins(cell, top=100, bottom=100, left=140, right=140)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.15

            lbl, val = metrics_data[row_idx][col_idx]
            run_lbl = p.add_run(f"{lbl}\n")
            run_lbl.font.size = Pt(8)
            run_lbl.font.bold = True
            run_lbl.font.color.rgb = RGBColor(100, 116, 139)

            run_val = p.add_run(val)
            run_val.font.size = Pt(10.5)
            run_val.font.bold = True
            run_val.font.color.rgb = RGBColor(15, 23, 42)

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # 5. Section 2: Speakers Roster & Speaking Share Table
    if speakers:
        h2 = doc.add_paragraph()
        h2.paragraph_format.space_before = Pt(8)
        h2.paragraph_format.space_after = Pt(4)
        r_h2 = h2.add_run("2. SPEAKER ROSTER & CONVERSATIONAL SHARE")
        r_h2.font.size = Pt(11)
        r_h2.font.bold = True
        r_h2.font.color.rgb = RGBColor(15, 23, 42)

        spk_table = doc.add_table(rows=1 + len(speakers), cols=6)
        spk_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        spk_table.autofit = False
        set_table_borders(spk_table, "CBD5E1")

        # Column widths: Name (1.8 in), Label (1.0 in), Talk Time (1.0 in), Share (1.0 in), Words (1.1 in), Pace (1.1 in) = 7.0 in
        spk_col_widths = [Inches(1.8), Inches(1.0), Inches(1.0), Inches(1.0), Inches(1.1), Inches(1.1)]

        # Header Row
        hdr_spk = spk_table.rows[0]
        set_row_header(hdr_spk)
        spk_headers = ["SPEAKER NAME", "SYSTEM LABEL", "TALK TIME", "SHARE (%)", "WORDS", "AVG PACE"]
        for i, name in enumerate(spk_headers):
            c = hdr_spk.cells[i]
            c.width = spk_col_widths[i]
            set_cell_background(c, "1E293B")  # Slate-800
            set_cell_margins(c, top=100, bottom=100, left=120, right=120)
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(name)
            r.font.size = Pt(8.5)
            r.font.bold = True
            r.font.color.rgb = RGBColor(255, 255, 255)

        # Pre-aggregate speaker statistics in O(turns)
        spk_stats = {}
        for t in turns:
            lbl = t.get("speaker_label", "SPEAKER_00")
            if lbl not in spk_stats:
                spk_stats[lbl] = {"talk_sec": 0.0, "words": 0}
            spk_stats[lbl]["talk_sec"] += t.get("duration", 0.0)
            spk_stats[lbl]["words"] += t.get("word_count", 0)

        # Data Rows
        for s_idx, spk in enumerate(speakers):
            row = spk_table.rows[1 + s_idx]
            set_row_cant_split(row)
            spk_label = spk.get("speaker_label", "SPEAKER_00")
            spk_display = spk.get("display_name") or spk_label
            color_hex = spk.get("color_hex", "#2563eb")

            stats = spk_stats.get(spk_label, {"talk_sec": 0.0, "words": 0})
            talk_sec = stats["talk_sec"]
            spk_words = stats["words"]
            share_pct = round((talk_sec / max(total_duration, 0.01)) * 100) if total_duration > 0 else 0
            spk_wpm = int(round(spk_words / max(talk_sec / 60.0, 0.01))) if talk_sec > 0 else 0

            bg = "FFFFFF" if s_idx % 2 == 0 else "F8FAFC"

            for i, c in enumerate(row.cells):
                c.width = spk_col_widths[i]
                set_cell_background(c, bg)
                set_cell_margins(c, top=80, bottom=80, left=120, right=120)
                c.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                c.paragraphs[0].paragraph_format.space_after = Pt(0)

            # Speaker Name
            p0 = row.cells[0].paragraphs[0]
            r0 = p0.add_run(spk_display)
            r0.font.bold = True
            r0.font.size = Pt(9.5)
            r0.font.color.rgb = hex_to_rgb(color_hex)

            # Label
            p1 = row.cells[1].paragraphs[0]
            r1 = p1.add_run(spk_label)
            r1.font.size = Pt(8.5)
            r1.font.color.rgb = RGBColor(100, 116, 139)

            # Talk Time
            p2 = row.cells[2].paragraphs[0]
            r2 = p2.add_run(f"{talk_sec:.1f}s")
            r2.font.size = Pt(9)
            r2.font.color.rgb = RGBColor(51, 65, 85)

            # Share
            p3 = row.cells[3].paragraphs[0]
            r3 = p3.add_run(f"{share_pct}%")
            r3.font.size = Pt(9)
            r3.font.bold = True
            r3.font.color.rgb = RGBColor(15, 23, 42)

            # Words
            p4 = row.cells[4].paragraphs[0]
            r4 = p4.add_run(f"{spk_words:,}")
            r4.font.size = Pt(9)
            r4.font.color.rgb = RGBColor(51, 65, 85)

            # Pace
            p5 = row.cells[5].paragraphs[0]
            r5 = p5.add_run(f"{spk_wpm} WPM")
            r5.font.size = Pt(9)
            r5.font.color.rgb = RGBColor(100, 116, 139)

        doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # 6. Section 3: Main Dialogue Transcript Table (The Star Feature)
    h3 = doc.add_paragraph()
    h3.paragraph_format.space_before = Pt(8)
    h3.paragraph_format.space_after = Pt(4)
    r_h3 = h3.add_run("3. COMPLETE DIALOGUE TRANSCRIPT")
    r_h3.font.size = Pt(11)
    r_h3.font.bold = True
    r_h3.font.color.rgb = RGBColor(15, 23, 42)

    if not turns:
        empty_p = doc.add_paragraph()
        empty_r = empty_p.add_run("No spoken dialogue segments recorded.")
        empty_r.font.italic = True
        empty_r.font.color.rgb = RGBColor(148, 163, 184)
    else:
        transcript_table = doc.add_table(rows=1 + len(turns), cols=3)
        transcript_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        transcript_table.autofit = False
        set_table_borders(transcript_table, "CBD5E1")

        # Column Widths: Time Interval (1.5 in), Speaker (1.5 in), Dialogue Content (4.0 in) = 7.0 in total
        col_widths = [Inches(1.5), Inches(1.5), Inches(4.0)]

        # Header Row
        hdr_row = transcript_table.rows[0]
        set_row_header(hdr_row)
        headers_text = ["TIME INTERVAL", "SPEAKER", "DIALOGUE CONTENT"]
        for idx, h_text in enumerate(headers_text):
            cell = hdr_row.cells[idx]
            cell.width = col_widths[idx]
            set_cell_background(cell, "0F172A")  # Slate-900 Dark Navy
            set_cell_margins(cell, top=120, bottom=120, left=140, right=140)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            run = p.add_run(h_text)
            run.font.bold = True
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(255, 255, 255)

        # Data Rows
        for t_idx, turn in enumerate(turns):
            row = transcript_table.rows[1 + t_idx]
            set_row_cant_split(row)
            start_tc = format_time_code(turn["start_time"], include_hours=True)
            end_tc = format_time_code(turn["end_time"], include_hours=True)
            dur = turn["duration"]
            wpm = turn.get("wpm", 0)
            spk_display = turn["display_name"]
            color_hex = turn.get("color_hex", "#2563eb")
            spk_label = turn.get("speaker_label", "SPEAKER_00")

            # Alternating Row Shading
            row_bg = "FFFFFF" if t_idx % 2 == 0 else "F8FAFC"

            for idx, cell in enumerate(row.cells):
                cell.width = col_widths[idx]
                set_cell_background(cell, row_bg)
                set_cell_margins(cell, top=100, bottom=100, left=140, right=140)
                cell.vertical_alignment = WD_ALIGN_VERTICAL.TOP
                cell.paragraphs[0].paragraph_format.space_after = Pt(0)

            # Column 1: Time Interval & Duration
            cell_time = row.cells[0]
            p_time = cell_time.paragraphs[0]
            p_time.paragraph_format.line_spacing = 1.15
            r_time = p_time.add_run(f"[{start_tc} – {end_tc}]\n")
            r_time.font.name = "Consolas"
            r_time.font.size = Pt(8.5)
            r_time.font.bold = True
            r_time.font.color.rgb = RGBColor(51, 65, 85)  # Slate-700

            r_dur = p_time.add_run(f"({dur:.1f}s • {wpm} WPM)")
            r_dur.font.size = Pt(8)
            r_dur.font.color.rgb = RGBColor(148, 163, 184)  # Slate-400

            # Column 2: Speaker Name, Addressee & Tag
            cell_spk = row.cells[1]
            p_spk = cell_spk.paragraphs[0]
            p_spk.paragraph_format.line_spacing = 1.15
            addr_text = f" → {turn['addressed_to']}" if turn.get("addressed_to") else ""
            r_spk = p_spk.add_run(f"{spk_display}{addr_text}\n")
            r_spk.font.bold = True
            r_spk.font.size = Pt(9.5)
            r_spk.font.color.rgb = hex_to_rgb(color_hex)

            r_tag = p_spk.add_run(f"[{spk_label}]")
            r_tag.font.size = Pt(7.5)
            r_tag.font.color.rgb = RGBColor(148, 163, 184)

            # Column 3: Dialogue Paragraph
            cell_text = row.cells[2]
            p_text = cell_text.paragraphs[0]
            p_text.paragraph_format.line_spacing = 1.25
            r_text = p_text.add_run(turn["text"])
            r_text.font.size = Pt(10)
            r_text.font.color.rgb = RGBColor(15, 23, 42)  # Slate-900

    # Save to disk
    doc.save(output_path)


def generate_pdf(
    transcript: Dict[str, Any],
    output_path: str,
    job: Optional[Dict[str, Any]] = None,
    orientation: str = "landscape"
):
    """
    Generates a production-grade Section-Wise & Speaker-Wise Video Flow PDF matching Image 2.
    Features:
      - Prominent document header: uppercase media stem, orange flow title, video metadata
      - Section-Wise Video Flow and Timestamped Transcript subheading card
      - 6-Column table: No., Section, Timecode, Duration, Speaker, Dialogue / Transcript
      - Dark navy header (#1e3a5f), white bold text, repeating table header on page breaks
      - Alternating section backgrounds (#eef4fa ice-blue tint vs white)
      - Microsecond-accurate timecodes and human-friendly duration labels
      - Two-pass NumberedCanvas with running header on page 2+ and Page X of Y footer
      - Supports both Landscape (default, optimal for 6 columns) and Portrait
    """
    try:
        import html
        from pathlib import Path
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.pdfgen import canvas
        from engine.topics import extract_video_topics, format_media_duration, get_media_and_transcript_metadata
    except ImportError:
        # Fallback to plain text if reportlab is not installed
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(generate_txt(transcript))
        return

    topics = extract_video_topics(transcript, job)
    meta = get_media_and_transcript_metadata(transcript, job, topics)
    filename = meta["filename"]
    stem = meta["stem"]
    dur_str = meta["dur_str"]

    is_portrait = (orientation.lower() == "portrait") if orientation else False
    page_size = letter if is_portrait else landscape(letter)
    page_w, page_h = page_size
    margin_x = 32 if is_portrait else 36
    margin_y = 32 if is_portrait else 36
    usable_width = page_w - (margin_x * 2)

    class NumberedCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            num_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self.draw_page_decorations(num_pages)
                canvas.Canvas.showPage(self)
            canvas.Canvas.save(self)

        def draw_page_decorations(self, page_count):
            self.saveState()
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#64748B"))
            # Running header on page 2+
            if self._pageNumber > 1:
                self.drawString(margin_x, page_h - 26, f"TMUX  •  {stem}  •  Section-Wise & Speaker-Wise Video Flow")
                self.drawRightString(page_w - margin_x, page_h - 26, f"Duration: {dur_str}")
                self.setStrokeColor(colors.HexColor("#CBD5E1"))
                self.setLineWidth(0.5)
                self.line(margin_x, page_h - 30, page_w - margin_x, page_h - 30)

            # Running footer on all pages
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(margin_x, 30, page_w - margin_x, 30)
            self.drawString(margin_x, 20, f"TMUX Studio  •  Video: {filename}  •  Duration: {dur_str}")
            self.drawRightString(page_w - margin_x, 20, f"Page {self._pageNumber} of {page_count}")
            self.restoreState()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=page_size,
        leftMargin=margin_x,
        rightMargin=margin_x,
        topMargin=margin_y,
        bottomMargin=margin_y
    )

    story = []

    # 1. Top Centered Document Brand Hierarchy matching user template
    title_style = ParagraphStyle(
        "DocTitle",
        fontName="Helvetica-Bold",
        fontSize=18 if not is_portrait else 16,
        leading=22 if not is_portrait else 20,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1E3A5F"),
        spaceAfter=3
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        fontName="Helvetica-Bold",
        fontSize=14 if not is_portrait else 12.5,
        leading=18 if not is_portrait else 16,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#C25E2E"),
        spaceAfter=4
    )
    meta_style = ParagraphStyle(
        "DocMeta",
        fontName="Helvetica-Oblique",
        fontSize=8.5 if not is_portrait else 8,
        leading=11.5 if not is_portrait else 11,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#475569"),
        spaceAfter=8
    )

    logo_path = get_tmux_logo_path()
    if logo_path:
        # TMUX logo 482x109 aspect ratio ~ 4.42:1
        logo_img = RLImage(str(logo_path), width=115, height=26, hAlign="CENTER")
        story.append(logo_img)
        story.append(Spacer(1, 4))

    story.append(Paragraph(html.escape(stem), title_style))
    story.append(Paragraph("Section-Wise &amp; Speaker-Wise Video Flow", subtitle_style))
    story.append(Paragraph(
        f"Video: <b>{html.escape(filename)}</b> &nbsp;|&nbsp; "
        f"Duration: <b>{dur_str}</b> &nbsp;|&nbsp; "
        f"Language: <b>{html.escape(meta['language'])}</b> &nbsp;|&nbsp; "
        f"Words: <b>{meta['word_count']}</b> &nbsp;|&nbsp; "
        f"Speakers: <b>{meta['speakers_count']}</b>",
        meta_style
    ))

    # 2. Document Subheading Card
    subheading_title_style = ParagraphStyle(
        "SubheadingTitle",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12.5,
        textColor=colors.HexColor("#1E3A5F")
    )
    subheading_desc_style = ParagraphStyle(
        "SubheadingDesc",
        fontName="Helvetica",
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#334155")
    )
    card_content = [
        [Paragraph("Section-Wise Video Flow and Timestamped Transcript", subheading_title_style)],
        [Paragraph(
            f"<b>Audio Specifications:</b> {html.escape(meta['audio_format'])} &nbsp;&bull;&nbsp; "
            f"<b>Duration:</b> {dur_str} &nbsp;&bull;&nbsp; "
            f"<b>Speech Cadence:</b> ~{meta['wpm']} WPM &nbsp;&bull;&nbsp; "
            f"<b>Language:</b> {html.escape(meta['language'])}",
            subheading_desc_style
        )],
        [Paragraph(
            f"<b>Transcript Metrics:</b> {meta['segment_count']} Dialogue Segments &nbsp;&bull;&nbsp; "
            f"<b>Total Words:</b> {meta['word_count']} &nbsp;&bull;&nbsp; "
            f"<b>Alignment:</b> Word-Level Microsecond Synchronized &nbsp;&bull;&nbsp; "
            f"<b>Speakers:</b> {html.escape(meta['speakers_summary'])}",
            subheading_desc_style
        )],
        [Paragraph(
            f"<b>Curriculum Mapping:</b> {meta['sections_count']} Sections ({html.escape(meta['sections_summary'])})",
            subheading_desc_style
        )],
        [Paragraph(
            f"<i>The transcript wording is taken from the supplied <b>{html.escape(stem)}</b> transcript source, "
            f"while the video duration, audio stream, and speaker/scene mapping were checked against the uploaded MUX video.</i>",
            subheading_desc_style
        )]
    ]
    card_table = Table(card_content, colWidths=[usable_width])
    card_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(card_table)
    story.append(Spacer(1, 8))

    # 3. Table Column Styles
    th_style = ParagraphStyle("TH", fontName="Helvetica-Bold", fontSize=9, leading=11, alignment=TA_CENTER, textColor=colors.white)
    cell_no_style = ParagraphStyle("CNo", fontName="Helvetica-Bold", fontSize=11 if not is_portrait else 10, leading=13, alignment=TA_CENTER, textColor=colors.HexColor("#0F172A"))
    cell_sec_style = ParagraphStyle("CSec", fontName="Helvetica-Bold", fontSize=8.5 if not is_portrait else 8, leading=11 if not is_portrait else 10, alignment=TA_CENTER, textColor=colors.HexColor("#0F172A"))
    cell_tc_style = ParagraphStyle("CTC", fontName="Helvetica-Bold", fontSize=8.5 if not is_portrait else 8, leading=11 if not is_portrait else 10, alignment=TA_CENTER, textColor=colors.HexColor("#C25E2E"))
    cell_dur_style = ParagraphStyle("CDur", fontName="Helvetica", fontSize=8.5 if not is_portrait else 8, leading=11 if not is_portrait else 10, alignment=TA_CENTER, textColor=colors.HexColor("#0F172A"))
    cell_spk_style = ParagraphStyle("CSpk", fontName="Helvetica-Bold", fontSize=8.5 if not is_portrait else 8, leading=11 if not is_portrait else 10, alignment=TA_CENTER, textColor=colors.HexColor("#0F172A"))
    cell_dlg_style = ParagraphStyle("CDlg", fontName="Helvetica", fontSize=8.5 if not is_portrait else 8, leading=11.5 if not is_portrait else 10.5, alignment=TA_LEFT, textColor=colors.HexColor("#0F172A"))

    # Column Widths
    if is_portrait:
        col_widths = [26, 96, 68, 44, 78, usable_width - (26 + 96 + 68 + 44 + 78)]
    else:
        col_widths = [32, 130, 80, 54, 94, usable_width - (32 + 130 + 80 + 54 + 94)]

    table_data = [[
        Paragraph("No.", th_style),
        Paragraph("Section", th_style),
        Paragraph("Timecode", th_style),
        Paragraph("Duration", th_style),
        Paragraph("Speaker", th_style),
        Paragraph("Dialogue / Transcript", th_style),
    ]]

    tstyles = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A5F")),
        ("BOX", (0, 0), (-1, 0), 1, colors.HexColor("#1E3A5F")),
        ("INNERGRID", (0, 0), (-1, 0), 0.5, colors.HexColor("#2D4D77")),
        ("TOPPADDING", (0, 0), (-1, 0), 5),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]

    row_idx = 1
    if not topics:
        empty_style = ParagraphStyle("EmptyStyle", fontName="Helvetica-Oblique", fontSize=9, textColor=colors.HexColor("#94A3B8"), alignment=TA_CENTER)
        table_data.append([
            Paragraph("-", cell_no_style),
            Paragraph("No Spoken Sections", cell_sec_style),
            Paragraph("-", cell_tc_style),
            Paragraph("-", cell_dur_style),
            Paragraph("-", cell_spk_style),
            Paragraph("No spoken dialogue recorded.", empty_style),
        ])
        tstyles.append(("BACKGROUND", (0, 1), (-1, 1), colors.white))
        tstyles.append(("BOX", (0, 1), (-1, 1), 0.75, colors.HexColor("#CBD5E1")))
        tstyles.append(("INNERGRID", (0, 1), (-1, 1), 0.5, colors.HexColor("#CBD5E1")))
    else:
        for s_idx, sec in enumerate(topics):
            turns = sec.get("turns", [])
            if not turns:
                continue
            start_r = row_idx
            end_r = row_idx + len(turns) - 1

            is_tinted = (sec["section_no"] % 2 != 0 and sec["section_no"] >= 3)
            sec_bg = colors.HexColor("#EEF4FA") if is_tinted else colors.white

            for t_idx, turn in enumerate(turns):
                if t_idx == 0:
                    c0 = Paragraph(str(sec["section_no"]), cell_no_style)
                    c1 = Paragraph(html.escape(sec["section"]), cell_sec_style)
                    c2 = Paragraph(html.escape(sec["timecode"]), cell_tc_style)
                    c3 = Paragraph(html.escape(sec["duration_label"]), cell_dur_style)
                else:
                    c0 = ""
                    c1 = ""
                    c2 = ""
                    c3 = ""

                c4 = Paragraph(html.escape(turn["speaker"]), cell_spk_style)
                c5 = Paragraph(html.escape(turn["text"]), cell_dlg_style)

                table_data.append([c0, c1, c2, c3, c4, c5])
                row_idx += 1

            # Style for this section block
            tstyles.append(("BACKGROUND", (0, start_r), (-1, end_r), sec_bg))
            tstyles.append(("BOX", (0, start_r), (-1, end_r), 0.75, colors.HexColor("#CBD5E1")))
            for c in range(6):
                tstyles.append(("LINEBEFORE", (c, start_r), (c, end_r), 0.5, colors.HexColor("#CBD5E1")))
            tstyles.append(("LINEAFTER", (5, start_r), (5, end_r), 0.5, colors.HexColor("#CBD5E1")))

            if len(turns) > 1:
                tstyles.append(("INNERGRID", (4, start_r), (5, end_r), 0.5, colors.HexColor("#E2E8F0")))

            tstyles.append(("TOPPADDING", (0, start_r), (-1, end_r), 4))
            tstyles.append(("BOTTOMPADDING", (0, start_r), (-1, end_r), 4))
            tstyles.append(("LEFTPADDING", (0, start_r), (-1, end_r), 5))
            tstyles.append(("RIGHTPADDING", (0, start_r), (-1, end_r), 5))

    main_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    main_table.setStyle(TableStyle(tstyles))
    story.append(main_table)

    doc.build(story, canvasmaker=NumberedCanvas)



