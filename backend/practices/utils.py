# backend/practices/utils.py
import datetime
import math
from typing import Iterable

import holidays


def add_working_days(start_date: datetime.date, days: int, skip_dates: Iterable[datetime.date]) -> datetime.date:
    current = start_date
    added = 0
    while added < days:
        current += datetime.timedelta(days=1)
        if current.weekday() < 5 and current not in skip_dates:
            added += 1
    return current


def calculate_end_date(start_date: datetime.date, coeficient: float = 1, daily_hours: int = 8) -> datetime.date:
    """
    Return the end date by adding the needed working days (hours/daily_hours),
    skipping weekends and national holidays for `country`.
    """
    hours = math.floor(round(coeficient * 160))

    working_days = math.ceil(hours / daily_hours)
    skip_dates = holidays.CountryHoliday("CZ")
    return add_working_days(start_date, working_days, skip_dates)
