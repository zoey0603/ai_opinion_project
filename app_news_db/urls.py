from django.urls import path

from . import views

app_name = "app_news_db"

urlpatterns = [
    path("", views.news_db, name="news_db"),
]
