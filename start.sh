#!/bin/bash
# 启动短长期比例监测网站

cd "$(dirname "$0")"

echo "🔶 启动期权短长期比例监测网站..."
echo "📊 数据源:"
echo "   - CSV历史数据: /root/.openclaw/workspace/btc_put_2023_to_now.csv"
echo "   - CSV历史数据: /root/.openclaw/workspace/eth_put_2023_to_now.csv"
echo "   - SQLite实时数据: /root/.openclaw/workspace/deribit_options.db"
echo ""
echo "🌐 访问地址: http://localhost:5000"
echo "⏹️  按 Ctrl+C 停止服务"
echo ""

python3 app.py
