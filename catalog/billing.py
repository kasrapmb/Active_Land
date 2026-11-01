"""Rolling calendar-month validity; expiry is exclusive and requires renewal."""
import jdatetime


def next_month(start):
    current = jdatetime.date.fromgregorian(date=start)
    year, month = (current.year + 1, 1) if current.month == 12 else (current.year, current.month + 1)
    day = current.day
    while day:
        try:
            return jdatetime.date(year, month, day).togregorian()
        except ValueError:
            day -= 1
    raise ValueError('Invalid subscription date')


def persian_date(value):
    return jdatetime.date.fromgregorian(date=value).strftime('%Y/%m/%d').translate(str.maketrans('0123456789','۰۱۲۳۴۵۶۷۸۹'))
