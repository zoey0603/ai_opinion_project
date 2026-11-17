# AI 工具輿情分析網站

使用 **Django** 建立的 AI 新聞分析網站，整理 ChatGPT、Claude、Gemini 相關新聞，透過圖表、關鍵字與 AI 摘要協助觀察新聞趨勢。

## 核心功能
- **新聞探索：** 日期篩選、新聞清單、關鍵字與每日聲量趨勢。
- **分析比較：** AI 工具比較、情緒分布、熱門事件與風險警報。
- **AI 分析：** 透過本機 **Ollama** 產生輿情報告及摘要，輔助判讀風險新聞；Ollama 不可用時，部分功能會使用規則式備援結果。

## 技術
Python、Django、Django Template、HTML、CSS、JavaScript、SQLite、Ollama（`gemma3:4b`）。

## 本機啟動
**完整 AI 生成功能需要先安裝 Ollama 並下載模型。**

1. 安裝 [Ollama](https://ollama.com/download)，並確認本機服務正在執行。
2. 下載專案使用的模型：
   ```bash
   ollama pull gemma3:4b
   ```
3. 安裝 Python 相依套件並啟動 Django：
   ```bash
   git clone https://github.com/zoey0603/ai_opinion_project.git
   cd ai_opinion_project
   python -m pip install -r requirements.txt
   python manage.py migrate
   python manage.py runserver
   ```
4. 開啟 `http://127.0.0.1:8000/`。AI 功能會呼叫本機 `http://localhost:11434/api/generate`。

> Ollama 需保持執行；模型推論速度取決於電腦效能。新聞資料來源及重新匯入流程需依專案實際資料設定處理。

**作品定位：** 課程／學習專案，非正式營運系統。
