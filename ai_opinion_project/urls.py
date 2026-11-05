"""
URL configuration for ai_opinion_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('app_home.urls')),
    path('topword/', include('app_topword.urls')),
    path('trend/', include('app_trend.urls')),
    path('compare/', include('app_compare.urls')),
    path('recommend/', include('app_recommend.urls')),
    path('news-db/', include('app_news_db.urls')),
    path('ai-report/', include('app_ai_report.urls')),
    path('ai-digest/', include('app_ai_digest.urls')),
    path('risk-alert/', include('app_risk_alert.urls')),
    path('hot-event/', include('app_hot_event.urls')),
    path('classification/', include('app_text_classification.urls')),
]
