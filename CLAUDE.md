# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此仓库中工作时提供指导。

## 项目概述

StableMoney 是一个基于 PyBroker 的 A 股回测框架。策略通过构建器模式组装：**DataSource**（含指标定义和 TDX 连接）、**BacktestConfig**（标的或板块、日期、资金、指标、warmup）、**Algo**（交易逻辑，实现 `__call__` 的类或裸函数，通过 `AlgoConfig` 注入风控参数）。数据源为通达信 TDX（通过 `tqcenter` 包的 `tq` 模块访问 TDX 能力）。指标由 TDX 公式引擎在服务端计算，而非 PyBroker 计算。指标通过 `TdxDataSource` 构造函数注入。支持通过 `MarketSector` 枚举按市场板块（主板、创业板、科创板等）自动获取股票列表，并通过 `SectorFilter` 按真实市值排序和筛选。

## 常用命令

项目使用 `.venv` 虚拟环境。如果虚拟环境不存在，先创建：

```bash
python -m venv .venv
```

所有命令和依赖安装均在虚拟环境中执行（使用 `.venv/Scripts/` 前缀）：

```bash
# 安装依赖
.venv/Scripts/pip install -e .
.venv/Scripts/pip install -e ".[dev]"

# 代码检查
.venv/Scripts/ruff check src/stablemoney

# 类型检查（严格模式）
.venv/Scripts/mypy src/stablemoney

# 运行示例（需 TDX 环境）
.venv/Scripts/python examples/tdx_rsi_strategy.py

# 运行测试
.venv/Scripts/python -m pytest tests/ -v

# 运行测试 + 覆盖率
.venv/Scripts/python -m pytest tests/ --cov=stablemoney --cov-report=term-missing
```

测试套件 181 个用例，覆盖 17 个测试文件。

## 架构

### 数据流

```
TdxDataSource(indicators=[RSI(14), MA(20)], tdx_dir="...")  # 构造时注入指标，自动初始化 TDX
        ↓
StrategyBuilder.run()
  → _resolve_symbols()                       # 解析 symbols 或 sector
    → [sector 模式] tq.get_stock_list()       # 获取板块股票列表
    → _fetch_market_cap()                     # 批量获取收盘价 + 逐股获取股本 → 计算真实市值
    → 按 SectorFilter 排序/过滤/限制数量
  → PyBroker Strategy.backtest()
    → TdxDataSource._fetch_data()        # 逐股票处理
      → tq.get_market_data()             # 通过 tq 获取单股 OHLCV
      → _convert_kline_to_dataframe()    # 转换为 PyBroker DataFrame
      → tq.formula_format_data()         # 格式化 K 线数据
      → tq.formula_set_data()            # 注入 K 线数据到公式引擎
      → 逐指标：tq.formula_zb()          # 通过 TDX 公式引擎计算指标
      → _merge_indicator_result()        # 解析响应，截取 warmup，合并到 DataFrame
      → pd.concat(all_stock_dfs)         # 拼接所有股票 DataFrame
    → algo(ctx)                          # 逐 bar 调用 Algo.__call__()
```

TDX 预计算的指标列通过 `register_custom_cols()` 注册，PyBroker 的 `ExecContext.__getattr__` 直接从 `ColumnScope` 读取，无需 indicator 包装。

### 核心设计模式

- **构造函数注入指标**：`TdxDataSource(indicators=[RSI(14), MA(20)], tdx_dir=...)` 在构造时注册自定义列、保存指标定义、并自动初始化 TDX 连接（添加 `tdx_dir` 到 `sys.path`，调用 `tq.initialize()`）。
- **Algo 交易逻辑**：交易逻辑通过 `set_algo()` 注入，支持类实例或裸函数，只需实现 `__call__(ctx: ExecContext) -> None`。风控参数通过 `AlgoConfig` 注入（如 `RSIAlgo(config=AlgoConfig(stop_loss_pct=5.0))`）。
- **Frozen dataclass**：`IndicatorDef`、`AlgoConfig`、`BacktestConfig`、`SectorFilter` 均为 frozen。`BacktestConfig` 的 `symbols` 和 `sector` 互斥（必须且只能提供一个），`sector` 通过 `MarketSector` 枚举指定市场板块。
- **构建器模式**：`StrategyBuilder` 提供流式接口，通过 `set_backtest(BacktestConfig)` 一次性设置标的、日期、资金、指标，调用 `run()` 完成校验、sector 解析、执行回测。

### TDX 集成

- 构造函数 `tdx_dir` 参数：传入 tqcenter.py 所在目录，`TdxDataSource` 自动添加到 `sys.path` 并调用 `tq.initialize(__file__)`
- 股票代码格式：`"600519.SH"`、`"000858.SZ"`（代码.市场后缀）
- K 线数据：`tq.get_market_data()` 返回 `Dict[str, DataFrame]`，keys 为 "Open"/"High"/"Low"/"Close"/"Volume"/"Amount"，每个 DataFrame 以 DatetimeIndex 为索引、股票代码为列
- 数据获取采用逐股票模式：每只股票独立获取 K 线、计算指标、构建 DataFrame，最后 `pd.concat` 拼接
- 指标计算流程（逐股票）：
  1. `tq.formula_format_data(kline_data)` 格式化 K 线数据
  2. `tq.formula_set_data(stock_code, stock_period, stock_data, count, dividend_type)` 注入数据
  3. `tq.formula_zb(formula_name, formula_arg)` 计算指标
  4. 返回 `{"Value": {"DIF": ["1.23", ...], ...}}` — 值为字符串或 `None`（warmup 期），取末尾 bar_count 个值对齐
- TDX 源码参考：`D:/Applications/tdx_test/PYPlugins/user/tqcenter.py`

### 指标定义

`IndicatorDef` 为声明式定义：`name`（TDX 公式名）、`params`（有序字典）、`outputs`（输出名元组）。内建指标为 `src/stablemoney/indicators/` 下的工厂函数（MA、EMA、MACD、RSI、KDJ、CCI、WR、BOLL、ATR、OBV、VOL_MA）。工厂函数故意使用大写命名（通过 ruff per-file-ignores 抑制 N802）。

### Algo 系统

- **交易逻辑接口**：`set_algo()` 接受 `Callable[[ExecContext], None]`，支持类实例（实现 `__call__`）或裸函数
- **AlgoConfig**：`src/stablemoney/algos/algo_config.py` 中的 frozen dataclass，存放通用风控参数（`stop_loss_pct`、`take_profit_pct`、`hold_bars`），作为 Algo 构造函数的参数注入
- **内建 Algo**：`src/stablemoney/algos/` 子包存放具体实现（`RSIAlgo`、`KDJMacdAlgo`、`KdjZxtrendAlgo`、`MACrossAlgo`、`MacdAlgo`、`KdjMacdMaAlgo`）
  - `KDJMacdAlgo`：买入信号为 J[-2]<0 且 J 下降 + MACD DIF/DEA>0 + close>MA60 + close<MA20，仅风控退出（止损/止盈/最大持股）
  - `KdjZxtrendAlgo`：买入信号为 ZXTREND SHORT_T 上穿 LONG_T（金叉）后 lookback（默认30）根 K 线内 KDJ.J < 0；卖出信号为 SHORT_T 跌穿 LONG_T（死叉）全部卖出，另支持止损/止盈/最大持股
- **用户自定义**：任何实现 `__call__(ctx: ExecContext) -> None` 的类或函数即可，无需继承

### Sector 系统

- **MarketSector 枚举**：`src/stablemoney/market_sector.py`，映射 TDX `get_stock_list` 的 market code。支持：`ALL`（全A）、`MAIN_SH`（沪主板）、`MAIN_SZ`（深主板）、`CHINEXT`（创业板）、`STAR`（科创板）、`BSE`（北交所）
- **SectorFilter frozen dataclass**：排序（`sort_by`："market_cap" 总市值 / "float_cap" 流通市值）、区间过滤（`min_market_cap`/`max_market_cap`，单位：亿元）、数量限制（`max_stocks`）
- **市值计算**：`get_market_data` 批量获取收盘价 + `get_stock_info` 逐股获取股本（万股），市值（亿）= 收盘价 × 股本 / 10000
- **执行顺序**：排序 → 区间过滤 → 取前 N 只

### 日志系统

- **模块**：`src/stablemoney/log.py`
- **初始化**：`setup_logging(level="ERROR", log_dir="logs")` 配置双输出，返回 session 目录 `Path`：
  - `propagate = False`：阻止日志传播到 Python 根 logger，防止 PyBroker 的 `basicConfig()` 导致日志泄露到控制台
  - 控制台 Handler：仅 ERROR 级别
  - 文件 Handler：`logs/backtest_YYYYMMDD_HHMMSS/backtest.log`，级别由参数控制
- **CSV dump**：`dump_stock_csv(df, symbol, tag)` 将 DataFrame 导出到 session 目录的 CSV 文件，按 `symbol`+`date` 排序后写入。用于 TDX 数据诊断（非正收盘价、格式化长度不匹配、指标计算不匹配等场景）
- **使用方式**：各模块通过 `logger = logging.getLogger(__name__)` 获取 logger，使用 `stablemoney` 命名空间
- **命令行参数**：example 脚本通过 `argparse --log-level DEBUG|INFO|WARNING|ERROR` 控制日志级别
- **数据摘要**：`log_dataframe(logger, title, df, level)` 按级别输出——DEBUG 输出完整 DataFrame，INFO 输出 shape + head()
- **日志内容覆盖**：数据获取流程、指标计算、sector 解析明细、交易决策（买入/卖出/止损）、回测起止

### 配置

`BacktestConfig` 统一存放回测参数（标的、日期、资金、指标、warmup），支持 YAML 序列化。通过 `_serialize()`/`_deserialize()` 实现 dict 转换，`save(path)`/`from_yaml(path)` 实现 YAML 文件 I/O。`StrategyBuilder.run()` 内部从 `BacktestConfig.initial_cash` 创建 PyBroker 的 `StrategyConfig`。

## 编码规范

### PEP 8 合规

严格遵循 PEP 8。工具链强制执行（`pyproject.toml` 配置）：

- **ruff**：E/W（pycodestyle）、F（Pyflakes）、I（isort）、N（pep8-naming）、UP（pyupgrade）、B（bugbear）、SIM（simplify）、TCH（type-checking）
- **mypy strict**：`strict = true`、`disallow_untyped_defs = true`、`disallow_incomplete_defs = true`

提交前必须通过：`ruff check` + `mypy` 无错误。

### 类型标注

所有函数和方法必须有完整的参数和返回值类型标注。局部变量在类型不显然时也需标注。规则：

- 使用 `X | None`（而非 `Optional[X]`）
- 使用 `from collections.abc import Callable, Iterable`（而非 `typing`）
- 仅用于类型标注的导入放入 `TYPE_CHECKING` 块
- Python 3.10+ 语法（`match`、`|` 联合类型、`ParamSpec` 等）

### 项目约定

- 文件以主类名命名（`strategy_builder.py`、`indicator_def.py` 等）
- 不做没必要的封装——直接使用 PyBroker 的 `ExecContext`，不自定义包装
- 指标工厂函数使用大写命名（`MA()`、`RSI()`），通过 ruff per-file-ignores 抑制 N802

## Claude Skills 参考

本项目配置了以下 Claude Code skills（`.claude/skills/`），按场景选用：

### 开发方法论

| Skill | 触发场景 | 说明 |
|-------|---------|------|
| `task-breakdown` | 新需求、想法拆解、任务规划 | 拷问假设 → 拆解为垂直切片任务 → 排优先级 |
| `tdd-methodology` | 测试编写、TDD 循环、接口设计 | 垂直切片 TDD 方法论（pytest） |
| `diagnose` | Bug 诊断、测试失败调查、异常排查 | 6 阶段系统化调试方法论 |
| `code-review` | 代码审查、架构改善、模块重构 | 代码质量检查 + 深模块架构改善 |

### 领域知识

| Skill | 触发场景 | 说明 |
|-------|---------|------|
| `dev-new-task` | 新功能开发、策略编写、模块重构 | 6 步开发闭环流程 |
| `pybroker-strategy` | 交易策略编写、回测、指标定义 | PyBroker 框架使用指南 |
| `tdx-market-data` | 通达信数据获取、TDX API 调用 | tqcenter Python SDK 参考 |

skill 之间有交叉依赖：
- 方法论链：`task-breakdown`（需求拆解）→ `tdd-methodology`（编码）→ `diagnose`（调试）→ `code-review`（审查改善）
- 编写新策略时，`dev-new-task` 的 Step 2 会自动加载 `pybroker-strategy`
- 涉及 TDX 数据获取时，`dev-new-task` 会加载 `tdx-market-data`
- `pybroker-strategy` 中的 DataSource 模式依赖 `tdx-market-data` 中的 TDX API
