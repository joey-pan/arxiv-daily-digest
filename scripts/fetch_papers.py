#!/usr/bin/env python3
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import json
import re
import yaml
from pathlib import Path


def load_config():
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_arxiv_papers(categories: list[str], max_results: int = 200) -> list[dict]:
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
    keywords = [kw.lower() for kw in config.get("keywords", [])]
    exclude = [ex.lower() for ex in config.get("exclude_keywords", [])]
    target_cats = set(config.get("categories", []))
    
    # 仅保留最近 24 小时内发布的论文
    now = datetime.utcnow()
    threshold = now - timedelta(days=1)
    
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
            # 只看最近 24 小时
            continue

        paper_cats = set(paper.get("categories", []))
        if not paper_cats.intersection(target_cats):
            continue
        
        text = (paper["title"] + " " + paper["abstract"]).lower()
        
        if any(ex in text for ex in exclude):
            continue
        
        if keywords and not any(kw in text for kw in keywords):
            continue
        
        paper["relevance_score"] = calculate_relevance(paper, config)
        filtered.append(paper)
    
    filtered.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    max_papers = config.get("max_papers_per_day", 15)
    return filtered[:max_papers]


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
    
    filtered = filter_papers(all_papers, config)
    print(f"Filtered to {len(filtered)} relevant papers")
    
    today = datetime.now().strftime("%Y-%m-%d")
    output_file = save_papers(filtered, today)
    
    return str(output_file)


if __name__ == "__main__":
    main()
