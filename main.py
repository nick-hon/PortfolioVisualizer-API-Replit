from flask import Flask, Response, request, render_template, send_from_directory
# import os
import json
import handleAPI.backtester as hBt

from flask_cors import CORS

app = Flask('app')

CORS(app)


with open('./StockData/simpleStockList.json', newline='') as jsonfile:
    Ticker = json.load(jsonfile)


@app.route('/')
def hello_world():
  return Response(json.dumps({"API_TEST": "OK"}),
                  mimetype='application/json',
                  status=200)



# Portfolios API
@app.route('/api/portfolios', methods=['POST'])
def portfoliosAPI():
    req = request.json
    data = hBt.run_backtest(
        start=req[0], end=req[1], portfolios=req[2])
    return Response(json.dumps(data), mimetype='application/json', status=200)


# Fond keywords
def filter_list(func, iterable):
    new_iterable = filter(func, iterable)
    return list(new_iterable)


# Search Symbol API
@app.route('/api/keyword/<search>')
def searchAPI(search):
    # print("--------/keyword-----------"+search)
    search = search.lower()

    def search_even(x):
        s = json.dumps(x["symbol"]).lower().find(search)
        n = json.dumps(x["name"]).lower().find(search)
        if s != -1 or n != -1:
            return True
        return False

    search_list = filter_list(search_even, Ticker)
    print(search_list)
    return Response(json.dumps(search_list), mimetype='application/json', status=200)

# limit Search Symbol API


@app.route('/api/keyword/<search>/limit/<max>')
def limitSearchAPI(search, max):
    # print("--------/keyword-with-Limit-applied-----------" +
    #       search + "---limit:" + max)

    def search_even(x):
        s = json.dumps(x['symbol']).lower().find(search)
        n = json.dumps(x['name']).lower().find(search)
        if s != -1 or n != -1:
            return True
        return False

    if max.isnumeric():
        search = search.lower()
        maxResults = int(max)
        g = filter_list(search_even, Ticker)
        if maxResults > len(g) | maxResults == 0:
            maxResults = len(g)
        count = 0
        limited_list = []
        while count < maxResults and count < len(g):
            limited_list.append(g[count])
            count += 1
        return Response(json.dumps({'results': limited_list, 'message': ''}), mimetype='application/json', status=200)
    else:
        print('Limit must be a number')
        return Response(json.dumps({'results': [], 'message': 'Limit must be a number'}), mimetype='application/json', status=400)


print("Server is running...")

if __name__ == '__main__':
    from waitress import serve
    serve(app, host='0.0.0.0', port=8080)

    # Test server
    # app.run(host='0.0.0.0', port=8000, debug=True)
