import json
import pandas as pd
import bt
import ffn
import ffn.utils as utils
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
            # Cleans ticker for use throughout bt:
            # Basically converts to lower case and removes any non-standard characters (GC=F -> gcf)
            # assets[ticker.lower().replace("=", "")] = portfolios[i]["assets"][j]["allocation"]
            assets[utils.clean_ticker(
                ticker)] = portfolios[i]["assets"][j]["allocation"]
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
    a_prices = download(start, end, portfolios, allocations)
    backtests = []
    for i in range(len(portfolios)):
        t = set_backtest(a_prices, portfolios[i]["name"], allocations[i])
        backtests.append(t)

    p_stats = bt.run(backtests[0], backtests[1], backtests[2])
    a_stats = ffn.calc_stats(a_prices)
    # Type returned from bt.run() is bt.backtest.Result, which is inherited from GroupStats
    # Type returned from ffn.calc_stats(): Series -> PerformanceStats | DataFrame -> GroupStats

    rf = 0.01   # Set risk-free rate, which is used in Sharpe Ratio calculations
    p_stats.set_riskfree_rate(rf)
    a_stats.set_riskfree_rate(rf)

    with open('data/metric_info.json', mode='r', encoding='utf8') as f:
        metric_info = json.load(f)
    with open('data/metric_groups.json', mode='r', encoding='utf8') as f:
        metric_groups = json.load(f)
    with open('data/result_metadata.json', mode='r', encoding='utf8') as f:
        result_metadatas = json.load(f)

    dfs = []

    for result, metadatas in result_metadatas.items():
        if metadatas['metricGroup'] is not None:
            if metadatas['subject'] == "portfolio":
                stats = p_stats.stats
            elif metadatas['subject'] == "asset":
                stats = a_stats.stats
            for group, metrics in metric_groups.items():
                if group == metadatas['metricGroup']:
                    df = stats.filter(items=metrics, axis=0)
                    # labelCns = [metric_info[m]['labelCn'] for m in metrics]
                    # df.insert(0, 'labelCn', labelCns)
                    dfs.append((result, df))

        elif result == "port_perf_chart":
            df = p_stats.prices
            dfs.append((result, df))

        elif result == "drawdown_chart":
            df = ffn.to_drawdown_series(p_stats.prices)
            dfs.append((result, df))

        elif result == "drawdowns":
            for i in range(len(portfolios)):
                df = p_stats[i].drawdown_details.sort_values(
                    'drawdown').head(5)
                dfs.append((portfolios[i]['name'] + " " + result, df))

        elif result == "asset_corr":
            df = a_prices.pct_change().corr()
            dfs.append((result, df))

    out_json = {}
    for result, df in dfs:
        df_json = df.to_json(orient='split', date_format='iso')
        out_json[result] = json.loads(df_json)

    out_json = json.dumps(out_json)
    return out_json
