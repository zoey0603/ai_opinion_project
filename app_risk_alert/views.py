import json
import threading
import time
from collections import Counter, defaultdict
from types import SimpleNamespace

from django.db import OperationalError, close_old_connections
from django.shortcuts import render

from app_news_db.models import NewsArticle
from app_news_db.utils import call_ollama, fallback_risk_summary, find_risk_hits
from .models import RiskAnalysisResult, RiskArticleJudgement


TOOLS = ["ChatGPT", "Gemini", "Claude"]
MAX_OLLAMA_TIMEOUT = 360
OLLAMA_TIMEOUT = 360
_JOB_LOCK = threading.Lock()
_JOB_STATE = {
    "running": False,
    "message": "尚未啟動 Ollama 背景判斷。",
    "processed": 0,
    "started_at": "",
    "finished_at": "",
}


def _parse_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y", "是"}
    return False


def _risk_level(score):
    if score <= 30:
        return "低風險"
    if score <= 60:
        return "中風險"
    return "高風險"


def _fallback_judgement(article, tool, type_hits, kw_hits, error=""):
    risk_type = Counter(type_hits).most_common(1)[0][0] if type_hits else "未明確"
    return {
        "is_risk": True,
        "risk_type": risk_type,
        "reason": "Ollama 無法完成二次判斷，因此暫以風險詞命中結果作為 fallback。請人工複核此筆新聞是否真的屬於該工具風險。",
        "judged_by": "fallback",
        "error_message": error,
    }


def _parse_ollama_json(raw_text):
    text = (raw_text or "").strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end + 1]
    data = json.loads(text)
    return {
        "is_risk": _parse_bool(data.get("is_risk")),
        "risk_type": str(data.get("risk_type", "")).strip()[:50],
        "reason": str(data.get("reason", "")).strip(),
    }


def _build_risk_prompt(article, tool, matched_keywords, keyword_risk_types):
    return f"""
你是一位科技新聞風險分析員。請判斷下面新聞是否「真的」和 {tool} 這個 AI 工具的風險有關。

判斷原則：
- 只有當新聞主題明確是 {tool}、其公司、產品、模型、服務、政策、資安、隱私、版權、監管、營運或技術問題時，才算風險。
- 如果只是順便提到 {tool}，但主題其實是 NVIDIA、Apple、Google 搜尋、Android、股價、晶片、GPU、人才流動、資料中心、投資市場或其他產業，不要算進 {tool} 風險。
- 請只輸出 JSON，不要輸出 Markdown。

可用 risk_type：
隱私風險、版權風險、安全風險、監管風險、公司營運風險、技術風險、非該工具風險

命中的風險詞：{matched_keywords}
關鍵字推測類別：{keyword_risk_types}

新聞標題：{article.title}
新聞工具分類：{article.tool}
新聞內文摘要：
{(article.content or '')[:900]}

請輸出：
{{
  "is_risk": true 或 false,
  "risk_type": "風險類別或非該工具風險",
  "reason": "一句繁體中文說明"
}}
"""


def _get_or_create_judgement(article, tool, type_hits, kw_hits, use_ai=True, ollama_budget=None, ollama_timeout=OLLAMA_TIMEOUT, retry_fallback=False):
    cached = RiskArticleJudgement.objects.filter(article=article, tool=tool).first()
    if cached and not retry_fallback:
        return cached
    if cached and (cached.judged_by != "fallback" or not use_ai):
        return cached

    matched_keywords = "|".join(kw_hits.keys())
    keyword_risk_types = "|".join(type_hits.keys())
    judgement_data = None

    if use_ai and ollama_budget is not None and ollama_budget["remaining"] <= 0:
        if cached:
            return cached
        judgement_data = _fallback_judgement(
            article,
            tool,
            type_hits,
            kw_hits,
            error="本次 Ollama 判斷額度已用完，先以 fallback 顯示；再次啟用可繼續補判斷。",
        )
        return SimpleNamespace(
            article=article,
            tool=tool,
            matched_keywords=matched_keywords,
            keyword_risk_types=keyword_risk_types,
            is_risk=judgement_data["is_risk"],
            risk_type=judgement_data["risk_type"],
            reason=judgement_data["reason"],
            judged_by="pending_fallback",
            error_message=judgement_data["error_message"],
        )

    if use_ai:
        try:
            if ollama_budget is not None:
                ollama_budget["remaining"] -= 1
            close_old_connections()
            raw = call_ollama(
                _build_risk_prompt(article, tool, matched_keywords, keyword_risk_types),
                timeout=ollama_timeout,
            )
            close_old_connections()
            judgement_data = _parse_ollama_json(raw)
            judgement_data["judged_by"] = "ollama"
            judgement_data["error_message"] = ""
            if not judgement_data["is_risk"]:
                judgement_data["risk_type"] = judgement_data["risk_type"] or "非該工具風險"
        except Exception as exc:
            judgement_data = _fallback_judgement(article, tool, type_hits, kw_hits, error=str(exc))
    else:
        judgement_data = _fallback_judgement(article, tool, type_hits, kw_hits)
        return SimpleNamespace(
            article=article,
            tool=tool,
            matched_keywords=matched_keywords,
            keyword_risk_types=keyword_risk_types,
            is_risk=judgement_data["is_risk"],
            risk_type=judgement_data["risk_type"],
            reason=judgement_data["reason"],
            judged_by=judgement_data["judged_by"],
            error_message=judgement_data["error_message"],
        )

    last_error = None
    for attempt in range(3):
        try:
            close_old_connections()
            judgement, _ = RiskArticleJudgement.objects.update_or_create(
                article=article,
                tool=tool,
                defaults={
                    "matched_keywords": matched_keywords,
                    "keyword_risk_types": keyword_risk_types,
                    "is_risk": judgement_data["is_risk"],
                    "risk_type": judgement_data["risk_type"],
                    "reason": judgement_data["reason"],
                    "judged_by": judgement_data["judged_by"],
                    "error_message": judgement_data["error_message"],
                },
            )
            return judgement
        except OperationalError as exc:
            last_error = exc
            if "locked" not in str(exc).lower():
                break
            time.sleep(1.5 * (attempt + 1))

    return SimpleNamespace(
        article=article,
        tool=tool,
        matched_keywords=matched_keywords,
        keyword_risk_types=keyword_risk_types,
        is_risk=judgement_data["is_risk"],
        risk_type=judgement_data["risk_type"],
        reason=f"{judgement_data['reason']}（資料庫忙碌，這次結果未寫入快取：{last_error}）",
        judged_by=f"{judgement_data['judged_by']}_unsaved",
        error_message=str(last_error),
    )


def _build_tool_result(tool, use_ai=True, save_result=False, ollama_budget=None, ollama_timeout=OLLAMA_TIMEOUT, retry_fallback=False):
    qs = NewsArticle.objects.filter(tool=tool).order_by("-date", "-created_at")
    total_count = qs.count()
    negative_count = qs.filter(sentiment="負面").count()
    risk_articles = []
    risk_type_counter = Counter()
    keyword_counter = Counter()
    candidate_count = 0
    ollama_count = 0
    fallback_count = 0
    cached_ollama_count = 0
    cached_fallback_count = 0

    for article in qs:
        type_hits, kw_hits = find_risk_hits(article.title, article.content)
        if not type_hits:
            continue

        candidate_count += 1
        existing = RiskArticleJudgement.objects.filter(article=article, tool=tool).only("judged_by").first()
        previous_judged_by = existing.judged_by if existing else ""
        if previous_judged_by == "ollama":
            cached_ollama_count += 1
        elif previous_judged_by == "fallback":
            cached_fallback_count += 1
        judgement = _get_or_create_judgement(
            article,
            tool,
            type_hits,
            kw_hits,
            use_ai=use_ai,
            ollama_budget=ollama_budget,
            ollama_timeout=ollama_timeout,
            retry_fallback=retry_fallback,
        )
        if judgement.judged_by == "ollama" and previous_judged_by != "ollama":
            ollama_count += 1
        if judgement.judged_by in {"fallback", "pending_fallback"}:
            fallback_count += 1

        if not judgement.is_risk:
            continue

        hit_keywords = [kw for kw in judgement.matched_keywords.split("|") if kw]
        risk_articles.append({
            "title": article.title,
            "date": article.date,
            "tool": article.tool,
            "link": article.link,
            "summary": (article.content or "")[:140],
            "hit_keywords": "、".join(hit_keywords),
            "risk_type": judgement.risk_type,
            "reason": judgement.reason,
            "judged_by": judgement.judged_by,
        })
        risk_type_counter[judgement.risk_type] += 1
        keyword_counter.update(hit_keywords)

    risk_count = len(risk_articles)
    risk_article_rate = risk_count / total_count if total_count else 0
    negative_rate = negative_count / total_count if total_count else 0
    risk_score = round(min(100, risk_article_rate * 60 + negative_rate * 40), 1)
    main_risk_type = risk_type_counter.most_common(1)[0][0] if risk_type_counter else "未明確"
    top_keywords = [word for word, _ in keyword_counter.most_common(8)]
    representative_titles = [item["title"] for item in risk_articles[:5]]

    if save_result:
        try:
            RiskAnalysisResult.objects.create(
                tool=tool,
                total_count=total_count,
                negative_count=negative_count,
                risk_count=risk_count,
                risk_score=risk_score,
                risk_level=_risk_level(risk_score),
                main_risk_type=main_risk_type,
                risk_keywords="|".join(top_keywords),
                representative_titles="|".join(representative_titles),
            )
        except OperationalError:
            pass

    return {
        "tool": tool,
        "total_count": total_count,
        "negative_count": negative_count,
        "candidate_count": candidate_count,
        "risk_count": risk_count,
        "ollama_count": ollama_count,
        "fallback_count": fallback_count,
        "cached_ollama_count": cached_ollama_count,
        "cached_fallback_count": cached_fallback_count,
        "risk_score": risk_score,
        "risk_level": _risk_level(risk_score),
        "main_risk_type": main_risk_type,
        "risk_keywords": top_keywords,
        "risk_articles": risk_articles[:8],
        "risk_type_counts": dict(risk_type_counter),
    }


def _set_job_state(**kwargs):
    with _JOB_LOCK:
        _JOB_STATE.update(kwargs)


def _get_job_state():
    with _JOB_LOCK:
        return dict(_JOB_STATE)


def _run_ollama_judgement_job(limit=None, retry_fallback=False):
    processed = 0
    budget = {"remaining": limit} if limit is not None else None
    try:
        _set_job_state(
            running=True,
            message="Ollama 背景判斷執行中，已判斷過的新聞會直接跳過。",
            processed=0,
            finished_at="",
        )
        close_old_connections()
        for tool in TOOLS:
            before = budget["remaining"] if budget is not None else None
            result = _build_tool_result(
                tool,
                use_ai=True,
                save_result=False,
                ollama_budget=budget,
                ollama_timeout=OLLAMA_TIMEOUT,
                retry_fallback=retry_fallback,
            )
            processed += result["ollama_count"] if budget is None else before - budget["remaining"]
            _set_job_state(processed=processed, message=f"Ollama 背景判斷執行中，目前已新增 {processed} 筆判斷。")
            if budget is not None and budget["remaining"] <= 0:
                break
        _set_job_state(
            running=False,
            message=f"Ollama 背景判斷完成，本次新增 {processed} 筆判斷。",
            processed=processed,
            finished_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        )
    except Exception as exc:
        _set_job_state(
            running=False,
            message=f"Ollama 背景判斷發生錯誤，已保留既有資料：{exc}",
            processed=processed,
            finished_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        )
    finally:
        close_old_connections()


def _start_ollama_judgement_job(limit=None, retry_fallback=False):
    with _JOB_LOCK:
        if _JOB_STATE["running"]:
            return False
        _JOB_STATE.update({
            "running": True,
            "message": "Ollama 背景判斷準備啟動。",
            "processed": 0,
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "finished_at": "",
        })
    thread = threading.Thread(
        target=_run_ollama_judgement_job,
        kwargs={"limit": limit, "retry_fallback": retry_fallback},
        daemon=True,
    )
    thread.start()
    return True


def home(request):
    use_ai = request.GET.get("ai") == "1"
    use_ai_summary = request.GET.get("summary_ai") == "1"
    retry_fallback = request.GET.get("retry_fallback") == "1"
    save_result = request.GET.get("save") == "1"
    limit_value = request.GET.get("limit", "").strip().lower()
    if limit_value and limit_value not in {"all", "none", "0"}:
        try:
            max_new = max(1, int(limit_value))
        except ValueError:
            max_new = None
    else:
        max_new = None
    ollama_timeout = OLLAMA_TIMEOUT
    if use_ai:
        _start_ollama_judgement_job(limit=max_new, retry_fallback=retry_fallback)

    ollama_budget = None
    results = [
        _build_tool_result(
            tool,
            use_ai=False,
            save_result=save_result,
            ollama_budget=ollama_budget,
            ollama_timeout=ollama_timeout,
        )
        for tool in TOOLS
    ]
    risk_summary = fallback_risk_summary(results)
    error = ""

    if use_ai_summary:
        prompt = f"""
你是一位 AI 工具風險觀察員。請根據以下已完成二次判斷的統計資料，用繁體中文生成「AI 工具風險觀察摘要」。
請比較 ChatGPT、Gemini、Claude 的風險分數、主要風險類別、負面新聞、疑似風險候選篇數與確認風險篇數，並提出後續觀察重點。

資料：
{results}
"""
        try:
            close_old_connections()
            risk_summary = call_ollama(prompt, timeout=ollama_timeout)
            close_old_connections()
            if not risk_summary:
                raise RuntimeError("Ollama 沒有回傳內容")
        except Exception as exc:
            risk_summary = fallback_risk_summary(results)
            error = f"Ollama 暫時無法生成摘要，已改用 fallback 風險摘要：{exc}"

    type_totals = defaultdict(int)
    for result in results:
        for risk_type, count in result["risk_type_counts"].items():
            type_totals[risk_type] += count

    return render(request, "app_risk_alert/home.html", {
        "results": results,
        "risk_summary": risk_summary,
        "error": error,
        "use_ai": use_ai,
        "use_ai_summary": use_ai_summary,
        "retry_fallback": retry_fallback,
        "save_result": save_result,
        "max_new": max_new,
        "ollama_timeout": ollama_timeout,
        "remaining_ollama_budget": None,
        "job_state": _get_job_state(),
        "chart_labels": json.dumps([item["tool"] for item in results], ensure_ascii=False),
        "chart_scores": json.dumps([item["risk_score"] for item in results], ensure_ascii=False),
        "risk_type_rows": [{"type": key, "count": value} for key, value in type_totals.items()],
    })
