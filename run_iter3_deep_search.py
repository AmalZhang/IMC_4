import itertools
import json
from pathlib import Path

from local_proxy_backtest import simulate


BASE_FILE = Path("trader_round3.py")
OUT_DIR = Path("ROUND_3/logs/variant_trials_iter3")


def apply_variant(
    base_text: str,
    take_5200: float,
    make_5200: float,
    limit_5200: int,
    no_make_5200: bool,
    late_cap: int,
    late_diff_thresh: int,
    late_urg_add: float,
) -> str:
    text = base_text
    text = text.replace('"VEV_5200": 2.6,', f'"VEV_5200": {take_5200:.1f},')
    text = text.replace('"VEV_5200": 3.0,', f'"VEV_5200": {make_5200:.1f},')
    text = text.replace('"VEV_5200": 150,', f'"VEV_5200": {limit_5200},')

    if no_make_5200:
        text = text.replace(
            'if product in ("VEV_5300", "VEV_6000", "VEV_6500"):',
            'if product in ("VEV_5200", "VEV_5300", "VEV_6000", "VEV_6500"):',
        )

    text = text.replace("cap = 185 if not late_phase else 170", f"cap = 185 if not late_phase else {late_cap}")
    text = text.replace(
        "if abs(diff) < (10 if not late_phase else 10):",
        f"if abs(diff) < (10 if not late_phase else {late_diff_thresh}):",
    )
    text = text.replace("urgency_edge += 0.0", f"urgency_edge += {late_urg_add}")
    return text


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base_text = BASE_FILE.read_text(encoding="utf-8")

    hedge_presets = [
        (170, 10, 0.0),
        (160, 10, 0.0),
        (170, 8, 0.5),
        (180, 12, 0.0),
    ]
    takes = [2.6, 3.0, 3.2]
    makes = [3.0, 3.4]
    limits = [100, 120, 150]
    no_make_opts = [False, True]

    stage1 = []
    for take_5200, make_5200, limit_5200, no_make_5200, (late_cap, late_diff, late_urg) in itertools.product(
        takes, makes, limits, no_make_opts, hedge_presets
    ):
        name = (
            f"t{take_5200:.1f}_m{make_5200:.1f}_l{limit_5200}_"
            f"nm{int(no_make_5200)}_c{late_cap}_d{late_diff}_u{late_urg}"
        )
        file_path = OUT_DIR / f"{name}.py"
        file_path.write_text(
            apply_variant(
                base_text,
                take_5200,
                make_5200,
                limit_5200,
                no_make_5200,
                late_cap,
                late_diff,
                late_urg,
            ),
            encoding="utf-8",
        )
        rep2 = simulate(file_path, Path("ROUND_3/prices_round_3_day_2.csv"), day=2)
        stage1.append(
            {
                "name": name,
                "file": str(file_path),
                "day2_pnl": rep2["total_proxy_pnl"],
                "day2_worst": rep2["worst_value"]["value"],
                "day2_velvet_two_sided": rep2["velvet_two_sided_submissions"],
            }
        )

    stage1.sort(key=lambda x: x["day2_pnl"], reverse=True)
    top = stage1[:12]

    final = []
    for item in top:
        path = Path(item["file"])
        day_reports = {}
        score = 0.0
        for day in (0, 1, 2):
            rep = simulate(path, Path(f"ROUND_3/prices_round_3_day_{day}.csv"), day=day)
            day_reports[f"day_{day}"] = {
                "pnl": rep["total_proxy_pnl"],
                "worst": rep["worst_value"]["value"],
                "velvet_two_sided_submissions": rep["velvet_two_sided_submissions"],
            }
            score += rep["total_proxy_pnl"]
        final.append(
            {
                "name": item["name"],
                "file": item["file"],
                "score_sum_day012": score,
                "stage1_day2_pnl": item["day2_pnl"],
                "days": day_reports,
            }
        )

    final.sort(key=lambda x: x["score_sum_day012"], reverse=True)
    print(json.dumps({"top12_from_day2_screen": final, "stage1_best20": stage1[:20]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
