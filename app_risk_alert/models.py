from django.db import models
from app_news_db.models import NewsArticle


class RiskAnalysisResult(models.Model):
    tool = models.CharField(max_length=20)
    total_count = models.IntegerField(default=0)
    negative_count = models.IntegerField(default=0)
    risk_count = models.IntegerField(default=0)
    risk_score = models.FloatField(default=0)
    risk_level = models.CharField(max_length=20, blank=True)
    main_risk_type = models.CharField(max_length=50, blank=True)
    risk_keywords = models.TextField(blank=True)
    representative_titles = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tool} - {self.risk_level} ({self.risk_score})"


class RiskArticleJudgement(models.Model):
    article = models.ForeignKey(NewsArticle, on_delete=models.CASCADE, related_name='risk_judgements')
    tool = models.CharField(max_length=20)
    matched_keywords = models.TextField(blank=True)
    keyword_risk_types = models.TextField(blank=True)
    is_risk = models.BooleanField(default=False)
    risk_type = models.CharField(max_length=50, blank=True)
    reason = models.TextField(blank=True)
    judged_by = models.CharField(max_length=20, default='ollama')
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('article', 'tool')
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['tool', 'is_risk']),
            models.Index(fields=['judged_by']),
            models.Index(fields=['risk_type']),
        ]

    def __str__(self):
        return f"{self.tool} - {self.article_id} - {'risk' if self.is_risk else 'not risk'}"
