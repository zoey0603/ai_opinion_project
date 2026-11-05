from django.apps import AppConfig


class AppNewsDbConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app_news_db'
    _startup_update_started = False

    def ready(self):
        import os
        import threading

        from django.conf import settings

        if not getattr(settings, "AUTO_UPDATE_ON_STARTUP", False):
            return

        should_run = (not settings.DEBUG) or os.environ.get("RUN_MAIN") == "true"
        if not should_run or AppNewsDbConfig._startup_update_started:
            return

        AppNewsDbConfig._startup_update_started = True

        def run_update():
            try:
                from app_news_db.utils import ensure_news_updated_today

                ensure_news_updated_today(start_page=1, end_page=36)
            except Exception:
                # 啟動時自動更新失敗不能影響網站正常開啟；詳細狀態會由 command 寫入 DataUpdateLog。
                pass

        thread = threading.Thread(target=run_update, daemon=True)
        thread.start()
