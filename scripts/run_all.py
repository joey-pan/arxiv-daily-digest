#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent


def run_script(name: str) -> bool:
    script_path = SCRIPTS_DIR / name
    print(f"\n{'='*50}")
    print(f"Running: {name}")
    print('='*50)
    
    result = subprocess.run([sys.executable, str(script_path)], cwd=SCRIPTS_DIR.parent)
    return result.returncode == 0


def main():
    steps = [
        ("fetch_papers.py", "Fetching papers from arXiv..."),
        ("summarize.py", "Generating AI summaries..."),
        ("generate_pages.py", "Building HTML pages...")
    ]
    
    for script, description in steps:
        print(f"\n🚀 {description}")
        if not run_script(script):
            print(f"❌ Failed at: {script}")
            sys.exit(1)
    
    print("\n" + "="*50)
    print("✅ All steps completed successfully!")
    print("📁 Output: public/index.html")
    print("="*50)


if __name__ == "__main__":
    main()
