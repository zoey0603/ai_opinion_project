from django.contrib import admin
from .models import AnalysisReport

@admin.register(AnalysisReport)
class AnalysisReportAdmin(admin.ModelAdmin):
    list_display = ('tool', 'start_date', 'end_date', 'total_count', 'created_at')
    list_filter = ('tool', 'start_date', 'end_date', 'created_at')
    search_fields = ('tool', 'report')