"""Session-authenticated JSON API. CSRF protection applies to every mutation."""
import json
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_GET,require_http_methods
from catalog.models import ClassType,Session
from portal.forms import ChildForm
from portal.models import Child
from .models import Booking
from .services import active_count,join_waiting,reserve


def error(message,status=400):
    return JsonResponse({'error':message},status=status)

@require_GET
def catalog(request):
    result=[]
    for item in ClassType.objects.filter(active=True).prefetch_related('sessions'):
        result.append({'id':item.pk,'slug':item.slug,'name':item.name,'min_age_months':item.min_age_months,'max_age_months':item.max_age_months,'monthly_fee_toman':item.monthly_fee,'duration_minutes':item.duration_minutes,'sessions':[{'id':slot.pk,'day':slot.get_weekday_display(),'start':str(slot.start_time),'end':str(slot.end_time),'available':max(0,slot.capacity-active_count(slot))} for slot in item.sessions.all() if slot.active]})
    return JsonResponse({'classes':result})

@require_http_methods(['GET','POST'])
def children(request):
    if not request.user.is_authenticated: return error('ورود الزامی است.',401)
    if request.method == 'GET':
        return JsonResponse({'children':list(Child.objects.filter(parent=request.user).values('id','full_name','birth_date','gender','attended_before','notes'))})
    try:
        data=json.loads(request.body)
        if not isinstance(data,dict): return error('بدنه JSON معتبر وارد کنید.')
    except (ValueError,UnicodeDecodeError): return error('بدنه JSON معتبر وارد کنید.')
    form=ChildForm(data)
    if not form.is_valid(): return JsonResponse({'errors':form.errors.get_json_data()},status=400)
    child=form.save(commit=False)
    child.parent=request.user
    child.save()
    return JsonResponse({'id':child.pk},status=201)

@require_http_methods(['GET','POST'])
def bookings(request):
    if not request.user.is_authenticated: return error('ورود الزامی است.',401)
    if request.method=='GET':
        return JsonResponse({'bookings':list(Booking.objects.filter(child__parent=request.user).values('id','child_id','session_id','amount','status','reserved_until','subscription_id'))})
    try:
        data=json.loads(request.body)
        if not isinstance(data,dict) or data.get('accept_rules') is not True: return error('پذیرش قوانین الزامی است.')
        child_id=int(data['child_id']); session_id=int(data['session_id'])
        if data.get('action')=='waiting':
            result=join_waiting(actor=request.user,child_id=child_id,session_id=session_id)
        else:
            result=reserve(actor=request.user,child_id=child_id,session_id=session_id)
    except (ValueError,KeyError,TypeError,UnicodeDecodeError): return error('ورودی نامعتبر است.')
    except (Child.DoesNotExist,Session.DoesNotExist): return error('یافت نشد.',404)
    except ValidationError as exc: return error(' '.join(exc.messages),409)
    return JsonResponse({'id':str(result.pk)},status=201)
