#!/usr/bin/env python3
import json
import os
from datetime import datetime
from pathlib import Path
from urllib import parse, request

import yaml


def load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def get_paper_count(today: str) -> int:
    data_dir = Path(__file__).parent.parent / "data" / "papers"
    file_path = data_dir / f"{today}.json"
    if not file_path.exists():
        return 0
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return len(data)
        return 0
    except Exception:
        return 0


def resolve_site_url(config: dict) -> str:
    site_cfg = config.get("site", {})
    base = site_cfg.get("base_url") or ""
    if base:
        return base.rstrip("/") + "/"

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in repo:
        owner, name = repo.split("/", 1)
        return f"https://{owner}.github.io/{name}/"

    return ""


def send_serverchan(key: str, title: str, desp: str) -> None:
    url = f"https://sctapi.ftqq.com/{key}.send"
    payload = parse.urlencode({"title": title, "desp": desp}).encode("utf-8")
    req = request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded;charset=utf-8")
    try:
        with request.urlopen(req, timeout=10) as resp:
            resp.read()
    except Exception as e:
        print(f"[notify_wechat] send failed: {e}")


def main() -> None:
    key = os.environ.get("SERVERCHAN_KEY")
    if not key:
        print("[notify_wechat] SERVERCHAN_KEY not set, skip WeChat notification")
        return

    config = load_config()
    today = get_today_str()
    count = get_paper_count(today)
    site_url = resolve_site_url(config) or ""

    if count > 0:
        title = f"ArXiv Daily Digest {today} 已更新 ({count} 篇)"
        desp_lines = [
            f"今日共 {count} 篇符合筛选条件的论文。",
        ]
    else:
        title = f"ArXiv Daily Digest {today} 暂无新论文"
        desp_lines = [
            "今天没有符合筛选条件的论文。",
        ]

    if site_url:
        desp_lines.append("")
        desp_lines.append(f"点击查看：{site_url}")

    desp = "\n".join(desp_lines)
    send_serverchan(key, title, desp)
    print(f"[notify_wechat] sent notification for {today}, count={count}")


if __name__ == "__main__":
    main()
