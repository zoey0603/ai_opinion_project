from django.core.management.base import BaseCommand
from django.utils import timezone

from app_news_db.models import DataUpdateLog
from app_news_db.utils import month_date_range, update_technews_ai


class Command(BaseCommand):
    help = "Update ChatGPT, Gemini and Claude news from TechNews AI category"

    def add_arguments(self, parser):
        parser.add_argument("--start-page", type=int, default=1)
        parser.add_argument("--end-page", type=int, default=36)
        parser.add_argument("--year", type=int, default=None)
        parser.add_argument("--month", type=int, default=None)
        parser.add_argument("--max-pages", type=int, default=None)

    def handle(self, *args, **options):
        start_page = options["start_page"]
        end_page = options["max_pages"] or options["end_page"]
        year = options["year"]
        month = options["month"]
        start_date = None
        end_date = None
        stop_before_start = False
        log_name = "technews_ai"

        if year and month:
            start_date, end_date = month_date_range(year, month)
            stop_before_start = True
            log_name = f"technews_ai_{year}_{month:02d}"

        try:
            result = update_technews_ai(
                start_page=start_page,
                end_page=end_page,
                start_date=start_date,
                end_date=end_date,
                stop_before_start=stop_before_start,
            )
            if start_date and end_date:
                result["message"] = f"{start_date} 至 {end_date}，{result['message']}"
            log = DataUpdateLog.objects.create(
                name=log_name,
                last_updated=timezone.now(),
                status="success",
                message=result["message"],
            )
            self.stdout.write(self.style.SUCCESS(log.message))
        except Exception as exc:
            DataUpdateLog.objects.create(
                name=log_name,
                last_updated=timezone.now(),
                status="failed",
                message=str(exc),
            )
            self.stdout.write(self.style.ERROR(f"更新失敗：{exc}"))
