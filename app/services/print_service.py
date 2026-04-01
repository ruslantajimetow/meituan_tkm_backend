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


async def print_order_receipt(order: Order, print_server_url: str | None = None) -> bool:
    """Generate and print a receipt for the given order.

    Uses the store's registered print_server_url if provided, otherwise falls
    back to the PRINT_AGENT_URL env var.

    Returns True if print was submitted successfully, False otherwise.
    Never raises — all errors are logged and swallowed.
    """
    logger.info("[PRINT] print_enabled=%s, store url=%s, fallback url=%s",
                settings.print_enabled, print_server_url, settings.print_agent_url)

    if not settings.print_enabled:
        logger.info("[PRINT] Printing disabled, skipping receipt for order %s", order.id)
        return False

    target_url = print_server_url or settings.print_agent_url
    logger.info("[PRINT] Sending receipt for order %s to %s/print", order.id, target_url)

    try:
        pdf_bytes = generate_receipt_pdf(order)
        logger.info("[PRINT] PDF generated for order %s, size=%d bytes", order.id, len(pdf_bytes))
    except Exception:
        logger.exception("[PRINT] Failed to generate receipt PDF for order %s", order.id)
        return False

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, read=30.0)) as client:
            resp = await client.post(
                f"{target_url}/print",
                content=pdf_bytes,
                headers={"Content-Type": "application/pdf"},
            )
        logger.info("[PRINT] Print agent responded %d for order %s: %s",
                    resp.status_code, order.id, resp.text)
        if resp.status_code == 200:
            return True
        return False
    except httpx.ConnectError as e:
        logger.warning("[PRINT] Connect error reaching %s for order %s: %s", target_url, order.id, e)
        return False
    except httpx.TimeoutException:
        logger.warning("[PRINT] Timeout reaching %s for order %s", target_url, order.id)
        return False
    except Exception:
        logger.exception("[PRINT] Unexpected error printing receipt for order %s", order.id)
        return False
