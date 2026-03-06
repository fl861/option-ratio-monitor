#!/bin/bash
# 部署到 GitHub Pages 的初始化脚本

echo "========================================="
echo "短长期比例监测网站 - GitHub 部署脚本"
echo "========================================="
echo ""

# 检查是否已经初始化 git
if [ ! -d ".git" ]; then
    echo "初始化 Git 仓库..."
    git init
    git add .
    git commit -m "Initial commit: 短长期比例监测网站"
    echo "✓ Git 仓库已初始化"
else
    echo "✓ Git 仓库已存在"
fi

echo ""
echo "接下来请执行以下步骤:"
echo ""
echo "1. 在 GitHub 创建新仓库: https://github.com/new"
echo "   仓库名: option-ratio-monitor"
echo ""
echo "2. 运行以下命令推送代码:"
echo "   git branch -M main"
echo "   git remote add origin https://github.com/[你的用户名]/option-ratio-monitor.git"
echo "   git push -u origin main"
echo ""
echo "3. 启用 GitHub Pages:"
echo "   - 进入仓库 Settings → Pages"
echo "   - Source 选择 'GitHub Actions' (自动部署)"
echo "   - 或选择 'Deploy from a branch' → Branch: main, Folder: /docs"
echo ""
echo "4. 访问网站:"
echo "   https://[你的用户名].github.io/option-ratio-monitor/"
echo ""
