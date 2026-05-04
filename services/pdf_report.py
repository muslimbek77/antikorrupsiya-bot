import logging
import os
from datetime import datetime
from typing import Dict, List, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

logger = logging.getLogger(__name__)


def generate_statistics_pdf(
    output_path: str,
    stats: Dict[str, int],
    category_stats: List[Tuple[str, int]],
    risk_stats: List[Tuple[str, int]],
    recent_appeals: List[Tuple],
) -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    document = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Korrupsiyaga oid murojaatlar bo'yicha hisobot", styles["Title"]))
    story.append(Paragraph(datetime.now().strftime("Sana: %Y-%m-%d %H:%M"), styles["Normal"]))
    story.append(Spacer(1, 16))

    summary_table = Table(
        [
            ["Ko'rsatkich", "Qiymat"],
            ["Jami murojaatlar", str(stats["total"])],
            ["Bugungi murojaatlar", str(stats["today"])],
            ["Yuqori xavf", str(stats["high_risk"])],
            ["Ko'rib chiqilmoqda", str(stats["in_review"])],
            ["Yakunlangan", str(stats["resolved"])],
        ],
        colWidths=[240, 180],
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123C7A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#EDF3FF")]),
                ("PADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 16))

    if category_stats:
        story.append(Paragraph("Toifalar kesimida", styles["Heading2"]))
        category_table = Table([["Toifa", "Soni"], *[[name, str(count)] for name, count in category_stats]])
        category_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9E8FF")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("PADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(category_table)
        story.append(Spacer(1, 14))

    if risk_stats:
        story.append(Paragraph("Xavf darajalari", styles["Heading2"]))
        risk_table = Table([["Xavf", "Soni"], *[[name, str(count)] for name, count in risk_stats]])
        risk_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FFE7C2")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("PADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(risk_table)
        story.append(Spacer(1, 14))

    if recent_appeals:
        story.append(Paragraph("So'nggi murojaatlar", styles["Heading2"]))
        table_rows = [["ID", "F.I.O", "Toifa", "Xavf", "Status"]]
        for appeal in recent_appeals[:10]:
            table_rows.append([
                str(appeal[0]),
                appeal[2],
                appeal[5],
                appeal[6],
                appeal[8],
            ])
        recent_table = Table(table_rows, colWidths=[35, 150, 135, 70, 90])
        recent_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123C7A")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(recent_table)

    document.build(story)
    logger.info("PDF report generated: %s", output_path)
    return output_path
