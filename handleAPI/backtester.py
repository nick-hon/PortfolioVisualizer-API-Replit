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


def clean_portfolios(portfolios):
    # List comprehension to return a new portfolios list containing only non-empty portfolios, i.e. any non-zero asset allocation
    return [p for p in portfolios if any(asset["allocation"] != 0.0 for asset in p["assets"])]


def download(start, end, portfolios, allocations=None):
    if allocations is None:
        allocations = []
    tickers = []
    for portfolio in portfolios:
        assets = {}
        for asset in portfolio["assets"]:
            ticker = asset["ticker"]
            # Cleans ticker for use throughout bt:
            # Basically converts to lower case and removes any non-standard characters (GC=F -> gcf)
            clean_ticker = utils.clean_ticker(ticker)
            assets[clean_ticker] = asset["allocation"]
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
    portfolios = clean_portfolios(portfolios)
    allocations = []
    a_prices = download(start, end, portfolios, allocations)
    backtests = []
    for i in range(len(portfolios)):
        t = set_backtest(a_prices, portfolios[i]["name"], allocations[i])
        backtests.append(t)

    p_stats = bt.run(*backtests)
    
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

    # The below code first checks metadatas['metricGroup'] in each item of the 
    # result_metadatas dictionary. 
    # If it is not None, it checks the value of metadatas['subject'] to determine 
    # whether to use p_stats.stats (portfolio stats) or a_stats.stats (asset stats) 
    # as the source of the data. It then looks up the appropriate list of metric keys
    # from the metric_groups dictionary using metadatas['metricGroup'], filters the 
    # source data to include only the desired metrics, and adds a new column to the 
    # resulting DataFrame with the corresponding label. The resulting DataFrame is 
    # then appended to the dfs list along with the key from the result_metadatas dict.
    # If it is None, it checks the value of result to determine which of several cases
    # to handle next. Basically it sources the data from either p_stats or a_stats.
    dfs = []
    for result, metadatas in result_metadatas.items():
        if metadatas['metricGroup'] is not None:
            if metadatas['subject'] == "portfolio":
                stats = p_stats.stats
            elif metadatas['subject'] == "asset":
                stats = a_stats.stats
            else:
                stats = None
                continue
            metrics = metric_groups.get(metadatas['metricGroup'], [])
            df = stats.filter(items=metrics, axis=0)
            # labelCns = [metric_info[m]['labelCn'] for m in metrics]
            # df.insert(0, 'labelCn', labelCns)
            dfs.append((result, df))
        else:
            if result == "port_perf_chart":
                df = p_stats.prices
                dfs.append((result, df))
           
            elif result == "drawdown_chart":
                df = ffn.to_drawdown_series(p_stats.prices)
                dfs.append((result, df))

            elif result == "drawdowns":
                for i in range(len(portfolios)):
                    if p_stats[i].drawdown_details is not None:
                        df = p_stats[i].drawdown_details.sort_values('drawdown').head(5)
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
