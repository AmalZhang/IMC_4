# IMC Prosperity 4 Project Notes

This workspace is for IMC Prosperity 4 algorithmic trading. Before changing
trading code, prefer the official/wiki rules over assumptions. The Notion MCP
source page is available in this workspace as "Prosperity 4 Wiki".

## Sources Checked

- Notion: `Prosperity 4 Wiki`
- Notion: `Round 3 - "Gloves Off"`
- Notion: `Writing an Algorithm in Python`
- Notion: `Game Mechanics Overview`
- Notion: `FAQ`
- Notion: `Rules`

## Python Submission Contract

- Submit a Python file defining class `Trader`.
- Required method: `run(self, state: TradingState)`.
- `run` must return exactly `(result, conversions, traderData)`.
- `result` is `Dict[str, List[Order]]`, keyed by product symbol.
- Orders must use `datamodel.Order(symbol, price, quantity)`.
- Positive order quantity means buy; negative quantity means sell.
- `OrderDepth.buy_orders` maps price to positive volume.
- `OrderDepth.sell_orders` maps price to negative volume.
- Outstanding player orders are cancelled at the end of each iteration.
- Matching is instantaneous against visible book orders.
- AWS Lambda is stateless: do not rely on class/global variables persisting
  between calls. Persist needed state through `traderData`.
- `traderData` is a string and is cut at 50,000 characters by the framework.
- `run` should finish within 900 ms; keep code lightweight.
- Conversions should be `0` or `None` unless a round explicitly supports
  conversion logic for a product.

## Library Rules

- Python 3.12 standard library is supported.
- External libraries are not generally supported except the wiki-listed
  supported libraries.
- Wiki-listed supported libraries include `pandas`, `numpy`, `statistics`,
  `math`, `typing`, and `jsonpickle`.
- For submitted trading code, prefer standard library only unless a stronger
  reason exists.
- Local analysis scripts may use broader tooling, but keep the submitted
  `Trader` implementation compatible with the competition environment.

## Position Limit Rules

- Position limits are absolute per product: position must stay between
  `-limit` and `+limit`.
- If aggregate buy orders for a product could exceed the long limit if fully
  filled, all orders for that product can be rejected.
- If aggregate sell orders for a product could exceed the short limit if fully
  filled, all orders for that product can be rejected.
- Always cap submitted orders per product against current `state.position`.

## Round 3: Gloves Off

- Round 3 starts Phase 2/GOAT; leaderboard resets to zero.
- Rounds 3, 4, and 5 last 48 hours.
- Round 3 algorithmic products:
  - `HYDROGEL_PACK`
  - `VELVETFRUIT_EXTRACT`
  - `VEV_4000`
  - `VEV_4500`
  - `VEV_5000`
  - `VEV_5100`
  - `VEV_5200`
  - `VEV_5300`
  - `VEV_5400`
  - `VEV_5500`
  - `VEV_6000`
  - `VEV_6500`
- Position limits:
  - `HYDROGEL_PACK`: 200
  - `VELVETFRUIT_EXTRACT`: 200
  - Each voucher: 300
- `HYDROGEL_PACK` and `VELVETFRUIT_EXTRACT` are delta-one products.
- Vouchers are options on `VELVETFRUIT_EXTRACT`; the number in `VEV_<strike>`
  is the strike price.
- Voucher expiration schedule:
  - 7 days at the start of Round 1
  - 6 days at the start of Round 2
  - 5 days at the start of Round 3 final simulation
  - Historical Round 3 data: day 0 starts at TTE 8d, day 1 at 7d, day 2 at 6d
- Vouchers cannot be exercised before expiry.
- Inventory does not carry into the next round; open positions are liquidated
  against hidden fair value at round end.

## Round 3 Manual Challenge

- Product: Ornamental Bio-Pods.
- Manual challenge is independent of algorithmic PnL.
- Secret counterparties have reserve prices uniformly over `670..920` in
  increments of 5, inclusive.
- Submit two bids manually in the UI.
- If first bid is higher than reserve price, trade occurs at first bid.
- If second bid is higher than reserve price and higher than the mean second
  bid of all players trading at their second bid, trade occurs at second bid.
- If second bid is higher than reserve but less than or equal to that mean,
  trade probability/PnL is penalized by `((920 - avg_b2) / (920 - b2)) ** 3`.
- Acquired Bio-Pods are sold next day at fair value 920.
- Current local EV analysis suggests bids around `(755, 840)` are optimal if
  average second bids are near 830-840; raise second bid if expecting a much
  higher crowd average.

## Local Files

- `ROUND_3/` contains historical price and trade CSVs for Round 3.
- `round3_analysis.py` is a local standard-library analysis script; do not
  submit it as the trading algorithm.
- `trader_round3.py` is the current Round 3 trading implementation.
- `IMC协作提交流程.md` is the Chinese operator guide for the human/Codex
  submission workflow in this workspace.

## Trading Code Checklist

- Keep import set competition-safe.
- Keep `Trader.run` return signature unchanged.
- Re-run `py_compile` after edits.
- Check aggregate per-product buy and sell quantities against position limits.
- Avoid large print output and large `traderData`.
- Treat `state.position` as the source of truth for inventory.
- Do not assume previous in-memory variables survive across calls.
- For Round 3 options, use TTE based on 5 days at start of final simulation and
  decrement by `timestamp / 1_000_000` days.
