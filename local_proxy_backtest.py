import csv
import importlib.util
import json
import sys
import types
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass
class Order:
    symbol: str
    price: int
    quantity: int


class OrderDepth:
    def __init__(self) -> None:
        self.buy_orders: Dict[int, int] = {}
        self.sell_orders: Dict[int, int] = {}


@dataclass
class TradingState:
    traderData: str
    timestamp: int
    listings: Dict[str, object]
    order_depths: Dict[str, OrderDepth]
    own_trades: Dict[str, list]
    market_trades: Dict[str, list]
    position: Dict[str, int]
    observations: Dict[str, object]


def install_datamodel_stub() -> None:
    module = types.ModuleType("datamodel")
    module.Order = Order
    module.OrderDepth = OrderDepth
    module.TradingState = TradingState
    sys.modules["datamodel"] = module


def load_trader(file_path: Path):
    install_datamodel_stub()
    spec = importlib.util.spec_from_file_location("strategy_module", str(file_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Trader()


def read_book_rows(prices_file: Path, day: int) -> Dict[int, Dict[str, dict]]:
    by_ts: Dict[int, Dict[str, dict]] = defaultdict(dict)
    with prices_file.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            if int(row["day"]) != day:
                continue
            ts = int(row["timestamp"])
            product = row["product"]
            by_ts[ts][product] = row
    return by_ts


def build_depth(row: dict) -> OrderDepth:
    depth = OrderDepth()
    for level in (1, 2, 3):
        bid_p = row.get(f"bid_price_{level}", "")
        bid_v = row.get(f"bid_volume_{level}", "")
        ask_p = row.get(f"ask_price_{level}", "")
        ask_v = row.get(f"ask_volume_{level}", "")
        if bid_p and bid_v:
            depth.buy_orders[int(float(bid_p))] = int(float(bid_v))
        if ask_p and ask_v:
            # datamodel convention: sell volume is negative
            depth.sell_orders[int(float(ask_p))] = -abs(int(float(ask_v)))
    return depth


def best_bid_ask(depth: OrderDepth):
    bid = max(depth.buy_orders) if depth.buy_orders else None
    ask = min(depth.sell_orders) if depth.sell_orders else None
    return bid, ask


def mark_to_market(cash: float, position: Dict[str, int], depths: Dict[str, OrderDepth]) -> float:
    value = cash
    for product, qty in position.items():
        depth = depths.get(product)
        if depth is None:
            continue
        bid, ask = best_bid_ask(depth)
        if bid is None or ask is None:
            continue
        mid = (bid + ask) / 2.0
        value += qty * mid
    return value


def simulate(strategy_file: Path, prices_file: Path, day: int = 2) -> dict:
    trader = load_trader(strategy_file)
    rows_by_ts = read_book_rows(prices_file, day)
    timestamps = sorted(rows_by_ts)

    trader_data = ""
    cash = 0.0
    position: Dict[str, int] = defaultdict(int)
    product_cash: Dict[str, float] = defaultdict(float)
    velvet_two_sided_submissions = 0
    velvet_late_buy_fills = 0
    velvet_late_sell_fills = 0
    state_values = []

    for ts in timestamps:
        order_depths: Dict[str, OrderDepth] = {
            product: build_depth(row) for product, row in rows_by_ts[ts].items()
        }
        state = TradingState(
            traderData=trader_data,
            timestamp=ts,
            listings={},
            order_depths=order_depths,
            own_trades={},
            market_trades={},
            position=dict(position),
            observations={},
        )

        result, _conv, trader_data = trader.run(state)
        if not isinstance(result, dict):
            result = {}

        # Detect same-tick bid+ask submission on same product.
        velvet_orders = result.get("VELVETFRUIT_EXTRACT", [])
        if velvet_orders:
            has_buy = any(o.quantity > 0 for o in velvet_orders)
            has_sell = any(o.quantity < 0 for o in velvet_orders)
            if has_buy and has_sell:
                velvet_two_sided_submissions += 1

        # Conservative fill model: only immediate top-of-book taking fills.
        for product, orders in result.items():
            depth = order_depths.get(product)
            if depth is None:
                continue
            best_bid, best_ask = best_bid_ask(depth)
            if best_bid is None or best_ask is None:
                continue
            ask_avail = -depth.sell_orders[best_ask]
            bid_avail = depth.buy_orders[best_bid]
            for order in orders:
                if order.quantity > 0 and order.price >= best_ask and ask_avail > 0:
                    filled = min(order.quantity, ask_avail)
                    ask_avail -= filled
                    position[product] += filled
                    cash -= filled * best_ask
                    product_cash[product] -= filled * best_ask
                    if product == "VELVETFRUIT_EXTRACT" and ts >= 900000:
                        velvet_late_buy_fills += filled
                elif order.quantity < 0 and order.price <= best_bid and bid_avail > 0:
                    sell_qty = -order.quantity
                    filled = min(sell_qty, bid_avail)
                    bid_avail -= filled
                    position[product] -= filled
                    cash += filled * best_bid
                    product_cash[product] += filled * best_bid
                    if product == "VELVETFRUIT_EXTRACT" and ts >= 900000:
                        velvet_late_sell_fills += filled

        state_values.append((ts, mark_to_market(cash, position, order_depths)))

    final_ts = timestamps[-1]
    final_depths = {product: build_depth(row) for product, row in rows_by_ts[final_ts].items()}
    total_value = mark_to_market(cash, position, final_depths)

    product_pnl: Dict[str, float] = {}
    for product, qty in position.items():
        depth = final_depths.get(product)
        if depth is None:
            continue
        bid, ask = best_bid_ask(depth)
        if bid is None or ask is None:
            continue
        mid = (bid + ask) / 2.0
        product_pnl[product] = product_cash[product] + qty * mid

    worst = min(state_values, key=lambda x: x[1]) if state_values else (0, 0.0)
    best = max(state_values, key=lambda x: x[1]) if state_values else (0, 0.0)
    return {
        "total_proxy_pnl": total_value,
        "final_position": dict(position),
        "product_proxy_pnl": dict(sorted(product_pnl.items())),
        "worst_value": {"timestamp": worst[0], "value": worst[1]},
        "best_value": {"timestamp": best[0], "value": best[1]},
        "velvet_two_sided_submissions": velvet_two_sided_submissions,
        "velvet_late_buy_fills": velvet_late_buy_fills,
        "velvet_late_sell_fills": velvet_late_sell_fills,
        "ticks": len(timestamps),
    }


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: python local_proxy_backtest.py <strategy.py> [day]")
        sys.exit(1)
    strategy = Path(sys.argv[1]).resolve()
    day = int(sys.argv[2]) if len(sys.argv) >= 3 else 2
    prices = Path("ROUND_3") / f"prices_round_3_day_{day}.csv"
    report = simulate(strategy, prices, day=day)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
