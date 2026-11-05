from django.core.management.base import BaseCommand

from app_news_db.models import NewsArticle
from app_news_db.utils import classify_tool


class Command(BaseCommand):
    help = "Reclassify existing NewsArticle.tool using relevance-based rules"

    def handle(self, *args, **options):
        changed = 0
        unchanged = 0
        to_other = 0

        for article in NewsArticle.objects.all().iterator():
            new_tool = classify_tool(article.title, article.content)
            if new_tool == article.tool:
                unchanged += 1
                continue

            old_tool = article.tool
            article.tool = new_tool
            article.save(update_fields=["tool"])
            changed += 1
            if new_tool == "Other":
                to_other += 1
            self.stdout.write(f"{old_tool} -> {new_tool}: {article.title}")

        self.stdout.write(self.style.SUCCESS(
            f"重算完成：變更 {changed} 筆，其中改為 Other {to_other} 筆，未變更 {unchanged} 筆。"
        ))
