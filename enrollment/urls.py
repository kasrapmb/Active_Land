from django.urls import path
from . import views
urlpatterns = [path('session/<int:session_id>/',views.register,name='register'),path('<uuid:pk>/',views.booking,name='booking'),path('<uuid:pk>/offline-payment/',views.offline_payment,name='offline-payment'),path('<uuid:pk>/cancel/',views.cancel_booking,name='cancel-booking')]
