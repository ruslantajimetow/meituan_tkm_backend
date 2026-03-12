"""Send PDF receipts to the host print agent for printing."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx

from app.core.config import settings
from app.services.receipt_service import generate_receipt_pdf

if TYPE_CHECKING:
    from app.models.order import Order

logger = logging.getLogger(__name__)


async def print_order_receipt(order: Order) -> bool:
    """Generate and print a receipt for the given order.

    Returns True if print was submitted successfully, False otherwise.
    Never raises — all errors are logged and swallowed.
    """
    if not settings.print_enabled:
        logger.info("Printing disabled, skipping receipt for order %s", order.id)
        return False

    try:
        pdf_bytes = generate_receipt_pdf(order)
    except Exception:
        logger.exception("Failed to generate receipt PDF for order %s", order.id)
        return False

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, read=30.0)) as client:
            resp = await client.post(
                f"{settings.print_agent_url}/print",
                content=pdf_bytes,
                headers={"Content-Type": "application/pdf"},
            )
        if resp.status_code == 200:
            logger.info("Receipt printed for order %s", order.id)
            return True
        logger.warning(
            "Print agent returned %d for order %s: %s",
            resp.status_code,
            order.id,
            resp.text,
        )
        return False
    except httpx.ConnectError:
        logger.warning("Print agent unreachable, order %s receipt not printed", order.id)
        return False
    except httpx.TimeoutException:
        logger.warning("Print agent timeout for order %s", order.id)
        return False
    except Exception:
        logger.exception("Unexpected error printing receipt for order %s", order.id)
        return False
