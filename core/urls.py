from django.urls import path,include
from .views import *


urlpatterns = [
    path('',home, name='home'),
    path('signin', signin, name= 'signin'),
    path('signup', signup, name='signup'),
    path('signout/', signout, name='signout'),


    path('index/', index,name='index'),
    path('ajax/', ajax, name= 'ajax'),
    path('scan/',scan,name='scan'),
    path('profiles/', profiles, name= 'profiles'),
    path('details/', details, name= 'details'),

    path('add_profile/',add_profile,name='add_profile'),
    path('edit_profile/<int:id>/',edit_profile,name='edit_profile'),
    path('delete_profile/<int:id>/',delete_profile,name='delete_profile'),


    path('clear_history/',clear_history,name='clear_history'),
    path('reset/',reset,name='reset'),

    path('camoff/',camoff,name='camoff'),

    path('attendance/',attendance,name='attendance'),
    path('attendance/download/',download,name='download'),



]
