# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此仓库中工作时提供指导。

## 项目概述

StableMoney 是一个基于 PyBroker 的 A 股回测框架。策略由四个组件通过构建器模式组装：**DataSource**、**StrategyConfig**、**Indicator**、**ExecuteCallback**。数据源为通达信 TDX（通过 `tqcenter` 包调用 DLL）。指标由 TDX 公式引擎在服务端计算，而非 PyBroker 计算。

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

# 运行示例（Mock 数据，无需 TDX 环境）
python examples/simple_rsi_strategy.py
```

暂无测试套件。

## 架构

### 数据流

```
StrategyBuilder.run()
  → DataSource.set_indicators()           # 向 PyBroker scope 注册自定义列
  → 注册透传 indicator                    # 将预计算列桥接到 PyBroker 指标管线
  → PyBroker Strategy.backtest()
    → TdxDataSource._fetch_data()
      → tq.get_market_data()             # 通过 DLL 获取 OHLCV
      → tq.formula_process_mul()         # 通过 TDX 公式引擎计算指标
      → 格式转换 + 合并                   # TDX Dict[str, DataFrame] → 单个 PyBroker DataFrame
    → 透传 indicator 函数                 # 从 BarData 读取预计算列
    → exec_fn(ctx)                       # 逐 bar 用户回调，通过 ctx.config.params 访问自定义参数
```

### 核心设计模式

- **透传指标**：TDX 计算的指标值通过 `StaticScope.register_custom_cols()` 注册为 DataFrame 自定义列。PyBroker 的 indicator 函数只是简单的列读取器（`getattr(bar_data, col_name)`），不做任何计算。
- **Frozen dataclass**：`IndicatorDef`、`StrategyConfig`、`BacktestConfig` 均为 frozen。`StrategyConfig` 继承 PyBroker 的 frozen `StrategyConfig`，增加 `params: dict[str, Any]` 字段，回调中通过 `ctx.config.params` 访问。
- **构建器模式**：`StrategyBuilder` 提供流式接口，调用 `run()` 完成校验、注入指标、执行回测。

### TDX 集成

- 股票代码格式：`"600519.SH"`、`"000858.SZ"`（代码.市场后缀）
- K 线数据：`tq.get_market_data()` 返回 `Dict[str, DataFrame]`，keys 为 "Open"/"High"/"Low"/"Close"/"Volume"/"Amount"，每个 DataFrame 以 DatetimeIndex 为索引、股票代码为列
- 指标计算：`tq.formula_process_mul(formula_name, formula_arg, stock_list, stock_period, start_time, end_time)`，`formula_arg` 为逗号分隔参数（如 KDJ 的 `"9,3,3"`）
- TDX 源码参考：`D:/Applications/tdx_test/PYPlugins/user/tqcenter.py`

### 指标定义

`IndicatorDef` 为声明式定义：`name`（TDX 公式名）、`params`（有序字典）、`outputs`（输出名元组）。内建指标为 `src/stablemoney/indicators/` 下的工厂函数（MA、EMA、MACD、RSI、KDJ、CCI、WR、BOLL、ATR、OBV、VOL_MA）。工厂函数故意使用大写命名（通过 ruff per-file-ignores 抑制 N802）。

### 配置

通过 `config_loader.py` 支持 YAML 配置文件。两个配置类：`StrategyConfig`（回测参数）和 `BacktestConfig`（标的、日期、指标）。均支持 `to_dict()`/`from_dict()` 序列化。

## 编码规范

- 全程严格类型标注，Python 3.10+
- 文件以主类名命名（`strategy_builder.py`、`indicator_def.py` 等）
- 不做没必要的封装——直接使用 PyBroker 的 `ExecContext`，不自定义包装
- 仅用于类型标注的导入放入 `TYPE_CHECKING` 块
- 使用 `from collections.abc import Callable, Iterable`（而非 `typing`）
- 使用 `X | None` 语法（而非 `Optional[X]`）
