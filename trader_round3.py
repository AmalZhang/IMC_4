import json
import math
from typing import Dict, List, Optional, Tuple

from datamodel import Order, OrderDepth, TradingState


class Trader:
    HYDROGEL = "HYDROGEL_PACK"
    VELVETFRUIT = "VELVETFRUIT_EXTRACT"
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
    LIMITS = {
        HYDROGEL: 200,
        VELVETFRUIT: 200,
        "VEV_4000": 300,
        "VEV_4500": 300,
        "VEV_5000": 300,
        "VEV_5100": 300,
        "VEV_5200": 300,
        "VEV_5300": 300,
        "VEV_5400": 300,
        "VEV_5500": 300,
        "VEV_6000": 300,
        "VEV_6500": 300,
    }

    # Fitted from historical day 0/1/2 where voucher TTE is 8/7/6 days.
    # m = log(K / S) / sqrt(T), vol = A*m^2 + B*m + C.
    IV_A = 0.15866407048780945
    IV_B = -0.003910782888893238
    IV_C = 0.23205497725840138

    OPTION_TAKE_EDGE = {
        "VEV_4000": 12.0,
        "VEV_4500": 9.0,
        "VEV_5000": 4.0,
        "VEV_5100": 3.0,
        "VEV_5200": 2.2,
        "VEV_5300": 1.7,
        "VEV_5400": 1.2,
        "VEV_5500": 1.0,
        "VEV_6000": 1.0,
        "VEV_6500": 1.0,
    }
    OPTION_MAKE_EDGE = {
        "VEV_4000": 13.0,
        "VEV_4500": 10.0,
        "VEV_5000": 4.5,
        "VEV_5100": 3.3,
        "VEV_5200": 2.5,
        "VEV_5300": 1.9,
        "VEV_5400": 1.4,
        "VEV_5500": 1.2,
        "VEV_6000": 1.2,
        "VEV_6500": 1.2,
    }

    def run(self, state: TradingState):
        memory = self.load_memory(state.traderData)
        result: Dict[str, List[Order]] = {}

        for product, anchor in ((self.HYDROGEL, 10000.0), (self.VELVETFRUIT, 5250.0)):
            if product in state.order_depths:
                mid = self.mid_price(state.order_depths[product])
                if mid is not None:
                    key = f"ema_{product}"
                    initial = mid if product == self.VELVETFRUIT else anchor
                    memory[key] = 0.92 * memory.get(key, initial) + 0.08 * mid

        if self.HYDROGEL in state.order_depths:
            fair = 0.80 * 10000.0 + 0.20 * memory.get(f"ema_{self.HYDROGEL}", 10000.0)
            result[self.HYDROGEL] = self.trade_delta_one(
                self.HYDROGEL,
                state.order_depths[self.HYDROGEL],
                state.position.get(self.HYDROGEL, 0),
                fair,
                take_edge=9.0,
                make_edge=8.0,
                skew=0.06,
            )

        spot_mid = None
        if self.VELVETFRUIT in state.order_depths:
            spot_mid = self.mid_price(state.order_depths[self.VELVETFRUIT])
            fair = spot_mid if spot_mid is not None else memory.get(f"ema_{self.VELVETFRUIT}", 5250.0)
            result[self.VELVETFRUIT] = self.trade_delta_one(
                self.VELVETFRUIT,
                state.order_depths[self.VELVETFRUIT],
                state.position.get(self.VELVETFRUIT, 0),
                fair,
                take_edge=3.0,
                make_edge=2.0,
                skew=0.04,
            )

        if spot_mid is not None:
            tte_years = self.tte_years(state.timestamp)
            vol_shift = self.estimate_vol_shift(state.order_depths, spot_mid, tte_years)
            expected_option_delta_change = 0.0
            for product in self.VOUCHERS:
                if product not in state.order_depths:
                    continue
                fair, delta = self.option_fair_and_delta(product, spot_mid, tte_years, vol_shift)
                orders, delta_change = self.trade_option(
                    product,
                    state.order_depths[product],
                    state.position.get(product, 0),
                    fair,
                    delta,
                )
                result[product] = orders
                expected_option_delta_change += delta_change

            if self.VELVETFRUIT in state.order_depths:
                hedge_orders = self.hedge_delta(
                    state.order_depths[self.VELVETFRUIT],
                    state.position.get(self.VELVETFRUIT, 0),
                    state.position,
                    spot_mid,
                    tte_years,
                    vol_shift,
                    expected_option_delta_change,
                )
                result[self.VELVETFRUIT] = hedge_orders + result.get(self.VELVETFRUIT, [])

        for product, orders in list(result.items()):
            result[product] = self.cap_orders(product, orders, state.position.get(product, 0))
        return result, 0, json.dumps(memory, separators=(",", ":"))

    def trade_delta_one(
        self,
        product: str,
        depth: OrderDepth,
        position: int,
        fair: float,
        take_edge: float,
        make_edge: float,
        skew: float,
    ) -> List[Order]:
        orders: List[Order] = []
        limit = self.LIMITS[product]
        pos = position
        skewed_fair = fair - skew * pos

        for price, volume in sorted(depth.sell_orders.items()):
            if price > skewed_fair - take_edge or pos >= limit:
                break
            qty = min(-volume, limit - pos)
            if qty > 0:
                orders.append(Order(product, price, qty))
                pos += qty

        for price, volume in sorted(depth.buy_orders.items(), reverse=True):
            if price < skewed_fair + take_edge or pos <= -limit:
                break
            qty = min(volume, pos + limit)
            if qty > 0:
                orders.append(Order(product, price, -qty))
                pos -= qty

        best_bid, best_ask = self.best_bid_ask(depth)
        if best_bid is None or best_ask is None:
            return orders

        bid_price = min(best_bid + 1, math.floor(skewed_fair - make_edge))
        ask_price = max(best_ask - 1, math.ceil(skewed_fair + make_edge))
        if bid_price < ask_price:
            buy_qty = min(20, limit - pos)
            sell_qty = min(20, pos + limit)
            if buy_qty > 0:
                orders.append(Order(product, bid_price, buy_qty))
            if sell_qty > 0:
                orders.append(Order(product, ask_price, -sell_qty))
        return orders

    def trade_option(
        self,
        product: str,
        depth: OrderDepth,
        position: int,
        fair: float,
        delta: float,
    ) -> Tuple[List[Order], float]:
        orders: List[Order] = []
        limit = self.LIMITS[product]
        pos = position
        delta_change = 0.0
        take_edge = self.OPTION_TAKE_EDGE[product]
        make_edge = self.OPTION_MAKE_EDGE[product]
        skewed_fair = fair - 0.025 * pos

        for price, volume in sorted(depth.sell_orders.items()):
            if price > skewed_fair - take_edge or pos >= limit:
                break
            qty = min(-volume, limit - pos, 35)
            if qty > 0:
                orders.append(Order(product, price, qty))
                pos += qty
                delta_change += qty * delta

        for price, volume in sorted(depth.buy_orders.items(), reverse=True):
            if price < skewed_fair + take_edge or pos <= -limit:
                break
            qty = min(volume, pos + limit, 35)
            if qty > 0:
                orders.append(Order(product, price, -qty))
                pos -= qty
                delta_change -= qty * delta

        # Deep OTM vouchers are mostly one-tick optionality; avoid making a market there.
        if product in ("VEV_6000", "VEV_6500"):
            return orders, delta_change

        best_bid, best_ask = self.best_bid_ask(depth)
        if best_bid is None or best_ask is None:
            return orders, delta_change

        bid_price = min(best_bid + 1, math.floor(skewed_fair - make_edge))
        ask_price = max(best_ask - 1, math.ceil(skewed_fair + make_edge))
        if bid_price < ask_price:
            buy_qty = min(25, limit - pos)
            sell_qty = min(25, pos + limit)
            if buy_qty > 0:
                orders.append(Order(product, bid_price, buy_qty))
            if sell_qty > 0:
                orders.append(Order(product, ask_price, -sell_qty))
        return orders, delta_change

    def hedge_delta(
        self,
        depth: OrderDepth,
        current_underlying_position: int,
        positions: Dict[str, int],
        spot: float,
        tte_years: float,
        vol_shift: float,
        expected_option_delta_change: float,
    ) -> List[Order]:
        net_option_delta = expected_option_delta_change
        for product in self.VOUCHERS:
            qty = positions.get(product, 0)
            if qty == 0:
                continue
            _, delta = self.option_fair_and_delta(product, spot, tte_years, vol_shift)
            net_option_delta += qty * delta

        target = int(round(max(-160, min(160, -net_option_delta))))
        diff = target - current_underlying_position
        if abs(diff) < 15:
            return []

        orders: List[Order] = []
        pos = current_underlying_position
        limit = self.LIMITS[self.VELVETFRUIT]
        urgency_edge = 4.0 if abs(diff) > 80 else 2.0

        if diff > 0:
            remaining = min(diff, limit - pos)
            for price, volume in sorted(depth.sell_orders.items()):
                if remaining <= 0 or price > spot + urgency_edge:
                    break
                qty = min(-volume, remaining)
                if qty > 0:
                    orders.append(Order(self.VELVETFRUIT, price, qty))
                    remaining -= qty
        else:
            remaining = min(-diff, pos + limit)
            for price, volume in sorted(depth.buy_orders.items(), reverse=True):
                if remaining <= 0 or price < spot - urgency_edge:
                    break
                qty = min(volume, remaining)
                if qty > 0:
                    orders.append(Order(self.VELVETFRUIT, price, -qty))
                    remaining -= qty
        return orders

    def estimate_vol_shift(self, order_depths: Dict[str, OrderDepth], spot: float, tte_years: float) -> float:
        diffs = []
        for product in ("VEV_5000", "VEV_5100", "VEV_5200", "VEV_5300", "VEV_5400", "VEV_5500"):
            depth = order_depths.get(product)
            mid = self.mid_price(depth) if depth is not None else None
            if mid is None or mid <= 1:
                continue
            strike = self.STRIKES[product]
            market_vol = self.implied_vol(mid, spot, strike, tte_years)
            model_vol = self.smile_vol(spot, strike, tte_years, 0.0)
            if market_vol > 0:
                diffs.append(market_vol - model_vol)
        if not diffs:
            return 0.0
        diffs.sort()
        median = diffs[len(diffs) // 2]
        return max(-0.025, min(0.025, median))

    def option_fair_and_delta(self, product: str, spot: float, tte_years: float, vol_shift: float) -> Tuple[float, float]:
        strike = self.STRIKES[product]
        vol = self.smile_vol(spot, strike, tte_years, vol_shift)
        fair = self.black_scholes_call(spot, strike, tte_years, vol)
        delta = self.black_scholes_delta(spot, strike, tte_years, vol)
        if product == "VEV_6000":
            fair = min(fair, 0.65)
        elif product == "VEV_6500":
            fair = min(fair, 0.80)
        return fair, delta

    def smile_vol(self, spot: float, strike: int, tte_years: float, shift: float) -> float:
        if tte_years <= 0:
            return 0.0
        moneyness = math.log(strike / spot) / math.sqrt(tte_years)
        vol = self.IV_A * moneyness * moneyness + self.IV_B * moneyness + self.IV_C + shift
        return max(0.12, min(1.20, vol))

    def black_scholes_call(self, spot: float, strike: int, tte_years: float, vol: float) -> float:
        if tte_years <= 0 or vol <= 0:
            return max(spot - strike, 0.0)
        vol_sqrt_t = vol * math.sqrt(tte_years)
        d1 = (math.log(spot / strike) + 0.5 * vol * vol * tte_years) / vol_sqrt_t
        d2 = d1 - vol_sqrt_t
        return spot * self.norm_cdf(d1) - strike * self.norm_cdf(d2)

    def black_scholes_delta(self, spot: float, strike: int, tte_years: float, vol: float) -> float:
        if tte_years <= 0 or vol <= 0:
            return 1.0 if spot > strike else 0.0
        vol_sqrt_t = vol * math.sqrt(tte_years)
        d1 = (math.log(spot / strike) + 0.5 * vol * vol * tte_years) / vol_sqrt_t
        return self.norm_cdf(d1)

    def implied_vol(self, price: float, spot: float, strike: int, tte_years: float) -> float:
        intrinsic = max(spot - strike, 0.0)
        if price <= intrinsic + 1e-7:
            return 0.0
        lo, hi = 0.001, 5.0
        for _ in range(28):
            mid = (lo + hi) / 2
            if self.black_scholes_call(spot, strike, tte_years, mid) < price:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    def tte_years(self, timestamp: int) -> float:
        return max(0.01 / 365, (5.0 - timestamp / 1_000_000) / 365)

    def mid_price(self, depth: Optional[OrderDepth]) -> Optional[float]:
        if depth is None or not depth.buy_orders or not depth.sell_orders:
            return None
        best_bid = max(depth.buy_orders)
        best_ask = min(depth.sell_orders)
        return (best_bid + best_ask) / 2

    def best_bid_ask(self, depth: OrderDepth) -> Tuple[Optional[int], Optional[int]]:
        best_bid = max(depth.buy_orders) if depth.buy_orders else None
        best_ask = min(depth.sell_orders) if depth.sell_orders else None
        return best_bid, best_ask

    def norm_cdf(self, x: float) -> float:
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    def load_memory(self, trader_data: str) -> Dict[str, float]:
        if not trader_data:
            return {}
        try:
            parsed = json.loads(trader_data)
            return {str(key): float(value) for key, value in parsed.items()}
        except Exception:
            return {}

    def cap_orders(self, product: str, orders: List[Order], position: int) -> List[Order]:
        limit = self.LIMITS[product]
        buy_capacity = max(0, limit - position)
        sell_capacity = max(0, position + limit)
        capped: List[Order] = []
        for order in orders:
            if order.quantity > 0:
                qty = min(order.quantity, buy_capacity)
                buy_capacity -= qty
            else:
                qty = -min(-order.quantity, sell_capacity)
                sell_capacity += qty
            if qty != 0:
                capped.append(Order(order.symbol, order.price, qty))
        return capped
