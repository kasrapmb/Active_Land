from django.contrib import admin
from .models import ClassType, Session

admin.site.site_header = 'مدیریت اکتیولند'
admin.site.site_title = 'اکتیولند'
admin.site.index_title = 'مدیریت کلاس‌ها و سانس‌ها'

class SessionInline(admin.TabularInline):
    model = Session
    extra = 0

@admin.register(ClassType)
class ClassTypeAdmin(admin.ModelAdmin):
    list_display = ['name','min_age_months','max_age_months','monthly_fee','active']
    list_filter = ['active']
    search_fields = ['name']
    inlines = [SessionInline]

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['class_type','weekday','start_time','end_time','capacity','active']
    list_filter = ['class_type','weekday','active']

from .models import Subscription, OfficialHoliday
from .billing import persian_date

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['child_name','parent','session','start_date','renewal_date','paid_amount']
    list_filter = ['session']
    search_fields = ['child_name','payment_reference','parent__username']
    readonly_fields = [field.name for field in Subscription._meta.fields]

    @admin.display(description='شروع اعتبار')
    def start_date(self, obj):
        return persian_date(obj.starts_on)

    @admin.display(description='سررسید تمدید')
    def renewal_date(self, obj):
        return persian_date(obj.expires_on)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

@admin.register(OfficialHoliday)
class OfficialHolidayAdmin(admin.ModelAdmin):
    list_display = ['title','day']
    ordering = ['day']
