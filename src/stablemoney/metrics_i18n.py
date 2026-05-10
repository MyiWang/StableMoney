"""Translate PyBroker backtest metric names to Chinese."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


METRIC_NAMES_CN: dict[str, str] = {
    "trade_count": "总交易次数",
    "initial_market_value": "初始资金",
    "end_market_value": "期末市值",
    "total_pnl": "总盈亏（含浮盈）",
    "unrealized_pnl": "未实现盈亏",
    "total_return_pct": "总收益率(%)",
    "total_profit": "总盈利金额",
    "total_loss": "总亏损金额",
    "total_fees": "总手续费",
    "max_drawdown": "最大回撤金额",
    "max_drawdown_pct": "最大回撤率(%)",
    "max_drawdown_date": "最大回撤日期",
    "win_rate": "胜率(%)",
    "loss_rate": "亏损率(%)",
    "winning_trades": "盈利交易次数",
    "losing_trades": "亏损交易次数",
    "avg_pnl": "平均每笔盈亏",
    "avg_return_pct": "平均每笔收益率(%)",
    "avg_trade_bars": "平均持仓K线数",
    "avg_profit": "盈利交易平均盈利",
    "avg_profit_pct": "盈利交易平均收益率(%)",
    "avg_winning_trade_bars": "盈利交易平均持仓K线数",
    "avg_loss": "亏损交易平均亏损",
    "avg_loss_pct": "亏损交易平均亏损率(%)",
    "avg_losing_trade_bars": "亏损交易平均持仓K线数",
    "largest_win": "最大单笔盈利",
    "largest_win_pct": "最大单笔盈利率(%)",
    "largest_win_bars": "最大单笔盈利持仓K线数",
    "largest_loss": "最大单笔亏损",
    "largest_loss_pct": "最大单笔亏损率(%)",
    "largest_loss_bars": "最大单笔亏损持仓K线数",
    "max_wins": "最大连续盈利次数",
    "max_losses": "最大连续亏损次数",
    "sharpe": "夏普比率",
    "sortino": "索提诺比率",
    "profit_factor": "盈亏比",
    "ulcer_index": "溃疡指数",
    "upi": "UPI（表现指数）",
    "equity_r2": "权益曲线R²拟合度",
    "std_error": "标准误差",
}


def translate_metrics(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of metrics_df with the ``name`` column translated to Chinese.

    Unknown metric names are left unchanged.
    """
    result = metrics_df.copy()
    if "name" in result.columns:
        result["name"] = result["name"].apply(
            lambda n: METRIC_NAMES_CN.get(n, n)
        )
    return result  # type: ignore[no-any-return]
