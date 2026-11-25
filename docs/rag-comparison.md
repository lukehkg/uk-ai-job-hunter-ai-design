# RAG 成熟度對照：AWS 企業 RAG 藍圖 vs 本平台現有設計

> 對照來源：一份外部策略文件（AWS DevOps 轉型 AI/RAG 策略，9 頁）提出嘅
> 「Enterprise Multi-Tenant Secure RAG Platform」藍圖：S3→SQS→Lambda 事件驅動攝取、
> pgvector/OpenSearch、hybrid search + 權限過濾、Cohere rerank、Guardrails、
> semantic cache、Ragas/Promptfoo CI 評估門檻、Golden Dataset。以下逐層對照本平台現狀。

直接答案：**本平台唔係 full RAG solution，係「RAG 用喺判斷層」嘅 partial RAG**。
Trust-score 真係行緊 retrieval-augmented generation（SQLite 向量庫搵歷史詐騙證據 →
GLM 出 verdict → 必須引用 `rag_evidence_used`），但求職搜尋只係 semantic search
唔生成答案。

| 層面 | PDF 建議（AWS 企業 RAG） | 現有設計（uk-ai-job-hunter） | 狀態 |
|---|---|---|---|
| 資料攝取 | 事件驅動：S3 → SQS → Lambda，即時向量化 | Cron 排程抓 job → dedup → parquet shard → HF dataset（batch，唔係即時） | 🟡 部分（有 pipeline 但 batch） |
| 文件處理 | Chunking + 保留 metadata | Job 文字短，唔使 chunking；有 normalized_skills / content_hash metadata | 🟡 |
| 向量庫 | Aurora pgvector / OpenSearch Serverless | SQLite + 本地 embedding（小型但真係用緊） | ✅ 有（輕量版） |
| Hybrid search | Vector + BM25 + 權限 metadata filter | FTS + vector 雙路（Mermaid 有 FTS、VEC） | 🟡 部分（冇權限過濾，見下） |
| Reranker | Cohere Rerank 重排 Top-K | ❌ 用 cosine 同 rule score 排序 | ❌ |
| 生成 + 引用 | 答案必須附 citations | Trust-score：GLM verdict 必須引用 `rag_evidence_used`（同一個設計理念） | ✅ 有（只喺判斷層） |
| Guardrails | Bedrock Guardrails 擋 prompt injection、PII 遮罩 | Passcode gating、rate limit、robots.txt、IP hash（API 安全有，但冇 LLM 內容層 guardrails） | 🟡 |
| Semantic cache | ElastiCache 相似問題直接命中 | ❌ | ❌ |
| RAG 評估門檻 | Ragas/Promptfoo：Faithfulness ≥ 0.85 先准 merge | ❌ RAG 冇；但 student model 有 F1/FPR/conf gates（同一個概念用喺訓練） | 🟡 |
| Golden Dataset | 正樣本 + 拒答樣本 + regression 樣本 | ❌ 冇 RAG 測試集 | ❌ |
| Feedback loop | Thumbs down 自動入測試集 | ❌（有 visitor log + digest，但唔係質素回饋） | ❌ |
| LLM 監控 | Per-query token 成本、拒答率、X-Ray 追蹤 | 🟡 有 access log、Telegram digest；冇 per-query token 成本儀表 | 🟡 |
| IaC / 一鍵部署 | Terraform/CDK + 成本標示 | ❌ 冇 Terraform；git push 部署去 HF Space | 🟡（HF 取代咗大部分） |
| Multi-tenant RBAC | 按部門隔離檢索結果 | ❌ 單租戶（一個 dashboard passcode + Basic Auth） | ❌ |
| Teacher→student 自我進化 | （PDF 冇呢層） | Phase A→GLM teacher→student distillation + promotion gates | ✅ 本平台獨有 |

結論：以該藍圖標準計做到約六成骨架；真 RAG（retrieval + generation + 引用證據）
只存在喺詐騙判斷條路。

## 對齊藍圖嘅優先次序（按性价比）

1. **Ragas/Promptfoo quality gate + Golden Dataset**（最平最加分）：30-80 條 job
   判斷案例，三種樣本（應判 scam / 應拒答 / 以前判錯），低過門檻 block merge。
   同 student promotion gates 係同一套紀律。
2. **Per-query token 成本記錄**：access_log 加 token/成本欄位，每日 digest 加一個數。
3. **Reranker**（可選）：cosine 排序對 job 搜尋夠用，有 spare credit 先加。
4. **Semantic cache**（可選）：trust-score 查詢重複率高，cache 一層慳 token。

相關頁面：[scam-detection.md](scam-detection.md) · [teacher-student-loop.md](teacher-student-loop.md) · [03-solution-architecture.md](03-solution-architecture.md)
