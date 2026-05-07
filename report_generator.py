"""
report_generator.py

Generates downloadable PDF reports for AURIX Mail Agent.
Reports:
  1. generate_spam_report()    — User | No. of Spam Mails Detected | Spam Mail Subjects  (UNCHANGED)
  2. generate_user_report()    — Username-wise full breakdown
  3. generate_date_report()    — Date-wise daily activity
  4. generate_combined_report()— Combined summary (stats + user + date + spam detail)
"""

import io
from collections import defaultdict
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from report_logger import get_all_logs

# ── Brand colours ──────────────────────────────────────────────────────────────
AURIX_BLUE   = colors.HexColor("#38bdf8")
AURIX_DARK   = colors.HexColor("#020617")
AURIX_PANEL  = colors.HexColor("#0f172a")
AURIX_RED    = colors.HexColor("#ef4444")
AURIX_YELLOW = colors.HexColor("#fbbf24")
AURIX_GREEN  = colors.HexColor("#22c55e")
AURIX_GREY   = colors.HexColor("#64748b")
WHITE        = colors.white

# ── Shared styles ───────────────────────────────────────────────────────────────
def _styles():
    base = getSampleStyleSheet()
    custom = {
        "title": ParagraphStyle("title", parent=base["Title"],
            fontSize=26, textColor=AURIX_BLUE, alignment=TA_CENTER,
            fontName="Helvetica-Bold", spaceAfter=4),
        "subtitle": ParagraphStyle("subtitle", parent=base["Normal"],
            fontSize=11, textColor=AURIX_GREY, alignment=TA_CENTER,
            fontName="Helvetica", spaceAfter=2),
        "section": ParagraphStyle("section", parent=base["Heading1"],
            fontSize=13, textColor=AURIX_BLUE, fontName="Helvetica-Bold",
            spaceBefore=14, spaceAfter=6),
        "body": ParagraphStyle("body", parent=base["Normal"],
            fontSize=10, textColor=colors.HexColor("#1e293b"),
            fontName="Helvetica", spaceAfter=4),
        "small": ParagraphStyle("small", parent=base["Normal"],
            fontSize=8, textColor=AURIX_GREY, fontName="Helvetica"),
        "bold": ParagraphStyle("bold", parent=base["Normal"],
            fontSize=10, textColor=colors.HexColor("#0f172a"),
            fontName="Helvetica-Bold"),
        "tag_spam": ParagraphStyle("tag_spam", parent=base["Normal"],
            fontSize=9, textColor=AURIX_RED, fontName="Helvetica-Bold"),
        "tag_safe": ParagraphStyle("tag_safe", parent=base["Normal"],
            fontSize=9, textColor=AURIX_GREEN, fontName="Helvetica-Bold"),
    }
    return {**{k: base[k] for k in base.byName}, **custom}


def _header_table(report_type: str, generated_at: str) -> Table:
    """Top banner with AURIX branding."""
    data = [[
        Paragraph("<b>🤖 AURIX</b>", ParagraphStyle("hdr", fontSize=18,
            textColor=AURIX_BLUE, fontName="Helvetica-Bold")),
        Paragraph(f"<b>{report_type}</b>", ParagraphStyle("hdrtype", fontSize=12,
            textColor=WHITE, fontName="Helvetica-Bold", alignment=TA_CENTER)),
        Paragraph(f"Generated: {generated_at}", ParagraphStyle("hdrdate", fontSize=8,
            textColor=AURIX_GREY, fontName="Helvetica", alignment=TA_RIGHT)),
    ]]
    t = Table(data, colWidths=[2*inch, 4*inch, 2*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), AURIX_PANEL),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
    ]))
    return t


def _stat_table(stats: list) -> Table:
    """Small key-value stat box. stats = [(label, value), ...]"""
    data = [
        [
            Paragraph(f"<b>{k}</b>", ParagraphStyle("sl", fontSize=10,
                textColor=AURIX_GREY, fontName="Helvetica-Bold")),
            Paragraph(str(v), ParagraphStyle("sv", fontSize=11,
                textColor=AURIX_BLUE, fontName="Helvetica-Bold")),
        ]
        for k, v in stats
    ]
    t = Table(data, colWidths=[3*inch, 4.8*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [colors.HexColor("#f1f5f9"), WHITE]),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
    ]))
    return t


def _data_table(headers: list, rows: list, col_widths: list = None) -> Table:
    """Styled data table."""
    header_row = [
        Paragraph(f"<b>{h}</b>", ParagraphStyle("th", fontSize=9,
            textColor=WHITE, fontName="Helvetica-Bold", alignment=TA_CENTER))
        for h in headers
    ]
    body_rows = [
        [
            Paragraph(str(cell), ParagraphStyle("td", fontSize=9,
                textColor=colors.HexColor("#1e293b"), fontName="Helvetica",
                alignment=TA_CENTER))
            for cell in row
        ]
        for row in rows
    ]
    data = [header_row] + body_rows
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0), AURIX_BLUE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), WHITE]),
        ("GRID",           (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 6),
    ]))
    return t


def _spam_summary_table(rows: list) -> Table:
    """
    Spam-specific table: User | No. of Spam Mails Detected | Spam Mail Subjects
    rows = [(username, spam_count, subjects_str), ...]
    """
    header_style = ParagraphStyle("th", fontSize=9, textColor=WHITE,
                                   fontName="Helvetica-Bold", alignment=TA_CENTER)
    cell_style   = ParagraphStyle("td", fontSize=9,
                                   textColor=colors.HexColor("#1e293b"),
                                   fontName="Helvetica", leading=13)
    center_style = ParagraphStyle("tdc", fontSize=9,
                                   textColor=colors.HexColor("#1e293b"),
                                   fontName="Helvetica-Bold", alignment=TA_CENTER)

    header_row = [
        Paragraph("User", header_style),
        Paragraph("No. of Spam Mails Detected", header_style),
        Paragraph("Spam Mail Subjects", header_style),
    ]

    body_rows = []
    for username, spam_count, subjects_str in rows:
        body_rows.append([
            Paragraph(username, cell_style),
            Paragraph(str(spam_count), center_style),
            Paragraph(subjects_str, cell_style),
        ])

    data = [header_row] + body_rows
    t = Table(data, colWidths=[1.6*inch, 1.6*inch, 4.6*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0), AURIX_BLUE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), WHITE]),
        ("GRID",           (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("TOPPADDING",     (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 6),
        ("LEFTPADDING",    (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 8),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def _divider():
    return HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"),
                      spaceAfter=8, spaceBefore=8)


def _footer(story: list):
    story.append(_divider())
    story.append(Paragraph(
        "Report generated by AURIX Mail Intelligence Agent · aurix.ai",
        ParagraphStyle("footer", fontSize=8, textColor=AURIX_GREY,
                       fontName="Helvetica", alignment=TA_CENTER)
    ))


# ══════════════════════════════════════════════════════════════════════════════
# 1. SPAM REPORT — UNCHANGED
#    User | No. of Spam Mails Detected | Spam Mail Subjects
# ══════════════════════════════════════════════════════════════════════════════

def generate_spam_report(logs: list = None) -> bytes:
    logs = logs or get_all_logs()
    buf  = io.BytesIO()
    doc  = SimpleDocTemplate(buf, pagesize=letter,
                             leftMargin=0.75*inch, rightMargin=0.75*inch,
                             topMargin=0.6*inch,   bottomMargin=0.6*inch)
    S   = _styles()
    now = datetime.now().strftime("%d %b %Y, %I:%M %p")

    story = []
    story.append(_header_table("Spam Detection Report", now))
    story.append(Spacer(1, 20))

    spam_logs = [e for e in logs if e.get("is_spam")]

    if not spam_logs:
        story.append(Paragraph("No spam emails detected yet.", S["body"]))
        doc.build(story)
        return buf.getvalue()

    by_user = defaultdict(list)
    for e in spam_logs:
        username = e.get("username", "Unknown")
        subject  = e.get("subject", "(No Subject)")
        by_user[username].append(subject)

    table_rows = []
    for username in sorted(by_user.keys()):
        subjects     = by_user[username]
        spam_count   = len(subjects)
        subjects_str = "\n".join(
            f"{i+1}. {subj[:70]}" for i, subj in enumerate(subjects)
        )
        table_rows.append((username, spam_count, subjects_str))

    story.append(Paragraph("Spam Detected — User Overview", S["section"]))
    story.append(Spacer(1, 6))
    story.append(_spam_summary_table(table_rows))
    story.append(Spacer(1, 20))

    _footer(story)
    doc.build(story)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
# 2. USERNAME-WISE REPORT
# ══════════════════════════════════════════════════════════════════════════════

def generate_user_report(logs: list = None) -> bytes:
    logs = logs or get_all_logs()
    buf  = io.BytesIO()
    doc  = SimpleDocTemplate(buf, pagesize=letter,
                             leftMargin=0.75*inch, rightMargin=0.75*inch,
                             topMargin=0.6*inch,   bottomMargin=0.6*inch)
    S   = _styles()
    now = datetime.now().strftime("%d %b %Y, %I:%M %p")

    story = []
    story.append(_header_table("Username-wise Report", now))
    story.append(Spacer(1, 16))

    by_user = defaultdict(list)
    for log in logs:
        by_user[log.get("username", "Unknown")].append(log)

    if not by_user:
        story.append(Paragraph("No data available yet.", S["body"]))
        doc.build(story)
        return buf.getvalue()

    # Summary table
    story.append(Paragraph("User Summary", S["section"]))
    summary_rows = []
    for user, entries in sorted(by_user.items()):
        total = len(entries)
        spam  = sum(1 for e in entries if e.get("is_spam"))
        safe  = total - spam
        repld = sum(1 for e in entries if e.get("replied"))
        rate  = f"{(spam/total*100):.1f}%" if total else "0%"
        summary_rows.append([user, total, safe, spam, repld, rate])

    story.append(_data_table(
        ["Username", "Total Emails", "Safe", "Spam", "Replies Sent", "Spam Rate"],
        summary_rows,
        col_widths=[1.6*inch, 1.1*inch, 0.9*inch, 0.9*inch, 1.1*inch, 1.0*inch],
    ))
    story.append(Spacer(1, 14))

    # Per-user detail
    for user, entries in sorted(by_user.items()):
        story.append(_divider())
        story.append(Paragraph(f"👤  {user}", S["section"]))

        total = len(entries)
        spam  = sum(1 for e in entries if e.get("is_spam"))
        story.append(_stat_table([
            ("Account Email",           entries[0].get("user_email", "—")),
            ("Total Emails Processed",  total),
            ("Spam Detected",           spam),
            ("Safe Emails",             total - spam),
            ("Replies Generated",       sum(1 for e in entries if e.get("replied"))),
            ("Last Active",             entries[-1].get("timestamp", "—")[:10]),
        ]))
        story.append(Spacer(1, 10))

        rows = []
        for e in entries[-20:]:
            rows.append([
                e.get("date", "—"),
                e.get("subject", "—")[:45],
                e.get("sender", "—")[:30],
                "🚫 SPAM" if e.get("is_spam") else "✅ Safe",
            ])
        if rows:
            story.append(_data_table(
                ["Date", "Subject", "Sender", "Status"],
                rows,
                col_widths=[0.9*inch, 2.8*inch, 2.1*inch, 0.9*inch],
            ))
        story.append(Spacer(1, 8))

    _footer(story)
    doc.build(story)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
# 3. DATE-WISE REPORT
# ══════════════════════════════════════════════════════════════════════════════

def generate_date_report(logs: list = None) -> bytes:
    logs = logs or get_all_logs()
    buf  = io.BytesIO()
    doc  = SimpleDocTemplate(buf, pagesize=letter,
                             leftMargin=0.75*inch, rightMargin=0.75*inch,
                             topMargin=0.6*inch,   bottomMargin=0.6*inch)
    S   = _styles()
    now = datetime.now().strftime("%d %b %Y, %I:%M %p")

    story = []
    story.append(_header_table("Date-wise Report", now))
    story.append(Spacer(1, 16))

    by_date = defaultdict(list)
    for log in logs:
        by_date[log.get("date", "Unknown")].append(log)

    if not by_date:
        story.append(Paragraph("No data available yet.", S["body"]))
        doc.build(story)
        return buf.getvalue()

    # Date summary table
    story.append(Paragraph("Daily Activity Summary", S["section"]))
    rows = []
    for date in sorted(by_date.keys(), reverse=True):
        entries = by_date[date]
        total   = len(entries)
        spam    = sum(1 for e in entries if e.get("is_spam"))
        users   = len(set(e.get("username") for e in entries))
        rows.append([date, total, total - spam, spam, users])

    story.append(_data_table(
        ["Date", "Total Emails", "Safe", "Spam", "Active Users"],
        rows,
        col_widths=[1.3*inch, 1.3*inch, 1.2*inch, 1.2*inch, 1.3*inch],
    ))
    story.append(Spacer(1, 16))

    # Per-day detail
    for date in sorted(by_date.keys(), reverse=True):
        entries = by_date[date]
        story.append(_divider())
        story.append(Paragraph(f"📅  {date}", S["section"]))

        total = len(entries)
        spam  = sum(1 for e in entries if e.get("is_spam"))
        story.append(_stat_table([
            ("Total Emails",  total),
            ("Spam Blocked",  spam),
            ("Safe Emails",   total - spam),
            ("Active Users",  len(set(e.get("username") for e in entries))),
        ]))
        story.append(Spacer(1, 8))

        detail_rows = []
        for e in entries:
            detail_rows.append([
                e.get("username", "—"),
                e.get("subject",  "—")[:40],
                e.get("sender",   "—")[:28],
                "🚫 SPAM" if e.get("is_spam") else "✅ Safe",
            ])
        story.append(_data_table(
            ["User", "Subject", "Sender", "Status"],
            detail_rows,
            col_widths=[1.2*inch, 2.8*inch, 2.0*inch, 0.9*inch],
        ))
        story.append(Spacer(1, 8))

    _footer(story)
    doc.build(story)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
# 4. COMBINED SUMMARY REPORT
# ══════════════════════════════════════════════════════════════════════════════

def generate_combined_report(logs: list = None) -> bytes:
    logs = logs or get_all_logs()
    buf  = io.BytesIO()
    doc  = SimpleDocTemplate(buf, pagesize=letter,
                             leftMargin=0.75*inch, rightMargin=0.75*inch,
                             topMargin=0.6*inch,   bottomMargin=0.6*inch)
    S   = _styles()
    now = datetime.now().strftime("%d %b %Y, %I:%M %p")

    story = []
    story.append(_header_table("Combined Summary Report", now))
    story.append(Spacer(1, 20))
    story.append(Paragraph("AURIX Mail Intelligence — Full Overview", S["subtitle"]))
    story.append(Spacer(1, 20))

    if not logs:
        story.append(Paragraph("No data available yet.", S["body"]))
        doc.build(story)
        return buf.getvalue()

    total      = len(logs)
    spam_count = sum(1 for e in logs if e.get("is_spam"))
    safe_count = total - spam_count
    users      = list(set(e.get("username", "Unknown") for e in logs))
    dates      = sorted(set(e.get("date", "") for e in logs))

    # ── Overall Stats ──
    story.append(Paragraph("📊 Overall Statistics", S["section"]))
    story.append(_stat_table([
        ("Total Emails Scanned", total),
        ("Spam Blocked",         spam_count),
        ("Safe Emails",          safe_count),
        ("Spam Rate",            f"{(spam_count/total*100):.1f}%" if total else "0%"),
        ("Total Users",          len(users)),
        ("Active Days",          len(dates)),
        ("Date Range",           f"{dates[0]} → {dates[-1]}" if dates else "—"),
    ]))
    story.append(Spacer(1, 16))

    # ── User Summary ──
    story.append(_divider())
    story.append(Paragraph("👤 User Summary", S["section"]))

    by_user = defaultdict(list)
    for log in logs:
        by_user[log.get("username", "Unknown")].append(log)

    user_rows = []
    for user, entries in sorted(by_user.items()):
        t = len(entries)
        s = sum(1 for e in entries if e.get("is_spam"))
        user_rows.append([user, t, t - s, s, f"{(s/t*100):.1f}%"])

    story.append(_data_table(
        ["Username", "Total", "Safe", "Spam", "Spam Rate"],
        user_rows,
        col_widths=[1.8*inch, 1.1*inch, 1.0*inch, 1.0*inch, 1.0*inch],
    ))
    story.append(Spacer(1, 14))

    # ── Date Summary ──
    story.append(_divider())
    story.append(Paragraph("📅 Daily Activity", S["section"]))

    by_date = defaultdict(list)
    for log in logs:
        by_date[log.get("date", "Unknown")].append(log)

    date_rows = []
    for date in sorted(by_date.keys(), reverse=True)[:30]:
        entries = by_date[date]
        t = len(entries)
        s = sum(1 for e in entries if e.get("is_spam"))
        date_rows.append([date, t, t - s, s])

    story.append(_data_table(
        ["Date", "Total", "Safe", "Spam"],
        date_rows,
        col_widths=[1.5*inch, 1.3*inch, 1.3*inch, 1.3*inch],
    ))
    story.append(Spacer(1, 14))

    # ── Spam Breakdown ──
    story.append(PageBreak())
    story.append(_header_table("Combined Summary Report — Spam Detail", now))
    story.append(Spacer(1, 16))
    story.append(Paragraph("🚫 Spam Breakdown by User & Day", S["section"]))

    spam_logs = [e for e in logs if e.get("is_spam")]
    if spam_logs:
        spam_rows = []
        for e in sorted(spam_logs, key=lambda x: x.get("date", ""), reverse=True):
            reasons = "; ".join(e.get("spam_reasons", []))[:55] or "—"
            spam_rows.append([
                e.get("date",     "—"),
                e.get("username", "—"),
                e.get("subject",  "—")[:32],
                reasons,
            ])
        story.append(_data_table(
            ["Date", "User", "Subject", "Reason"],
            spam_rows,
            col_widths=[0.9*inch, 1.0*inch, 2.2*inch, 2.55*inch],
        ))
    else:
        story.append(Paragraph("No spam emails recorded.", S["body"]))

    story.append(Spacer(1, 20))
    _footer(story)
    doc.build(story)
    return buf.getvalue()