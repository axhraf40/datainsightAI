"""Génération de rapports PDF pour les datasets analysés."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _p(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


def build_pdf_report(
    overview: dict[str, Any],
    summary: str,
    insights: list[str],
    chart_images: list[bytes],
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleFR",
        parent=styles["Title"],
        fontSize=20,
        spaceAfter=16,
        textColor=colors.HexColor("#1f4e79"),
    )
    heading_style = ParagraphStyle(
        "HeadingFR",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=14,
        spaceAfter=8,
        textColor=colors.HexColor("#2e75b6"),
    )
    body_style = ParagraphStyle(
        "BodyFR",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        spaceAfter=8,
    )

    story = [
        Paragraph("Rapport d'analyse de données", title_style),
        Paragraph(f"Généré le {_p(overview.get('generated_at', ''))}", body_style),
        Spacer(1, 0.4 * cm),
    ]

    for file_info in overview.get("files", []):
        story.append(Paragraph(f"Dataset : {_p(file_info['name'])}", heading_style))
        meta = [
            ["Lignes", str(file_info["rows"])],
            ["Colonnes", ", ".join(file_info["columns"])],
        ]
        table = Table(meta, colWidths=[4 * cm, 12 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#d9e2f3")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph("<b>Statistiques descriptives</b>", body_style))
        story.append(Paragraph(f"<pre>{_p(file_info['describe'])}</pre>", body_style))

    story.append(Paragraph("Résumé exécutif", heading_style))
    story.append(Paragraph(_p(summary), body_style))

    if insights:
        story.append(Paragraph("Insights automatiques", heading_style))
        for insight in insights:
            story.append(Paragraph(_p(insight.replace("**", "")), body_style))
            story.append(Spacer(1, 0.2 * cm))

    valid_charts = [img for img in chart_images if img]
    if valid_charts:
        story.append(Paragraph("Graphiques", heading_style))
        for chart_bytes in valid_charts:
            try:
                img = Image(BytesIO(chart_bytes))
                img.drawHeight = 8 * cm
                img.drawWidth = 14 * cm
                story.append(img)
                story.append(Spacer(1, 0.3 * cm))
            except Exception:
                continue

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
