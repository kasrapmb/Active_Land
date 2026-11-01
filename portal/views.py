from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .authentication import DeliveryUnavailable, request_code, verify_code
from .forms import ChildForm, CodeForm, PhoneForm, ProfileForm
from .models import Child, ParentProfile
from catalog.models import Subscription
from enrollment.models import Booking

def login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = PhoneForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            phone = request_code(form.cleaned_data['phone'],request.META.get('REMOTE_ADDR','unknown'))
        except ValidationError as error:
            form.add_error(None,error)
        except Exception:
            # Provider failures must never return credentials or response bodies.
            form.add_error(None,'ارسال پیامک در دسترس نیست؛ کمی بعد تلاش کنید یا با مجموعه تماس بگیرید.')
        else:
            request.session['login_phone'] = phone
            return redirect('verify')
    return render(request,'portal/form.html',{'form':form,'title':'ورود والدین','intro':'با شماره همراه وارد شوید؛ حساب شما پس از تأیید ساخته می‌شود.','button':'دریافت کد ورود'})

def verify(request):
    phone = request.session.get('login_phone')
    if not phone:
        return redirect('login')
    form = CodeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = verify_code(phone,form.cleaned_data['code'])
        if user:
            auth_login(request,user)
            request.session.pop('login_phone',None)
            return redirect('dashboard')
        form.add_error(None,'کد نامعتبر یا منقضی شده است؛ پس از پنج تلاش، کد تازه بگیرید.')
    return render(request,'portal/form.html',{'form':form,'title':'کد ورود را وارد کنید','intro':'کد تا سه دقیقه معتبر است.','button':'ورود به حساب','back':'login'})

@login_required
@require_POST
def logout(request):
    auth_logout(request)
    return redirect('home')

@login_required
def dashboard(request):
    return render(request,'portal/dashboard.html',{'bookings':Booking.objects.filter(child__parent=request.user).select_related('child','session__class_type').order_by('-created_at'), 'children':request.user.children.all(),'subscriptions':Subscription.objects.filter(parent=request.user).select_related('session__class_type').order_by('-starts_on')})

@login_required
def profile(request):
    instance, _ = ParentProfile.objects.get_or_create(user=request.user,defaults={'phone':request.user.username.removeprefix('parent:')})
    form = ProfileForm(request.POST or None,instance=instance)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request,'اطلاعات والد ذخیره شد.')
        return redirect('dashboard')
    return render(request,'portal/form.html',{'form':form,'title':'اطلاعات والد','button':'ذخیره اطلاعات'})

@login_required
def child_add(request):
    form = ChildForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        child = form.save(commit=False)
        child.parent = request.user
        child.save()
        messages.success(request,'فرزند شما اضافه شد.')
        return redirect('dashboard')
    return render(request,'portal/form.html',{'form':form,'title':'افزودن فرزند','button':'ثبت اطلاعات کودک'})

@login_required
def receipt(request,pk):
    item = get_object_or_404(Subscription.objects.select_related('session__class_type'),pk=pk,parent=request.user)
    return render(request,'portal/receipt.html',{'item':item})
