# -*- coding: utf-8 -*-
"""
change_password.py - 고전 디지털 도서관 접속 비밀번호 변경 자동화 도구

사용법:
    python change_password.py --password "새비밀번호" [--deploy] [--push]
    
옵션:
    --password, -p : 새로 지정할 열람 비밀번호
    --deploy       : 변경 후 Google Drive로 자동 배포 (deploy_to_gdrive.py 실행)
    --push         : 변경 후 Git 커밋 및 GitHub origin main으로 자동 푸시
"""
import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

# Support UTF-8 console output on Windows
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
AUTH_JS = BASE_DIR / "auth.js"
DEPLOY_SCRIPT = BASE_DIR / "deploy_to_gdrive.py"

def compute_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def update_auth_js(new_password: str) -> str:
    if not AUTH_JS.exists():
        raise FileNotFoundError(f"auth.js 파일을 찾을 수 없습니다: {AUTH_JS}")

    new_hash = compute_sha256(new_password)
    content = AUTH_JS.read_text(encoding="utf-8")

    # 1. Update hash pattern
    hash_pattern = r"(hash\s*:\s*['\"])[a-fA-F0-9]{64}(['\"])"
    if not re.search(hash_pattern, content):
        raise ValueError("auth.js 내에서 SHA-256 hash 설정 구문을 찾을 수 없습니다.")
    content = re.sub(hash_pattern, rf"\g<1>{new_hash}\g<2>", content)

    # 2. Update plainFallback pattern
    fallback_pattern = r"(plainFallback\s*:\s*['\"])[^'\"]*(['\"])"
    if re.search(fallback_pattern, content):
        content = re.sub(fallback_pattern, rf"\g<1>{new_password}\g<2>", content)

    # 3. Update top comment password mention
    comment_pattern = r"(Password Protection:\s*)[^\s\n\r]*(.*)"
    content = re.sub(comment_pattern, rf"\g<1>{new_password}\g<2>", content)

    AUTH_JS.write_text(content, encoding="utf-8")
    return new_hash

def main():
    parser = argparse.ArgumentParser(description="고전 디지털 도서관 비밀번호 변경 도구")
    parser.add_argument("--password", "-p", required=True, help="새로 설정할 접속 비밀번호")
    parser.add_argument("--deploy", action="store_true", help="Google Drive로 즉시 배포")
    parser.add_argument("--push", action="store_true", help="Git 커밋 및 GitHub origin main으로 푸시")
    args = parser.parse_args()

    new_pw = args.password.strip()
    if not new_pw:
        print("[오류] 비밀번호는 공백일 수 없습니다.")
        sys.exit(1)

    print("============================================================")
    print("  고전 디지털 도서관 비밀번호 변경 작업")
    print("============================================================")
    print(f"  새 비밀번호 : {new_pw}")
    
    new_hash = update_auth_js(new_pw)
    print(f"  SHA-256 해시 : {new_hash}")
    print(f"  [성공] auth.js 파일이 갱신되었습니다.")

    # Deploy to Google Drive
    if args.deploy and DEPLOY_SCRIPT.exists():
        print("\n------------------------------------------------------------")
        print("  Google Drive 배포 진행 중...")
        subprocess.run([sys.executable, str(DEPLOY_SCRIPT)], check=False)

    # Commit and Push to GitHub
    if args.push:
        print("\n------------------------------------------------------------")
        print("  Git 커밋 및 GitHub 푸시 진행 중...")
        subprocess.run(["git", "-C", str(BASE_DIR), "add", "auth.js"], check=False)
        commit_msg = f"security: 사이트 접속 비밀번호 변경 (SHA-256: {new_hash[:8]}...)"
        subprocess.run(["git", "-C", str(BASE_DIR), "commit", "-m", commit_msg], check=False)
        subprocess.run(["git", "-C", str(BASE_DIR), "push", "origin", "main"], check=False)

    print("\n============================================================")
    print("  비밀번호 변경 작업이 안전하게 완료되었습니다.")
    print("============================================================")

if __name__ == "__main__":
    main()
