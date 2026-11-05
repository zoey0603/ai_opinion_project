from django.db import models


class NewsArticle(models.Model):
    TOOL_CHOICES = [
        ('ChatGPT', 'ChatGPT'),
        ('Gemini', 'Gemini'),
        ('Claude', 'Claude'),
        ('Other', 'Other'),
    ]

    SENTIMENT_CHOICES = [
        ('正面', '正面'),
        ('中性', '中性'),
        ('負面', '負面'),
    ]

    title = models.CharField(max_length=300)
    date = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=100, blank=True)
    content = models.TextField(blank=True)
    tool = models.CharField(max_length=20, choices=TOOL_CHOICES)
    sentiment = models.CharField(max_length=10, choices=SENTIMENT_CHOICES, blank=True)
    keywords = models.TextField(blank=True)
    link = models.URLField(max_length=500, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['tool', 'date']),
            models.Index(fields=['date']),
            models.Index(fields=['sentiment']),
        ]

    def __str__(self):
        return f"{self.tool} - {self.title}"


class DataUpdateLog(models.Model):
    STATUS_CHOICES = [
        ('success', 'success'),
        ('failed', 'failed'),
        ('skipped', 'skipped'),
    ]

    name = models.CharField(max_length=80, default='technews_ai')
    last_updated = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='success')
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.status} - {self.created_at:%Y-%m-%d %H:%M}"
