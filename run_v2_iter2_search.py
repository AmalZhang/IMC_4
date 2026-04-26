import json
from pathlib import Path

from local_proxy_backtest import simulate


BASE_FILE = Path("ROUND_3/logs/Zhang_v2/407588.py")
OUT_DIR = Path("ROUND_3/logs/variant_trials_iter2")


def make_variant(base_text: str, late_cap: int, late_diff_thresh: int, late_urg_add: float) -> str:
    text = base_text
    text = text.replace("cap = 185 if not late_phase else 200", f"cap = 185 if not late_phase else {late_cap}")
    text = text.replace("if abs(diff) < (10 if not late_phase else 6):", f"if abs(diff) < (10 if not late_phase else {late_diff_thresh}):")
    text = text.replace("urgency_edge += 1.0", f"urgency_edge += {late_urg_add}")
    return text


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base_text = BASE_FILE.read_text(encoding="utf-8")

    results = []
    for late_cap in (150, 160, 170, 180):
        for late_diff_thresh in (8, 10, 12):
            for late_urg_add in (0.0, 0.5, 1.0):
                name = f"cap{late_cap}_d{late_diff_thresh}_u{late_urg_add}"
                text = make_variant(base_text, late_cap, late_diff_thresh, late_urg_add)
                path = OUT_DIR / f"{name}.py"
                path.write_text(text, encoding="utf-8")

                total = 0.0
                day_reports = {}
                for day in (0, 1, 2):
                    prices = Path("ROUND_3") / f"prices_round_3_day_{day}.csv"
                    rep = simulate(path, prices, day=day)
                    total += rep["total_proxy_pnl"]
                    day_reports[f"day_{day}"] = {
                        "pnl": rep["total_proxy_pnl"],
                        "worst": rep["worst_value"]["value"],
                        "velvet_two_sided_submissions": rep["velvet_two_sided_submissions"],
                    }

                results.append(
                    {
                        "name": name,
                        "file": str(path),
                        "score_sum_day012": total,
                        "days": day_reports,
                    }
                )

    results.sort(key=lambda x: x["score_sum_day012"], reverse=True)
    print(json.dumps(results[:10], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
