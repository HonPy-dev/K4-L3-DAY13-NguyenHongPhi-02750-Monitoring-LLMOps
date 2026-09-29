"""Render 6-panel dashboard từ data/logs.jsonl theo config/dashboard.yaml contract.

Chạy: python scripts/render_dashboard.py [output.png]
Kết quả mặc định: submission/evidence/11-dashboard-overview.png
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml

LOG_PATH = Path("data/logs.jsonl")
CONFIG_PATH = Path("config/dashboard.yaml")
DEFAULT_OUTPUT = Path("submission/evidence/11-dashboard-overview.png")
TIME_RANGE_MINUTES = 60


def load_records() -> list[dict]:
    records = []
    if LOG_PATH.exists():
        for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def percentile(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = max(0, min(len(ordered) - 1, round(p / 100 * (len(ordered) - 1))))
    return ordered[k]


def fmt(values: list[float], digits: int = 1) -> str:
    if not values:
        return "n/a"
    return f"max {max(values):.{digits}f}"


def main() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    panels = {p["id"]: p for p in config["dashboard"]["panels"]}
    records = load_records()

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=TIME_RANGE_MINUTES)
    in_window = [
        r for r in records
        if "ts" in r and parse_ts(r["ts"]) >= window_start
    ]
    sent = [r for r in in_window if r.get("event") == "response_sent"]
    received = [r for r in in_window if r.get("event") == "request_received"]
    failed = [r for r in in_window if r.get("event") == "request_failed"]

    latencies = [r["latency_ms"] for r in sent if r.get("latency_ms") is not None]
    ttfts = [r["ttft_ms"] for r in sent if r.get("ttft_ms") is not None]
    costs = [r["cost_usd"] for r in sent if r.get("cost_usd") is not None]
    tokens_in = sum(r.get("tokens_in") or 0 for r in sent)
    tokens_out = sum(r.get("tokens_out") or 0 for r in sent)
    quality = [r["quality_score"] for r in sent if r.get("quality_score") is not None]
    tool_calls = [r for r in sent if r.get("tool_success") is not None]
    retrieval_ok = sum(1 for r in tool_calls if r["tool_success"] is True)

    error_rate = len(failed) / len(received) * 100 if received else 0.0
    retrieval_rate = retrieval_ok / len(tool_calls) * 100 if tool_calls else 0.0
    traffic_rpm = len(received) / TIME_RANGE_MINUTES

    # Tong hop theo phut cho cac panel time-series
    by_minute: dict[str, dict[str, float]] = {}
    for r in sent:
        key = parse_ts(r["ts"]).strftime("%H:%M")
        slot = by_minute.setdefault(key, {"cost": 0.0, "count": 0})
        slot["cost"] += r.get("cost_usd") or 0
        slot["count"] += 1

    fig, axes = plt.subplots(2, 3, figsize=(20, 9))
    fig.suptitle(
        f"{config['dashboard']['title']}  |  time range: last {TIME_RANGE_MINUTES}m"
        f"  |  refresh: {config['dashboard']['refresh_seconds']}s  |  source: data/logs.jsonl"
        f"  |  generated: {now.strftime('%Y-%m-%d %H:%M UTC')}",
        fontsize=13,
    )
    blue, red, green, orange = "#4A90D9", "#E4574F", "#50C878", "#E8A838"

    # Panel 1: latency
    ax = axes[0][0]
    p50, p95, p99 = percentile(latencies, 50), percentile(latencies, 95), percentile(latencies, 99)
    ttft95 = percentile(ttfts, 95)
    th = panels["latency"]["threshold"]["value"]
    bars = ax.bar(["P50", "P95", "P99", "TTFT P95"], [p50, p95, p99, ttft95], color=[blue, orange, blue, green])
    ax.axhline(th, color=red, linestyle="--", label=f"SLO p95 <= {th} ms")
    for b, v in zip(bars, [p50, p95, p99, ttft95]):
        ax.text(b.get_x() + b.get_width() / 2, v + 40, f"{v:.0f}", ha="center", fontsize=9)
    ax.set_title("Latency percentiles and TTFT")
    ax.set_ylabel("ms")
    ax.legend(fontsize=8)

    # Panel 2: traffic
    ax = axes[0][1]
    minutes = sorted(by_minute)
    counts = [by_minute[m]["count"] for m in minutes] or [0]
    ax.bar(minutes or ["--"], counts, color=blue)
    ax.axhline(panels["traffic"]["threshold"]["value"], color=green, linestyle="--", label="min 1 req/min")
    ax.set_title(f"Request traffic (total {len(received)}, avg {traffic_rpm:.1f}/min)")
    ax.set_ylabel("requests / minute")
    ax.legend(fontsize=8)

    # Panel 3: errors
    ax = axes[0][2]
    th_err = panels["errors"]["threshold"]["value"]
    bars = ax.bar(["error rate", "retrieval success"], [error_rate, retrieval_rate], color=[red if error_rate > th_err else green, green])
    ax.axhline(th_err, color=red, linestyle="--", label=f"error rate <= {th_err}%")
    ax.axhline(90, color=orange, linestyle=":", label="retrieval >= 90%")
    for b, v in zip(bars, [error_rate, retrieval_rate]):
        ax.text(b.get_x() + b.get_width() / 2, v + 2, f"{v:.1f}%", ha="center", fontsize=9)
    ax.set_title("Error rate and retrieval success")
    ax.set_ylabel("percent")
    ax.set_ylim(0, 115)
    ax.legend(fontsize=8)

    # Panel 4: cost
    ax = axes[1][0]
    th_cost = panels["cost"]["threshold"]["value"]
    cost_by_min = [by_minute[m]["cost"] for m in minutes] or [0]
    ax.bar(minutes or ["--"], cost_by_min, color=blue)
    total_cost = sum(costs)
    ax.axhline(th_cost / TIME_RANGE_MINUTES, color=red, linestyle="--", label=f"window budget <= ${th_cost}")
    ax.set_title(f"Cost over time (total ${total_cost:.4f})")
    ax.set_ylabel("USD / minute")
    ax.legend(fontsize=8)

    # Panel 5: tokens
    ax = axes[1][1]
    th_tok = panels["tokens"]["threshold"]["value"]
    bars = ax.bar(["tokens_in", "tokens_out", "total"], [tokens_in, tokens_out, tokens_in + tokens_out], color=[blue, green, orange])
    ax.axhline(th_tok, color=red, linestyle="--", label=f"total <= {th_tok:,}")
    for b, v in zip(bars, [tokens_in, tokens_out, tokens_in + tokens_out]):
        ax.text(b.get_x() + b.get_width() / 2, v + 400, f"{v:,}", ha="center", fontsize=9)
    ax.set_title("Input and output tokens")
    ax.set_ylabel("tokens")
    ax.legend(fontsize=8)

    # Panel 6: quality
    ax = axes[1][2]
    th_q = panels["quality"]["threshold"]["value"]
    mean_q = sum(quality) / len(quality) if quality else 0
    ax.bar(["mean quality_score"], [mean_q], color=green if mean_q >= th_q else red)
    ax.axhline(th_q, color=red, linestyle="--", label=f"SLO >= {th_q}")
    ax.text(0, mean_q + 0.02, f"{mean_q:.3f}", ha="center", fontsize=10)
    ax.set_title("Quality proxy")
    ax.set_ylabel("score (0-1)")
    ax.set_ylim(0, 1.1)
    ax.legend(fontsize=8)

    for row in axes:
        for a in row:
            a.tick_params(axis="x", rotation=45, labelsize=8)

    output = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(output, dpi=110)
    print(f"Dashboard saved to {output}")
    print(f"records in window: {len(in_window)} | sent: {len(sent)} | p95: {p95:.0f}ms | error rate: {error_rate:.1f}% | total cost: ${total_cost:.4f}")


if __name__ == "__main__":
    main()
