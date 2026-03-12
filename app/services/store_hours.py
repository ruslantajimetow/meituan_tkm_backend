from datetime import datetime, time, timedelta, timezone

# Turkmenistan is UTC+5, no DST
TMT_OFFSET = timezone(timedelta(hours=5))


def current_tmt_time() -> time:
    """Return the current time in Turkmenistan timezone."""
    return datetime.now(TMT_OFFSET).time()


def is_store_open(
    opening_time: time | None,
    closing_time: time | None,
) -> bool:
    """Determine if a store is currently open based on its operating hours.

    Handles overnight hours (e.g., 22:00 - 06:00).
    Returns False if either time is not set.
    """
    if opening_time is None or closing_time is None:
        return False

    now = current_tmt_time()

    if opening_time <= closing_time:
        # Normal hours: e.g. 09:00 - 22:00
        return opening_time <= now < closing_time
    else:
        # Overnight hours: e.g. 22:00 - 06:00
        return now >= opening_time or now < closing_time
