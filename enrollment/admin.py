from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import AuditEvent,Booking,Notification,WaitingEntry

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['child','session','amount','status','created_at','payment_action']
    list_filter = ['status','session']
    search_fields = ['child__full_name','child__parent__parentprofile__phone']
    readonly_fields = [field.name for field in Booking._meta.fields]
    @admin.display(description='پرداخت حضوری')
    def payment_action(self,obj):
        if obj.status == 'held':
            return format_html('<a href="{}">تأیید رسید</a>',reverse('offline-payment',args=[obj.pk]))
        return '—'
    def has_add_permission(self,request): return False
    def has_delete_permission(self,request,obj=None): return False

class ReadOnlyAdmin(admin.ModelAdmin):
    def get_readonly_fields(self,request,obj=None): return [field.name for field in self.model._meta.fields]
    def has_add_permission(self,request): return False
    def has_delete_permission(self,request,obj=None): return False
    def has_change_permission(self,request,obj=None): return False

@admin.register(WaitingEntry)
class WaitingAdmin(ReadOnlyAdmin):
    actions=['close_requests']
    def has_change_permission(self,request,obj=None):
        return request.user.has_perm('enrollment.change_waitingentry')
    @admin.action(description='بستن درخواست‌های انتخاب‌شده پس از پیگیری پشتیبانی')
    def close_requests(self,request,queryset):
        from django.db import transaction
        from catalog.models import Session
        from .services import notify_opening
        with transaction.atomic():
            sessions=list(Session.objects.select_for_update().filter(pk__in=queryset.values('session_id')).order_by('pk'))
            for entry in queryset:
                self.log_change(request,entry,'Waiting request closed by support')
            queryset.update(active=False)
            for session in sessions: notify_opening(session)
    list_display = ['child','session','created_at','notified_at','active']
    list_filter = ['session','active']

@admin.register(Notification)
class NotificationAdmin(ReadOnlyAdmin):
    list_display = ['recipient','created_at','sent_at','attempts']

@admin.register(AuditEvent)
class AuditAdmin(ReadOnlyAdmin):
    list_display = ['actor','action','booking','created_at']

from .models import Absence,GatewayPayment
@admin.register(Absence)
class AbsenceAdmin(admin.ModelAdmin):
    list_display=['subscription','missed_on','makeup_on','recorded_by']
    exclude=['recorded_by']
    def save_model(self,request,obj,form,change):
        obj.recorded_by=request.user
        super().save_model(request,obj,form,change)

@admin.register(GatewayPayment)
class GatewayAdmin(ReadOnlyAdmin):
    list_display=['booking','amount','needs_review','verified_at']
    list_filter=['needs_review']


from .models import Attendance
@admin.register(Attendance)
class AttendanceAdmin(ReadOnlyAdmin):
    list_display = ['subscription', 'day', 'recorded_by']
    list_filter = ['day']
