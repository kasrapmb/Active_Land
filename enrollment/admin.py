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
    list_display = ['child','session','created_at','notified_at','active']
    list_filter = ['session','active']

@admin.register(Notification)
class NotificationAdmin(ReadOnlyAdmin):
    list_display = ['recipient','created_at','sent_at','attempts']

@admin.register(AuditEvent)
class AuditAdmin(ReadOnlyAdmin):
    list_display = ['actor','action','booking','created_at']
