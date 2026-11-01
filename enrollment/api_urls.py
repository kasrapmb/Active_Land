from django.urls import path
from . import api
urlpatterns=[path('catalog/',api.catalog),path('children/',api.children),path('bookings/',api.bookings)]
