#!/usr/bin/env python3
import argparse
import json
import math
import statistics
import sys
from typing import Any, Dict, List, Optional, Tuple


def _get(obj: Dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in obj:
            return obj[name]
    return None


def _median(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return statistics.median(values)


def _mad(values: List[float], med: float) -> float:
    return statistics.median([abs(v - med) for v in values]) if values else 0.0


def _robust_z(value: float, med: float, mad: float) -> Optional[float]:
    if mad <= 0:
        return None
    return 0.6745 * (value - med) / mad


def _safe_ratio(num: float, den: float) -> Optional[float]:
    if den == 0:
        return None
    return num / den


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_usage(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    return _get(data, "dailyUsage", "daily_usage") or []


def parse_trend(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    return _get(data, "trendStat", "trend_stat") or []


def format_value(metric: str, value: float) -> str:
    if metric.endswith("_bytes"):
        return f"{value:.0f} bytes"
    if metric.endswith("_usec"):
        return f"{value/1e6:.2f} sec"
    if metric.endswith("_nanos"):
        return f"{value/1e9:.2f} sec"
    return f"{value:.2f}"


def detect_usage_anomalies(daily: List[Dict[str, Any]]) -> List[str]:
    metrics = [
        "invocations",
        "actionCacheHits",
        "casCacheHits",
        "totalDownloadSizeBytes",
        "totalUploadSizeBytes",
        "totalExternalDownloadSizeBytes",
        "totalInternalDownloadSizeBytes",
        "totalWorkflowDownloadSizeBytes",
        "linuxExecutionDurationUsec",
        "cloudCpuNanos",
        "cloudRbeCpuNanos",
        "cloudWorkflowCpuNanos",
    ]
    anomalies: List[str] = []
    for metric in metrics:
        series: List[Tuple[str, float]] = []
        for entry in daily:
            period = entry.get("period", "")
            value = entry.get(metric, 0) or 0
            if isinstance(value, str):
                try:
                    value = float(value)
                except ValueError:
                    value = 0
            series.append((period, float(value)))
        values = [v for _, v in series]
        med = _median(values)
        if med is None:
            continue
        mad = _mad(values, med)
        for period, value in series:
            z = _robust_z(value, med, mad)
            ratio = _safe_ratio(value, med)
            if z is not None and abs(z) >= 3.5:
                anomalies.append(
                    f"usage:{metric} {period} value {format_value(metric, value)} (z={z:.2f}, median={format_value(metric, med)})"
                )
            elif ratio is not None and (ratio >= 2.0 or ratio <= 0.5) and med > 0:
                anomalies.append(
                    f"usage:{metric} {period} value {format_value(metric, value)} ({ratio:.2f}x median {format_value(metric, med)})"
                )
    return anomalies


def detect_trend_anomalies(trends: List[Dict[str, Any]]) -> List[str]:
    anomalies: List[str] = []
    hit_rates: List[Tuple[str, float]] = []
    downloads: List[Tuple[str, float]] = []
    for entry in trends:
        label = entry.get("name") or str(entry.get("bucketStartTimeMicros", ""))
        hits = float(entry.get("actionCacheHits", 0) or 0)
        misses = float(entry.get("actionCacheMisses", 0) or 0)
        rate = _safe_ratio(hits, hits + misses)
        if rate is not None:
            hit_rates.append((label, rate))
        downloads.append((label, float(entry.get("totalDownloadSizeBytes", 0) or 0)))

    if hit_rates:
        rates_only = [r for _, r in hit_rates]
        med = _median(rates_only)
        mad = _mad(rates_only, med) if med is not None else 0.0
        for label, rate in hit_rates:
            if med is None:
                continue
            z = _robust_z(rate, med, mad)
            if z is not None and z <= -3.0:
                anomalies.append(
                    f"trend:ac_hit_rate {label} rate {rate:.3f} (z={z:.2f}, median={med:.3f})"
                )
            elif rate < med - 0.10:
                anomalies.append(
                    f"trend:ac_hit_rate {label} rate {rate:.3f} (median {med:.3f})"
                )

    if downloads:
        vals = [v for _, v in downloads]
        med = _median(vals)
        if med is not None:
            mad = _mad(vals, med)
            for label, value in downloads:
                z = _robust_z(value, med, mad)
                ratio = _safe_ratio(value, med)
                if z is not None and abs(z) >= 3.5:
                    anomalies.append(
                        f"trend:download_bytes {label} value {format_value('total_download_size_bytes', value)} (z={z:.2f}, median={format_value('total_download_size_bytes', med)})"
                    )
                elif ratio is not None and (ratio >= 2.0 or ratio <= 0.5) and med > 0:
                    anomalies.append(
                        f"trend:download_bytes {label} value {format_value('total_download_size_bytes', value)} ({ratio:.2f}x median {format_value('total_download_size_bytes', med)})"
                    )
    return anomalies


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect anomalies in BuildBuddy usage/trends JSON.")
    parser.add_argument("--usage", help="Path to GetUsage response JSON")
    parser.add_argument("--trend", help="Path to GetTrend response JSON")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    anomalies: List[str] = []

    if args.usage:
        usage_data = load_json(args.usage)
        daily = parse_usage(usage_data)
        anomalies.extend(detect_usage_anomalies(daily))

    if args.trend:
        trend_data = load_json(args.trend)
        trends = parse_trend(trend_data)
        anomalies.extend(detect_trend_anomalies(trends))

    if args.json:
        print(json.dumps({"anomalies": anomalies}, indent=2))
    else:
        if not anomalies:
            print("No anomalies detected with current thresholds.")
        else:
            print("Anomalies detected:")
            for item in anomalies:
                print(f"- {item}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
