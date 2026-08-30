"""
클리티 제품 상세 본문 영역(내부 텍스트/상세 컷) 다운로드 및 분석 스크립트.
"""
import sys
import io
import os
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

URL = "https://cleety.com/product/detail.html?product_no=14"
IMAGE_DIR = "intimate/images/cleety"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
}

r = requests.get(URL, headers=headers, timeout=10)
soup = BeautifulSoup(r.text, "html.parser")

detail = soup.select_one("#prdDetail") or soup

imgs = detail.find_all("img")
print(f"상세 영역 img 태그 수: {len(imgs)}")

detail_downloaded = []
idx = 1
for img in imgs:
    src = img.get("src") or img.get("ec-data-src") or ""
    if src and not src.startswith("data:"):
        furl = urljoin(URL, src)
        ext = os.path.splitext(furl.split("?")[0])[1] or ".jpg"
        try:
            im_r = requests.get(furl, headers=headers, timeout=10)
            if len(im_r.content) > 10000:
                sname = f"cleety_detail_{idx:02d}{ext}"
                spath = os.path.join(IMAGE_DIR, sname)
                with open(spath, "wb") as f:
                    f.write(im_r.content)
                detail_downloaded.append({"index": idx, "url": furl, "path": spath, "bytes": len(im_r.content)})
                print(f"[{idx}] 다운로드: {sname} ({len(im_r.content):,}b)")
                idx += 1
                if idx > 12:
                    break
        except Exception as e:
            pass

print("상세 다운로드 완료")
