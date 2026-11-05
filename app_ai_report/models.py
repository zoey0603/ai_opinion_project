from django.db import models

class AnalysisReport(models.Model):
    TOOL_CHOICES = [
        ('ChatGPT', 'ChatGPT'),
        ('Gemini', 'Gemini'),
        ('Claude', 'Claude'),
        ('ALL', 'ALL'),
    ]

    tool = models.CharField(max_length=20, choices=TOOL_CHOICES)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    total_count = models.IntegerField(default=0)
    report = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tool} report - {self.created_at:%Y-%m-%d %H:%M}"