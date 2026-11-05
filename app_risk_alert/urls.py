from django.urls import path

from . import views

app_name = 'app_risk_alert'

urlpatterns = [
    path('', views.home, name='home'),
]
