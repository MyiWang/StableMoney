# StableMoney

基于 PyBroker 的 A 股规则型回测框架。通过通达信 TDX 数据源获取行情数据，利用 TDX 公式引擎计算技术指标，以构建器模式组装策略并执行回测。

> **当前阶段**：策略组装基础框架已完成，尚未接入真实 TDX 环境。

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

### 四组件模型

一个回测策略由四个核心组件构成，通过 `StrategyBuilder` 组装：

```
┌─────────────────────────────────────────────────────────┐
│                   StrategyBuilder                        │
│                                                         │
│  DataSource        StrategyConfig      IndicatorDef     │
│  (行情+指标数据)    (回测参数)          (指标定义)        │
│        │                │                  │             │
│        └────────────────┼──────────────────┘             │
│                         ▼                                │
│                   ExecuteCallback                        │
│                   (交易逻辑)                              │
│                         │                                │
│                         ▼                                │
│                    TestResult                            │
└─────────────────────────────────────────────────────────┘
```

- **DataSource** — 数据源，负责获取 OHLCV 行情和指标数据。当前实现为 `TdxDataSource`（通达信）
- **StrategyConfig** — 回测参数配置，扩展了 PyBroker 的 `StrategyConfig`，增加自定义 `params` 字典
- **IndicatorDef** — 声明式指标定义，描述指标名称、参数和输出
- **ExecuteCallback** — 交易逻辑回调，接收 PyBroker 的 `ExecContext`，逐 bar 执行

### 数据流

```
StrategyBuilder.run()
  │
  ├─ 1. DataSource.set_indicators()          ← 注入指标定义，注册自定义列
  ├─ 2. 注册透传 indicator 函数               ← 桥接预计算值到 PyBroker 指标管线
  └─ 3. PyBroker Strategy.backtest()
       │
       ├─ TdxDataSource._fetch_data()
       │   ├─ tq.get_market_data()           ← DLL 调用：OHLCV 行情
       │   ├─ tq.formula_process_mul()       ← DLL 调用：TDX 公式引擎计算指标
       │   └─ 格式转换 + 合并                 ← TDX Dict[str,DF] → PyBroker DataFrame
       │
       ├─ 透传 indicator 函数                 ← 从 BarData 读取预计算列
       ├─ exec_fn(ctx)                        ← 逐 bar 用户回调
       │   └─ ctx.config.params               ← 访问自定义参数
       │
       └─ TestResult                          ← 回测结果
```

### 透传指标模式

TDX 在服务端计算指标，PyBroker 不做指标计算。通过「透传」模式桥接：

1. `set_indicators()` 将指标列名注册为 PyBroker 自定义列（`StaticScope.register_custom_cols()`）
2. `_fetch_data()` 返回的 DataFrame 包含指标列
3. `_register_passthrough_indicators()` 注册简单的列读取函数（`getattr(bar_data, col_name)`）
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
| `tqcenter` | `D:\Applications\tdx_test\PYPlugins\user\tqcenter.py` | TDX DLL 桥接层，非 pip 包，需在 `sys.path` 中 |

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

### 方式一：代码构造

```python
from pybroker.context import ExecContext
from stablemoney import StrategyBuilder, StrategyConfig
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


result = (
    StrategyBuilder()
    .set_data_source(TdxDataSource())
    .set_config(StrategyConfig(
        initial_cash=500_000,
        params={"stop_loss_pct": 5.0, "take_profit_pct": 10.0},
    ))
    .add_indicator(RSI(14))
    .add_indicator(MA(20))
    .set_exec_fn(my_strategy)
    .set_symbols(["600519.SH", "000858.SZ"])
    .set_date_range("2024-01-01", "2024-12-31")
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
from stablemoney.tdx_data_source import TdxDataSource

strategy_config, backtest_config = load_config("strategy.yaml")

result = (
    StrategyBuilder()
    .set_data_source(TdxDataSource())
    .set_config(strategy_config)
    .add_indicators(backtest_config.indicators)
    .set_exec_fn(my_strategy)
    .set_symbols(backtest_config.symbols)
    .set_date_range(backtest_config.start_date, backtest_config.end_date)
    .run()
)
```

### 方式三：运行 Mock 示例

无需 TDX 环境，使用模拟数据运行：

```bash
python examples/simple_rsi_strategy.py
```

## 目录结构

```
StableMoney/
├── pyproject.toml                          # 项目元数据、依赖、工具配置
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
│   └── simple_rsi_strategy.py              # Mock 数据 RSI 策略示例
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

流式构建器，组装并运行回测：

```python
result = (
    StrategyBuilder()
    .set_data_source(data_source)
    .set_config(config)
    .add_indicator(RSI(14))
    .set_exec_fn(trading_logic)
    .set_symbols(["600519.SH"])
    .set_date_range("2024-01-01", "2024-12-31")
    .run()  # → TestResult
)
```

### TdxDataSource（`tdx_data_source.py`）

继承 PyBroker 的 `DataSource`，通过 `tqcenter` 调用 TDX DLL：

- 股票代码格式：`"600519.SH"`、`"000858.SZ"`
- 行情获取：`tq.get_market_data()` → `Dict[str, DataFrame]`
- 指标计算：`tq.formula_process_mul()` → TDX 公式引擎批量计算
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
| `TdxDataSource` 数据源 | **框架完成，集成待验证** | API 调用逻辑已编写，响应格式解析待确认 |
| 内建指标（11个） | 已完成 | MA, EMA, MACD, RSI, KDJ, CCI, WR, BOLL, ATR, OBV, VOL_MA |
| Mock 数据示例 | 已完成 | `examples/simple_rsi_strategy.py` |
| 工具链配置 | 已完成 | ruff + mypy strict 通过 |
| Claude Code 技能 | 已完成 | PyBroker 参考、TDX API 参考 |

### 待完成

| 任务 | 优先级 | 说明 |
|------|--------|------|
| TDX 真实环境集成测试 | 高 | `_merge_indicator_data()` 的响应格式解析需根据实际 API 返回确认 |
| `_find_record()` 性能优化 | 中 | 当前 O(n^2) 线性扫描，大数据集下需改为索引查找 |
| 测试套件 | 中 | 暂无测试 |
| 版本控制初始化 | 中 | 尚未初始化 git 仓库 |
| `.gitignore` 配置 | 低 | 需排除 `.venv/`、`__pycache__/`、`.ruff_cache/` 等 |
| 具体策略实现 | 待定 | 用户尚未指定第一个具体策略需求 |

## 编码规范

- **Python 版本**：>= 3.10，全程严格类型标注
- **风格检查**：`ruff check src/stablemoney`，目标规则集 E/W/F/I/N/UP/B/SIM/TCH
- **类型检查**：`mypy src/stablemoney`，strict 模式
- **命名约定**：文件以主类名命名（如 `strategy_builder.py`）；指标工厂函数使用大写（如 `MA()`、`RSI()`）
- **封装原则**：不做没必要的封装——直接使用 PyBroker 的 `ExecContext`，不自定义包装类
- **导入规范**：仅用于类型标注的导入放入 `TYPE_CHECKING` 块；使用 `collections.abc` 代替 `typing`（如 `Callable`、`Iterable`）；使用 `X | None` 代替 `Optional[X]`

## 已知限制

1. **TDX 集成未验证** — `_merge_indicator_data()` 中的响应格式解析为占位实现，需根据真实 `tq.formula_process_mul()` 返回数据确认
2. **`tqcenter` 非标准包** — TDX 桥接层为本地 DLL 调用，需手动添加到 `sys.path`，不可通过 pip 安装
3. **性能问题** — `_convert_kline_to_dataframe()` 中的 `_find_record()` 为 O(n^2) 线性扫描
4. **无测试覆盖** — 当前没有任何单元测试或集成测试
5. **无版本控制** — 项目尚未初始化 git 仓库

## 后续规划

1. **接入真实 TDX 环境** — 使用通达信 DLL 跑通端到端回测
2. **具体策略开发** — 根据用户需求实现第一个实际策略
3. **前后端可视化** — 将项目扩展为前后端应用，前端展示回测结果
4. **自定义指标支持** — 允许用户编写 PyBroker 原生指标函数（通过 `IndicatorDef.compute_fn`）
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
