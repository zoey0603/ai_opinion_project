from django.urls import path

from . import views

app_name = 'app_hot_event'

urlpatterns = [
    path('', views.home, name='home'),
]
