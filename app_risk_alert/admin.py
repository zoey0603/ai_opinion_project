from django.contrib import admin

from .models import RiskAnalysisResult, RiskArticleJudgement


@admin.register(RiskAnalysisResult)
class RiskAnalysisResultAdmin(admin.ModelAdmin):
    list_display = ('tool', 'risk_score', 'risk_level', 'main_risk_type', 'total_count', 'created_at')
    list_filter = ('tool', 'risk_level', 'created_at')
    search_fields = ('risk_keywords', 'representative_titles')


@admin.register(RiskArticleJudgement)
class RiskArticleJudgementAdmin(admin.ModelAdmin):
    list_display = ('article', 'tool', 'is_risk', 'risk_type', 'judged_by', 'updated_at')
    list_filter = ('tool', 'is_risk', 'risk_type', 'judged_by', 'updated_at')
    search_fields = ('article__title', 'matched_keywords', 'reason', 'error_message')
    readonly_fields = ('created_at', 'updated_at')
