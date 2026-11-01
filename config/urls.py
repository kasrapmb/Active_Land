from django.contrib import admin
from django.urls import path, include
from catalog.views import home
urlpatterns = [path('account/', include('portal.urls')), path('', home, name='home'), path('admin/', admin.site.urls)]
