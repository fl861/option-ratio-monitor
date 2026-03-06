#!/usr/bin/env python3
"""
生成六张图的数据
基于历史CSV计算短期/中期/长期的价格、日均价格、比例
"""

import pandas as pd
import json
import re
from datetime import datetime

BTC_CSV = '/root/.openclaw/workspace/btc_put_2023_to_now.csv'
ETH_CSV = '/root/.openclaw/workspace/eth_put_2023_to_now.csv'
OUTPUT = '/root/.openclaw/workspace/projects/option-ratio-monitor/docs/charts_6_data.json'

def parse_expiry(name):
    match = re.search(r'-([0-9]{1,2})([A-Z]{3})([0-9]{2,4})-', name)
    if not match:
        return None
    day = int(match.group(1))
    month = {'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
             'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12}.get(match.group(2), 1)
    year = int(match.group(3))
    if year < 100:
        year += 2000
    try:
        return datetime(year, month, day).date()
    except:
        return None

def classify_expiry(expiry, trade):
    if not expiry or not trade:
        return None
    days = (expiry - trade).days
    if 3 <= days <= 9:
        return 'short'
    elif 10 <= days <= 16:
        return 'medium'
    elif 17 <= days <= 35:
        return 'long'
    return None

print("读取数据...")
btc = pd.read_csv(BTC_CSV, usecols=['instrument_name', 'trade_timestamp', 'mark_price', 'mark_iv', 'index_price'])
btc['currency'] = 'BTC'
eth = pd.read_csv(ETH_CSV, usecols=['instrument_name', 'trade_timestamp', 'mark_price', 'mark_iv', 'index_price'])
eth['currency'] = 'ETH'
df = pd.concat([btc, eth], ignore_index=True)

print("解析日期...")
df['trade_date'] = pd.to_datetime(df['trade_timestamp'], unit='ms').dt.date
df['expiry_date'] = df['instrument_name'].apply(parse_expiry)
df['expiry_type'] = df.apply(lambda x: classify_expiry(x['expiry_date'], x['trade_date']), axis=1)
df = df[df['expiry_type'].isin(['short', 'medium', 'long'])]

print("计算每日数据...")
results = {}
for (date, curr), grp in df.groupby(['trade_date', 'currency']):
    date_str = str(date)
    if date_str not in results:
        results[date_str] = {'BTC': {}, 'ETH': {}}
    
    for exp_type in ['short', 'medium', 'long']:
        exp_data = grp[grp['expiry_type'] == exp_type]
        if not exp_data.empty:
            avg_price = exp_data['mark_price'].mean()
            avg_iv = exp_data['mark_iv'].mean()
            avg_days = (exp_data['expiry_date'].iloc[0] - date).days if exp_data['expiry_date'].iloc[0] else 7
            daily_price = avg_price / avg_days if avg_days > 0 else 0
            index_price = exp_data['index_price'].iloc[-1]
            
            results[date_str][curr][exp_type] = {
                'price': round(avg_price, 6),
                'daily_price': round(daily_price, 6),
                'iv': round(avg_iv, 2),
                'days': avg_days,
                'index_price': round(index_price, 2)
            }
    
    # 计算比例
    if all(k in results[date_str][curr] for k in ['short', 'medium', 'long']):
        s = results[date_str][curr]['short']
        m = results[date_str][curr]['medium']
        l = results[date_str][curr]['long']
        
        results[date_str][curr]['ratios'] = {
            'sm': round(s['daily_price'] / m['daily_price'], 4) if m['daily_price'] > 0 else 0,
            'sl': round(s['daily_price'] / l['daily_price'], 4) if l['daily_price'] > 0 else 0,
            'ml': round(m['daily_price'] / l['daily_price'], 4) if l['daily_price'] > 0 else 0
        }

# 转换为图表格式
sorted_dates = sorted(results.keys())
output = {
    'dates': sorted_dates,
    'btc_price': {k: [] for k in ['short', 'medium', 'long']},
    'eth_price': {k: [] for k in ['short', 'medium', 'long']},
    'btc_daily': {k: [] for k in ['short', 'medium', 'long']},
    'eth_daily': {k: [] for k in ['short', 'medium', 'long']},
    'btc_ratio': {k: [] for k in ['sm', 'sl', 'ml']},
    'eth_ratio': {k: [] for k in ['sm', 'sl', 'ml']},
    'btc_iv': {k: [] for k in ['short', 'medium', 'long']},
    'eth_iv': {k: [] for k in ['short', 'medium', 'long']},
}

for d in sorted_dates:
    for curr in ['BTC', 'ETH']:
        curr_lower = curr.lower()
        for exp in ['short', 'medium', 'long']:
            val = results[d].get(curr, {}).get(exp, {})
            output[f'{curr_lower}_price'][exp].append(val.get('price', 0))
            output[f'{curr_lower}_daily'][exp].append(val.get('daily_price', 0))
            output[f'{curr_lower}_iv'][exp].append(val.get('iv', 0))
        
        ratios = results[d].get(curr, {}).get('ratios', {})
        for r in ['sm', 'sl', 'ml']:
            output[f'{curr_lower}_ratio'][r].append(ratios.get(r, 0))

with open(OUTPUT, 'w') as f:
    json.dump(output, f)

print(f"✓ 完成! 共 {len(sorted_dates)} 天数据")
print(f"  日期范围: {sorted_dates[0]} 至 {sorted_dates[-1]}")
print(f"  输出文件: {OUTPUT}")

# 打印最新数据验证
latest = sorted_dates[-1]
print(f"\n最新数据 ({latest}):")
print(f"  BTC 短期价格: {output['btc_price']['short'][-1]:.6f}")
print(f"  BTC 短期日均: {output['btc_daily']['short'][-1]:.6f}")
print(f"  BTC 短/长比例: {output['btc_ratio']['sl'][-1]:.4f}")
