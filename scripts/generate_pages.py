#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime
import yaml
import shutil


def load_config():
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


CATEGORY_NAMES = {
    "cs.CV": "计算机视觉",
    "cs.CL": "自然语言处理",
    "cs.LG": "机器学习",
    "cs.AI": "人工智能",
    "cs.GR": "图形学",
    "cs.HC": "人机交互",
    "cs.MM": "多媒体",
    "cs.RO": "机器人",
    "cs.NE": "神经与进化计算",
    "stat.ML": "统计机器学习"
}


def generate_paper_html(paper: dict) -> str:
    summary = paper.get("summary", {})
    title_zh = summary.get("title_zh", "")

    authors_str = ", ".join(paper["authors"][:5])
    if len(paper["authors"]) > 5:
        authors_str += f" 等 ({len(paper['authors'])} 位作者)"

    cat_name = CATEGORY_NAMES.get(paper.get("primary_category", ""), paper.get("primary_category", ""))
    score = paper.get("score")

    score_html = f'<span class="score-badge">相关性 {int(score)}/100</span>' if isinstance(score, (int, float)) else ""

    return f'''
    <article class="paper-card">
      <div class="paper-header">
        <div class="left-header">
          <span class="category-badge">{cat_name}</span>
          <span class="paper-id">{paper["id"]}</span>
        </div>
        {score_html}
      </div>
      <h3 class="paper-title">
        <a href="{paper["abs_url"]}" target="_blank">{paper["title"]}</a>
      </h3>
      {f'<p class="paper-title-zh">{title_zh}</p>' if title_zh else ''}
      <p class="paper-authors">{authors_str}</p>
      
      <div class="paper-summary">
        {f'<div class="summary-section"><strong>核心贡献:</strong> {summary.get("core_contribution", "")}</div>' if summary.get("core_contribution") else ''}
        {f'<div class="summary-section"><strong>方法:</strong> {summary.get("method", "")}</div>' if summary.get("method") else ''}
        {f'<div class="summary-section"><strong>关键发现:</strong> {summary.get("findings", "")}</div>' if summary.get("findings") else ''}
      </div>
      
      <details class="paper-abstract">
        <summary>查看原文摘要</summary>
        <p>{paper["abstract"]}</p>
      </details>
      
      <div class="paper-links">
        <a href="{paper["abs_url"]}" target="_blank" class="link-btn">📄 arXiv</a>
        <a href="{paper["pdf_url"]}" target="_blank" class="link-btn">📥 PDF</a>
      </div>
    </article>
    '''


def generate_index_html(papers: list[dict], date_str: str, config: dict) -> str:
    site_config = config.get("site", {})
    
    papers_html = "\n".join([generate_paper_html(p) for p in papers])
    
    cat_counts = {}
    for p in papers:
        cat = p.get("primary_category", "other")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    
    stats_html = " | ".join([f"{CATEGORY_NAMES.get(k, k)}: {v}" for k, v in sorted(cat_counts.items())])
    
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{site_config.get("title", "ArXiv Daily Digest")}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Noto+Sans+SC:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #0f0f0f;
            --card-bg: #1a1a1a;
            --card-border: #2a2a2a;
            --text: #e0e0e0;
            --text-muted: #888;
            --accent: #6366f1;
            --accent-hover: #818cf8;
            --success: #22c55e;
        }}
        
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        body {{
            font-family: 'Inter', 'Noto Sans SC', -apple-system, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            padding: 2rem;
            max-width: 900px;
            margin: 0 auto;
        }}
        
        header {{
            text-align: center;
            margin-bottom: 3rem;
            padding-bottom: 2rem;
            border-bottom: 1px solid var(--card-border);
        }}
        
        h1 {{ font-size: 2.5rem; margin-bottom: 0.5rem; }}
        
        .subtitle {{
            color: var(--text-muted);
            font-size: 1.1rem;
        }}
        
        .date {{
            font-size: 1.2rem;
            color: var(--accent);
            margin: 1rem 0;
        }}
        
        .stats {{
            font-size: 0.9rem;
            color: var(--text-muted);
        }}

        .archive-link-top {{
            margin-top: 1rem;
            font-size: 0.9rem;
        }}

        .archive-link-top a {{
            color: var(--accent);
            text-decoration: none;
        }}
        
        .paper-card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            transition: border-color 0.2s;
        }}
        
        .paper-card:hover {{
            border-color: var(--accent);
        }}
        
        .paper-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
            gap: 0.75rem;
        }}

        .left-header {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .category-badge {{
            background: var(--accent);
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
        }}
        
        .paper-id {{
            color: var(--text-muted);
            font-size: 0.85rem;
            font-family: monospace;
        }}

        .score-badge {{
            border-radius: 999px;
            border: 1px solid var(--accent);
            padding: 0.15rem 0.6rem;
            font-size: 0.8rem;
            color: var(--accent);
            background: rgba(99, 102, 241, 0.12);
        }}
        
        .paper-title {{
            font-size: 1.15rem;
            line-height: 1.4;
            margin-bottom: 0.5rem;
        }}
        
        .paper-title a {{
            color: var(--text);
            text-decoration: none;
        }}
        
        .paper-title a:hover {{
            color: var(--accent);
        }}
        
        .paper-title-zh {{
            color: var(--text-muted);
            font-size: 1rem;
            margin-bottom: 0.5rem;
        }}
        
        .paper-authors {{
            color: var(--text-muted);
            font-size: 0.9rem;
            margin-bottom: 1rem;
        }}
        
        .paper-summary {{
            background: rgba(99, 102, 241, 0.1);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
        }}
        
        .summary-section {{
            margin-bottom: 0.5rem;
        }}
        
        .summary-section:last-child {{
            margin-bottom: 0;
        }}
        
        .summary-section strong {{
            color: var(--accent);
        }}
        
        .paper-abstract {{
            margin-bottom: 1rem;
        }}
        
        .paper-abstract summary {{
            cursor: pointer;
            color: var(--text-muted);
            font-size: 0.9rem;
        }}
        
        .paper-abstract p {{
            margin-top: 0.75rem;
            font-size: 0.9rem;
            color: var(--text-muted);
        }}
        
        .paper-links {{
            display: flex;
            gap: 0.75rem;
        }}
        
        .link-btn {{
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            padding: 0.5rem 1rem;
            background: var(--card-border);
            color: var(--text);
            text-decoration: none;
            border-radius: 6px;
            font-size: 0.85rem;
            transition: background 0.2s;
        }}
        
        .link-btn:hover {{
            background: var(--accent);
        }}
        
        footer {{
            text-align: center;
            padding-top: 2rem;
            margin-top: 2rem;
            border-top: 1px solid var(--card-border);
            color: var(--text-muted);
            font-size: 0.9rem;
        }}
        
        footer a {{
            color: var(--accent);
            text-decoration: none;
        }}
        
        @media (max-width: 600px) {{
            body {{ padding: 1rem; }}
            h1 {{ font-size: 1.75rem; }}
            .paper-card {{ padding: 1rem; }}
        }}
    </style>
</head>
<body>
    <header>
        <h1>{site_config.get("title", "📚 ArXiv Daily Digest")}</h1>
        <p class="subtitle">{site_config.get("description", "每日论文精选")}</p>
        <p class="date">📅 {date_str}</p>
        <p class="stats">共 {len(papers)} 篇论文 | {stats_html}</p>
        <p class="archive-link-top"><a href="archive.html">查看历史归档 →</a></p>
    </header>
    
    <main>
        {papers_html}
    </main>
    
    <footer>
        <p>由 <a href="https://github.com">ArXiv Daily Digest</a> 自动生成</p>
        <p>数据来源: <a href="https://arxiv.org">arXiv.org</a> | AI 总结: DeepSeek</p>
    </footer>
</body>
</html>'''


def generate_archive_html(all_dates: list[str], config: dict) -> str:
    site_config = config.get("site", {})
    
    dates_html = "\n".join([
        f'<a href="{d}.html" class="archive-link">{d}</a>'
        for d in sorted(all_dates, reverse=True)
    ])
    
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>归档 - {site_config.get("title", "ArXiv Daily Digest")}</title>
    <style>
        :root {{
            --bg: #0f0f0f;
            --card-bg: #1a1a1a;
            --card-border: #2a2a2a;
            --text: #e0e0e0;
            --text-muted: #888;
            --accent: #6366f1;
        }}
        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            background: var(--bg);
            color: var(--text);
            padding: 2rem;
            max-width: 600px;
            margin: 0 auto;
        }}
        h1 {{ margin-bottom: 2rem; }}
        .archive-link {{
            display: block;
            padding: 1rem;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 8px;
            margin-bottom: 0.5rem;
            color: var(--text);
            text-decoration: none;
        }}
        .archive-link:hover {{
            border-color: var(--accent);
        }}
        .back {{ margin-bottom: 2rem; }}
        .back a {{ color: var(--accent); }}
    </style>
</head>
<body>
    <p class="back"><a href="index.html">← 返回今日</a></p>
    <h1>📚 历史归档</h1>
    {dates_html}
</body>
</html>'''


def main():
    config = load_config()
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data" / "papers"
    output_dir = project_root / "public"
    
    output_dir.mkdir(exist_ok=True)
    
    today = datetime.now().strftime("%Y-%m-%d")
    today_file = data_dir / f"{today}.json"
    
    if today_file.exists():
        with open(today_file, "r", encoding="utf-8") as f:
            papers = json.load(f)
        
        index_html = generate_index_html(papers, today, config)
        (output_dir / "index.html").write_text(index_html, encoding="utf-8")
        (output_dir / f"{today}.html").write_text(index_html, encoding="utf-8")
        print(f"Generated index.html with {len(papers)} papers")
    
    all_dates = [f.stem for f in data_dir.glob("*.json")]
    archive_html = generate_archive_html(all_dates, config)
    (output_dir / "archive.html").write_text(archive_html, encoding="utf-8")
    print(f"Generated archive.html with {len(all_dates)} dates")


if __name__ == "__main__":
    main()
