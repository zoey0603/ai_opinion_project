from django.urls import path

from . import views

app_name = 'app_ai_digest'

urlpatterns = [
    path('', views.home, name='home'),
    path('history/', views.history, name='history'),
]
