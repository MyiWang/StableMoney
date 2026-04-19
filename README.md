# StableMoney

基于 PyBroker 的 A 股规则型回测框架。通过通达信 TDX 数据源获取行情数据，利用 TDX 公式引擎计算技术指标，以构建器模式组装策略并执行回测。

> **当前阶段**：框架已完成，TDX API 集成已实现（`formula_set_data` + `formula_zb`），待连接真实 TDX 环境做端到端验证。

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

一个回测策略由四个组件构成，通过 `StrategyBuilder` 组装。指标通过 `TdxDataSource` 构造函数注入：

```
┌─────────────────────────────────────────────────────────┐
│                   StrategyBuilder                        │
│                                                         │
│  TdxDataSource(indicators=[...],  StrategyConfig        │
│                 tdx_dir="...")    (回测参数+自定义params) │
│  (行情 + 指标数据 + TDX 连接)       │                    │
│        │                           │                    │
│        └───────────────────────────┘                    │
│                    ▼                                     │
│             BacktestConfig                               │
│             (标的、日期、指标)                            │
│                    ▼                                     │
│             ExecuteCallback                              │
│             (交易逻辑)                                   │
│                    ▼                                     │
│               TestResult                                 │
└─────────────────────────────────────────────────────────┘
```

- **TdxDataSource** — 数据源，构造时接收指标定义和 `tdx_dir`（自动初始化 TDX 连接），逐股票获取 OHLCV 行情和计算指标
- **StrategyConfig** — 回测参数配置，扩展了 PyBroker 的 `StrategyConfig`，增加自定义 `params` 字典
- **BacktestConfig** — 回测运行配置，包含标的、日期范围、指标定义
- **ExecuteCallback** — 交易逻辑回调，接收 PyBroker 的 `ExecContext`，逐 bar 执行

### 数据流

```
TdxDataSource(indicators=[RSI(14), MA(20)], tdx_dir="...")  # 构造时注入指标，自动初始化 TDX
        ↓
StrategyBuilder.run()
  │
  ├─ 1. 注册透传 indicator 函数               ← 桥接预计算值到 PyBroker 指标管线
  └─ 2. PyBroker Strategy.backtest()
       │
       ├─ TdxDataSource._fetch_data()        # 逐股票处理
       │   ├─ 逐股票：tq.get_market_data()   ← DLL 调用：单股 OHLCV
       │   ├─ _convert_kline_to_dataframe()  ← 转换为 PyBroker DataFrame
       │   ├─ tq.formula_format_data()       ← 格式化 K 线数据
       │   ├─ tq.formula_set_data()          ← 注入 K 线到公式引擎
       │   ├─ 逐指标：tq.formula_zb()        ← TDX 公式引擎计算指标
       │   ├─ _merge_indicator_result()      ← 解析响应，截取 warmup，合并
       │   └─ pd.concat(all_stock_dfs)       ← 拼接所有股票 DataFrame
       │
       ├─ 透传 indicator 函数                 ← 从 BarData 读取预计算列
       ├─ exec_fn(ctx)                        ← 逐 bar 用户回调
       │   └─ ctx.config.params               ← 访问自定义参数
       │
       └─ TestResult                          ← 回测结果
```

### 透传指标模式

TDX 在服务端计算指标，PyBroker 不做指标计算。通过「透传」模式桥接：

1. `TdxDataSource(indicators=[...], tdx_dir=...)` 构造时注册自定义列并自动初始化 TDX 连接
2. `_fetch_data()` 逐股票获取 K 线、计算指标、构建 DataFrame，最后拼接
3. `StrategyBuilder` 注册简单的列读取函数（`getattr(bar_data, col_name)`）作为 PyBroker indicator
4. 用户回调中通过 `ctx.indicator("RSI_14")` 访问指标值

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

### 方式一：代码构造（使用 StrategyConfig + BacktestConfig）

```python
from pybroker.context import ExecContext
from stablemoney import BacktestConfig, StrategyBuilder, StrategyConfig
from stablemoney.tdx_data_source import TdxDataSource
from stablemoney.indicators import RSI, MA


def my_strategy(ctx: ExecContext) -> None:
    rsi = ctx.indicator("RSI_14")
    ma = ctx.indicator("MA_20")
    stop_loss_pct = ctx.config.params["stop_loss_pct"]

    pos = ctx.long_pos()

    # 止损
    if pos is not None and pos.entries:
        entry_price = float(pos.entries[0].price)
        pnl_pct = (ctx.close[-1] - entry_price) / entry_price * 100
        if pnl_pct <= -stop_loss_pct:
            ctx.sell_all_shares()
            return

    # 买入：RSI 超卖
    if rsi[-1] < 30 and pos is None:
        ctx.buy_shares = 100

    # 卖出：RSI 超买
    if rsi[-1] > 70 and pos is not None:
        ctx.sell_all_shares()


strategy_config = StrategyConfig(
    initial_cash=500_000,
    params={"stop_loss_pct": 5.0, "take_profit_pct": 10.0},
)
backtest_config = BacktestConfig(
    symbols=["600519.SH", "000858.SZ"],
    start_date="2024-01-01",
    end_date="2024-12-31",
    indicators=[RSI(14), MA(20)],
)

result = (
    StrategyBuilder()
    .set_data_source(TdxDataSource(
        indicators=backtest_config.indicators,
        tdx_dir=r"D:\Applications\tdx_test\PYPlugins\user",
    ))
    .set_config(strategy_config)
    .set_backtest(backtest_config)
    .set_exec_fn(my_strategy)
    .run()
)
```

### 方式二：配置文件

```yaml
# strategy.yaml
strategy:
  initial_cash: 500000
  buy_delay: 1
  sell_delay: 1
  params:
    stop_loss_pct: 5.0
    take_profit_pct: 10.0

backtest:
  symbols:
    - "600519.SH"
    - "000858.SZ"
  start_date: "2024-01-01"
  end_date: "2024-12-31"
  period: "1d"
  dividend_type: "front"
  indicators:
    - name: "RSI"
      params: {period: 14}
    - name: "MA"
      params: {period: 20}
```

```python
from stablemoney import StrategyBuilder
from stablemoney.config_loader import load_config
from stablemoney.indicator_def import IndicatorDef
from stablemoney.tdx_data_source import TdxDataSource

strategy_config, backtest_config = load_config("strategy.yaml")
indicators = [
    IndicatorDef(**ind) for ind in backtest_config.to_dict()["indicators"]
]

result = (
    StrategyBuilder()
    .set_data_source(TdxDataSource(
        indicators=indicators,
        tdx_dir=r"D:\Applications\tdx_test\PYPlugins\user",
    ))
    .set_config(strategy_config)
    .set_backtest(backtest_config)
    .set_exec_fn(my_strategy)
    .run()
)
```

### 方式三：运行示例

```bash
# Mock 数据示例（无需 TDX 环境）
python examples/simple_rsi_strategy.py

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
│       ├── strategy_config.py              # StrategyConfig + BacktestConfig
│       ├── strategy_builder.py             # StrategyBuilder 构建器
│       ├── tdx_data_source.py              # TdxDataSource 数据源
│       ├── config_loader.py                # YAML 配置加载/保存
│       └── indicators/                     # 内建指标工厂函数
│           ├── __init__.py                 # 导出所有内建指标
│           ├── trend.py                    # MA, EMA, MACD
│           ├── oscillator.py               # RSI, KDJ, CCI, WR
│           ├── volatility.py               # BOLL, ATR
│           └── volume.py                   # OBV, VOL_MA
├── examples/
│   ├── simple_rsi_strategy.py              # Mock 数据 RSI 策略示例
│   └── tdx_rsi_strategy.py                # TDX 真实数据 RSI 策略示例
└── .venv/                                  # Python 虚拟环境
```

## 核心模块说明

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

### StrategyConfig（`strategy_config.py`）

扩展 PyBroker 的 frozen dataclass，增加 `params` 字典：

```python
config = StrategyConfig(
    initial_cash=500_000,
    params={"stop_loss_pct": 5.0},
)
# 回调中访问：ctx.config.params["stop_loss_pct"]
```

同时包含 `BacktestConfig`，用于配置回测运行参数（标的、日期、指标列表），均支持 `to_dict()` / `from_dict()` 序列化。

### StrategyBuilder（`strategy_builder.py`）

流式构建器，组装并运行回测。支持 `set_backtest(BacktestConfig)` 一次性设置标的和日期：

```python
# 使用 BacktestConfig
result = (
    StrategyBuilder()
    .set_data_source(TdxDataSource(indicators=[RSI(14), MA(20)]))
    .set_config(config)
    .set_backtest(backtest_config)
    .set_exec_fn(trading_logic)
    .run()  # → TestResult
)

# 或分步设置
result = (
    StrategyBuilder()
    .set_data_source(TdxDataSource(indicators=[RSI(14), MA(20)]))
    .set_config(config)
    .set_exec_fn(trading_logic)
    .set_symbols(["600519.SH"])
    .set_date_range("2024-01-01", "2024-12-31")
    .run()
)
```

### TdxDataSource（`tdx_data_source.py`）

继承 PyBroker 的 `DataSource`，通过 `tqcenter` 调用 TDX DLL：

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

## 开发进度

### 已完成

| 模块 | 状态 | 说明 |
|------|------|------|
| `IndicatorDef` 数据类 | 已完成 | 声明式指标定义，支持单值/多值输出 |
| `StrategyConfig` / `BacktestConfig` | 已完成 | 扩展 PyBroker 配置，支持序列化 |
| `config_loader` YAML 加载 | 已完成 | 配置文件读取/保存 |
| `StrategyBuilder` 构建器 | 已完成 | 流式接口，透传指标注册 |
| `TdxDataSource` 数据源 | 已完成 | 构造函数注入指标，`formula_zb` 逐股计算，向量化 K 线转换 |
| 内建指标（11个） | 已完成 | MA, EMA, MACD, RSI, KDJ, CCI, WR, BOLL, ATR, OBV, VOL_MA |
| Mock 数据示例 | 已完成 | `examples/simple_rsi_strategy.py` |
| TDX 真实数据示例 | 已完成 | `examples/tdx_rsi_strategy.py` |
| 工具链配置 | 已完成 | ruff + mypy strict 通过 |
| Git 版本控制 | 已完成 | 已初始化，含 `.gitignore` |

### 待完成

| 任务 | 优先级 | 说明 |
|------|--------|------|
| TDX 真实环境端到端测试 | 高 | 连接真实 DLL 验证完整回测流程 |
| 测试套件 | 中 | 暂无测试 |
| 具体策略实现 | 待定 | 用户尚未指定第一个具体策略需求 |

## 编码规范

- **Python 版本**：>= 3.10，全程严格类型标注
- **风格检查**：`ruff check src/stablemoney`，目标规则集 E/W/F/I/N/UP/B/SIM/TCH
- **类型检查**：`mypy src/stablemoney`，strict 模式
- **命名约定**：文件以主类名命名（如 `strategy_builder.py`）；指标工厂函数使用大写（如 `MA()`、`RSI()`）
- **封装原则**：不做没必要的封装——直接使用 PyBroker 的 `ExecContext`，不自定义包装类
- **导入规范**：仅用于类型标注的导入放入 `TYPE_CHECKING` 块；使用 `collections.abc` 代替 `typing`（如 `Callable`、`Iterable`）；使用 `X | None` 代替 `Optional[X]`

## 已知限制

1. **`tqcenter` 非标准包** — TDX 桥接层为本地 DLL 调用，通过 `TdxDataSource(tdx_dir=...)` 自动加载，不可通过 pip 安装
2. **需运行通达信客户端** — TDX DLL 连接需要通达信客户端处于运行状态
3. **无测试覆盖** — 当前没有任何单元测试或集成测试

## 后续规划

1. **接入真实 TDX 环境** — 使用通达信 DLL 跑通端到端回测
2. **具体策略开发** — 根据用户需求实现第一个实际策略
3. **前后端可视化** — 将项目扩展为前后端应用，前端展示回测结果
4. **自定义指标支持** — 允许用户编写 PyBroker 原生指标函数
5. **策略库** — 积累常用策略模板

## 参考

| 资源 | 位置 |
|------|------|
| PyBroker 源码 | `.venv/Lib/site-packages/pybroker/` |
| TDX API 源码 | `D:\Applications\tdx_test\PYPlugins\user\tqcenter.py` |
| PyBroker 技能文档 | `.claude/skills/pybroker-skill/` |
| TDX 数据源技能文档 | `.claude/skills/tdx-market-data/` |

## License

MIT
