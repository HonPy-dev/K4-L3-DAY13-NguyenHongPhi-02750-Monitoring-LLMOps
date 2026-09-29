# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Nguyễn Hồng Phi
- **MSSV:** L3A202602750
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/HonPy-dev/K4-L3-DAY13-NguyenHongPhi-02750-Monitoring-LLMOps
- **Commit SHA cuối:** `9919e5f1e71d16cde6b50bad04ff9537f0d1bcde`
- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-L3A202602750` — ⚠️ project hiện tại trên Langfuse Cloud đang tên "My Project", cần đổi tên theo đúng convention này (Project Settings) để trace evidence hợp lệ.

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | **30/100** — FAILED: missing required fields, correlation ID (0 unique), enrichment thiếu; PASSED: PII scrubbing | **100/100** (CP1) — 4/4 PASSED, 0 missing fields, 0 missing enrichment, 11 unique correlation IDs, 0 PII leak | Đạt yêu cầu CP1 (≥80/100) |
| `validate_dashboard.py` | **HỢP LỆ: 6/6 panel** | | Contract dashboard đã đủ ngay từ baseline |
| `pytest` | **22 passed** (3.54s) | **27 passed** (CP1: +5 test PII) | Không có test fail |
| Số traces hợp lệ | 10 observations `lab-agent-run` ingest thành công sau 1 lần chạy `load_test.py` (10/10 request trả 200) | **35 traces** hôm nay (CP2), root AGENT + child RETRIEVER/GENERATION | Đích ≥10 traces đạt; trace IDs ở §5 |
| Số PII leak | 0 | | Theo `validate_logs.py` baseline |
| Latency P95 / TTFT P95 | _chưa đo (CP2)_ | **P95 latency 1124 ms** (SLO ≤3000); TTFT ~50 ms | Đo trên 10 request load test concurrency 5 |
| Retrieval success rate | _chưa đo (CP2)_ | **100%** (10/10 `tool_success=true`) | Theo panel errors dashboard |

### CP0 — Setup & baseline (2026-09-29)

- Tạo `.venv` (Python 3.11.0), cài `requirements.txt` đúng pin.
- `.env` cấu hình đủ 5 biến `LANGFUSE_*` (keys cá nhân, `BASE_URL=https://cloud.langfuse.com`).
- API chạy `uvicorn app.main:app --env-file .env` — `/health` trả `{"ok": true, "tracing_enabled": true}`.
- `load_test.py`: 10/10 request 200; `data/logs.jsonl` tạo 21 records.
- Trace xác nhận ingest vào project Langfuse cá nhân (query `v2/observations` thấy `lab-agent-run`).
- Ghi chú: log server có cảnh báo 404 `Prompt not found: 'day13-chat' (label production)` — đúng kỳ vọng, prompt chưa tạo (thuộc CP2); app dùng fallback local.

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** `CorrelationIdMiddleware` đọc header `x-request-id`; nếu giá trị khớp format `req-<8-hex>` thì dùng lại, ngược lại sinh mới bằng `secrets.token_hex(4)`. ID được `bind_contextvars(correlation_id=...)` để structlog tự gắn vào mọi log record của request, lưu vào `request.state` để truyền xuống agent/Langfuse metadata, và trả về client qua header `x-request-id` + trường `correlation_id` trong response body.
- **Các metadata được ghi vào structured log:** `correlation_id`, `env` (bind ở middleware); `user_id_hash` (SHA-256 12 ký tự), `session_id`, `feature`, `model` (bind ở `/chat`); kèm các field nghiệp vụ `latency_ms`, `ttft_ms`, `tokens_in/out`, `cost_usd`, `tool_name`, `tool_success`.
- **Cách bảo đảm PII được scrub trước khi ghi:** processor `scrub_event` được đăng ký trong structlog pipeline **trước** `JSONRenderer` và `JsonlFileProcessor` (file writer), nên mọi payload (`message_preview`, `answer_preview`, `event`) đều bị redact trước khi serialize/ghi file. Pattern: email, SĐT VN, CCCD 12 số, thẻ tín dụng, hộ chiếu (`[A-Z]\d{7}`), địa chỉ VN (số nhà + Ngõ/Đường/Phố/Phường...).
- **Cách kiểm chứng kết quả:** `validate_logs.py` = **100/100** (0 PII leak); gửi request chứa email/SĐT/CCCD/thẻ thật qua `/chat` thì log ghi nhận `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CCCD]`, `[REDACTED_CREDIT_CARD]`; grep toàn bộ `data/logs.jsonl` tìm PII nguyên văn trả về 0 kết quả; pytest 27 passed (bổ sung 5 test PII cho CCCD/thẻ/hộ chiếu/địa chỉ/kết hợp).

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** workload tự chạy qua `scripts/load_test.py --concurrency 5` (10 request, `user_id_hash` của tôi) + các run riêng cho prompt versioning; xác nhận bằng `GET /api/public/v2/observations` lọc `name=lab-agent-run` trong project — 35 root observations hôm nay (2026-09-29), nhiều hơn yêu cầu ≥10.
- **Cấu trúc root/retrieval/generation observations:** root `lab-agent-run` (type AGENT) → child `retrieval` (type RETRIEVER, input=message, output doc_count) + child `llm_generation` (type GENERATION, model=claude-sonnet-4-5, input=prompt text, usage input/output/total tokens). Tách bằng `client.start_as_current_observation()` của Langfuse SDK v4 trong `app/agent.py`.
- **Cách nối trace với log:** trace metadata chứa `correlation_id` (format `req-<8-hex>`) — cùng giá trị nằm trong mọi log record của request trong `data/logs.jsonl`.
- **Prompt name:** `day13-chat` (biến `Feature/Docs/Question` theo contract PROMPT_VERSIONING.md).
- **Version/label baseline:** version 1 — labels `baseline`, `production` (ban đầu).
- **Version/label candidate:** version 2 — thêm dòng system + giới hạn "at most 3 sentences", label `candidate`.
- **Trace ID của mỗi version:**
  - baseline (v1): `f4e481f6494cd87dfb04932669dcfbd7` (08:42:57 UTC)
  - candidate (v2): `4179a021eff78036d3763eb8488bbc95` (08:43:17 UTC)
  - sau promote production→v2: `fc1fa24e8f8d911be7f3e78f28411879` (08:43:32 UTC, version 2)
  - sau rollback production→v1: `b0f6dda1669bb93f7024d08bc9f0df5b` (08:43:34 UTC, version 1)
- **Cách promote và rollback `production`:** dùng SDK `client.update_prompt(name, version, new_labels)` — promote: gán `production` cho v2; rollback: gán lại `production` cho v1 và bỏ label cũ khỏi v2. Xác nhận cuối: `get_prompt(label="production")` → version 1. Root observation có trường `version` = 1/2 tương ứng làm bằng chứng trên từng trace.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** dựng bằng `scripts/render_dashboard.py` (matplotlib) đọc trực tiếp `data/logs.jsonl` theo contract `config/dashboard.yaml`, time range 60 phút, hiển thị đủ tên panel/đơn vị/threshold: Latency (P50/P95/P99/TTFT P95, ms, SLO p95≤3000), Traffic (req/phút), Errors (error rate + retrieval success, %), Cost (USD/phút + tổng), Tokens (tokens_in/out), Quality (mean, SLO≥0.75). Evidence: `evidence/11-dashboard-overview.png`.
- **SLO và lý do chọn:** giữ nguyên SLO chính `fast_successful_requests` 99.5% trong 28 ngày với SLI `response_sent` có `latency_ms ≤ 3000`. Ngưỡng 3000 ms hợp lý so với baseline đo được: P95 thực tế ≈ 1124 ms (margin ~2.7x), đủ rộng cho tail latency khi retrieval chậm nhưng vẫn bắt được incident dạng rag_slow (thêm 2.5s sẽ đẩy P95 vượt ngưỡng).
- **Cách tính error budget:** budget = 0.5% события trong 28 ngày. Với ~10k request/tháng (giả định traffic lab), budget = 50 request chậm/lỗi. Đã dùng: error rate 0%, latency P95 1124ms ≤ 3000ms → error budget còn nguyên 100% (0/50).
- **Ba alert và runbook tương ứng:** (1) `HighLatencyP95` warning — P95>3000ms duy trì 5 phút; (2) `HighErrorRate` critical — error rate >2% duy trì 5 phút; (3) `DailyCostBudgetBurn` warning — tổng cost 24h > 2.5 USD duy trì 15 phút. Cả ba dựa trên triệu chứng (latency/lỗi/chi phí người dùng chịu), kênh Slack `#day13-alerts`, runbook đầy đủ 3 bước kiểm tra + mitigation tại `docs/alerts.md`.

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1` (cohort K4, seed 1311, file riêng của Lab Coach L3A đặt tại `config/challenge.json`, đã gitignore)
- **Khoảng thời gian điều tra:** 2026-09-29 09:23:55–09:24:09 UTC (chạy `inject_incident.py` + `load_test.py --challenge --concurrency 5`)
- **Triệu chứng từ metrics:** panel Latency — P95 tăng từ 1124 ms (baseline) lên **2652 ms**, vượt threshold challenge 2000 ms; error rate vẫn 0%, TTFT ~50 ms không đổi → loại trừ lỗi và LLM. Evidence: `evidence/12-incident-metric.png`.
- **Log line và correlation ID liên quan:** 5/5 request `feature=monitoring` đều 2651–2652 ms, `tool_success=true`, ví dụ line `response_sent | corr req-577bd224 | latency 2651 ms | ts 2026-09-29T09:24:00.549Z`. Evidence: `evidence/13-incident-log.png`.
- **Trace ID và span gây ảnh hưởng:** trace **`549b88b969f6f3d80bdfd7d2f1b575a1`** (map với corr `req-577bd224` theo timestamp). Waterfall: AGENT tổng 2.653s = **RETRIEVER `retrieval` 2.503s (94%)** + GENERATION `llm_generation` 0.151s → span gây ảnh hưởng là RETRIEVER. Evidence: `evidence/14-incident-trace.png`.
- **Root cause:** đủ 3 tín hiệu cùng chỉ một nguyên nhân — metric (P95 2652ms vượt 2000ms), log (mọi request monitoring đều ~2651ms, không lỗi, TTFT bình thường), trace (span retrieval dài 2.5s/trace): hàm `retrieve()` trong `app/mock_rag.py` bị giảm tốc 2.5 giây cho truy vấn thuộc feature `monitoring` (incident `rag_slow` theo challenge — vector store/RAG retrieval chậm), không phải do LLM hay guardrail.
- **Fix action:** khôi phục hiệu năng retrieval — kiểm tra vector store (network/index) mà `retrieve()` gọi; khởi động lại hoặc chuyển corpus fallback; sau khi đã xác định, tắt incident bằng `inject_incident.py --disable` và xác nhận P95 quay về ~1.1s.
- **Preventive measure:** (1) alert `HighLatencyP95` (P95>3000ms 5 phút liên tục) sẽ tự bắt sự cố này trong production; (2) thêm timeout + circuit breaker quanh retrieval (ví dụ cutoff 1.5s, fallback corpus static) để một dependency chậm không kéo cả request; (3) SLO error budget theo dõi phần trăm request chậm thay vì chỉ mean.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**
- **Một lỗi/blocker đã gặp:**
- **Cách tìm nguyên nhân và xử lý:**
- **Cách hiểu luồng Metrics → Logs → Traces:**
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
- **Điều quan trọng nhất đã học:**
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:**

## 9. Checklist trước khi nộp

- [ ] Kết quả và evidence thuộc commit SHA cuối.
- [ ] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [ ] Incident evidence nối đúng metric → log → trace.
- [ ] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [ ] Repository chạy lại được theo README.
- [ ] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
