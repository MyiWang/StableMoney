# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此仓库中工作时提供指导。

## 项目概述

StableMoney 是一个基于 PyBroker 的 A 股回测框架。策略通过构建器模式组装：**DataSource**（含指标定义和 TDX 连接）、**BacktestConfig**（标的、日期、资金、指标、warmup）、**Algo**（交易逻辑，实现 `__call__` 的类或裸函数，通过 `AlgoConfig` 注入风控参数）。数据源为通达信 TDX（通过 `tqcenter` 包的 `tq` 模块访问 TDX 能力）。指标由 TDX 公式引擎在服务端计算，而非 PyBroker 计算。指标通过 `TdxDataSource` 构造函数注入。

## 常用命令

```bash
# 代码检查
ruff check src/stablemoney

# 类型检查（严格模式）
mypy src/stablemoney

# 可编辑模式安装
pip install -e .

# 安装开发依赖
pip install -e ".[dev]"

# 运行示例（需 TDX 环境）
python examples/tdx_rsi_strategy.py
```

暂无测试套件。

## 架构

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
- **Frozen dataclass**：`IndicatorDef`、`AlgoConfig`、`BacktestConfig` 均为 frozen。`BacktestConfig` 包含 `initial_cash` 和 `warmup` 字段，`run()` 内部据此创建 PyBroker 的 `StrategyConfig`。
- **构建器模式**：`StrategyBuilder` 提供流式接口，通过 `set_backtest(BacktestConfig)` 一次性设置标的、日期、资金、指标，调用 `run()` 完成校验、执行回测。

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
- **AlgoConfig**：`src/stablemoney/algo_config.py` 中的 frozen dataclass，存放通用风控参数（`stop_loss_pct`、`take_profit_pct`），作为 Algo 构造函数的参数注入
- **内建 Algo**：`src/stablemoney/algos/` 子包存放具体实现（如 `RSIAlgo`）
- **用户自定义**：任何实现 `__call__(ctx: ExecContext) -> None` 的类或函数即可，无需继承

### 配置

通过 `config_loader.py` 支持 YAML 配置文件。`BacktestConfig` 统一存放回测参数（标的、日期、资金、指标、warmup）。`StrategyBuilder.run()` 内部从 `BacktestConfig.initial_cash` 创建 PyBroker 的 `StrategyConfig`。支持 `to_dict()`/`from_dict()` 序列化。

## 编码规范

- 全程严格类型标注，Python 3.10+
- 文件以主类名命名（`strategy_builder.py`、`indicator_def.py` 等）
- 不做没必要的封装——直接使用 PyBroker 的 `ExecContext`，不自定义包装
- 仅用于类型标注的导入放入 `TYPE_CHECKING` 块
- 使用 `from collections.abc import Callable, Iterable`（而非 `typing`）
- 使用 `X | None` 语法（而非 `Optional[X]`）
