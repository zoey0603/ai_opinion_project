from django.db import models


class DigestReport(models.Model):
    REPORT_TYPES = [
        ('5_points', '5 點懶人包'),
        ('professional', '專業分析報告'),
        ('presentation', '簡報口語稿'),
        ('student', '給高中生看的版本'),
        ('social', '社群貼文版'),
    ]

    tool = models.CharField(max_length=20)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    report_type = models.CharField(max_length=30, choices=REPORT_TYPES)
    total_count = models.IntegerField(default=0)
    digest_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tool} {self.get_report_type_display()} - {self.created_at:%Y-%m-%d %H:%M}"

