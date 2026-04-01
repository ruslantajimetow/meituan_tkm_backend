"""Structured error codes for API responses.

Every HTTPException detail should be a dict with `code` and `message` so
frontends can match on stable codes and display localised, user-friendly text.

Usage:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=Errors.store_closed(),
    )
"""

from typing import Any


def _error(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "message": message, **extra}


class Errors:
    # ── Auth ──────────────────────────────────────────────────────────────────
    @staticmethod
    def invalid_credentials() -> dict:
        return _error("INVALID_CREDENTIALS", "Invalid email or password.")

    @staticmethod
    def phone_not_verified() -> dict:
        return _error("PHONE_NOT_VERIFIED", "Please verify your phone number first.")

    @staticmethod
    def token_expired() -> dict:
        return _error("TOKEN_EXPIRED", "Your session has expired. Please log in again.")

    @staticmethod
    def unauthorized() -> dict:
        return _error("UNAUTHORIZED", "You are not authorized to perform this action.")

    # ── Store ─────────────────────────────────────────────────────────────────
    @staticmethod
    def store_not_found() -> dict:
        return _error("STORE_NOT_FOUND", "Store not found.")

    @staticmethod
    def store_not_approved() -> dict:
        return _error("STORE_NOT_APPROVED", "This store is not yet approved.")

    @staticmethod
    def store_closed() -> dict:
        return _error("STORE_CLOSED", "This store is currently closed. Please try again during opening hours.")

    # ── Order ─────────────────────────────────────────────────────────────────
    @staticmethod
    def min_order_not_met(min_amount: float) -> dict:
        return _error(
            "MIN_ORDER_NOT_MET",
            f"Your order does not meet the minimum order amount of {min_amount:.0f}.",
            min_amount=min_amount,
        )

    @staticmethod
    def order_not_found() -> dict:
        return _error("ORDER_NOT_FOUND", "Order not found.")

    @staticmethod
    def order_already_cancelled() -> dict:
        return _error("ORDER_ALREADY_CANCELLED", "This order has already been cancelled.")

    @staticmethod
    def order_cannot_be_cancelled() -> dict:
        return _error("ORDER_CANNOT_BE_CANCELLED", "This order can no longer be cancelled.")

    @staticmethod
    def invalid_order_transition(current: str, requested: str) -> dict:
        return _error(
            "INVALID_ORDER_TRANSITION",
            f"Cannot change order status from '{current}' to '{requested}'.",
        )

    # ── Menu ──────────────────────────────────────────────────────────────────
    @staticmethod
    def menu_item_not_found(item_id: str | None = None) -> dict:
        msg = f"Menu item {item_id} not found in this store." if item_id else "Menu item not found."
        return _error("MENU_ITEM_NOT_FOUND", msg)

    @staticmethod
    def menu_item_unavailable(name: str) -> dict:
        return _error("MENU_ITEM_UNAVAILABLE", f"'{name}' is currently unavailable.")

    # ── Generic ───────────────────────────────────────────────────────────────
    @staticmethod
    def not_found(resource: str = "Resource") -> dict:
        return _error("NOT_FOUND", f"{resource} not found.")

    @staticmethod
    def internal() -> dict:
        return _error("INTERNAL_ERROR", "Something went wrong. Please try again later.")
