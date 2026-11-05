import threading
from datetime import timedelta

from django.db import close_old_connections
from django.db.utils import OperationalError, ProgrammingError
from django.shortcuts import render
from django.utils import timezone

from app_news_db.models import DataUpdateLog, NewsArticle
from app_news_db.utils import ensure_news_updated_today


_UPDATE_LOCK = threading.Lock()
_UPDATE_RUNNING = False


def _latest_update_log():
    return DataUpdateLog.objects.filter(name="technews_ai").order_by("-created_at").first()


def _needs_update_today():
    today = timezone.localdate()
    latest_log = _latest_update_log()
    if latest_log and latest_log.status == "running" and latest_log.last_updated:
        running_age = timezone.now() - latest_log.last_updated
        if running_age <= timedelta(minutes=30):
            return False

    latest_success = (
        DataUpdateLog.objects
        .filter(name="technews_ai", status="success")
        .order_by("-last_updated", "-created_at")
        .first()
    )
    if latest_success and latest_success.last_updated:
        return timezone.localtime(latest_success.last_updated).date() != today
    if latest_log and latest_log.last_updated and timezone.localtime(latest_log.last_updated).date() == today:
        return latest_log.status not in {"failed", "running"}
    return True


def _run_update_in_background():
    global _UPDATE_RUNNING
    try:
        close_old_connections()
        ensure_news_updated_today(start_page=1, end_page=36)
    finally:
        close_old_connections()
        with _UPDATE_LOCK:
            _UPDATE_RUNNING = False


def _start_update_if_needed():
    global _UPDATE_RUNNING
    if not _needs_update_today():
        return _latest_update_log(), ""

    with _UPDATE_LOCK:
        if _UPDATE_RUNNING:
            return _latest_update_log(), "資料更新正在背景執行中，網站會先使用既有資料。"
        _UPDATE_RUNNING = True

    DataUpdateLog.objects.create(
        name="technews_ai",
        last_updated=timezone.now(),
        status="running",
        message="首頁已觸發背景更新，資料更新完成前網站會先使用既有資料。",
    )
    thread = threading.Thread(target=_run_update_in_background, daemon=True)
    thread.start()
    return _latest_update_log(), "已啟動背景資料更新，完成後會寫入 DataUpdateLog。"


def home(request):
    update_log = None
    update_error = ""

    try:
        update_log, update_error = _start_update_if_needed()
    except (OperationalError, ProgrammingError) as exc:
        update_error = f"資料表尚未建立，請先執行 migrate：{exc}"
    except Exception as exc:
        update_error = f"自動更新檢查失敗，已使用既有資料：{exc}"
        try:
            update_log = DataUpdateLog.objects.filter(name="technews_ai").order_by("-created_at").first()
        except Exception:
            update_log = None

    try:
        total_news = NewsArticle.objects.count()
        tool_counts = {
            "ChatGPT": NewsArticle.objects.filter(tool="ChatGPT").count(),
            "Gemini": NewsArticle.objects.filter(tool="Gemini").count(),
            "Claude": NewsArticle.objects.filter(tool="Claude").count(),
            "Other": NewsArticle.objects.filter(tool="Other").count(),
        }
        analysis_news_count = tool_counts["ChatGPT"] + tool_counts["Gemini"] + tool_counts["Claude"]
    except (OperationalError, ProgrammingError):
        total_news = 0
        analysis_news_count = 0
        tool_counts = {"ChatGPT": 0, "Gemini": 0, "Claude": 0, "Other": 0}

    return render(request, "app_home/home.html", {
        "project_title": "AI 工具輿情觀測與智慧分析平台",
        "intro": "本系統以科技新聞為資料來源，分析 ChatGPT、Gemini、Claude 的新聞聲量、情緒、熱門關鍵字與趨勢變化。期末版本新增新聞懶人包、風險警報與爆紅原因分析，讓使用者不只看到數據，也能快速理解 AI 工具近期的輿情變化與可能風險。",
        "total_news": total_news,
        "analysis_news_count": analysis_news_count,
        "tool_counts": tool_counts,
        "update_log": update_log,
        "update_error": update_error,
    })
