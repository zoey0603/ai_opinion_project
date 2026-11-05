from django.contrib import admin
from .models import DataUpdateLog, NewsArticle

@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'tool', 'date', 'source', 'sentiment', 'created_at')
    search_fields = ('title', 'content', 'source', 'tool', 'keywords')
    list_filter = ('tool', 'sentiment', 'source', 'date')


@admin.register(DataUpdateLog)
class DataUpdateLogAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'last_updated', 'created_at')
    search_fields = ('name', 'message')
    list_filter = ('name', 'status', 'created_at')
