# 📚 ArXiv Daily Digest

每日自动收集、AI 总结、推送你研究领域的 arXiv 新论文。

**零成本部署**：GitHub Actions + GitHub Pages，完全免费。

## ✨ 功能特点

- 🔍 **智能筛选**：根据关键词和研究方向自动筛选最相关论文
- 🤖 **AI 中文摘要**：DeepSeek 生成每篇论文的中文总结（核心贡献、方法、发现）
- 📱 **响应式界面**：美观的暗色主题，支持手机访问
- 📅 **历史归档**：自动保存每日论文，随时查阅
- ⚡ **全自动运行**：GitHub Actions 每天定时执行

## 🚀 5 分钟部署指南

### 1. Fork 本仓库

点击右上角 `Fork` 按钮。

### 2. 配置 DeepSeek API Key

1. 去 [DeepSeek 开放平台](https://platform.deepseek.com/) 注册账号
2. 创建 API Key（新用户赠送 500万 tokens）
3. 在你 Fork 的仓库中：Settings → Secrets and variables → Actions
4. 点击 `New repository secret`
5. Name: `DEEPSEEK_API_KEY`，Value: 你的 API Key

### 3. 启用 GitHub Pages

1. Settings → Pages
2. Source 选择 `GitHub Actions`

### 4. 自定义配置（可选）

编辑 `config.yaml` 文件：

```yaml
# 修改你关注的 arXiv 分类
categories:
  - cs.CV    # 计算机视觉
  - cs.CL    # NLP
  - cs.LG    # 机器学习

# 添加你的研究关键词
keywords:
  - diffusion
  - multimodal
  - design
  - generation
```

### 5. 手动触发首次运行

1. Actions → Daily ArXiv Digest
2. 点击 `Run workflow`

几分钟后访问 `https://你的用户名.github.io/arxiv-daily-digest/`

## 📁 项目结构

```
arxiv-daily-digest/
├── config.yaml              # 配置文件（关键词、分类等）
├── scripts/
│   ├── fetch_papers.py      # 抓取 arXiv 论文
│   ├── summarize.py         # DeepSeek AI 总结
│   ├── generate_pages.py    # 生成 HTML
│   └── run_all.py           # 本地运行入口
├── data/papers/             # 论文数据（JSON）
├── public/                  # 生成的网站
└── .github/workflows/       # 自动化配置
```

## 🖥️ 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export DEEPSEEK_API_KEY="your-api-key"

# 运行完整流程
python scripts/run_all.py

# 查看结果
open public/index.html
```

## 💰 成本估算

- **GitHub Actions**: 免费（公开仓库）
- **GitHub Pages**: 免费
- **DeepSeek API**: ~0.2 元/天（15篇论文）
  - 约 6 元/月，180 元/年

## 🛠️ 高级配置

### 修改运行时间

编辑 `.github/workflows/daily-update.yml`:

```yaml
on:
  schedule:
    # UTC 时间，北京时间 = UTC + 8
    - cron: '0 0 * * *'  # 北京时间 8:00
    # - cron: '0 22 * * *'  # 北京时间 6:00（次日）
```

### 添加微信推送

安装 [Server酱](https://sct.ftqq.com/)，获取 SendKey，添加到 Secrets，修改 workflow。

## 📄 License

MIT
