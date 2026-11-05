from django.contrib import admin

from .models import DigestReport


@admin.register(DigestReport)
class DigestReportAdmin(admin.ModelAdmin):
    list_display = ('tool', 'report_type', 'start_date', 'end_date', 'total_count', 'created_at')
    list_filter = ('tool', 'report_type', 'created_at')
    search_fields = ('digest_text',)

