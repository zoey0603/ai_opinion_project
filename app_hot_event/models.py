from django.db import models


class HotEvent(models.Model):
    tool = models.CharField(max_length=20)
    event_date = models.DateField()
    today_count = models.IntegerField(default=0)
    yesterday_count = models.IntegerField(default=0)
    growth_count = models.IntegerField(default=0)
    growth_rate = models.FloatField(default=0)
    top_keywords = models.TextField(blank=True)
    representative_titles = models.TextField(blank=True)
    possible_reason = models.TextField(blank=True)
    reason_source = models.CharField(max_length=30, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-event_date', '-created_at']

    def __str__(self):
        return f"{self.tool} {self.event_date} +{self.growth_count}"


class HotEventRAGQuery(models.Model):
    STATUS_CHOICES = [
        ('pending', 'pending'),
        ('running', 'running'),
        ('success', 'success'),
        ('failed', 'failed'),
    ]

    question = models.CharField(max_length=300)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    tool = models.CharField(max_length=20, default='ALL')
    retrieved_context = models.TextField(blank=True)
    stats_text = models.TextField(blank=True)
    answer = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', '-created_at']
        indexes = [
            models.Index(fields=['status', 'updated_at']),
            models.Index(fields=['tool', 'updated_at']),
        ]

    def __str__(self):
        return f"{self.question[:40]} - {self.status}"
