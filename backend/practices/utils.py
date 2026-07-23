# backend/practices/utils.py
import datetime
import math
import warnings
from collections.abc import Iterable

import holidays


def add_working_days(start_date: datetime.date, days: int, skip_dates: Iterable[datetime.date]) -> datetime.date:
    current = start_date
    added = 1
    while added < days:
        current += datetime.timedelta(days=1)
        if current.weekday() < 5 and current not in skip_dates:
            added += 1
    return current


def calculate_end_date(
    start_date: datetime.date, coefficient: float | None = None, daily_hours: int = 8, min_hours: int | None = None
) -> datetime.date:
    """
    Return the end date by adding the needed working days (hours/daily_hours),
    skipping weekends and national holidays for `country`.

    Args:
        start_date: Start date of the practice.
        coefficient: DEPRECATED — use min_hours instead. If provided, hours = round(coefficient * 160).
        daily_hours: Number of hours per working day (default 8).
        min_hours: Total minimum hours for the practice (from Subject.min_hours).
                   Takes precedence over coefficient if provided.
    """
    if min_hours is not None:
        hours = min_hours
    elif coefficient is not None:
        warnings.warn(
            "coefficient is deprecated, use min_hours instead",
            DeprecationWarning,
            stacklevel=2,
        )
        hours = round(coefficient * 160)
    else:
        hours = 480  # default KI/BOP

    working_days = math.ceil(hours / daily_hours)
    skip_dates = holidays.country_holidays("CZ")
    return add_working_days(start_date, working_days, skip_dates)
