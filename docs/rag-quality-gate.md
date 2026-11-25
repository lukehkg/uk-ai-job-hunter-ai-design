# RAG Quality Gate: Golden Dataset + Actions Workflow

> 廣東話喺前，English 喺後（同一頁雙語）。
> Cantonese first, English after (same page, both languages).

---

## 廣東話

呢套 gate 係將「信任 score 同 tag 判斷嘅質素」由「無人量度」變成「每次改動都被數字攔住」。三個動機全部來自真實事件：

1. **靜默降級已經發生過兩次**。HF Inference Endpoint 死咗之後，trust-score 全部靜靜哋跌落 keyword fallback，冇任何警報，直到 2026-11-16 audit 先發現。GLM teacher 嘅 offline tests 全部 mock 咗 HTTP 層——證明「接線正確」，但證明唔到「真模型出嚟嘅 verdict 仍然啱」。
2. **產品嘅核心傷害位係誤判**。Trust-score 誤判一間正經公司做 scam，受害者係真搵工嘅人。呢種錯誤而家冇任何自動偵測。
3. **Student 接棒需要驗收標準**。當 student model 取代 GLM 做判斷嗰日，同一份 golden dataset 就係 student-vs-teacher agreement 嘅 acceptance test。一份投資，兩個用途。

### 已實作

- **`backend/evals/golden_dataset.jsonl`**：20 條 cases，三種 sample type——
  - *positive*：8 條 scam/harvesting/ghost（收費培訓班、free income、external portal、不現實人工、WhatsApp 收 CV、90 日舊廣告）+ 6 條 clean（Faculty AI £72,500、Databricks、NHS 護士等真實形態）；
  - *refusal*：2 條資料太少，必須 abstain，唔可以作故仔（防幻覺第一道防線）；
  - *regression*：2 條歷史事件回歸（dead-pool 事件：clean job 永遠唔可以誤 flag；evidence 契約：有 flag 必須有 `rag_evidence_used`）。
  - Case schema：`{id, sample_type, category, title, company, location, salary, description, expected, source, created_from, last_verified}`；只有 teacher LLM 判到嘅 case（例如不現實人工）標 `requires_teacher: true`。
- **`backend/scripts/run_rag_gate.py`**：跑**真** `score_trust()` pipeline，唔係 mock。
  - `offline` 模式（CI 預設）：hermetic stubs，零網路零 secrets，幾秒跑完；驗證 schema、flag⇒evidence invariant、clean case abstention、classification 同 score 閾值一致。
  - `live` 模式：無 stub，用真 GLM（teacher flag 開就生效）。
  - Fail 就非零 exit，報告寫入 `exports/rag_gate/report-latest.json`。
- **`.github/workflows/rag-quality-gate.yml`**：只監察 `trust_score.py` / `matching.py` / `evals/**` / `run_rag_gate.py` 改動，唔會喺無關 push 燒 Actions 分鐘；live gate 冇 secret 就自動跳過，workflow 保持綠。

### 首次驗證

Offline gate **17/20 passed + 3 skipped（teacher-only）+ 0 failed**；新 offline tests 9/9 passed；全套 backend suite 重跑確認無破壞現有 pipeline。

### 點樣持續用

每次生產出錯判，加一條 regression case 入 golden dataset，下次改 prompt/model 自動重跑——呢個就係 quality gate 嘅 feedback loop。`OPENROUTER_API_KEY` secret 加咗之後，live gate 自動啟用。

---

## English

This gate turns trust-score quality from "unmeasured" into "blocked by numbers on every change". Three motivations, all from real events:

1. **Silent degradation already happened twice.** When the HF Inference Endpoint died, every live trust score quietly dropped onto the keyword fallback with no alert; it surfaced in the 2026-11-16 audit. The GLM teacher's offline tests mock the HTTP layer — they prove the wiring, not that the real model's verdicts are still right.
2. **The product's core harm is misjudgment.** Flagging a legitimate company as a scam hurts real job seekers. Today nothing detects that automatically.
3. **The student handover needs an acceptance test.** When the student model replaces GLM, the same golden dataset becomes the student-vs-teacher agreement test. One investment, two targets.

### What shipped

- **`backend/evals/golden_dataset.jsonl`**: 20 cases, three sample types — positive (8 scam/harvesting/ghost patterns + 6 clean real-world shapes: Faculty AI £72,500, Databricks, NHS nurse), refusal (2 minimal postings that must abstain, not invent flags — the first anti-hallucination line), regression (2 incident cases: the dead-pool event, and the evidence contract that any flag must carry `rag_evidence_used`). Cases the teacher LLM alone can judge (e.g. unrealistic salary) are marked `requires_teacher: true`.
- **`backend/scripts/run_rag_gate.py`**: runs the **real** `score_trust()` pipeline, not a mock. Offline mode (CI default): hermetic stubs, zero network, zero secrets, seconds to run; verifies schema shape, the flag⇒evidence invariant, clean-case abstention, and classification-vs-threshold consistency. Live mode: no stubs, uses the real GLM teacher when enabled. Non-zero exit on failure; report at `exports/rag_gate/report-latest.json`.
- **`.github/workflows/rag-quality-gate.yml`**: triggers only on changes that can alter verdict behaviour (`trust_score.py`, `matching.py`, `evals/**`, `run_rag_gate.py`), so it burns no Actions minutes on unrelated pushes. The live job auto-skips when the `OPENROUTER_API_KEY` secret is absent.

### First verification

Offline gate **17/20 passed + 3 skipped (teacher-only) + 0 failed**; new offline tests 9/9 passed; the full backend suite re-ran green, so no existing pipeline, flow, or data changed.

### How to keep it alive

Every production misjudgment becomes one new regression case in the dataset; the gate re-runs it on the next prompt or model change — that is the feedback loop. Adding the `OPENROUTER_API_KEY` secret enables the live gate automatically.

---

相關頁面 Related pages: [rag-comparison.md](rag-comparison.md) · [teacher-student-loop.md](teacher-student-loop.md) · [scam-detection.md](scam-detection.md)
