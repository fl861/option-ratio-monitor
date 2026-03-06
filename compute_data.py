#!/usr/bin/env python3
"""
预计算历史比例数据
生成 ratios_data.json
"""

import pandas as pd
import re
import json
from datetime import datetime

BTC_CSV = '/root/.openclaw/workspace/btc_put_2023_to_now.csv'
ETH_CSV = '/root/.openclaw/workspace/eth_put_2023_to_now.csv'
OUTPUT = '/root/.openclaw/workspace/projects/option-ratio-monitor/ratios_data.json'

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
    elif 17 <= days <= 35:
        return 'long'
    return None

print("读取BTC数据...")
btc = pd.read_csv(BTC_CSV, usecols=['instrument_name', 'trade_timestamp', 'mark_price', 'index_price'])
btc['currency'] = 'BTC'

print("读取ETH数据...")
eth = pd.read_csv(ETH_CSV, usecols=['instrument_name', 'trade_timestamp', 'mark_price', 'index_price'])
eth['currency'] = 'ETH'

print("合并数据...")
df = pd.concat([btc, eth], ignore_index=True)

print("解析日期...")
df['trade_date'] = pd.to_datetime(df['trade_timestamp'], unit='ms').dt.date
df['expiry_date'] = df['instrument_name'].apply(parse_expiry)
df['expiry_type'] = df.apply(lambda x: classify_expiry(x['expiry_date'], x['trade_date']), axis=1)

# 只保留短长期
df = df[df['expiry_type'].isin(['short', 'long'])]

print(f"处理 {len(df)} 条记录...")

# 计算每日比例
results = {}
for (date, curr), grp in df.groupby(['trade_date', 'currency']):
    short = grp[grp['expiry_type'] == 'short']['mark_price'].mean()
    long = grp[grp['expiry_type'] == 'long']['mark_price'].mean()
    price = grp['index_price'].iloc[-1]
    
    if pd.notna(short) and pd.notna(long) and long > 0:
        ratio = short / long
        date_str = str(date)
        if date_str not in results:
            results[date_str] = {'btc_ratio': 0, 'eth_ratio': 0, 'btc_price': 0, 'eth_price': 0}
        results[date_str][f'{curr.lower()}_ratio'] = round(ratio, 4)
        results[date_str][f'{curr.lower()}_price'] = round(price, 2)

# 排序并格式化
sorted_dates = sorted(results.keys())
output = {
    'dates': sorted_dates,
    'btc_ratios': [results[d]['btc_ratio'] for d in sorted_dates],
    'eth_ratios': [results[d]['eth_ratio'] for d in sorted_dates],
    'btc_prices': [results[d]['btc_price'] for d in sorted_dates],
    'eth_prices': [results[d]['eth_price'] for d in sorted_dates]
}

with open(OUTPUT, 'w') as f:
    json.dump(output, f)

print(f"完成! 共 {len(sorted_dates)} 天数据")
print(f"日期范围: {sorted_dates[0]} 至 {sorted_dates[-1]}")
print(f"BTC比例范围: {min(output['btc_ratios']):.2f} - {max(output['btc_ratios']):.2f}")
