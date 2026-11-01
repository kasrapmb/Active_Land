from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from catalog.billing import persian_date
from catalog.models import ClassType, OfficialHoliday, Session, Subscription
from portal.models import Child
from .forms import AttendanceForm
from .models import Booking
from .roster import billing_status, latest_subscriptions, lesson_summary
from .services import record_attendance


def require_staff(request):
    if not request.user.is_staff:
        raise Http404


def session_cards(queryset):
    today = timezone.localdate()
    queryset = queryset.select_related('class_type').prefetch_related(
        Prefetch('subscription_set', queryset=Subscription.objects.all()),
        Prefetch('booking_set', queryset=Booking.objects.filter(status='held', reserved_until__gt=timezone.now())),
    )
    result = []
    for slot in queryset:
        latest = [sub for sub in latest_subscriptions(slot.subscription_set.all()) if not sub.cancelled_at]
        active = sum(sub.starts_on <= today < sub.expires_on for sub in latest)
        due = sum(sub.expires_on <= today for sub in latest)
        soon = sum(today < sub.expires_on <= today + timedelta(days=3) for sub in latest)
        holds = len(slot.booking_set.all())
        result.append({'session': slot, 'active': active, 'due': due, 'soon': soon, 'holds': holds,
                       'available': max(0, slot.capacity - active - holds)})
    return result


def management_classes():
    courses = list(ClassType.objects.all())
    cards = session_cards(Session.objects.all())
    for course in courses:
        course.management_sessions = [card for card in cards if card['session'].class_type_id == course.pk]
        course.active_children = sum(card['active'] for card in course.management_sessions)
        course.due_count = sum(card['due'] for card in course.management_sessions)
    return courses


@login_required
@permission_required('catalog.view_subscription', raise_exception=True)
def class_detail(request, pk):
    require_staff(request)
    course = get_object_or_404(ClassType, pk=pk)
    return render(request, 'enrollment/class_detail.html', {'course': course, 'sessions': session_cards(course.sessions.all())})


@login_required
@permission_required(('catalog.view_subscription', 'portal.view_child', 'portal.view_parentprofile'), raise_exception=True)
def session_detail(request, pk):
    require_staff(request)
    slot = get_object_or_404(Session.objects.select_related('class_type'), pk=pk)
    today = timezone.localdate()
    date_form = AttendanceForm({'day': request.GET.get('day', persian_date(today)), 'status': 'present'})
    selected = date_form.cleaned_data['day'] if date_form.is_valid() else today
    if date_form.errors:
        messages.error(request, 'تاریخ واردشده معتبر نبود؛ امروز نمایش داده شد.')
    subscriptions = list(Subscription.objects.filter(session=slot).select_related('child', 'parent__parentprofile', 'session').prefetch_related('attendance_set', 'absence_set').order_by('-starts_on', '-pk'))
    live = [sub for sub in latest_subscriptions(subscriptions) if not sub.cancelled_at]
    holidays = set(OfficialHoliday.objects.filter(day__gte=min((sub.starts_on for sub in subscriptions), default=today), day__lte=max((sub.expires_on for sub in subscriptions), default=today)).values_list('day', flat=True))
    chosen_status = request.GET.get('status', 'active')
    if chosen_status not in ('active', 'due', 'all'):
        chosen_status = 'active'
    search = request.GET.get('q', '').strip()[:150].translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789'))
    rows = []
    for sub in live:
        bill = billing_status(sub, today)
        if chosen_status == 'active' and not sub.starts_on <= today < sub.expires_on:
            continue
        if chosen_status == 'due' and sub.expires_on > today:
            continue
        profile = getattr(sub.parent, 'parentprofile', None)
        if search and search not in sub.child_name and search not in (profile.phone if profile else ''):
            continue
        attendance = next((entry for entry in sub.attendance_set.all() if entry.day == selected), None)
        absence = next((entry for entry in sub.absence_set.all() if entry.missed_on == selected), None)
        rows.append({'subscription': sub, 'profile': profile, 'billing': bill,
                     'lessons': lesson_summary(sub, holidays=holidays, today=today),
                     'attendance': 'present' if attendance else 'absent' if absence else '',
                     'can_record': sub.starts_on <= selected < sub.expires_on and selected <= today and (selected.weekday() + 2) % 7 == slot.weekday and selected not in holidays})
    return render(request, 'enrollment/session_detail.html', {
        'slot': slot, 'summary': session_cards(Session.objects.filter(pk=pk))[0], 'rows': rows,
        'selected_day': persian_date(selected), 'status': chosen_status, 'search': search,
        'is_class_day': (selected.weekday() + 2) % 7 == slot.weekday and selected not in holidays,
    })


@login_required
@permission_required(('catalog.view_subscription', 'portal.view_child', 'portal.view_parentprofile'), raise_exception=True)
def child_detail(request, pk):
    require_staff(request)
    child = get_object_or_404(Child.objects.select_related('parent__parentprofile'), pk=pk)
    return render(request, 'portal/child_detail.html', child_context(child, manager=True))


def child_context(child, *, manager=False):
    subscriptions = Subscription.objects.filter(child=child).select_related('session__class_type').prefetch_related('attendance_set', 'absence_set').order_by('-starts_on', '-pk')
    rows = [{'subscription': sub, 'lessons': lesson_summary(sub), 'billing': billing_status(sub)} for sub in subscriptions]
    return {'child': child, 'profile': getattr(child.parent, 'parentprofile', None), 'history': rows, 'manager_view': manager}


@login_required
@permission_required('enrollment.change_booking', raise_exception=True)
@require_POST
def attendance(request, pk):
    require_staff(request)
    sub = get_object_or_404(Subscription, pk=pk)
    form = AttendanceForm(request.POST)
    if form.is_valid():
        try:
            record_attendance(actor=request.user, subscription_id=pk, day=form.cleaned_data['day'], status=form.cleaned_data['status'])
        except ValidationError as error:
            messages.error(request, ' '.join(error.messages))
        else:
            messages.success(request, 'حضور و غیاب ذخیره شد.')
    else:
        messages.error(request, 'تاریخ شمسی و وضعیت معتبر وارد کنید.')
    from django.urls import reverse
    from urllib.parse import urlencode
    date = form.cleaned_data.get('day')
    filters = {}
    if date:
        filters['day'] = persian_date(date)
    status = request.POST.get('return_status', 'active')
    if status in ('active', 'due', 'all'):
        filters['status'] = status
    if request.POST.get('return_q'):
        filters['q'] = request.POST['return_q'][:150]
    query = urlencode(filters)
    return redirect(reverse('management-session', args=[sub.session_id]) + ('?' + query if query else ''))
