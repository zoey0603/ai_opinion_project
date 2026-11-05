from django.contrib import admin

from .models import ClassificationRecord


@admin.register(ClassificationRecord)
class ClassificationRecordAdmin(admin.ModelAdmin):
    list_display = ('predicted_tool', 'predicted_sentiment', 'predicted_topic', 'predicted_risk_type', 'created_at')
    list_filter = ('predicted_tool', 'predicted_sentiment', 'predicted_topic', 'predicted_risk_type', 'created_at')
    search_fields = ('title', 'input_text', 'keywords', 'explanation')
