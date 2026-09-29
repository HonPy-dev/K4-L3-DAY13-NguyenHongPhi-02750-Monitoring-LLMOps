# Alert và Runbook

Mỗi alert dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ. Kênh thông báo chung: Slack `#day13-alerts`.

## Alert 1

- **Tên:** HighLatencyP95
- **Severity:** warning
- **Duration:** duy trì 5 phút
- **Kênh thông báo:** Slack `#day13-alerts`
- **SLI/SLO liên quan:** `fast_successful_requests` — SLI `latency_ms <= 3000`; dashboard panel *Latency percentiles and TTFT*, threshold p95 ≤ 3000 ms
- **Điều kiện và thời gian duy trì:** P95 của `response_sent.latency_ms` > 3000 ms liên tục 5 phút
- **Ảnh hưởng tới người dùng:** hơn 5% request chậm hơn 3 giây; trải nghiệm chat rõ ràng giật/treo.
- **Ba bước kiểm tra đầu tiên:**
  1. Mở dashboard panel *Latency* — xem P95/TTFT P95 và khoảng thời gian bắt đầu tăng.
  2. Lọc `data/logs.jsonl` các `response_sent` có `latency_ms > 3000`, lấy một `correlation_id`.
  3. Mở trace có cùng correlation ID trên Langfuse, xem waterfall để xác định span nào dài (retrieval vs llm_generation).
- **Mitigation tạm thời:** nếu retrieval là bottleneck, bật fallback corpus local / giảm top-k; nếu LLM là bottleneck, hạ max output tokens hoặc chuyển tạm sang model nhẹ hơn (đổi `model` binding).
- **Owner:** oncall-llm

## Alert 2

- **Tên:** HighErrorRate
- **Severity:** critical
- **Duration:** duy trì 5 phút
- **Kênh thông báo:** Slack `#day13-alerts`
- **SLI/SLO liên quan:** guardrail `error_rate_pct_max: 2`; dashboard panel *Error rate and retrieval success*
- **Điều kiện và thời gian duy trì:** `count(request_failed)/count(request_received)*100 > 2%` liên tục 5 phút
- **Ảnh hưởng tới người dùng:** request bị lỗi 500, người dùng không nhận được câu trả lời.
- **Ba bước kiểm tra đầu tiên:**
  1. Dashboard panel *Errors*: xác nhận error rate và breakdown `error_type`.
  2. Lọc log `event == "request_failed"`, đếm theo `error_type`, lấy một `correlation_id` lỗi.
  3. Mở trace tương ứng: nếu `tool_success == false` ở span retrieval → nghi ngờ vector store; kiểm tra `/health` để xem incidents nào đang bật.
- **Mitigation tạm thời:** nếu retrieval fail (RuntimeError vector store) → khởi động lại dependency/circuit breaker sang corpus fallback; đồng thời bật retry ở client.
- **Owner:** oncall-llm

## Alert 3

- **Tên:** DailyCostBudgetBurn
- **Severity:** warning
- **Duration:** duy trì 15 phút
- **Kênh thông báo:** Slack `#day13-alerts`
- **SLI/SLO liên quan:** guardrail `daily_cost_usd_max: 2.5`; dashboard panel *Cost over time*
- **Điều kiện và thời gian duy trì:** tổng `sum(response_sent.cost_usd)` trong 24h > 2.5 USD (vẫn duy trì trên ngưỡng sau 15 phút)
- **Ảnh hưởng tới người dùng:** gián tiếp — ngân sách cạn sớm, có thể phải rate-limit hoặc hạ chất lượng model.
- **Ba bước kiểm tra đầu tiên:**
  1. Panel *Cost* + *Tokens*: xác nhận tổng cost và tokens_in/out tăng bất thường.
  2. Lọc log theo `tokens_out` cao bất thường, lấy `correlation_id`.
  3. Mở trace: kiểm tra `llm_generation` usage — prompt phình (tokens_in cao) hay output dài (tokens_out cao, dấu hiệu cost_spike).
- **Mitigation tạm thời:** đặt cap output tokens, rollback prompt version mới nhất nếu prompt v2 làm output dài hơn, hoặc tạm rate-limit theo `user_id_hash`.
- **Owner:** oncall-llm
