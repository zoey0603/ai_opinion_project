from django.db import models


class ClassificationRecord(models.Model):
    title = models.CharField(max_length=300, blank=True)
    input_text = models.TextField()
    predicted_tool = models.CharField(max_length=20, blank=True)
    predicted_sentiment = models.CharField(max_length=10, blank=True)
    predicted_topic = models.CharField(max_length=40, blank=True)
    predicted_risk_type = models.CharField(max_length=40, blank=True)
    keywords = models.TextField(blank=True)
    explanation = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.predicted_tool} / {self.predicted_topic} / {self.created_at:%Y-%m-%d %H:%M}"
