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
