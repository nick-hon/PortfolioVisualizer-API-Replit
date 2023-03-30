import json
import pandas as pd
import bt
import yfinance

# 2022-12-22: Yahoo made changes to an underlying API that broke compatiblity
# Temp fix: Use yfinance.pdr_override() until a permanent fix, probably in
# pandas_datareader.data.get_data_yahoo(), is available
yfinance.pdr_override()


def download(start, end, portfolios, allocations=None):
    if allocations == None:
        allocations = []
    tickers = []
    for i in range(len(portfolios)):
        assets = {}
        for j in range(len(portfolios[i]["assets"])):
            ticker = portfolios[i]["assets"][j]["ticker"]
            # Data cleaning for the ticker,
            # which is converted to lower case and any equal sign (=) is removed
            assets[ticker.lower().replace(
                "=", "")] = portfolios[i]["assets"][j]["allocation"]
            if ticker not in tickers:
                tickers.append(ticker)
        allocations.append(assets)

    prices = bt.get(tickers, start=start, end=end)
    return prices


def set_backtest(prices, strategy_name, weight):
    strategy = bt.Strategy(strategy_name, [
        bt.algos.RunYearly(),
        bt.algos.SelectAll(),
        bt.algos.WeighSpecified(**weight),
        bt.algos.Rebalance()])
    backtest = bt.Backtest(strategy, prices, initial_capital=1000000.0)
    return backtest


def run_backtest(start, end, portfolios):
    allocations = []
    prices = download(start, end, portfolios, allocations)
    backtests = []
    for i in range(len(portfolios)):
        t = set_backtest(prices, portfolios[i]["name"], allocations[i])
        backtests.append(t)

    res = bt.run(backtests[0], backtests[1], backtests[2])
    rf = 0.01   # Set risk-free rate, which is used in Sharpe Ratio calculations
    res.set_riskfree_rate(rf)
    prices_perf = pd.DataFrame(prices).calc_stats()
    prices_perf.set_riskfree_rate(rf)

    # Returns json containing 3 DataFrames
    df1 = res.prices            # 1. portfolio time series
    df2 = res.stats             # 2. portfolio statistics
    df3 = prices_perf.stats     # 3. asset statistics

    df1_json = df1.to_json(orient='split', date_format='iso')
    df2_json = df2.to_json(orient='split', date_format='iso')
    df3_json = df3.to_json(orient='split', date_format='iso')
    out_json = {'df1': json.loads(df1_json),
                'df2': json.loads(df2_json),
                'df3': json.loads(df3_json)
                }
    out_json = json.dumps(out_json)

    # For debug purpose:
    # print(out_json)
    # data = json.loads(out_json)

    return out_json
