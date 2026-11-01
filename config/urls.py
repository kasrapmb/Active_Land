from django.contrib import admin
from django.urls import path, include
from catalog.views import home
from portal.views import health
urlpatterns = [path('health/',health), path('api/v1/', include('enrollment.api_urls')), path('registration/', include('enrollment.urls')), path('account/', include('portal.urls')), path('', home, name='home'), path('admin/', admin.site.urls)]
