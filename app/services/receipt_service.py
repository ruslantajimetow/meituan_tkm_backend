"""Generate A4 PDF receipts for orders using reportlab."""

from __future__ import annotations

import io
from datetime import timedelta, timezone
from typing import TYPE_CHECKING

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

if TYPE_CHECKING:
    from app.models.order import Order

TMT_TZ = timezone(timedelta(hours=5))


def generate_receipt_pdf(order: Order) -> bytes:
    """Generate a printable A4 PDF receipt for the given order.

    The order must have its `items` and `store` relationships loaded.
    Returns raw PDF bytes.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    elements: list = []

    # -- Store name --
    store_name = getattr(order.store, "name", "Store") if order.store else "Store"
    elements.append(Paragraph(store_name, ParagraphStyle(
        "StoreName",
        parent=styles["Title"],
        fontSize=18,
        alignment=1,
        spaceAfter=4,
    )))

    # -- Title --
    elements.append(Paragraph("Order Receipt", ParagraphStyle(
        "ReceiptTitle",
        parent=styles["Heading2"],
        alignment=1,
        spaceAfter=8,
    )))

    # -- Order info --
    order_id_short = str(order.id)[:8]
    order_time = order.created_at.astimezone(TMT_TZ).strftime("%Y-%m-%d %H:%M")
    info_style = ParagraphStyle("Info", parent=styles["Normal"], fontSize=11, spaceAfter=2)

    elements.append(Paragraph(f"<b>Order ID:</b> #{order_id_short}", info_style))
    elements.append(Paragraph(f"<b>Date:</b> {order_time}", info_style))
    elements.append(Spacer(1, 8))

    # -- Separator --
    elements.append(Table(
        [[""]],
        colWidths=[doc.width],
        style=TableStyle([("LINEBELOW", (0, 0), (-1, 0), 1, colors.grey)]),
    ))
    elements.append(Spacer(1, 8))

    # -- Items table --
    header = ["#", "Item", "Qty", "Price", "Total"]
    table_data = [header]
    for idx, item in enumerate(order.items, 1):
        table_data.append([
            str(idx),
            item.name,
            str(item.quantity),
            f"{float(item.unit_price):.2f}",
            f"{float(item.total_price):.2f}",
        ])

    col_widths = [8 * mm, None, 15 * mm, 25 * mm, 25 * mm]
    # Calculate remaining width for Item column
    fixed = sum(w for w in col_widths if w is not None)
    col_widths[1] = doc.width - fixed

    items_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5f5f4")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 10))

    # -- Totals --
    totals_style = ParagraphStyle("Totals", parent=styles["Normal"], fontSize=11, alignment=2)
    bold_totals = ParagraphStyle("BoldTotals", parent=totals_style, fontSize=13)

    elements.append(Paragraph(
        f"Subtotal: {float(order.subtotal):.2f} TMT", totals_style,
    ))
    elements.append(Paragraph(
        f"Delivery Fee: {float(order.delivery_fee):.2f} TMT", totals_style,
    ))
    elements.append(Paragraph(
        f"<b>Total: {float(order.total):.2f} TMT</b>", bold_totals,
    ))
    elements.append(Spacer(1, 8))

    # -- Separator --
    elements.append(Table(
        [[""]],
        colWidths=[doc.width],
        style=TableStyle([("LINEBELOW", (0, 0), (-1, 0), 1, colors.grey)]),
    ))
    elements.append(Spacer(1, 8))

    # -- Customer info --
    customer_style = ParagraphStyle("Customer", parent=styles["Normal"], fontSize=11, spaceAfter=4)
    elements.append(Paragraph(f"<b>Customer Phone:</b> {order.customer_phone}", customer_style))
    elements.append(Paragraph(
        f"<b>Delivery Address:</b> {order.delivery_address}", customer_style,
    ))

    if order.note:
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(f"<b>Note:</b> <i>{order.note}</i>", customer_style))

    # -- Build PDF --
    doc.build(elements)
    return buf.getvalue()
