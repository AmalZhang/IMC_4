import copy
import json
from pathlib import Path
from typing import Dict

from local_proxy_backtest import simulate


BASE_FILE = Path("ROUND_3/logs/Zhang_v2/407588.py")
OUT_DIR = Path("ROUND_3/logs/variant_trials")


def apply_rules(text: str, rules: Dict[str, str]) -> str:
    out = text
    for old, new in rules.items():
        if old not in out:
            raise RuntimeError(f"pattern not found: {old}")
        out = out.replace(old, new)
    return out


def variant_rules() -> Dict[str, Dict[str, str]]:
    return {
        "v2_base_copy": {},
        "v2_5200_wider_edges": {
            '"VEV_5200": 2.6,': '"VEV_5200": 3.2,',
            '"VEV_5200": 3.0,': '"VEV_5200": 3.8,',
            '"VEV_5200": 150,': '"VEV_5200": 110,',
        },
        "v2_5200_no_make": {
            'if product in ("VEV_5300", "VEV_6000", "VEV_6500"):':
            'if product in ("VEV_5200", "VEV_5300", "VEV_6000", "VEV_6500"):',
            '"VEV_5200": 150,': '"VEV_5200": 110,',
        },
        "v2_smaller_option_sizes": {
            "min(-volume, risk_limit - pos, 22)": "min(-volume, risk_limit - pos, 16)",
            "min(volume, pos + risk_limit, 22)": "min(volume, pos + risk_limit, 16)",
            "buy_qty = min(16, max(0, risk_limit - pos))": "buy_qty = min(12, max(0, risk_limit - pos))",
            "sell_qty = min(16, max(0, pos + risk_limit))": "sell_qty = min(12, max(0, pos + risk_limit))",
        },
        "v2_hedge_smoother": {
            "cap = 185 if not late_phase else 200": "cap = 185 if not late_phase else 170",
            "if abs(diff) < (10 if not late_phase else 6):": "if abs(diff) < (10 if not late_phase else 10):",
            "urgency_edge += 1.0": "urgency_edge += 0.5",
        },
        "v2_combo_5200_and_hedge": {
            '"VEV_5200": 2.6,': '"VEV_5200": 3.2,',
            '"VEV_5200": 3.0,': '"VEV_5200": 3.8,',
            '"VEV_5200": 150,': '"VEV_5200": 100,',
            'if product in ("VEV_5300", "VEV_6000", "VEV_6500"):':
            'if product in ("VEV_5200", "VEV_5300", "VEV_6000", "VEV_6500"):',
            "cap = 185 if not late_phase else 200": "cap = 185 if not late_phase else 170",
            "if abs(diff) < (10 if not late_phase else 6):": "if abs(diff) < (10 if not late_phase else 10):",
            "urgency_edge += 1.0": "urgency_edge += 0.5",
        },
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base_text = BASE_FILE.read_text(encoding="utf-8")
    all_results = []

    for name, rules in variant_rules().items():
        text = apply_rules(base_text, rules) if rules else copy.copy(base_text)
        file_path = OUT_DIR / f"{name}.py"
        file_path.write_text(text, encoding="utf-8")

        day_reports = {}
        total_score = 0.0
        for day in (0, 1, 2):
            prices_file = Path("ROUND_3") / f"prices_round_3_day_{day}.csv"
            report = simulate(file_path, prices_file, day=day)
            day_reports[f"day_{day}"] = {
                "pnl": report["total_proxy_pnl"],
                "worst": report["worst_value"]["value"],
                "velvet_two_sided_submissions": report["velvet_two_sided_submissions"],
            }
            total_score += report["total_proxy_pnl"]

        all_results.append(
            {
                "name": name,
                "file": str(file_path),
                "score_sum_day012": total_score,
                "days": day_reports,
            }
        )

    all_results.sort(key=lambda x: x["score_sum_day012"], reverse=True)
    print(json.dumps(all_results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
