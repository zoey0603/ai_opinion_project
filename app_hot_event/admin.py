from django.contrib import admin

from .models import HotEvent, HotEventRAGQuery


@admin.register(HotEvent)
class HotEventAdmin(admin.ModelAdmin):
    list_display = ('tool', 'event_date', 'today_count', 'yesterday_count', 'growth_rate', 'reason_source', 'created_at')
    list_filter = ('tool', 'reason_source', 'event_date', 'created_at')
    search_fields = ('top_keywords', 'representative_titles', 'possible_reason')


@admin.register(HotEventRAGQuery)
class HotEventRAGQueryAdmin(admin.ModelAdmin):
    list_display = ('question', 'tool', 'status', 'start_date', 'end_date', 'updated_at')
    list_filter = ('status', 'tool', 'created_at')
    search_fields = ('question', 'answer', 'retrieved_context', 'stats_text')
