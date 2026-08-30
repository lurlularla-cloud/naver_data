"""
이너생각 공식몰 상세페이지 본문 이미지 전체 다운로드 스크립트.
전체 상세 이미지를 순서대로 다운로드하여 완벽한 분석을 수행합니다.
"""
import sys
import io
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

URL = "https://saengak.co.kr/product/%EC%9D%B4%EB%84%88%EC%83%9D%EA%B0%81-%EB%B0%B8%EB%9F%B0%EC%8B%B1-%ED%9C%A9%EB%93%9C%EC%9B%8C%EC%8B%9C-180ml/102/category/1/display/2/?icid=MAIN.product_listmain_1"
IMAGE_DIR = "intimate/images/saengak"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
}

resp = requests.get(URL, headers=headers, timeout=15)
soup = BeautifulSoup(resp.text, "html.parser")
prd_detail = soup.select_one("#prdDetail") or soup

imgs = prd_detail.find_all("img")
print(f"발견된 이미지 태그: {len(imgs)}개")

count = 1
for img in imgs:
    src = img.get("src") or img.get("ec-data-src") or ""
    if not src or src.startswith("data:"):
        continue
    full_url = urljoin(URL, src)
    ext = os.path.splitext(full_url.split("?")[0])[1] or ".jpg"
    if ext.lower() not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        continue
    
    try:
        r = requests.get(full_url, headers=headers, timeout=10)
        if len(r.content) > 5000:  # 유의미한 이미지
            save_name = f"saengak_detail_{count:02d}{ext}"
            save_path = os.path.join(IMAGE_DIR, save_name)
            with open(save_path, "wb") as f:
                f.write(r.content)
            print(f"[{count:02d}] {save_name} ({len(r.content):,}b) <- {full_url}")
            count += 1
    except Exception as e:
        print(f"다운로드 실패: {e}")
