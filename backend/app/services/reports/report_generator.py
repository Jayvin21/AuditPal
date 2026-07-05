import csv
import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from sqlalchemy.orm import Session

from app.models.audit_run import AuditRun
from app.models.finding import Finding
from app.models.workspace import Workspace


def format_status(status: str | None) -> str:
    if not status:
        return "-"
    return status.replace("_", " ").title()


def safe(value):
    if value is None:
        return "-"
    return str(value)


def get_workspace_or_error(workspace_id: int, db: Session) -> Workspace:
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise ValueError("Workspace not found")
    return workspace


def get_latest_audit_run(workspace_id: int, db: Session) -> AuditRun | None:
    return (
        db.query(AuditRun)
        .filter(AuditRun.workspace_id == workspace_id)
        .order_by(AuditRun.id.desc())
        .first()
    )


def get_findings(workspace_id: int, db: Session) -> list[Finding]:
    return (
        db.query(Finding)
        .filter(Finding.workspace_id == workspace_id)
        .order_by(Finding.risk_level.asc(), Finding.id.asc())
        .all()
    )


def generate_findings_csv(workspace_id: int, db: Session) -> str:
    workspace = get_workspace_or_error(workspace_id, db)
    findings = get_findings(workspace_id, db)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Client",
        "Audit Period",
        "Audit Type",
        "Finding ID",
        "Risk",
        "Type",
        "Title",
        "Description",
        "Review Status",
        "Reviewer Note",
        "Evidence",
    ])

    for finding in findings:
        writer.writerow([
            workspace.client_name,
            workspace.audit_period,
            workspace.audit_type,
            finding.id,
            finding.risk_level,
            finding.finding_type,
            finding.title,
            finding.description,
            format_status(finding.status),
            finding.reviewer_note or "",
            finding.evidence or {},
        ])

    return output.getvalue()


def generate_audit_pdf(workspace_id: int, db: Session) -> bytes:
    workspace = get_workspace_or_error(workspace_id, db)
    audit_run = get_latest_audit_run(workspace_id, db)
    findings = get_findings(workspace_id, db)

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=0.45 * inch,
        leftMargin=0.45 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "AuditPalTitle",
        parent=styles["Title"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#17352E"),
        spaceAfter=10,
    )

    section_style = ParagraphStyle(
        "AuditPalSection",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#17352E"),
        spaceBefore=12,
        spaceAfter=8,
    )

    body_style = ParagraphStyle(
        "AuditPalBody",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#17352E"),
    )

    muted_style = ParagraphStyle(
        "AuditPalMuted",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#5F7D70"),
    )

    story = []

    story.append(Paragraph("AuditPal Audit Report", title_style))
    story.append(Paragraph(
        f"Generated on {datetime.now().strftime('%d %b %Y, %I:%M %p')}",
        muted_style,
    ))
    story.append(Spacer(1, 10))

    summary_data = [
        ["Client", workspace.client_name],
        ["Audit Period", workspace.audit_period],
        ["Audit Type", workspace.audit_type],
        ["Workspace Status", workspace.status],
    ]

    if audit_run:
        summary_data.extend([
            ["Latest Audit Run ID", str(audit_run.id)],
            ["Run Status", audit_run.status],
            ["Total Records", str(audit_run.total_records)],
            ["Checked Records", str(audit_run.checked_records)],
            ["Unchecked Records", str(audit_run.unchecked_records)],
            ["Issues Found", str(audit_run.issues_found)],
        ])

    summary_table = Table(summary_data, colWidths=[2.0 * inch, 5.8 * inch])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EDF6F0")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#17352E")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#C8DDD0")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_table)

    high = len([f for f in findings if f.risk_level == "high"])
    medium = len([f for f in findings if f.risk_level == "medium"])
    low = len([f for f in findings if f.risk_level == "low"])

    story.append(Paragraph("Risk Summary", section_style))

    risk_table = Table([
        ["High", "Medium", "Low", "Total"],
        [str(high), str(medium), str(low), str(len(findings))],
    ], colWidths=[1.4 * inch, 1.4 * inch, 1.4 * inch, 1.4 * inch])

    risk_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DFEAE2")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#17352E")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#C8DDD0")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(risk_table)

    story.append(Paragraph("Audit Findings", section_style))

    table_data = [[
        "ID",
        "Risk",
        "Type",
        "Title",
        "Status",
        "Reviewer Note",
    ]]

    for finding in findings:
        table_data.append([
            str(finding.id),
            safe(finding.risk_level).upper(),
            Paragraph(safe(finding.finding_type).replace("_", " "), body_style),
            Paragraph(safe(finding.title), body_style),
            Paragraph(format_status(finding.status), body_style),
            Paragraph(safe(finding.reviewer_note), body_style),
        ])

    if len(table_data) == 1:
        table_data.append(["-", "-", "-", "No findings available", "-", "-"])

    findings_table = Table(
        table_data,
        colWidths=[
            0.45 * inch,
            0.75 * inch,
            1.45 * inch,
            3.2 * inch,
            1.4 * inch,
            3.7 * inch,
        ],
        repeatRows=1,
    )

    findings_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#358873")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#C8DDD0")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6FBF8")]),
    ]))

    story.append(findings_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph(
        "Note: AuditPal is an audit assistance system. Findings are generated from uploaded files and mapped columns. Final validation must be performed by a human reviewer.",
        muted_style,
    ))

    doc.build(story)

    pdf = buffer.getvalue()
    buffer.close()
    return pdf