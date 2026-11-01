"""Management summaries distinguish scheduled lessons from recorded attendance."""
from datetime import timedelta
from django.utils import timezone
from catalog.models import OfficialHoliday


def lesson_summary(subscription, *, holidays=None, today=None):
    today = today or timezone.localdate()
    if holidays is None:
        holidays = set(OfficialHoliday.objects.filter(day__gte=subscription.starts_on, day__lt=subscription.expires_on).values_list('day', flat=True))
    dates = []
    day = subscription.starts_on
    while day < subscription.expires_on:
        if (day.weekday() + 2) % 7 == subscription.session.weekday and day not in holidays:
            dates.append(day)
        day += timedelta(days=1)
    attended = list(subscription.attendance_set.all())
    missed = list(subscription.absence_set.all())
    recorded = {entry.day for entry in attended} | {entry.missed_on for entry in missed}
    return {
        'planned': len(dates),
        'present': len(attended),
        'absent': len(missed),
        'remaining': 0 if subscription.cancelled_at else sum(day >= today and day not in recorded for day in dates),
        'unrecorded': sum(day < today and day not in recorded for day in dates),
        'dates': dates,
    }


def billing_status(subscription, today=None):
    today = today or timezone.localdate()
    if subscription.cancelled_at:
        return {'label': 'لغوشده', 'tone': 'muted', 'days': None}
    days = (subscription.expires_on - today).days
    if days <= 0:
        return {'label': 'نیازمند تمدید', 'tone': 'danger', 'days': days}
    if days <= 3:
        return {'label': 'نزدیک سررسید', 'tone': 'warning', 'days': days}
    return {'label': 'دارای اعتبار', 'tone': 'success', 'days': days}


def latest_subscriptions(subscriptions):
    latest = {}
    for sub in subscriptions:
        key = sub.child_id or (sub.parent_id, sub.child_name, sub.birth_date)
        if key not in latest or (sub.starts_on, sub.pk) > (latest[key].starts_on, latest[key].pk):
            latest[key] = sub
    return list(latest.values())
