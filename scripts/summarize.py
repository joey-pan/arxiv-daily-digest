#!/usr/bin/env python3
import json
import os
import time
from pathlib import Path
from datetime import datetime
import yaml

try:
    from openai import OpenAI
except ImportError:
    print("Installing openai package...")
    import subprocess
    subprocess.check_call(["pip", "install", "openai"])
    from openai import OpenAI


def load_config():
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_client(config: dict) -> OpenAI:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY environment variable not set")
    
    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )


SUMMARY_PROMPT = """你是一个学术论文总结助手。请用中文总结以下论文,包含:

1. **标题翻译**: 将英文标题翻译成中文
2. **核心贡献**: 用1-2句话概括论文的主要贡献
3. **方法概述**: 简要描述所用方法(3-4句)
4. **关键发现**: 主要实验结果或结论

论文标题: {title}

论文摘要:
{abstract}

请用以下JSON格式返回(确保是有效JSON):
{{
    "title_zh": "中文标题",
    "core_contribution": "核心贡献描述",
    "method": "方法概述",
    "findings": "关键发现"
}}"""


def summarize_paper(client: OpenAI, paper: dict, config: dict) -> dict:
    ds_config = config.get("deepseek", {})
    
    prompt = SUMMARY_PROMPT.format(
        title=paper["title"],
        abstract=paper["abstract"]
    )
    
    try:
        response = client.chat.completions.create(
            model=ds_config.get("model", "deepseek-chat"),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=ds_config.get("max_tokens", 500),
            temperature=ds_config.get("temperature", 0.3)
        )
        
        content = response.choices[0].message.content.strip()
        
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        summary = json.loads(content)
        return summary
        
    except json.JSONDecodeError:
        return {
            "title_zh": paper["title"],
            "core_contribution": "摘要生成失败",
            "method": "",
            "findings": ""
        }
    except Exception as e:
        print(f"Error summarizing paper {paper['id']}: {e}")
        return None


def process_papers(papers_file: str):
    config = load_config()
    
    with open(papers_file, "r", encoding="utf-8") as f:
        papers = json.load(f)
    
    if not papers:
        print("No papers to summarize")
        return
    
    client = create_client(config)
    
    for i, paper in enumerate(papers):
        if "summary" in paper and paper["summary"]:
            print(f"Skipping already summarized: {paper['id']}")
            continue
            
        print(f"[{i+1}/{len(papers)}] Summarizing: {paper['title'][:60]}...")
        
        summary = summarize_paper(client, paper, config)
        if summary:
            paper["summary"] = summary
        
        time.sleep(0.5)
    
    with open(papers_file, "w", encoding="utf-8") as f:
        json.dump(papers, f, ensure_ascii=False, indent=2)
    
    print(f"Summarization complete. Updated {papers_file}")


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    papers_file = Path(__file__).parent.parent / "data" / "papers" / f"{today}.json"
    
    if not papers_file.exists():
        print(f"Papers file not found: {papers_file}")
        print("Run fetch_papers.py first")
        return
    
    process_papers(str(papers_file))


if __name__ == "__main__":
    main()
