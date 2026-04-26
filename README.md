# StableMoney

基于 PyBroker 的 A 股规则型回测框架。通过通达信 TDX 数据源获取行情数据，利用 TDX 公式引擎计算技术指标，以构建器模式组装策略并执行回测。

## 目录

- [项目架构](#项目架构)
- [环境与依赖](#环境与依赖)
- [快速开始](#快速开始)
- [目录结构](#目录结构)
- [核心模块说明](#核心模块说明)
- [开发进度](#开发进度)
- [编码规范](#编码规范)
- [已知限制](#已知限制)
- [后续规划](#后续规划)

## 项目架构

### 组件模型

一个回测策略由三个组件构成，通过 `StrategyBuilder` 组装：

```
┌─────────────────────────────────────────────────────────┐
│                   StrategyBuilder                        │
│                                                         │
│  TdxDataSource(indicators=[...],  BacktestConfig        │
│                 tdx_dir="...")    (标的、日期、资金、     │
│  (行情 + 指标数据 + TDX 连接)      指标、warmup)         │
│        │                           │                    │
│        └───────────────────────────┘                    │
│                    ▼                                     │
│             algo + AlgoConfig                            │
│             (交易逻辑 + 风控参数)                        │
│                    ▼                                     │
│               TestResult                                 │
└─────────────────────────────────────────────────────────┘
```

- **TdxDataSource** — 数据源，构造时接收指标定义和 `tdx_dir`（自动初始化 TDX 连接），逐股票获取 OHLCV 行情和计算指标
- **BacktestConfig** — 回测运行配置，包含标的、日期范围、初始资金、指标定义、warmup
- **Algo + AlgoConfig** — 交易逻辑（实现 `__call__(ctx)` 的类或裸函数）+ 通用风控参数（止损/止盈比例）

### 数据流

```
TdxDataSource(indicators=[RSI(14), MA(20)], tdx_dir="...")  # 构造时注入指标，自动初始化 TDX
        ↓
StrategyBuilder.run()
  → PyBroker Strategy.backtest()
    → TdxDataSource._fetch_data()        # 逐股票处理
      → tq.get_market_data()             # 通过 tq 获取单股 OHLCV
      → _convert_kline_to_dataframe()    # 转换为 PyBroker DataFrame
      → tq.formula_format_data()         # 格式化 K 线数据
      → tq.formula_set_data()            # 注入 K 线到公式引擎
      → 逐指标：tq.formula_zb()          # TDX 公式引擎计算指标
      → _merge_indicator_result()        # 解析响应，截取 warmup，合并
      → pd.concat(all_stock_dfs)         # 拼接所有股票 DataFrame
    → algo(ctx)                          # 逐 bar 调用 Algo.__call__()
```

TDX 预计算的指标列通过 `register_custom_cols()` 注册为 DataFrame 自定义列，`ctx.COLUMN_NAME` 通过 `ExecContext.__getattr__` 直接从 `ColumnScope` 读取。

## 环境与依赖

### 运行环境

| 项目 | 要求 |
|------|------|
| Python | >= 3.10 |
| 操作系统 | Windows（TDX DLL 仅支持 Windows） |
| 通达信 | 需安装通达信客户端 + tqcenter 插件 |

### 核心依赖

| 包 | 用途 |
|----|------|
| `lib-pybroker >= 1.2.0` | 回测引擎 |
| `pandas >= 1.5.0` | 数据处理 |
| `numpy >= 1.23.0` | 数值计算 |
| `pyyaml >= 6.0` | YAML 配置文件 |

### 开发依赖

| 包 | 用途 |
|----|------|
| `mypy >= 1.0` | 静态类型检查（严格模式） |
| `ruff >= 0.1.0` | 代码检查与格式化 |

### 外部依赖

| 组件 | 路径 | 说明 |
|------|------|------|
| `tqcenter` | `D:\Applications\tdx_test\PYPlugins\user\tqcenter.py` | TDX DLL 桥接层，非 pip 包，通过 `TdxDataSource(tdx_dir=...)` 自动加载 |

### 安装

```bash
# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 安装项目（可编辑模式）
pip install -e .

# 安装开发工具
pip install -e ".[dev]"
```

## 快速开始

### 方式一：使用内建 Algo 类

```python
from stablemoney import AlgoConfig, BacktestConfig, StrategyBuilder
from stablemoney.algos import RSIAlgo
from stablemoney.data_sources import TdxDataSource
from stablemoney.indicators import MA, RSI

backtest_config = BacktestConfig(
    symbols=["600519.SH", "000858.SZ"],
    start_date="2024-01-01",
    end_date="2024-12-31",
    initial_cash=500_000,
    indicators=[RSI(14), MA(20)],
    warmup=100,
)

result = (
    StrategyBuilder()
    .set_data_source(TdxDataSource(
        indicators=backtest_config.indicators,
        tdx_dir=r"D:\Applications\tdx_test\PYPlugins\user",
    ))
    .set_backtest(backtest_config)
    .set_algo(RSIAlgo(config=AlgoConfig(stop_loss_pct=5.0)))
    .run()
)
```

### 方式二：自定义策略类

```python
import numpy as np
from pybroker.context import ExecContext

from stablemoney import AlgoConfig, BacktestConfig, StrategyBuilder
from stablemoney.data_sources import TdxDataSource
from stablemoney.indicators import MA, RSI


class MyAlgo:
    def __init__(self, config: AlgoConfig) -> None:
        self.config = config

    def __call__(self, ctx: ExecContext) -> None:
        rsi = ctx.RSI_14
        ma = ctx.MA_20

        if np.isnan(rsi[-1]) or np.isnan(ma[-1]):
            return

        pos = ctx.long_pos()

        if pos is not None and pos.entries and self.config.stop_loss_pct > 0:
            entry_price = float(pos.entries[0].price)
            pnl_pct = (ctx.close[-1] - entry_price) / entry_price * 100
            if pnl_pct <= -self.config.stop_loss_pct:
                ctx.sell_all_shares()  # type: ignore[no-untyped-call]
                return

        if rsi[-1] < 35 and pos is None:
            ctx.buy_shares = 100

        if rsi[-1] > 65 and pos is not None:
            ctx.sell_all_shares()  # type: ignore[no-untyped-call]


backtest_config = BacktestConfig(
    symbols=["600519.SH"],
    start_date="2024-01-01",
    end_date="2024-12-31",
    initial_cash=500_000,
    indicators=[RSI(14), MA(20)],
)

result = (
    StrategyBuilder()
    .set_data_source(TdxDataSource(indicators=backtest_config.indicators, tdx_dir=r"..."))
    .set_backtest(backtest_config)
    .set_algo(MyAlgo(config=AlgoConfig(stop_loss_pct=5.0)))
    .run()
)
```

### 方式三：裸函数回调

```python
from stablemoney import BacktestConfig, StrategyBuilder
from stablemoney.data_sources import TdxDataSource
from stablemoney.indicators import MA, RSI


def my_strategy(ctx) -> None:
    rsi = ctx.RSI_14
    if rsi[-1] < 30:
        ctx.buy_shares = 100
    if rsi[-1] > 70:
        ctx.sell_all_shares()


backtest_config = BacktestConfig(
    symbols=["600519.SH"],
    start_date="2024-01-01",
    end_date="2024-12-31",
    initial_cash=500_000,
    indicators=[RSI(14), MA(20)],
)

result = (
    StrategyBuilder()
    .set_data_source(TdxDataSource(indicators=backtest_config.indicators, tdx_dir=r"..."))
    .set_backtest(backtest_config)
    .set_algo(my_strategy)
    .run()
)
```

### 方式四：运行示例

```bash
# TDX 真实数据示例（需 TDX 环境）
python examples/tdx_rsi_strategy.py
```

## 目录结构

```
StableMoney/
├── pyproject.toml                          # 项目元数据、依赖、工具配置
├── .gitignore                              # Git 忽略规则
├── README.md                               # 本文件
├── CLAUDE.md                               # Claude Code 工作指引
├── src/
│   └── stablemoney/
│       ├── __init__.py                     # 公共 API 导出
│       ├── py.typed                        # PEP 561 类型标记
│       ├── indicator_def.py                # IndicatorDef 数据类
│       ├── algo_config.py                  # AlgoConfig 风控参数
│       ├── strategy_config.py              # BacktestConfig
│       ├── strategy_builder.py             # StrategyBuilder 构建器
│       ├── config_loader.py                # YAML 配置加载/保存
│       ├── algos/                          # 内建 Algo 实现
│       │   ├── __init__.py                 # 导出所有内建 Algo
│       │   ├── rsi_algo.py                 # RSI 超卖/超买 Algo
│       │   ├── kdj_macd_algo.py            # KDJ 金死叉 + MACD 过滤 Algo
│       │   ├── kdj_macd_ma_algo.py         # KDJ 超卖 + MACD 多头 + MA 多头 Algo
│       │   ├── macd_algo.py                # MACD 金死叉 Algo
│       │   └── ma_cross_algo.py            # MA 均线交叉 Algo
│       ├── data_sources/                   # 数据源实现
│       │   ├── __init__.py                 # 导出 TdxDataSource
│       │   └── tdx_data_source.py          # TDX 通达信数据源
│       └── indicators/                     # 内建指标工厂函数
│           ├── __init__.py                 # 导出所有内建指标
│           ├── trend.py                    # MA, EMA, MACD
│           ├── oscillator.py               # RSI, KDJ, CCI, WR
│           ├── volatility.py               # BOLL, ATR
│           └── volume.py                   # OBV, VOL_MA
├── tests/                                  # 单元测试（105 个用例，97% 覆盖率）
│   ├── conftest.py                         # 共享 fixture
│   ├── test_indicator_def.py               # IndicatorDef 测试
│   ├── test_algo_config.py                 # AlgoConfig 测试
│   ├── test_strategy_config.py             # BacktestConfig 序列化测试
│   ├── test_config_loader.py               # YAML 配置加载/保存测试
│   ├── test_strategy_builder.py            # StrategyBuilder 测试
│   ├── test_indicators_trend.py            # MA, EMA, MACD 测试
│   ├── test_indicators_oscillator.py       # RSI, KDJ, CCI, WR 测试
│   ├── test_indicators_volatility.py       # BOLL, ATR 测试
│   ├── test_indicators_volume.py           # OBV, VOL_MA 测试
│   ├── algos/
│   │   ├── conftest.py                     # Algo mock helpers
│   │   ├── test_rsi_algo.py               # RSIAlgo 交易逻辑测试
│   │   ├── test_kdj_macd_algo.py           # KDJMacdAlgo 测试
│   │   ├── test_kdj_macd_ma_algo.py        # KdjMacdMaAlgo 测试
│   │   ├── test_macd_algo.py              # MacdAlgo 测试
│   │   └── test_ma_cross_algo.py           # MACrossAlgo 测试
│   └── data_sources/
│       └── test_tdx_data_source.py         # TDX 数据源测试
├── examples/
│   ├── tdx_rsi_strategy.py                # TDX RSI 策略示例
│   ├── tdx_kdj_macd_strategy.py           # TDX KDJ+MACD 策略示例
│   ├── tdx_kdj_macd_ma_strategy.py        # TDX KDJ+MACD+MA 三信号策略示例
│   ├── tdx_macd_strategy.py               # TDX MACD 策略示例
│   └── tdx_ma_cross_strategy.py           # TDX MA 交叉策略示例
└── .venv/                                  # Python 虚拟环境
```

## 核心模块说明

### Algo + AlgoConfig（交易逻辑与风控参数）

交易逻辑通过 `set_algo()` 注入，支持类实例或裸函数，只需实现 `__call__(ctx: ExecContext) -> None`。风控参数通过 `AlgoConfig` 注入：

```python
from stablemoney import AlgoConfig

# 类方式
class MyAlgo:
    def __init__(self, config: AlgoConfig) -> None:
        self.config = config

    def __call__(self, ctx: ExecContext) -> None:
        ...

# 裸函数方式
def my_strategy(ctx: ExecContext) -> None:
    ...

# 两种方式都通过 set_algo 注入
builder.set_algo(MyAlgo(config=AlgoConfig(stop_loss_pct=5.0)))
builder.set_algo(my_strategy)
```

`AlgoConfig` 为 frozen dataclass，包含通用风控参数：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `stop_loss_pct` | `float` | `0.0` | 止损百分比（0 表示不启用） |
| `take_profit_pct` | `float` | `0.0` | 止盈百分比（0 表示不启用） |

### IndicatorDef（`indicator_def.py`）

声明式指标定义，与 TDX 公式引擎对接：

```python
from stablemoney.indicators import KDJ, RSI

rsi = RSI(14)
# IndicatorDef(name="RSI", params={"period": 14}, outputs=("value",))
# .full_name    → "RSI_14"
# .column_names → ["RSI_14"]
# .formula_arg  → "14"

kdj = KDJ(9, 3, 3)
# IndicatorDef(name="KDJ", params={"k_period": 9, "k_smooth": 3, "d_smooth": 3}, outputs=("K","D","J"))
# .full_name    → "KDJ_9_3_3"
# .column_names → ["KDJ_9_3_3_K", "KDJ_9_3_3_D", "KDJ_9_3_3_J"]
# .formula_arg  → "9,3,3"
```

### BacktestConfig（`strategy_config.py`）

Frozen dataclass，包含回测所需的所有配置：

```python
backtest_config = BacktestConfig(
    symbols=["600519.SH", "000858.SZ"],
    start_date="2024-01-01",
    end_date="2024-12-31",
    initial_cash=500_000,       # 初始资金，默认 100,000
    indicators=[RSI(14), MA(20)],
    warmup=100,                 # warmup bar 数，默认 None（不跳过）
)
# 支持序列化：backtest_config.to_dict() / BacktestConfig.from_dict(data)
```

`StrategyBuilder.run()` 内部从 `BacktestConfig.initial_cash` 创建 PyBroker 的 `StrategyConfig`。

### StrategyBuilder（`strategy_builder.py`）

流式构建器，组装并运行回测：

```python
result = (
    StrategyBuilder()
    .set_data_source(TdxDataSource(indicators=backtest_config.indicators, tdx_dir=r"..."))
    .set_backtest(backtest_config)
    .set_algo(RSIAlgo(config=AlgoConfig(stop_loss_pct=5.0)))
    .run()  # → TestResult
)
```

### TdxDataSource（`data_sources/tdx_data_source.py`）

继承 PyBroker 的 `DataSource`，通过 `tqcenter`（`tq` 模块）访问 TDX 能力：

- 构造函数接收 `indicators` 列表和 `tdx_dir`（自动初始化 TDX 连接）
- 逐股票处理：每只股票独立获取 K 线、计算指标、构建 DataFrame，最后 `pd.concat` 拼接
- 股票代码格式：`"600519.SH"`、`"000858.SZ"`
- 行情获取：`tq.get_market_data()` → `Dict[str, DataFrame]`
- 指标计算流程（逐股票）：
  1. `tq.formula_format_data(kline_data)` 格式化 K 线数据
  2. `tq.formula_set_data()` 注入数据到公式引擎
  3. `tq.formula_zb(formula_name, formula_arg)` 计算指标
  4. `_merge_indicator_result()` 解析 `{"Value": {"KEY": ["str", ...]}}` 响应，截取 warmup，处理 `None` 值
- 支持周期：1d, 1w, 1mon, 1h, 30m, 15m, 5m, 1m

### 内建指标

| 类别 | 指标 | 说明 |
|------|------|------|
| 趋势 | `MA`, `EMA`, `MACD` | 移动平均、指数移动平均、MACD |
| 震荡 | `RSI`, `KDJ`, `CCI`, `WR` | 相对强弱、随机指标、CCI、威廉指标 |
| 波动 | `BOLL`, `ATR` | 布林带、真实波幅 |
| 成交量 | `OBV`, `VOL_MA` | 能量潮、成交量均线 |

### 内建 Algo

| Algo | 说明 |
|------|------|
| `RSIAlgo` | RSI 超卖买入 / 超买卖出，可配置止损比例和阈值 |
| `KDJMacdAlgo` | KDJ 金叉买入 + MACD 多头过滤，KDJ 死叉卖出 |
| `KdjMacdMaAlgo` | KDJ.J < 0 + MACD DIF/DEA > 0 + MA10 > MA20 三信号买入，仅靠风控退出 |
| `MacdAlgo` | MACD 金叉买入（DIF > 0 且 DEA > 0），MACD 死叉卖出 |
| `MACrossAlgo` | MA10/MA20 金叉买入，死叉卖出 |

## 开发进度

### 已完成

| 模块 | 状态 | 说明 |
|------|------|------|
| `IndicatorDef` 数据类 | 已完成 | 声明式指标定义，支持单值/多值输出 |
| `AlgoConfig` 风控参数 | 已完成 | 通用止损/止盈配置 |
| `BacktestConfig` | 已完成 | 统一回测配置（含 initial_cash、warmup），支持序列化 |
| `config_loader` YAML 加载 | 已完成 | 配置文件读取/保存 |
| `StrategyBuilder` 构建器 | 已完成 | 流式接口，`set_algo()` 支持类和裸函数 |
| `TdxDataSource` 数据源 | 已完成 | 构造函数注入指标，`formula_zb` 逐股计算 |
| `RSIAlgo` 内建策略 | 已完成 | RSI 超卖/超买 + AlgoConfig 止损 |
| 内建指标（11个） | 已完成 | MA, EMA, MACD, RSI, KDJ, CCI, WR, BOLL, ATR, OBV, VOL_MA |
| TDX 真实数据示例 | 已完成 | `examples/tdx_rsi_strategy.py` |
| 工具链配置 | 已完成 | ruff + mypy strict 通过 |
| 端到端验证 | 已完成 | 通过真实 TDX 环境验证完整回测流程 |
| 单元测试 | 已完成 | pytest 211 个用例，85% 覆盖率 |

### 待完成

暂无

## 编码规范

- **Python 版本**：>= 3.10，全程严格类型标注
- **风格检查**：`ruff check src/stablemoney`，目标规则集 E/W/F/I/N/UP/B/SIM/TCH
- **类型检查**：`mypy src/stablemoney`，strict 模式
- **命名约定**：文件以主类名命名（如 `strategy_builder.py`）；指标工厂函数使用大写（如 `MA()`、`RSI()`）
- **导入规范**：仅用于类型标注的导入放入 `TYPE_CHECKING` 块；使用 `collections.abc` 代替 `typing`（如 `Callable`、`Iterable`）；使用 `X | None` 代替 `Optional[X]`

## 已知限制

1. **`tqcenter` 非标准包** — TDX 桥接层封装了内部 DLL 调用，通过 `TdxDataSource(tdx_dir=...)` 自动加载 `tq` 模块，不可通过 pip 安装
2. **需运行通达信客户端** — TDX DLL 连接需要通达信客户端处于运行状态

## 后续规划

1. **策略组合** — 支持多 Algo 组合（信号投票、过滤器链等）
3. **前后端可视化** — 将项目扩展为前后端应用，前端展示回测结果
4. **自定义指标支持** — 允许用户编写 PyBroker 原生指标函数

## 参考

| 资源 | 位置 |
|------|------|
| PyBroker 源码 | `.venv/Lib/site-packages/pybroker/` |
| TDX API 源码 | `D:\Applications\tdx_test\PYPlugins\user\tqcenter.py` |
| PyBroker 技能文档 | `.claude/skills/pybroker-skill/` |
| TDX 数据源技能文档 | `.claude/skills/tdx-market-data/` |

## License

MIT
