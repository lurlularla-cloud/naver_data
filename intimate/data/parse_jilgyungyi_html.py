"""
질경이 네이버 브랜드스토어 HTML 텍스트 정밀 분석 및 상품 상세 이미지 추출 스크립트.
"""
import sys
import io
import re
import json
import requests
from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

URL = "https://brand.naver.com/jilgyungyi/products/10364943970"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
}

r = requests.get(URL, headers=headers, timeout=10)
html = r.text

# 1. 상품명 찾기
name_match = re.search(r'"name":"([^"]+)"', html)
if name_match:
    print(f"매칭된 상품명: {name_match.group(1)}")

# 2. 가격 찾기
price_match = re.search(r'"discountedSalePrice":([0-9]+)', html)
orig_price_match = re.search(r'"salePrice":([0-9]+)', html)
if price_match:
    print(f"할인가: {price_match.group(1)}")
if orig_price_match:
    print(f"정상가: {orig_price_match.group(1)}")

# 3. 이미지 URL 모두 찾기
img_urls = re.findall(r'https://shop-phinf\.pstatic\.net/[^"\'\s>]+', html)
print(f"발견된 네이버 CDN 이미지 URL 수: {len(img_urls)}")

unique_imgs = []
for u in img_urls:
    clean_u = u.replace('\\"', '').replace('\\', '').split('?')[0]
    if clean_u not in unique_imgs:
        unique_imgs.append(clean_u)

print(f"고유 이미지 URL 수: {len(unique_imgs)}")
for i, u in enumerate(unique_imgs[:15]):
    print(f"[{i+1}] {u}")

# 유의미한 상세 이미지 다운로드
import os
os.makedirs("intimate/images/jilgyungyi", exist_ok=True)
downloaded = []
cnt = 1
for u in unique_imgs:
    try:
        im_r = requests.get(u, headers=headers, timeout=10)
        if len(im_r.content) > 30000:  # 30KB 이상 유의미한 이미지
            spath = f"intimate/images/jilgyungyi/jilgyungyi_detail_{cnt:02d}.jpg"
            with open(spath, "wb") as f:
                f.write(im_r.content)
            downloaded.append({"index": cnt, "url": u, "path": spath, "bytes": len(im_r.content)})
            print(f"다운로드 성공 [{cnt}]: {spath} ({len(im_r.content):,} bytes)")
            cnt += 1
            if cnt > 8:
                break
    except Exception as e:
        pass
