from django.urls import path
from . import views
urlpatterns = [path('',views.dashboard,name='dashboard'),path('login/',views.login,name='login'),path('verify/',views.verify,name='verify'),path('logout/',views.logout,name='logout'),path('profile/',views.profile,name='profile'),path('children/new/',views.child_add,name='child-add'),path('receipts/<int:pk>/',views.receipt,name='receipt')]
