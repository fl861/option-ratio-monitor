# 短长期比例近两年监测

追踪 BTC/ETH 期权短期(5天)与长期(26天)隐含波动率比例的历史趋势。

🔗 **在线访问**: https://[你的用户名].github.io/option-ratio-monitor/

## 数据概览

- **数据范围**: 2023-01-01 至 2026-02-25 (共1066天)
- **数据来源**: Deribit 历史期权数据
- **计算逻辑**: 短期(5-9天)Put IV / 长期(20-35天)Put IV

### 当前数据 (2026-02-25)

| 指标 | BTC | ETH |
|------|-----|-----|
| 短长期比例 | 0.60x | 0.12x |
| 历史分位 | 64.9% | - |
| 历史最高 | 10.05x | 44.77x |
| 历史最低 | 0.03x | 0.05x |
| 历史平均 | 0.63x | 0.77x |

## 部署到 GitHub Pages

### 方法1: 使用 GitHub Actions 自动部署

1. **创建 GitHub 仓库**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/[你的用户名]/option-ratio-monitor.git
   git push -u origin main
   ```

2. **启用 GitHub Pages**
   - 进入仓库 Settings → Pages
   - Source 选择 "GitHub Actions"
   - 推送代码后会自动部署

### 方法2: 手动部署

1. 进入仓库 Settings → Pages
2. Source 选择 "Deploy from a branch"
3. Branch 选择 "main"，文件夹选择 "/docs"
4. 保存后即可访问

## 项目结构

```
.
├── docs/                   # GitHub Pages 部署目录
│   ├── index.html         # 主页面
│   └── data.json          # 历史数据 (1066天)
├── .github/workflows/     # GitHub Actions 配置
│   └── deploy.yml
├── compute_data.py        # 数据预处理脚本
├── app.py                 # Flask 后端 (本地开发用)
└── README.md
```

## 本地开发

```bash
# 方式1: 使用 Flask 后端
cd /root/.openclaw/workspace/projects/option-ratio-monitor
python3 app.py
# 访问 http://localhost:5000

# 方式2: 直接使用静态文件
cd docs
python3 -m http.server 8000
# 访问 http://localhost:8000
```

## 技术栈

- 前端: HTML5 + Chart.js
- 数据: 预计算 JSON (51KB)
- 部署: GitHub Pages
- 模型: Kimi K2.5

## 数据来源

- `btc_put_2023_to_now.csv` - BTC期权历史数据
- `eth_put_2023_to_now.csv` - ETH期权历史数据

## License

MIT
