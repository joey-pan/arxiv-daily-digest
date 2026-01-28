#!/usr/bin/env python3
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import json
import re
import os
from pathlib import Path

import yaml

try:
    from openai import OpenAI
except ImportError:  # 本地环境缺少 openai 包时自动安装
    import subprocess
    subprocess.check_call(["pip", "install", "openai"])
    from openai import OpenAI


def load_config():
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_arxiv_papers(categories: list[str], max_results: int = 300) -> list[dict]:
    # NOTE: On CI environments (including GitHub Actions), arXiv may return HTTP 406
    # if no explicit User-Agent is provided. We build a Request with headers to avoid that.
    base_url = "http://export.arxiv.org/api/query?"
    
    cat_query = " OR ".join([f"cat:{cat}" for cat in categories])
    
    yesterday = datetime.now() - timedelta(days=2)
    date_str = yesterday.strftime("%Y%m%d")
    
    params = {
        "search_query": f"({cat_query})",
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending"
    }
    
    url = base_url + urllib.parse.urlencode(params)

    headers = {
        "User-Agent": "arxiv-daily-digest/0.1 (+https://github.com/joey-pan/arxiv-daily-digest)",
        "Accept": "application/atom+xml,application/xml"
    }

    req = urllib.request.Request(url, headers=headers)

    with urllib.request.urlopen(req, timeout=30) as response:
        xml_data = response.read().decode("utf-8")
    
    return parse_arxiv_response(xml_data)


def parse_arxiv_response(xml_data: str) -> list[dict]:
    root = ET.fromstring(xml_data)
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    
    papers = []
    for entry in root.findall("atom:entry", ns):
        paper = {
            "id": extract_arxiv_id(entry.find("atom:id", ns).text),
            "title": clean_text(entry.find("atom:title", ns).text),
            "abstract": clean_text(entry.find("atom:summary", ns).text),
            "authors": [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)],
            "published": entry.find("atom:published", ns).text[:10],
            "updated": entry.find("atom:updated", ns).text[:10],
            "categories": [c.get("term") for c in entry.findall("atom:category", ns)],
            "pdf_url": f"https://arxiv.org/pdf/{extract_arxiv_id(entry.find('atom:id', ns).text)}.pdf",
            "abs_url": f"https://arxiv.org/abs/{extract_arxiv_id(entry.find('atom:id', ns).text)}"
        }
        
        primary_cat = entry.find("arxiv:primary_category", ns)
        if primary_cat is not None:
            paper["primary_category"] = primary_cat.get("term")
        else:
            paper["primary_category"] = paper["categories"][0] if paper["categories"] else ""
            
        papers.append(paper)
    
    return papers


def extract_arxiv_id(url: str) -> str:
    match = re.search(r"(\d{4}\.\d{4,5})(v\d+)?$", url)
    return match.group(1) if match else url.split("/")[-1]


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def calculate_relevance(paper: dict, config: dict) -> float:
    score = 0.0
    weights = config.get("relevance_weights", {})
    keywords = [kw.lower() for kw in config.get("keywords", [])]
    
    title_lower = paper["title"].lower()
    abstract_lower = paper["abstract"].lower()
    
    for kw in keywords:
        if kw in title_lower:
            score += weights.get("keyword_in_title", 3.0)
        if kw in abstract_lower:
            score += weights.get("keyword_in_abstract", 1.0)
    
    target_categories = config.get("categories", [])
    if paper.get("primary_category") in target_categories:
        score += weights.get("primary_category", 2.0)
    
    return score


def filter_papers(papers: list[dict], config: dict) -> list[dict]:
    """基础时间过滤：仅保留最近 30 天内的论文。

    不再在这里做关键词/领域筛选，交给 DeepSeek 打分决定相关性，
    这样第一次运行会对抓取到的 300 篇全部打分，之后只对新论文打分。
    """

    # 仅保留最近 30 天内发布的论文
    now = datetime.utcnow()
    threshold = now - timedelta(days=30)

    filtered = []
    for paper in papers:
        # arXiv published 字段格式为 YYYY-MM-DD
        pub_str = paper.get("published")
        try:
            pub_dt = datetime.strptime(pub_str, "%Y-%m-%d")
        except Exception:
            # 无法解析发布日期的论文直接跳过
            continue

        if pub_dt < threshold:
            # 只看最近 30 天
            continue

        filtered.append(paper)

    # 为无 DeepSeek 打分时的回退行为提供一个合理顺序：按发布时间降序
    filtered.sort(key=lambda x: x.get("published", ""), reverse=True)

    return filtered


def load_seen_ids() -> set[str]:
    """载入已推送过的论文 ID 集合，用于避免重复推荐。"""
    path = Path(__file__).parent.parent / "data" / "seen_ids.json"
    if not path.exists():
        return set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return set(str(x) for x in data)
    except Exception:
        return set()
    return set()


def save_seen_ids(seen: set[str]) -> None:
    path = Path(__file__).parent.parent / "data" / "seen_ids.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, ensure_ascii=False, indent=2)


def select_unseen(papers: list[dict], seen: set[str], limit: int) -> tuple[list[dict], set[str]]:
    """从已排序论文列表中选出未推送过的前 limit 篇。"""
    selected: list[dict] = []
    new_seen: set[str] = set()

    for paper in papers:
        pid = paper.get("id")
        if not pid:
            continue
        if pid in seen:
            continue
        selected.append(paper)
        new_seen.add(pid)
        if len(selected) >= limit:
            break

    return selected, new_seen


def load_scores() -> dict[str, int]:
    """载入 DeepSeek 打分缓存，避免重复打分。"""
    path = Path(__file__).parent.parent / "data" / "scores.json"
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            # 统一转成 int 分数
            return {str(k): int(v) for k, v in data.items()}
    except Exception:
        return {}
    return {}


def save_scores(scores: dict[str, int]) -> None:
    path = Path(__file__).parent.parent / "data" / "scores.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False, indent=2)


RANK_PROMPT_TEMPLATE = """你是一个论文筛选与打分助手，请基于以下信息判断论文是否\"高度符合\"用户的兴趣。
请严格遵循下面的兴趣画像：
{profile}
打分标准（0-100 分）：
- 80-100：与图形/视觉设计、布局生成、text-to-image 等紧密相关，方法实用、可用于构建工具或系统。
- 40-79：与图像生成、多模态、视觉美学等相关，但与图形设计/布局生成的直接联系较弱或不清晰。
- 0-39：医学影像或与图形设计无关的方向（如纯医学、临床、MRI/CT、肿瘤等）应尽量给低分。
请只根据标题和摘要进行判断。
论文标题: {title}
论文摘要:
{abstract}
现在请**只输出一个 JSON 对象**，不要输出任何解释文字、不要使用代码块、不要添加额外内容。
JSON 格式严格如下（注意 score 必须是 0 到 100 之间的整数）：
{{
  "score": 0-100
}}"""


def create_ds_client(config: dict):
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("[rank] DEEPSEEK_API_KEY not set, skip DeepSeek ranking")
        return None

    ds = config.get("deepseek", {})
    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )


def score_with_deepseek(client: OpenAI, paper: dict, config: dict):
    profile = config.get("preference", {}).get("profile") or ""
    prompt = RANK_PROMPT_TEMPLATE.format(
        profile=profile,
        title=paper.get("title", ""),
        abstract=paper.get("abstract", ""),
    )

    ds_cfg = config.get("deepseek", {})
    try:
        resp = client.chat.completions.create(
            model=ds_cfg.get("model", "deepseek-chat"),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=64,
            temperature=0.0,
        )
        content = resp.choices[0].message.content.strip()

        # 处理可能的代码块包裹和多余说明文本，只保留第一个 JSON 对象
        if content.startswith("```"):
            # ```json ... ``` 或 ``` ... ```
            parts = content.split("```", 2)
            if len(parts) >= 2:
                content = parts[1]
            content = content.lstrip()
            if content.lower().startswith("json"):
                # 去掉前缀 json
                content = content.split("\n", 1)[1] if "\n" in content else ""

        # 抽取第一个 {...} 作为 JSON
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_str = content[start : end + 1]
        else:
            json_str = content

        data = json.loads(json_str)
        score = int(data.get("score", 0))
        # clamp
        score = max(0, min(100, score))
        return score
    except Exception as e:
        print(f"[rank] DeepSeek scoring failed for {paper.get('id')}: {e}")
        return None


def save_papers(papers: list[dict], date_str: str):
    data_dir = Path(__file__).parent.parent / "data" / "papers"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = data_dir / f"{date_str}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(papers, f, ensure_ascii=False, indent=2)
    
    print(f"Saved {len(papers)} papers to {output_file}")
    return output_file


def main():
    config = load_config()
    
    print(f"Fetching papers from categories: {config['categories']}")
    all_papers = fetch_arxiv_papers(config["categories"])
    print(f"Fetched {len(all_papers)} papers from arXiv")

    base_filtered = filter_papers(all_papers, config)
    print(f"Filtered to {len(base_filtered)} candidates in last 30 days")

    # 加载历史打分和已推送 ID
    scores = load_scores()
    seen = load_seen_ids()
    limit = config.get("max_papers_per_day", 5)

    client = create_ds_client(config)

    # 仅对未打分论文调用 DeepSeek 打分
    if client is not None:
        new_scores = 0
        for paper in base_filtered:
            pid = paper.get("id")
            if not pid or pid in scores:
                continue
            s = score_with_deepseek(client, paper, config)
            if s is not None:
                scores[pid] = s
                new_scores += 1
        if new_scores:
            print(f"Scored {new_scores} new papers with DeepSeek")
            save_scores(scores)
        else:
            print("No new papers to score with DeepSeek")
    else:
        print("DeepSeek client not available, fallback to heuristic relevance only")

    # 根据 DeepSeek 分数（或启发式分数）排序
    def paper_score(p: dict) -> float:
        pid = p.get("id")
        if pid in scores:
            return float(scores[pid])
        # 没有 DeepSeek 分数时退回到 0，由 filter_papers 的时间排序提供基础顺序
        return 0.0

    ranked = sorted(base_filtered, key=paper_score, reverse=True)

    # 从排好序的列表中选出未推送过的 top-K
    today_papers, new_seen = select_unseen(ranked, seen, limit)
    print(f"Selected {len(today_papers)} unseen papers (limit={limit})")

    today = datetime.now().strftime("%Y-%m-%d")
    output_file = save_papers(today_papers, today)

    if new_seen:
        updated_seen = seen.union(new_seen)
        save_seen_ids(updated_seen)
        print(f"Updated seen_ids.json with {len(new_seen)} new ids (total={len(updated_seen)})")
    else:
        print("No new unseen papers to add to seen_ids.json")

    return str(output_file)


if __name__ == "__main__":
    main()
