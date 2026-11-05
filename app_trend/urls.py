from django.urls import path
from . import views

urlpatterns = [
    path('', views.trend, name='trend'),
]