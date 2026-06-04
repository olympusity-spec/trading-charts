from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS
import yfinance as yf
import os

app = Flask(__name__)
CORS(app)

PORTFOLIO = {
    'ASTS':  {'shares': 105.00, 'cost': 109.91},
    'SOXX':  {'shares':  30.00, 'cost': 570.45},
    'MRVL':  {'shares':  39.00, 'cost': 271.39},
    'DELL':  {'shares':   5.00, 'cost': 456.28},
    'ARM':   {'shares':  29.00, 'cost': 363.65},
    'SOXL':  {'shares':  15.00, 'cost': 224.69},
    'QCLN':  {'shares':  25.00, 'cost':  66.50},
}

TF_MAP = {
    '5m':  {'period': '5d',   'interval': '5m'},
    '15m': {'period': '15d',  'interval': '15m'},
    '1h':  {'period': '730d', 'interval': '1h'},
    '4h':  {'period': '60d',  'interval': '1h'},
    '1d':  {'period': '2y',   'interval': '1d'},
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(
        os.path.join(app.root_path, 'templates'), filename)

@app.route('/api/history/<symbol>')
def history(symbol):
    try:
        tf  = request.args.get('tf', '1d')
        cfg = TF_MAP.get(tf, TF_MAP['1d'])
        # retry up to 3 times
        df = None
        for attempt in range(3):
            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(
                    period=cfg['period'],
                    interval=cfg['interval'])
                if not df.empty:
                    break
            except Exception:
                if attempt == 2:
                    raise
                continue

        if df is None or df.empty:
            return jsonify({'error': 'no data'}), 404

        bars = []
        for ts, row in df.iterrows():
            try:
                bars.append({
                    'time':   int(ts.timestamp()),
                    'open':   round(float(row['Open']),  4),
                    'high':   round(float(row['High']),  4),
                    'low':    round(float(row['Low']),   4),
                    'close':  round(float(row['Close']), 4),
                    'volume': int(row['Volume']),
                })
            except Exception:
                continue
        return jsonify(bars)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/quote/<symbol>')
def quote(symbol):
    try:
        info     = yf.Ticker(symbol).fast_info
        price    = round(float(info.last_price), 2)
        prev     = round(float(info.previous_close), 2)
        chg      = round(price - prev, 2)
        chg_pct  = round(chg / prev * 100, 2) if prev else 0
        pos      = PORTFOLIO.get(symbol, {})
        shares   = pos.get('shares', 0)
        cost     = pos.get('cost', 0)
        mkt_val  = round(price * shares, 2)
        cost_val = round(cost  * shares, 2)
        return jsonify({
            'symbol':     symbol,
            'price':      price,
            'prev':       prev,
            'change':     chg,
            'change_pct': chg_pct,
            'shares':     shares,
            'cost':       cost,
            'mkt_val':    mkt_val,
            'today_pnl':  round(chg * shares, 2),
            'total_pnl':  round(mkt_val - cost_val, 2),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/portfolio')
def portfolio():
    try:
        results    = []
        total_val  = 228.62
        total_cost = 228.62
        today_pnl  = 0
        total_pnl  = 0
        for sym, pos in PORTFOLIO.items():
            try:
                info    = yf.Ticker(sym).fast_info
                price   = round(float(info.last_price), 2)
                prev    = round(float(info.previous_close), 2)
                chg     = round(price - prev, 2)
                chg_pct = round(chg / prev * 100, 2) if prev else 0
                shares  = pos['shares']
                cost    = pos['cost']
                mv      = round(price * shares, 2)
                cv      = round(cost  * shares, 2)
                tp      = round(chg   * shares, 2)
                ttl     = round(mv - cv, 2)
                total_val  += mv
                total_cost += cv
                today_pnl  += tp
                total_pnl  += ttl
                results.append({
                    'symbol': sym, 'price': price,
                    'change': chg, 'change_pct': chg_pct,
                    'shares': shares, 'cost': cost,
                    'mkt_val': mv, 'today_pnl': tp, 'total_pnl': ttl,
                })
            except Exception as ex:
                print(f'  {sym} error: {ex}')
        return jsonify({
            'holdings':   results,
            'total_val':  round(total_val,  2),
            'total_cost': round(total_cost, 2),
            'today_pnl':  round(today_pnl,  2),
            'total_pnl':  round(total_pnl,  2),
            'cash':       228.62,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
