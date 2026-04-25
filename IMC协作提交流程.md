# IMC 比赛协作提交流程

这份文档用于规范你和 Codex 在 IMC Prosperity 比赛中的协作方式，目标是把“研究、改代码、提交、看日志、继续迭代”这件事做成稳定流程，而不是临时来回沟通。

## 核心结论

当前最稳的模式是：

- Codex 负责：读取 Wiki、分析历史数据、修改代码、本地校验、解释问题、根据测试日志继续优化。
- 你负责：在 IMC 网页端上传 Python 文件、设为 `active`、查看平台测试结果和 debug log、把关键信息回传给 Codex。

不建议把流程设计成“Codex 自动持续提交”。原因：

- Prosperity 最终生效的是网页 UI 中最后一个 `active` 的算法版本。
- 当前协作环境里，Codex 不能稳定代替你完成网页端上传并确认 `active` 状态。
- 比赛截止前，人工确认一次“当前 active 的文件就是目标版本”是必要动作。

## 标准工作流

每一轮建议按下面流程执行。

### 1. 建立当前轮次目标

你先明确这次迭代属于哪一种：

- 新建策略
- 修复报错
- 降低超时风险
- 修复仓位/下单逻辑
- 根据平台测试结果继续优化 PnL

对 Codex 下达任务时，尽量明确说：

- 当前轮次，例如 `Round 3`
- 当前主文件，例如 `trader_round3.py`
- 当前遇到的问题，例如 `平台测试报超时`、`PnL 下降`、`某产品亏损严重`
- 是否已有新的平台日志/截图/回测结果

### 2. Codex 本地分析与改代码

Codex 会负责：

- 读取本地代码和 `ROUND_3/` 历史数据
- 对照 Notion Wiki 检查接口、仓位限制、库限制、TTE 等规则
- 修改提交用代码
- 做本地最低限度校验

本项目当前约定：

- 提交文件：`trader_round3.py`
- 本地分析脚本：`round3_analysis.py`
- 规则索引：`AGENTS.md`
- GitHub 仓库：`https://github.com/AmalZhang/IMC_4.git`
- 平台测试日志目录：`ROUND_3/logs/`

### 3. 提交前检查

在你上传前，至少确认下面几点：

1. 提交文件中存在 `class Trader`
2. `run(self, state)` 返回 `(result, conversions, traderData)`
3. 导入库符合比赛环境
4. 没有把分析脚本错传成提交文件
5. `traderData` 没有做超大对象持久化
6. 同一产品的聚合买单/卖单不会越过 position limit
7. 没有明显的大量 `print`
8. 本地至少通过一次：

```python
python -m py_compile trader_round3.py
```

如果 Codex 没明确说“这个版本可提交”，不要直接上传。

### 4. 你在 IMC 平台执行上传

你需要做的动作：

1. 打开当前轮次的 Algorithmic Challenge
2. 上传 `trader_round3.py`
3. 等待平台完成测试
4. 确认该版本被设为 `active`
5. 记录这次提交的关键信息

必须确认的一点：

- 平台上最终被锁定的是最后一个成功并设为 `active` 的版本，不是你本地最新文件。

## GitHub 同步工作流

当前仓库已经完成以下配置：

- 本地仓库已初始化
- 远端 `origin` 已连接到 `https://github.com/AmalZhang/IMC_4.git`
- `main` 已经成功推送到 GitHub

这意味着你和队友现在可以直接围绕同一个仓库协作。

### 你队友第一次开始协作

让队友执行：

```powershell
git clone https://github.com/AmalZhang/IMC_4.git
cd IMC_4
```

### 你每天开始工作前

```powershell
git checkout main
git pull
```

### 队友每天开始工作前

```powershell
git checkout main
git pull
git checkout -b feat/r3-本次任务名
```

### 队友完成一次实验后

```powershell
python -m py_compile trader_round3.py round3_analysis.py
git add .
git commit -m "feat: 描述本次改动"
git push -u origin feat/r3-本次任务名
```

### 你合入主线前

你需要做的不是马上上传 IMC，而是先确认：

1. 这次改动只解决一个明确问题
2. 本地检查已通过
3. 没有破坏主线当前稳定性
4. 如有平台日志，解释与改动目标一致

### IMC 平台日志的版本管理

当前约定是把平台上传后的测试日志也纳入仓库，便于你和队友基于同一份结果分析。

建议保留这些文件：

- `ROUND_3/logs/<run_id>/<run_id>.py`
- `ROUND_3/logs/<run_id>/<run_id>.log`
- `ROUND_3/logs/<run_id>/<run_id>.json`

不建议删除旧日志，除非仓库体积明显失控。

## 每次提交后必须回传给 Codex 的信息

为了让 Codex 高效迭代，你提交后尽量按下面模板回传信息。

### 最低配回传模板

```text
轮次：Round 3
版本名：r3_v03
是否成功上传：是/否
是否 active：是/否
平台测试是否通过：是/否
总 PnL：
分产品表现：
是否有报错：
是否有超时：
debug log 里的关键报错/异常：
我观察到的问题：
```

### 最有价值的附加信息

- 平台返回的 debug log 文本
- 每个产品的 PnL 或表现截图
- 平台给出的异常栈
- 你主观观察到的现象

例如：

- `VEV_5300 和 VEV_5400 经常来回打脸`
- `HYDROGEL_PACK 在尾盘亏损明显`
- `平台没有报错，但总成交很少`

## 版本管理建议

建议你采用简单版本名，不要靠记忆区分。

推荐格式：

- `r3_v01`
- `r3_v02`
- `r3_v03_hotfix`
- `r3_v04_hedge`

每次提交时你可以顺手在聊天里告诉 Codex：

```text
这次我提交的是 r3_v05，对应当前 trader_round3.py
```

这样后续定位问题会快很多。

## 截止前 6 小时的节奏

比赛后半段不要再按平时节奏做大改，建议切成三段。

### T-6h 到 T-3h

目标：

- 允许做中等规模修改
- 重点修复明确亏损点
- 保留一个最近稳定版本作为回退基线

这阶段可以做：

- 参数调整
- 单产品策略修正
- 风控和限仓修正
- 小范围结构调整

不建议做：

- 完全推翻已有策略
- 引入大依赖
- 复杂重构

### T-3h 到 T-1h

目标：

- 只做小改
- 以稳定性优先

这阶段建议只做：

- 阈值微调
- 日志精简
- 超时修复
- 仓位裁剪修复
- 个别产品关闭或降权

### T-1h 到截止

目标：

- 不再做大改
- 只保留最稳版本

最后一小时建议：

1. 只在发现明确严重 bug 时改代码
2. 否则保留当前最稳版本
3. 再次确认平台上 `active` 的版本正确
4. 截止前最后 10-15 分钟不要做激进提交

## 你和 Codex 的职责边界

### 适合交给 Codex 的工作

- 读 Wiki 并提炼规则
- 分析 CSV 历史数据
- 做策略研究
- 修改 `trader_round3.py`
- 增加/修复限仓、定价、对冲逻辑
- 解释 debug log
- 根据测试结果继续迭代

### 必须由你确认的工作

- 上传到 Prosperity 平台
- 设为 `active`
- 查看平台最终测试结果
- 截止前确认当前生效版本

## 推荐协作口令

为了减少沟通成本，后面可以直接用这几种固定句式。

### 让 Codex 开始新一轮修改

```text
基于当前 trader_round3.py，继续优化 Round 3。
这次目标：提升 VEV 系列表现，优先避免超限和过度对冲。
```

### 让 Codex 根据平台结果修复

```text
这是平台测试结果，请你基于这个结果继续改。
重点处理：超时 / 仓位超限 / 某产品持续亏损。
```

### 让 Codex 只做提交前审查

```text
请只检查当前 trader_round3.py 是否符合 Wiki 规则和提交要求，不要大改策略。
```

### 让 Codex 做截止前保守版

```text
现在进入截止前保守阶段，请基于当前版本只做稳定性修复，不做大改。
```

## 当前项目建议

结合当前 workspace，建议你实际执行时按下面方式走：

1. 以 `trader_round3.py` 作为唯一提交文件
2. `round3_analysis.py` 只用于本地分析，不上传
3. `ROUND_3/logs/` 中的平台测试日志可以上传到 GitHub，便于协作分析
4. 每次提交后把平台结果贴给 Codex
5. Codex 修改后，你再上传新版本
6. 截止前保留一个你确认过的稳定版本，不要只留实验版

## 一句话执行原则

最佳模式不是“Codex 自动提交”，而是“Codex 持续迭代代码，你持续控制平台提交状态”，这样最稳，也最符合 Prosperity 的提交机制。
