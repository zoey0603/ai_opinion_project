from django.urls import path
from . import views

app_name = "app_ai_report"

urlpatterns = [
    path('', views.home, name='home'),
    path('generate/', views.generate_report, name='generate_report'),
    path('history/', views.history, name='history'),
]