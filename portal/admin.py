from django.contrib import admin
from .models import Child, ParentProfile

@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ['full_name','parent','birth_date','attended_before']
    search_fields = ['full_name','parent__parentprofile__phone']

@admin.register(ParentProfile)
class ParentAdmin(admin.ModelAdmin):
    list_display = ['full_name','phone','emergency_phone']
    search_fields = ['full_name','phone']
    readonly_fields = ['phone','user']
    def has_add_permission(self,request): return False
