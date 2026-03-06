#!/usr/bin/env python3
"""
短长期比例监测网站 - Flask后端 (轻量版)
使用预计算的JSON缓存文件
"""

from flask import Flask, jsonify, render_template
import json
import os
from datetime import datetime

app = Flask(__name__, template_folder='templates', static_folder='static')

# 预计算的数据文件
DATA_FILE = '/root/.openclaw/workspace/projects/option-ratio-monitor/ratios_data.json'

def load_data():
    """加载预计算数据"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {'dates': [], 'btc_ratios': [], 'eth_ratios': [], 'btc_prices': [], 'eth_prices': []}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/current')
def get_current():
    data = load_data()
    if not data['dates']:
        return jsonify({'error': 'No data'})
    
    idx = -1
    return jsonify({
        'timestamp': f"{data['dates'][idx]}T00:00:00",
        'btc_price': data['btc_prices'][idx],
        'eth_price': data['eth_prices'][idx],
        'btc_ratio_sl': data['btc_ratios'][idx],
        'eth_ratio_sl': data['eth_ratios'][idx],
    })

@app.route('/api/ratios/chart')
def get_chart():
    return jsonify(load_data())

@app.route('/api/stats')
def get_stats():
    data = load_data()
    btc = [r for r in data['btc_ratios'] if r > 0]
    eth = [r for r in data['eth_ratios'] if r > 0]
    
    if not btc:
        return jsonify({'error': 'No data'})
    
    btc_cur = btc[-1]
    btc_sorted = sorted(btc)
    pct = btc_sorted.index(btc_cur) / len(btc_sorted) * 100
    
    return jsonify({
        'btc': {
            'current': round(btc_cur, 2),
            'max': round(max(btc), 2),
            'min': round(min(btc), 2),
            'mean': round(sum(btc)/len(btc), 2),
            'percentile': round(pct, 1)
        },
        'eth': {
            'current': round(eth[-1], 2) if eth else None,
            'max': round(max(eth), 2) if eth else None,
            'min': round(min(eth), 2) if eth else None,
            'mean': round(sum(eth)/len(eth), 2) if eth else None,
        },
        'date_range': {
            'start': data['dates'][0] if data['dates'] else None,
            'end': data['dates'][-1] if data['dates'] else None,
            'total_days': len(data['dates'])
        }
    })

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
