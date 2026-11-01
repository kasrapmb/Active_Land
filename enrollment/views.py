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
    return render(request,'enrollment/booking.html',{'item':item})

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
