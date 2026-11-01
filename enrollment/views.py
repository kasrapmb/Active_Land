from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404,redirect,render
from django.views.decorators.http import require_POST
from catalog.models import Session
from .forms import OfflinePaymentForm,RegistrationForm
from .models import Booking
from .services import active_count,cancel,confirm_offline,join_waiting,reserve

@login_required
def register(request,session_id):
    session = get_object_or_404(Session.objects.select_related('class_type'),pk=session_id,active=True,class_type__active=True)
    form = RegistrationForm(request.POST or None,user=request.user)
    available = max(0,session.capacity-active_count(session))
    if request.method == 'POST' and form.is_valid():
        try:
            if request.POST.get('action') == 'waiting':
                join_waiting(actor=request.user,child_id=form.cleaned_data['child'].pk,session_id=session.pk)
                messages.success(request,'در فهرست انتظار ثبت شدید. پس از آزادشدن ظرفیت، پیامک دعوت ارسال می‌شود.')
                return redirect('dashboard')
            booking = reserve(actor=request.user,child_id=form.cleaned_data['child'].pk,session_id=session.pk)
            return redirect('booking',pk=booking.pk)
        except ValidationError as error:
            form.add_error(None,error)
    return render(request,'enrollment/register.html',{'form':form,'session':session,'available':available})

@login_required
def booking(request,pk):
    item = get_object_or_404(Booking.objects.select_related('child','session__class_type'),pk=pk,child__parent=request.user)
    return render(request,'enrollment/booking.html',{'item':item,'payment_enabled':bool(settings.PAYMENT_BACKEND)})

@login_required
@permission_required('enrollment.change_booking',raise_exception=True)
def offline_payment(request,pk):
    if not request.user.is_staff:
        raise Http404
    item = get_object_or_404(Booking.objects.select_related('child','session__class_type'),pk=pk)
    form = OfflinePaymentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        from django.db import IntegrityError
        try:
            confirm_offline(actor=request.user,booking_id=item.pk,reference=form.cleaned_data['reference'])
        except (ValidationError,IntegrityError):
            form.add_error(None,'ثبت پرداخت انجام نشد؛ وضعیت رزرو و تکراری‌نبودن رسید را بررسی کنید.')
        else:
            messages.success(request,'پرداخت و اشتراک تأیید شدند.')
            return redirect('/admin/enrollment/booking/')
    return render(request,'portal/form.html',{'form':form,'title':f'تأیید پرداخت حضوری: {item.child.full_name}','intro':'فقط پس از دریافت و تأیید مبلغ کامل رسید را ثبت کنید.','button':'ثبت قطعی پرداخت'})

@login_required
@permission_required('enrollment.change_booking',raise_exception=True)
@require_POST
def cancel_booking(request,pk):
    cancel(actor=request.user,booking_id=get_object_or_404(Booking,pk=pk).pk)
    messages.success(request,'ثبت‌نام لغو شد؛ بازپرداخت باید توسط پشتیبانی پیگیری شود.')
    return redirect('/admin/enrollment/booking/')

@login_required
@require_POST
def pay(request,pk):
    from django.conf import settings
    from django.urls import reverse
    from .gateway import GatewayUnavailable
    from .services import start_gateway
    item=get_object_or_404(Booking,pk=pk,child__parent=request.user)
    callback=settings.PUBLIC_BASE_URL.rstrip('/')+reverse('payment-callback',args=[item.pk])
    try:
        destination=start_gateway(actor=request.user,booking_id=item.pk,callback_url=callback)
    except (GatewayUnavailable,ValidationError):
        messages.error(request,'درگاه در دسترس نیست یا رزرو منقضی شده است؛ پرداخت تأیید نشده است.')
        return redirect('booking',pk=item.pk)
    return redirect(destination)


def payment_callback(request,pk):
    from .gateway import GatewayUnavailable
    from .services import verify_gateway
    item=get_object_or_404(Booking,pk=pk)
    try:
        payment=verify_gateway(booking_id=item.pk,authority=request.GET.get('Authority',''))
    except (GatewayUnavailable,ValidationError):
        title='پرداخت تأیید نشد'
        message='وضعیت پرداخت نیازمند بررسی است. اگر وجه کسر شده، با پشتیبانی پیگیری کنید؛ ثبت‌نام قطعی اعلام نشده است.'
    else:
        title='پرداخت نیازمند پیگیری است' if payment.needs_review else 'پرداخت تأیید شد'
        message='پرداخت پس از پایان رزرو دریافت شده است؛ پشتیبانی باید تخصیص ظرفیت یا بازپرداخت را پیگیری کند.' if payment.needs_review else 'برای مشاهده وضعیت ثبت‌نام و رسید، وارد حساب والدین شوید.'
    # Public callback never discloses child data or payment identifiers.
    return render(request,'enrollment/result.html',{'title':title,'message':message})

@login_required
@permission_required('enrollment.change_booking',raise_exception=True)
def transfer_booking(request,pk):
    from .forms import TransferForm
    from .services import transfer
    if not request.user.is_staff: raise Http404
    item=get_object_or_404(Booking,pk=pk)
    form=TransferForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        try: transfer(actor=request.user,booking_id=item.pk,target_id=form.cleaned_data['target'].pk,note=form.cleaned_data['note'])
        except ValidationError as error: form.add_error(None,error)
        else:
            messages.success(request,'انتقال ثبت شد؛ مبلغ پرداخت قبلی بدون تغییر در سوابق باقی ماند.')
            return redirect('/admin/enrollment/booking/')
    return render(request,'portal/form.html',{'form':form,'title':'انتقال سانس','button':'ثبت انتقال'})

@login_required
@permission_required('catalog.view_subscription',raise_exception=True)
def management(request):
    if not request.user.is_staff: raise Http404
    from django.db.models import Sum
    from catalog.models import Subscription
    from .models import GatewayPayment,WaitingEntry
    subs=Subscription.objects.select_related('parent','session__class_type').order_by('-created_at')
    report=subs.values('session__class_type__name').annotate(total=Sum('paid_amount')).order_by('session__class_type__name')
    return render(request,'enrollment/management.html',{'total':subs.aggregate(total=Sum('paid_amount'))['total'] or 0,'report':report,'subscriptions':subs[:100],'bookings':Booking.objects.select_related('child','session__class_type').order_by('-created_at')[:100],'review':GatewayPayment.objects.filter(needs_review=True).count(),'waiting':WaitingEntry.objects.filter(active=True).count()})

@login_required
@permission_required('catalog.view_subscription',raise_exception=True)
def export(request):
    if not request.user.is_staff: raise Http404
    from io import BytesIO
    from openpyxl import Workbook
    from django.http import HttpResponse
    from catalog.billing import persian_date
    from catalog.models import Subscription
    book=Workbook();sheet=book.active;sheet.title='ثبت‌نام‌ها';sheet.sheet_view.rightToLeft=True
    sheet.append(['کودک','کلاس','روز','مبلغ تومان','شروع','سررسید','وضعیت'])
    for row in Subscription.objects.select_related('session__class_type').iterator():
        # Prefix spreadsheet formula markers in all user-provided cells.
        def safe(value):
            value=str(value)
            return "'"+value if value.lstrip().startswith(('=','+','-','@')) else value
        sheet.append([safe(row.child_name),safe(row.session.class_type.name),row.session.get_weekday_display(),row.paid_amount,persian_date(row.starts_on),persian_date(row.expires_on),'لغوشده' if row.cancelled_at else 'ثبت‌شده'])
    buffer=BytesIO();book.save(buffer)
    response=HttpResponse(buffer.getvalue(),content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition']='attachment; filename="activeland-enrollments.xlsx"'
    response['Cache-Control']='no-store'
    return response

@login_required
@permission_required('enrollment.change_booking',raise_exception=True)
def manual_registration(request):
    from .forms import ManualRegistrationForm
    from catalog.services import record_paid_month
    from django.db import IntegrityError
    if not request.user.is_staff: raise Http404
    form=ManualRegistrationForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        data=form.cleaned_data;child=data['child']
        try:
            record_paid_month(parent=child.parent,child_name=child.full_name,birth_date=child.birth_date,session_id=data['session'].pk,payment_reference=data['reference'],recorded_by=request.user,age_override_reason=data['age_override_reason'])
        except (ValidationError,IntegrityError,PermissionError):
            form.add_error(None,'ثبت انجام نشد؛ سن، ظرفیت، اشتراک تکراری و شناسه رسید را بررسی کنید. استثنای سن فقط با دلیل و دسترسی مدیر سایت مجاز است.')
        else:
            messages.success(request,'اشتراک و رسید پرداخت حضوری ثبت شد.')
            return redirect('management')
    return render(request,'portal/form.html',{'form':form,'title':'ثبت‌نام دستی','intro':'فقط پس از دریافت و تأیید شهریه کامل ثبت کنید. حساب والد و کودک باید از قبل ایجاد شده باشند.','button':'ثبت قطعی اشتراک'})
