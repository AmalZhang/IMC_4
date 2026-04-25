import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path
from statistics import NormalDist


ROOT = Path("ROUND_3")
VOUCHERS = [
    "VEV_4000",
    "VEV_4500",
    "VEV_5000",
    "VEV_5100",
    "VEV_5200",
    "VEV_5300",
    "VEV_5400",
    "VEV_5500",
    "VEV_6000",
    "VEV_6500",
]
STRIKES = {product: int(product.split("_")[1]) for product in VOUCHERS}

NORM = NormalDist()


def as_float(value):
    return None if value == "" else float(value)


def norm_cdf(x):
    return NORM.cdf(x)


def black_scholes_call(spot, strike, tte_years, vol):
    if tte_years <= 0 or vol <= 0:
        return max(spot - strike, 0.0)
    vol_sqrt_t = vol * math.sqrt(tte_years)
    d1 = (math.log(spot / strike) + 0.5 * vol * vol * tte_years) / vol_sqrt_t
    d2 = d1 - vol_sqrt_t
    return spot * norm_cdf(d1) - strike * norm_cdf(d2)


def implied_vol(price, spot, strike, tte_years):
    intrinsic = max(spot - strike, 0.0)
    if price <= intrinsic + 1e-7:
        return 0.0
    lo, hi = 0.001, 5.0
    for _ in range(34):
        mid = (lo + hi) / 2
        if black_scholes_call(spot, strike, tte_years, mid) < price:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def load_prices():
    rows = []
    for path in sorted(ROOT.glob("prices_round_3_day_*.csv")):
        with path.open(newline="") as file:
            for row in csv.DictReader(file, delimiter=";"):
                row["day"] = int(row["day"])
                row["timestamp"] = int(row["timestamp"])
                row["mid_price"] = float(row["mid_price"])
                for col in ("bid_price_1", "ask_price_1", "bid_volume_1", "ask_volume_1"):
                    row[col] = as_float(row[col])
                rows.append(row)
    return rows


def product_stats(rows):
    by_product = defaultdict(list)
    for row in rows:
        by_product[row["product"]].append(row)

    print("PRODUCT STATS")
    for product in sorted(by_product):
        mids = [row["mid_price"] for row in by_product[product]]
        spreads = [
            row["ask_price_1"] - row["bid_price_1"]
            for row in by_product[product]
            if row["ask_price_1"] is not None and row["bid_price_1"] is not None
        ]
        print(
            f"{product:22s} mean={statistics.mean(mids):9.3f} "
            f"std={statistics.pstdev(mids):7.3f} min={min(mids):8.2f} "
            f"max={max(mids):8.2f} spread={statistics.mean(spreads):6.3f}"
        )


def fit_iv_surface(rows):
    by_time = defaultdict(dict)
    for row in rows:
        if row["timestamp"] % 1000 == 0:
            by_time[(row["day"], row["timestamp"])][row["product"]] = row["mid_price"]

    xs = []
    ys = []
    by_product = defaultdict(list)
    for (day, timestamp), prices in sorted(by_time.items()):
        spot = prices["VELVETFRUIT_EXTRACT"]
        tte_years = (8 - day - timestamp / 1_000_000) / 365
        for product in VOUCHERS:
            strike = STRIKES[product]
            price = prices[product]
            if price <= 1.0:
                continue
            vol = implied_vol(price, spot, strike, tte_years)
            if vol <= 0 or not math.isfinite(vol):
                continue
            extrinsic = price - max(spot - strike, 0.0)
            if strike < 5000 and extrinsic < 1.0:
                continue
            moneyness = math.log(strike / spot) / math.sqrt(tte_years)
            xs.append(moneyness)
            ys.append(vol)
            by_product[product].append(vol)

    n = len(xs)
    sums = [sum(x**power for x in xs) for power in range(5)]
    rhs = [sum(y * x**power for x, y in zip(xs, ys)) for power in range(3)]
    matrix = [
        [sums[4], sums[3], sums[2], rhs[2]],
        [sums[3], sums[2], sums[1], rhs[1]],
        [sums[2], sums[1], n, rhs[0]],
    ]
    for i in range(3):
        pivot = max(range(i, 3), key=lambda row: abs(matrix[row][i]))
        matrix[i], matrix[pivot] = matrix[pivot], matrix[i]
        div = matrix[i][i]
        for col in range(i, 4):
            matrix[i][col] /= div
        for row in range(3):
            if row == i:
                continue
            factor = matrix[row][i]
            for col in range(i, 4):
                matrix[row][col] -= factor * matrix[i][col]

    a, b, c = [matrix[i][3] for i in range(3)]
    rmse = math.sqrt(sum((a * x * x + b * x + c - y) ** 2 for x, y in zip(xs, ys)) / n)

    print("\nIMPLIED VOL STATS")
    for product in VOUCHERS:
        values = by_product[product]
        if values:
            print(
                f"{product:8s} n={len(values):5d} mean={statistics.mean(values):.5f} "
                f"std={statistics.pstdev(values):.5f}"
            )
    print(f"surface: vol = {a:.8f} * m^2 + {b:.8f} * m + {c:.8f}; rmse={rmse:.5f}")

    print("\nMODEL FAIR VALUES AT S=5250, TTE=5D")
    for product in VOUCHERS:
        strike = STRIKES[product]
        tte_years = 5 / 365
        moneyness = math.log(strike / 5250) / math.sqrt(tte_years)
        vol = max(0.05, min(2.0, a * moneyness * moneyness + b * moneyness + c))
        print(f"{product:8s} vol={vol:.5f} fair={black_scholes_call(5250, strike, tte_years, vol):8.3f}")


def manual_bid_ev(avg_second_bid):
    reserves = list(range(670, 921, 5))

    def score(first_bid, second_bid):
        multiplier = 1.0
        if second_bid <= avg_second_bid:
            multiplier = ((920 - avg_second_bid) / (920 - second_bid)) ** 3 if second_bid < 920 else 0.0
        pnl = 0.0
        for reserve in reserves:
            if first_bid > reserve:
                pnl += 920 - first_bid
            elif second_bid > reserve:
                pnl += (920 - second_bid) * multiplier
        return pnl / len(reserves)

    candidates = []
    for first_bid in range(670, 921, 5):
        for second_bid in range(670, 921, 5):
            candidates.append((score(first_bid, second_bid), first_bid, second_bid))
    return sorted(candidates, reverse=True)[:5]


def main():
    rows = load_prices()
    product_stats(rows)
    fit_iv_surface(rows)

    print("\nMANUAL CHALLENGE EV BY ASSUMED AVG SECOND BID")
    for avg in (830, 840, 850, 860, 870, 880, 890):
        best = ", ".join(f"({b1},{b2})={ev:.2f}" for ev, b1, b2 in manual_bid_ev(avg)[:3])
        print(f"avg_b2={avg}: {best}")


if __name__ == "__main__":
    main()
