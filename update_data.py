#!/usr/bin/env python3
"""
获取Deribit最新期权数据并更新JSON
用于GitHub Actions自动更新
"""

import requests
import json
import os
from datetime import datetime, timedelta

DATA_FILE = 'docs/charts_6_data.json'

def get_deribit_data():
    """从Deribit获取期权数据"""
    
    # 获取现货价格
    btc_perp = requests.get('https://www.deribit.com/api/v2/public/ticker?instrument_name=BTC-PERPETUAL', timeout=30).json()
    eth_perp = requests.get('https://www.deribit.com/api/v2/public/ticker?instrument_name=ETH-PERPETUAL', timeout=30).json()
    
    btc_price = btc_perp['result']['index_price']
    eth_price = eth_perp['result']['index_price']
    
    # 获取期权合约
    btc_instruments = requests.get(
        'https://www.deribit.com/api/v2/public/get_instruments?currency=BTC&kind=option&expired=false',
        timeout=30
    ).json()
    
    eth_instruments = requests.get(
        'https://www.deribit.com/api/v2/public/get_instruments?currency=ETH&kind=option&expired=false',
        timeout=30
    ).json()
    
    today = datetime.now()
    
    def filter_by_expiry(instruments, days_range, target_strike_ratio):
        """筛选符合到期日范围的合约"""
        min_days, max_days = days_range
        target_strike = instruments[0]['strike'] * target_strike_ratio if instruments else 0
        
        candidates = []
        for inst in instruments:
            if inst['option_type'] != 'put':
                continue
            expiry_ts = inst['expiration_timestamp'] / 1000
            expiry_date = datetime.fromtimestamp(expiry_ts)
            days_to_expiry = (expiry_date - today).days
            
            if min_days <= days_to_expiry <= max_days:
                candidates.append({
                    'instrument': inst['instrument_name'],
                    'strike': inst['strike'],
                    'days': days_to_expiry
                })
        
        if not candidates:
            return None
        
        # 找最接近目标行权价的
        closest = min(candidates, key=lambda x: abs(x['strike'] - target_strike))
        return closest
    
    def get_option_price(instrument_name):
        """获取期权价格"""
        try:
            orderbook = requests.get(
                f'https://www.deribit.com/api/v2/public/get_order_book?instrument_name={instrument_name}',
                timeout=30
            ).json()
            result = orderbook['result']
            return {
                'mark_price': result.get('mark_price', 0),
                'mark_iv': result.get('mark_iv', 0),
                'bid': result.get('best_bid_price', 0),
                'ask': result.get('best_ask_price', 0)
            }
        except:
            return None
    
    results = {}
    
    for currency, instruments, price, strike_ratio in [
        ('BTC', btc_instruments['result'], btc_price, 0.9),
        ('ETH', eth_instruments['result'], eth_price, 0.85)
    ]:
        # 筛选合约
        short_inst = filter_by_expiry(instruments, (3, 9), price * strike_ratio)
        medium_inst = filter_by_expiry(instruments, (10, 16), price * strike_ratio)
        long_inst = filter_by_expiry(instruments, (17, 35), price * strike_ratio)
        
        results[currency] = {
            'index_price': price,
            'short': None,
            'medium': None,
            'long': None
        }
        
        for exp_type, inst in [('short', short_inst), ('medium', medium_inst), ('long', long_inst)]:
            if inst:
                price_data = get_option_price(inst['instrument'])
                if price_data:
                    days = inst['days']
                    results[currency][exp_type] = {
                        'price': price_data['mark_price'],
                        'daily_price': price_data['mark_price'] / days if days > 0 else 0,
                        'iv': price_data['mark_iv'],
                        'days': days
                    }
        
        # 计算比例
        if all(results[currency][k] for k in ['short', 'medium', 'long']):
            s = results[currency]['short']
            m = results[currency]['medium']
            l = results[currency]['long']
            results[currency]['ratios'] = {
                'sm': s['daily_price'] / m['daily_price'] if m['daily_price'] > 0 else 0,
                'sl': s['daily_price'] / l['daily_price'] if l['daily_price'] > 0 else 0,
                'ml': m['daily_price'] / l['daily_price'] if l['daily_price'] > 0 else 0
            }
    
    return results

def update_data():
    """更新数据文件"""
    
    # 获取最新数据
    new_data = get_deribit_data()
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 读取现有数据
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)
    
    # 检查今天是否已有数据
    if today in data['dates']:
        idx = data['dates'].index(today)
        print(f"更新今天的数据: {today}")
    else:
        idx = len(data['dates'])
        data['dates'].append(today)
        print(f"添加新数据: {today}")
    
    # 更新数据
    for curr in ['btc', 'eth']:
        curr_upper = curr.upper()
        if curr_upper not in new_data:
            continue
            
        curr_data = new_data[curr_upper]
        
        # 价格和日均价格
        for exp in ['short', 'medium', 'long']:
            val = curr_data.get(exp, {})
            if val:
                if idx >= len(data[f'{curr}_price'][exp]):
                    data[f'{curr}_price'][exp].append(val.get('price', 0))
                    data[f'{curr}_daily'][exp].append(val.get('daily_price', 0))
                    data[f'{curr}_iv'][exp].append(val.get('iv', 0))
                else:
                    data[f'{curr}_price'][exp][idx] = val.get('price', 0)
                    data[f'{curr}_daily'][exp][idx] = val.get('daily_price', 0)
                    data[f'{curr}_iv'][exp][idx] = val.get('iv', 0)
        
        # 比例
        ratios = curr_data.get('ratios', {})
        for r in ['sm', 'sl', 'ml']:
            if idx >= len(data[f'{curr}_ratio'][r]):
                data[f'{curr}_ratio'][r].append(ratios.get(r, 0))
            else:
                data[f'{curr}_ratio'][r][idx] = ratios.get(r, 0)
    
    # 保存
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✓ 数据已更新: {today}")
    print(f"  BTC SL比例: {new_data.get('BTC', {}).get('ratios', {}).get('sl', 0):.2f}x")
    print(f"  ETH SL比例: {new_data.get('ETH', {}).get('ratios', {}).get('sl', 0):.2f}x")

if __name__ == '__main__':
    update_data()
