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
    
    def filter_by_expiry(instruments, days_range, target_strike, currency, prefer_days=None):
        """筛选符合到期日范围的合约"""
        min_days, max_days = days_range
        
        candidates = []
        for inst in instruments:
            if inst['option_type'] != 'put':
                continue
            expiry_ts = inst['expiration_timestamp'] / 1000
            expiry_date = datetime.fromtimestamp(expiry_ts)
            days_to_expiry = (expiry_date - today).days
            
            if min_days <= days_to_expiry <= max_days:
                # 只选择接近目标行权价的 (±5%范围内)
                if abs(inst['strike'] - target_strike) / target_strike <= 0.05:
                    candidates.append({
                        'instrument': inst['instrument_name'],
                        'strike': inst['strike'],
                        'days': days_to_expiry
                    })
        
        if not candidates:
            return None
        
        # 如果有 prefer_days，优先选择最接近该天数的
        if prefer_days is not None:
            closest = min(candidates, key=lambda x: (abs(x['days'] - prefer_days), abs(x['strike'] - target_strike)))
        else:
            # 否则选择最接近目标行权价的
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
            
            # 使用 bid/ask 中间价，而不是 mark_price
            bid = result.get('best_bid_price', 0)
            ask = result.get('best_ask_price', 0)
            mid_price = (bid + ask) / 2 if bid > 0 and ask > 0 else result.get('mark_price', 0)
            
            return {
                'mark_price': mid_price,
                'mark_iv': result.get('mark_iv', 0),
                'bid': bid,
                'ask': ask
            }
        except:
            return None
    
    def validate_data(short, medium, long, currency):
        """验证数据是否合理"""
        if not all([short, medium, long]):
            return False, "缺失数据"
        
        # 检查价格是否合理 (短期价格不应低于长期的1/10)
        if short['price'] < long['price'] * 0.1:
            return False, f"短期价格异常低: {short['price']:.6f} vs 长期: {long['price']:.6f}"
        
        # 检查IV是否合理 (短期IV通常高于长期)
        if short['iv'] < long['iv'] * 0.5:
            return False, f"短期IV异常低: {short['iv']:.2f}% vs 长期: {long['iv']:.2f}%"
        
        return True, "OK"
    
    results = {}
    
    for currency, instruments, price, strike_ratio in [
        ('BTC', btc_instruments['result'], btc_price, 0.9),
        ('ETH', eth_instruments['result'], eth_price, 0.85)
    ]:
        target_strike = price * strike_ratio
        
        # 到期日选择策略: 短5-9天 / 中12-16天 / 长25-65天(最接近30天)
        short_inst = filter_by_expiry(instruments, (5, 9), target_strike, currency)
        medium_inst = filter_by_expiry(instruments, (12, 16), target_strike, currency)
        long_inst = filter_by_expiry(instruments, (25, 65), target_strike, currency, prefer_days=30)
        
        print(f"\n{currency} 选中合约:")
        print(f"  短期: {short_inst}")
        print(f"  中期: {medium_inst}")
        print(f"  长期: {long_inst}")
        
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
                        'days': days,
                        'strike': inst['strike']
                    }
        
        # 验证数据
        is_valid, msg = validate_data(
            results[currency]['short'],
            results[currency]['medium'],
            results[currency]['long'],
            currency
        )
        print(f"  验证结果: {msg}")
        
        if not is_valid:
            print(f"  ⚠️ 数据异常，跳过今日{currency}数据")
            results[currency]['skip'] = True
            continue
        
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
        print(f"\n更新今天的数据: {today}")
    else:
        idx = len(data['dates'])
        data['dates'].append(today)
        print(f"\n添加新数据: {today}")
    
    # 更新数据
    for curr in ['btc', 'eth']:
        curr_upper = curr.upper()
        if curr_upper not in new_data:
            continue
        
        # 如果数据异常被标记跳过，则复制昨天的数据
        if new_data[curr_upper].get('skip', False):
            print(f"  {curr_upper}: 数据异常，使用昨日数据")
            if idx > 0:
                for exp in ['short', 'medium', 'long']:
                    data[f'{curr}_price'][exp][idx] = data[f'{curr}_price'][exp][idx-1]
                    data[f'{curr}_daily'][exp][idx] = data[f'{curr}_daily'][exp][idx-1]
                    data[f'{curr}_iv'][exp][idx] = data[f'{curr}_iv'][exp][idx-1]
                for r in ['sm', 'sl', 'ml']:
                    data[f'{curr}_ratio'][r][idx] = data[f'{curr}_ratio'][r][idx-1]
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
        
        print(f"  {curr_upper} SL比例: {ratios.get('sl', 0):.2f}x")
    
    # 保存
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n✓ 数据已更新: {today}")

if __name__ == '__main__':
    update_data()
