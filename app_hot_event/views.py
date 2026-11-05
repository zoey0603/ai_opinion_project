import json
import threading
import time
from collections import defaultdict
from datetime import timedelta

from django.db import close_old_connections
from django.db.models import Count
from django.shortcuts import render
from django.utils import timezone

from app_news_db.models import NewsArticle
from app_news_db.utils import call_ollama, collect_keyword_counts, fallback_hot_event
from .models import HotEvent, HotEventRAGQuery


TOOLS = ["ChatGPT", "Gemini", "Claude"]
OLLAMA_TIMEOUT = 360
RAG_TOP_K = 5
PRESET_RAG_QUESTIONS = {
    "most_discussed_tool": "最近一星期最多討論度的 AI 工具是哪一個？",
    "most_negative_tool": "最近一星期哪個 AI 工具負面新聞最多？",
    "fastest_growth_tool": "最近一星期哪個 AI 工具聲量成長最明顯？",
    "hot_keywords_week": "最近一星期 AI 工具新聞的熱門關鍵字是什麼？",
    "representative_news_week": "最近一星期有哪些最具代表性的 AI 工具新聞？",
}
_JOB_LOCK = threading.Lock()
_JOB_STATE = {
    "running": False,
    "message": "尚未啟動 Ollama 背景分析。",
    "processed": 0,
    "started_at": "",
    "finished_at": "",
}


def _daily_counts(tool=None):
    qs = NewsArticle.objects.exclude(date__isnull=True)
    if tool and tool != "ALL":
        qs = qs.filter(tool=tool)
    rows = qs.values("date__date").annotate(count=Count("id")).order_by("date__date")
    return {row["date__date"]: row["count"] for row in rows if row["date__date"]}


def _build_retrieved_context(news_items):
    retrieved = []
    for index, article in enumerate(news_items, start=1):
        content = (article.content or "").strip().replace("\n", " ")
        retrieved.append({
            "rank": index,
            "title": article.title,
            "date": article.date,
            "source": article.source,
            "tool": article.tool,
            "link": article.link,
            "snippet": content[:220] or "目前查無內文摘要",
            "keywords": article.keywords or "",
            "keyword_list": [keyword for keyword in (article.keywords or "").split("|") if keyword][:6],
        })
    return retrieved


def _latest_news_date():
    latest = NewsArticle.objects.exclude(date__isnull=True).order_by("-date").first()
    return timezone.localtime(latest.date).date() if latest and latest.date else timezone.localdate()


def _recent_news_qs(days=7, tool=None):
    end_date = _latest_news_date()
    start_date = end_date - timedelta(days=days - 1)
    qs = NewsArticle.objects.filter(
        date__date__gte=start_date,
        date__date__lte=end_date,
        tool__in=TOOLS,
    )
    if tool and tool != "ALL":
        qs = qs.filter(tool=tool)
    return qs.order_by("-date", "-created_at"), start_date, end_date


def _format_count_rows(rows):
    if not rows:
        return "目前查無資料"
    return "、".join([f"{row['tool']} {row['count']} 篇" for row in rows])


def _serialize_retrieved_context(retrieved_context):
    if not retrieved_context:
        return "目前查無檢索證據。"
    lines = []
    for item in retrieved_context:
        lines.append(
            f"[{item['rank']}] {item['title']}\n"
            f"日期：{item['date']:%Y-%m-%d}\n"
            f"工具：{item['tool']}\n"
            f"來源：{item['source']}\n"
            f"關鍵字：{item['keywords']}\n"
            f"摘要：{item['snippet']}\n"
            f"連結：{item['link']}"
        )
    return "\n\n".join(lines)


def _search_terms_from_question(question):
    question = (question or "").strip()
    terms = []
    for tool in TOOLS:
        if tool.lower() in question.lower():
            terms.append(tool)
    for word in ["風險", "負面", "熱門", "關鍵字", "聲量", "討論", "爆紅", "監管", "隱私", "安全", "版權", "模型", "投資", "發布", "合作"]:
        if word in question:
            terms.append(word)
    return terms


def _retrieve_free_question(question, days=7, tool="ALL"):
    qs, start_date, end_date = _recent_news_qs(days=days, tool=tool)
    terms = _search_terms_from_question(question)
    scored = []
    for article in qs:
        haystack = f"{article.title} {article.keywords} {(article.content or '')[:1200]}".lower()
        score = 0
        for term in terms:
            score += haystack.count(term.lower()) * 3
        score += 2 if article.title and any(term.lower() in article.title.lower() for term in terms) else 0
        score += 1
        scored.append((score, article.date, article.id, article))
    scored.sort(key=lambda row: (row[0], row[1], row[2]), reverse=True)
    retrieved_news = [row[3] for row in scored[:RAG_TOP_K]]
    retrieved_context = _build_retrieved_context(retrieved_news)
    tool_counts = list(qs.values("tool").annotate(count=Count("id")).order_by("-count", "tool"))
    sentiment_counts = list(qs.values("sentiment").annotate(count=Count("id")).order_by("-count", "sentiment"))
    top_keywords = collect_keyword_counts(qs, topn=12)
    stats = [
        {"label": "檢索期間", "value": f"{start_date} 至 {end_date}"},
        {"label": "各工具新聞量", "value": _format_count_rows(tool_counts)},
        {"label": "情緒分布", "value": "、".join([f"{row['sentiment'] or '未標記'} {row['count']} 篇" for row in sentiment_counts]) or "目前查無資料"},
        {"label": "熱門關鍵字", "value": "、".join([f"{keyword}({count})" for keyword, count in top_keywords]) or "目前查無資料"},
    ]
    return {
        "question": question,
        "start_date": start_date,
        "end_date": end_date,
        "tool": tool,
        "stats": stats,
        "retrieved_context": retrieved_context,
    }


def _generate_ollama_rag_answer(question, stats, retrieved_context):
    stats_text = "\n".join([f"- {row['label']}：{row['value']}" for row in stats])
    evidence_text = _serialize_retrieved_context(retrieved_context)
    prompt = f"""
你是一位 AI 工具輿情分析員。請使用檢索增強生成 RAG 回答使用者問題。
你只能根據「檢索統計」與「檢索新聞證據」回答，不要編造沒有出現在證據中的資訊。

使用者問題：{question}

檢索統計：
{stats_text}

檢索新聞證據：
{evidence_text}

請用繁體中文輸出：
1. 直接回答
2. 依據哪些檢索證據
3. 補充觀察
4. 後續可以追蹤什麼
"""
    return call_ollama(prompt, timeout=OLLAMA_TIMEOUT)


def _run_free_rag_query_job(query_id):
    try:
        close_old_connections()
        query = HotEventRAGQuery.objects.get(id=query_id)
        query.status = "running"
        query.message = "正在檢索新聞。"
        query.save(update_fields=["status", "message", "updated_at"])

        rag = _retrieve_free_question(query.question, days=7, tool=query.tool)
        query.start_date = rag["start_date"]
        query.end_date = rag["end_date"]
        query.stats_text = "\n".join([f"{row['label']}：{row['value']}" for row in rag["stats"]])
        query.retrieved_context = _serialize_retrieved_context(rag["retrieved_context"])
        query.message = "已完成檢索，正在交給 Ollama 生成回答。"
        query.save(update_fields=[
            "start_date", "end_date", "stats_text", "retrieved_context", "message", "updated_at",
        ])

        answer = _generate_ollama_rag_answer(query.question, rag["stats"], rag["retrieved_context"])
        query.answer = answer
        query.status = "success"
        query.message = "Ollama RAG 回答已完成。"
        query.save(update_fields=[
            "start_date", "end_date", "stats_text", "retrieved_context",
            "answer", "status", "message", "updated_at",
        ])
    except Exception as exc:
        try:
            query = HotEventRAGQuery.objects.get(id=query_id)
            query.status = "failed"
            query.message = f"Ollama RAG 回答失敗：{exc}"
            query.save(update_fields=["status", "message", "updated_at"])
        except Exception:
            pass
    finally:
        close_old_connections()


def _start_free_rag_query(question, tool="ALL"):
    existing = (
        HotEventRAGQuery.objects
        .filter(question=question.strip(), tool=tool, status__in=["pending", "running"])
        .order_by("-created_at")
        .first()
    )
    if existing:
        return existing
    query = HotEventRAGQuery.objects.create(
        question=question.strip(),
        tool=tool,
        status="pending",
        message="已建立 RAG 查詢，等待背景 Ollama 分析。",
    )
    thread = threading.Thread(target=_run_free_rag_query_job, kwargs={"query_id": query.id}, daemon=True)
    thread.start()
    return query


def _preset_query_cards():
    cards = []
    for key, question in PRESET_RAG_QUESTIONS.items():
        latest = (
            HotEventRAGQuery.objects
            .filter(question=question)
            .order_by("-updated_at", "-created_at")
            .first()
        )
        cards.append({
            "key": key,
            "question": question,
            "latest": latest,
        })
    return cards


def _retrieve_preset_question(question_key):
    question = PRESET_RAG_QUESTIONS.get(question_key, PRESET_RAG_QUESTIONS["most_discussed_tool"])
    qs, start_date, end_date = _recent_news_qs(days=7)
    stats = []
    selected_news_qs = qs
    conclusion = "目前查無足夠資料。"

    tool_counts = list(qs.values("tool").annotate(count=Count("id")).order_by("-count", "tool"))
    negative_counts = list(
        qs.filter(sentiment="負面").values("tool").annotate(count=Count("id")).order_by("-count", "tool")
    )

    if question_key == "most_discussed_tool":
        top = tool_counts[0] if tool_counts else None
        if top:
            conclusion = f"最近一星期討論度最高的是 {top['tool']}，共有 {top['count']} 篇新聞。"
            selected_news_qs = qs.filter(tool=top["tool"])
        stats.append({"label": "各工具新聞量", "value": _format_count_rows(tool_counts)})

    elif question_key == "most_negative_tool":
        top = negative_counts[0] if negative_counts else None
        if top:
            conclusion = f"最近一星期負面新聞最多的是 {top['tool']}，共有 {top['count']} 篇負面新聞。"
            selected_news_qs = qs.filter(tool=top["tool"], sentiment="負面")
        stats.append({"label": "各工具負面新聞量", "value": _format_count_rows(negative_counts)})
        stats.append({"label": "各工具總新聞量", "value": _format_count_rows(tool_counts)})

    elif question_key == "fastest_growth_tool":
        previous_start = start_date - timedelta(days=7)
        previous_end = start_date - timedelta(days=1)
        growth_rows = []
        for tool in TOOLS:
            recent_count = qs.filter(tool=tool).count()
            previous_count = NewsArticle.objects.filter(
                tool=tool,
                date__date__gte=previous_start,
                date__date__lte=previous_end,
            ).count()
            growth_rows.append({
                "tool": tool,
                "count": recent_count,
                "previous": previous_count,
                "growth": recent_count - previous_count,
            })
        growth_rows.sort(key=lambda row: (row["growth"], row["count"]), reverse=True)
        top = growth_rows[0] if growth_rows else None
        if top:
            conclusion = (
                f"最近一星期聲量成長最明顯的是 {top['tool']}，"
                f"本期 {top['count']} 篇、前期 {top['previous']} 篇，增加 {top['growth']} 篇。"
            )
            selected_news_qs = qs.filter(tool=top["tool"])
        stats.append({
            "label": "本期與前期比較",
            "value": "、".join([f"{row['tool']} 本期 {row['count']} / 前期 {row['previous']} / 增加 {row['growth']}" for row in growth_rows]),
        })

    elif question_key == "hot_keywords_week":
        top_keywords = collect_keyword_counts(qs, topn=12)
        conclusion = "最近一星期熱門關鍵字包含：" + "、".join([keyword for keyword, _ in top_keywords])
        stats.append({"label": "熱門關鍵字", "value": "、".join([f"{keyword}({count})" for keyword, count in top_keywords])})

    else:
        conclusion = "以下是最近一星期較具代表性的 AI 工具新聞。"
        stats.append({"label": "各工具新聞量", "value": _format_count_rows(tool_counts)})

    retrieved_news = list(selected_news_qs[:RAG_TOP_K])
    retrieved_context = _build_retrieved_context(retrieved_news)
    return {
        "question_key": question_key,
        "question": question,
        "start_date": start_date,
        "end_date": end_date,
        "stats": stats,
        "retrieved_context": retrieved_context,
        "fallback_answer": conclusion,
    }


def _generate_preset_rag_answer(rag_result, use_ai=False):
    if not use_ai:
        return rag_result["fallback_answer"]

    evidence_lines = []
    for item in rag_result["retrieved_context"]:
        evidence_lines.append(
            f"[{item['rank']}] {item['title']}\n"
            f"日期：{item['date']:%Y-%m-%d}\n"
            f"工具：{item['tool']}\n"
            f"關鍵字：{item['keywords']}\n"
            f"摘要：{item['snippet']}\n"
            f"連結：{item['link']}"
        )
    stats_text = "\n".join([f"- {row['label']}：{row['value']}" for row in rag_result["stats"]])
    evidence_text = "\n\n".join(evidence_lines) or "目前查無檢索證據。"
    prompt = f"""
你是一位 AI 工具輿情分析員。請使用 RAG 方法回答使用者問題，只能根據下方「檢索統計」和「檢索新聞證據」回答，不要編造資料。

使用者問題：{rag_result['question']}
資料期間：{rag_result['start_date']} 到 {rag_result['end_date']}

檢索統計：
{stats_text}

檢索新聞證據：
{evidence_text}

請用繁體中文輸出：
1. 直接答案
2. 證據依據
3. 後續觀察建議
"""
    try:
        answer = call_ollama(prompt, timeout=OLLAMA_TIMEOUT)
        return answer or rag_result["fallback_answer"]
    except Exception:
        return rag_result["fallback_answer"]


def _event_reason(event_data, use_ai=False):
    if not use_ai:
        return fallback_hot_event(event_data)

    retrieved_lines = []
    for item in event_data.get("retrieved_context", []):
        retrieved_lines.append(
            f"[{item['rank']}] 標題：{item['title']}\n"
            f"日期：{item['date']:%Y-%m-%d}\n"
            f"來源：{item['source']}\n"
            f"關鍵字：{item['keywords']}\n"
            f"摘要：{item['snippet']}\n"
            f"連結：{item['link']}"
        )
    retrieved_context = "\n\n".join(retrieved_lines) or "目前查無可用檢索證據。"

    prompt = f"""
你是一位科技新聞輿情分析員。請使用 RAG 方法，只根據「檢索到的新聞證據」分析這一天為什麼聲量上升。
請使用繁體中文，並避免補充證據中沒有出現的事實。

請輸出固定格式：
1. 爆紅原因摘要：用 2 到 3 句說明最可能造成聲量上升的主題。
2. 證據對應：列出你引用了哪些檢索證據編號，例如 [1]、[2]，並說明各自支持哪個判斷。
3. 可能事件背景：根據證據整理事件脈絡。
4. 後續觀察重點：列出 2 到 3 個接下來要觀察的方向。

工具名稱：{event_data['tool']}
日期：{event_data['event_date']}
當天新聞篇數：{event_data['today_count']}
前一天新聞篇數：{event_data['yesterday_count']}
熱門關鍵字：{event_data['top_keywords']}
代表新聞標題：{event_data['representative_titles']}

檢索到的新聞證據：
{retrieved_context}
"""
    try:
        text = call_ollama(prompt, timeout=OLLAMA_TIMEOUT)
        if not text:
            raise RuntimeError("Ollama 沒有回傳內容")
        return text
    except Exception:
        return fallback_hot_event(event_data)


def _save_event_result(event_data):
    saved_event = (
        HotEvent.objects
        .filter(tool=event_data["tool"], event_date=event_data["event_date"])
        .order_by("-created_at")
        .first()
    )
    defaults = {
        "today_count": event_data["today_count"],
        "yesterday_count": event_data["yesterday_count"],
        "growth_count": event_data["growth_count"],
        "growth_rate": event_data["growth_rate"],
        "top_keywords": event_data["top_keywords"],
        "representative_titles": "|".join(event_data["representative_titles"]),
        "possible_reason": event_data["possible_reason"],
        "reason_source": event_data.get("reason_source", ""),
    }
    if saved_event:
        for field, value in defaults.items():
            setattr(saved_event, field, value)
        saved_event.save(update_fields=[*defaults.keys()])
        return saved_event, "updated"
    return HotEvent.objects.create(
        tool=event_data["tool"],
        event_date=event_data["event_date"],
        **defaults,
    ), "created"


def _detect_events(tool, use_ai=False, save_result=False, force_ai=False):
    counts = _daily_counts(tool)
    if not counts:
        return []

    max_count = max(counts.values())
    events = []
    for event_date in sorted(counts.keys()):
        today_count = counts[event_date]
        yesterday_count = counts.get(event_date - timedelta(days=1), 0)
        is_spike = (
            today_count >= 3 and (
                (yesterday_count > 0 and today_count >= yesterday_count * 2) or
                (yesterday_count == 0)
            )
        )
        is_peak_day = today_count == max_count
        if not is_spike and not is_peak_day:
            continue

        day_qs = NewsArticle.objects.filter(date__date=event_date)
        if tool != "ALL":
            day_qs = day_qs.filter(tool=tool)
        day_qs = day_qs.order_by("-date", "-created_at")
        top_keywords = "|".join([kw for kw, _ in collect_keyword_counts(day_qs, topn=8)])
        representative_news = list(day_qs[:RAG_TOP_K])
        representative_titles = [item.title for item in representative_news]
        retrieved_context = _build_retrieved_context(representative_news)
        growth_count = today_count - yesterday_count
        growth_rate = round((growth_count / yesterday_count) * 100, 1) if yesterday_count else 100.0

        event_data = {
            "tool": tool,
            "event_date": event_date,
            "today_count": today_count,
            "yesterday_count": yesterday_count,
            "growth_count": growth_count,
            "growth_rate": growth_rate,
            "top_keywords": top_keywords,
            "top_keywords_list": [keyword for keyword in top_keywords.split("|") if keyword],
            "representative_titles": representative_titles,
            "representative_news": representative_news,
            "retrieved_context": retrieved_context,
            "rag_query": f"{tool} {event_date} 爆紅原因 {top_keywords}",
            "is_peak_day": is_peak_day,
        }
        saved_event = (
            HotEvent.objects
            .filter(tool=tool, event_date=event_date)
            .order_by("-created_at")
            .first()
        )
        if save_result:
            if use_ai or force_ai:
                event_data["possible_reason"] = _event_reason(event_data, use_ai=True)
                event_data["reason_source"] = "RAG Ollama 已儲存"
            elif saved_event and saved_event.possible_reason:
                event_data["possible_reason"] = saved_event.possible_reason
                event_data["reason_source"] = "資料庫已儲存"
            else:
                event_data["possible_reason"] = _event_reason(event_data, use_ai=False)
                event_data["reason_source"] = "fallback 已儲存"
            _, save_action = _save_event_result(event_data)
            event_data["save_action"] = save_action
        elif saved_event and saved_event.possible_reason:
            event_data["possible_reason"] = saved_event.possible_reason
            event_data["reason_source"] = saved_event.reason_source or "資料庫已儲存"
        else:
            event_data["possible_reason"] = _event_reason(event_data, use_ai=use_ai)
            event_data["reason_source"] = "即時計算"
        events.append(event_data)

    return events


def _set_job_state(**kwargs):
    with _JOB_LOCK:
        _JOB_STATE.update(kwargs)


def _get_job_state():
    with _JOB_LOCK:
        return dict(_JOB_STATE)


def _run_ollama_hot_event_job():
    processed = 0
    try:
        _set_job_state(
            running=True,
            message="Ollama 爆紅原因背景分析執行中，完成後會覆蓋網頁上的已儲存原因。",
            processed=0,
            finished_at="",
        )
        close_old_connections()
        for tool in ["ALL", *TOOLS]:
            events = _detect_events(tool, use_ai=True, save_result=True, force_ai=True)
            processed += len(events)
            _set_job_state(processed=processed, message=f"Ollama 背景分析執行中，目前已處理 {processed} 個事件。")
        _set_job_state(
            running=False,
            message=f"Ollama 背景分析完成，本次已更新 {processed} 個爆紅事件。",
            processed=processed,
            finished_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        )
    except Exception as exc:
        _set_job_state(
            running=False,
            message=f"Ollama 背景分析發生錯誤，已保留既有資料：{exc}",
            processed=processed,
            finished_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        )
    finally:
        close_old_connections()


def _start_hot_event_job():
    with _JOB_LOCK:
        if _JOB_STATE["running"]:
            return False
        _JOB_STATE.update({
            "running": True,
            "message": "Ollama 爆紅原因背景分析準備啟動。",
            "processed": 0,
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "finished_at": "",
        })
    thread = threading.Thread(target=_run_ollama_hot_event_job, daemon=True)
    thread.start()
    return True


def _trend_chart_data():
    all_dates = sorted(set().union(*[_daily_counts(tool).keys() for tool in TOOLS]))
    per_tool = {tool: _daily_counts(tool) for tool in TOOLS}
    return {
        "labels": [str(date) for date in all_dates],
        "datasets": {tool: [per_tool[tool].get(date, 0) for date in all_dates] for tool in TOOLS},
    }


def home(request):
    use_ai = request.GET.get("ai") == "1"
    start_ai_job = request.GET.get("ai_job") == "1"
    save_result = request.GET.get("save") == "1"
    free_question = request.GET.get("q", "").strip()
    free_tool = request.GET.get("tool", "ALL")
    if free_tool not in ["ALL", *TOOLS]:
        free_tool = "ALL"
    question_key = request.GET.get("question", "most_discussed_tool")
    if question_key not in PRESET_RAG_QUESTIONS:
        question_key = "most_discussed_tool"
    rag_ai = request.GET.get("rag_ai") == "1"
    if start_ai_job:
        _start_hot_event_job()
    if free_question:
        _start_free_rag_query(free_question, tool=free_tool)

    events = []
    for tool in ["ALL", *TOOLS]:
        events.extend(_detect_events(tool, use_ai=False, save_result=save_result))
    events = sorted(events, key=lambda item: (item["event_date"], item["growth_count"]), reverse=True)

    biggest = max(events, key=lambda item: item["growth_count"], default=None)
    chart = _trend_chart_data()
    recent_rag_queries = list(HotEventRAGQuery.objects.order_by("-updated_at", "-created_at")[:5])

    return render(request, "app_hot_event/home.html", {
        "events": events,
        "event_count": len(events),
        "biggest": biggest,
        "use_ai": use_ai,
        "start_ai_job": start_ai_job,
        "save_result": save_result,
        "job_state": _get_job_state(),
        "ollama_timeout": OLLAMA_TIMEOUT,
        "preset_questions": PRESET_RAG_QUESTIONS,
        "selected_question": question_key,
        "rag_ai": rag_ai,
        "preset_query_cards": _preset_query_cards(),
        "free_question": free_question,
        "free_tool": free_tool,
        "recent_rag_queries": recent_rag_queries,
        "tools": TOOLS,
        "chart_labels": json.dumps(chart["labels"], ensure_ascii=False),
        "chatgpt_data": json.dumps(chart["datasets"].get("ChatGPT", []), ensure_ascii=False),
        "gemini_data": json.dumps(chart["datasets"].get("Gemini", []), ensure_ascii=False),
        "claude_data": json.dumps(chart["datasets"].get("Claude", []), ensure_ascii=False),
    })
