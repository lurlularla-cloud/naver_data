"""
비레시피(brecipe.com) 자사몰 여성청결제 상세페이지 스크래핑 및 이미지 다운로드 스크립트.
제품 기본 정보(제품명, 가격, 용량)를 추출하여 JSON 저장 및 상세페이지 상단 핵심 이미지를 다운로드합니다.
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

URL = "https://brecipe.com/product/detail.html?product_no=120&cate_no=80&display_group=1"
OUTPUT_JSON = "intimate/data/beautyrecipe.json"
IMAGE_DIR = "intimate/images/beautyrecipe"

os.makedirs("intimate/data", exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

print(f"[1/3] URL 요청 중: {URL}")
resp = requests.get(URL, headers=headers, timeout=15)
print(f"상태코드: {resp.status_code}, 크기: {len(resp.text):,} bytes")

soup = BeautifulSoup(resp.text, "html.parser")

# 1. 제품명 추출
name_elem = soup.select_one(".headingArea h2") or soup.select_one(".name") or soup.select_one(".prd_name") or soup.find("meta", property="og:title")
title = name_elem.get("content") if name_elem and name_elem.name == "meta" else (name_elem.get_text(strip=True) if name_elem else "")

# 2. 가격 및 옵션 추출
price_custom = soup.select_one("#span_product_price_custom") or soup.select_one(".price_custom")
price_sale = soup.select_one("#span_product_price_text") or soup.select_one(".price")
price_custom_txt = price_custom.get_text(strip=True) if price_custom else ""
price_sale_txt = price_sale.get_text(strip=True) if price_sale else ""

prices = {}
for tr in soup.select("table tr"):
    th = tr.find("th")
    td = tr.find("td")
    if th and td:
        k = th.get_text(strip=True)
        v = td.get_text(" ", strip=True)
        if any(w in k for w in ["소비자가", "판매가", "할인", "배송", "용량", "적립", "상품명"]):
            prices[k] = v

print(f"추출된 제품명: {title}")
print(f"추출된 가격/기본정보: {prices}")

# 3. 상세 이미지 추출
prd_detail = soup.select_one("#prdDetail") or soup.select_one(".cont") or soup
images = []
for img in prd_detail.find_all("img"):
    src = img.get("src") or img.get("ec-data-src") or img.get("data-src") or ""
    if src and not src.startswith("data:"):
        full_src = urljoin(URL, src)
        if any(ext in full_src.lower() for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]):
            if full_src not in [im['src'] for im in images]:
                images.append({"src": full_src, "alt": img.get("alt", "")})

print(f"상세 이미지 총 {len(images)}개 발견")

# 상위 이미지 다운로드 (핵심 컷 1~8개)
downloaded_images = []
count = 1
for img_info in images:
    img_url = img_info["src"]
    try:
        ext = os.path.splitext(img_url.split("?")[0])[1] or ".jpg"
        img_resp = requests.get(img_url, headers=headers, timeout=10)
        if len(img_resp.content) > 15000:  # 15KB 이상 유의미한 상세 이미지
            save_name = f"brecipe_img_{count:02d}{ext}"
            save_path = os.path.join(IMAGE_DIR, save_name)
            with open(save_path, "wb") as f:
                f.write(img_resp.content)
            downloaded_images.append({
                "index": count,
                "url": img_url,
                "local_path": save_path,
                "size_bytes": len(img_resp.content)
            })
            print(f"[{count:02d}] 이미지 다운로드 완료: {save_path} ({len(img_resp.content):,} bytes)")
            count += 1
            if count > 10:
                break
    except Exception as e:
        print(f"다운로드 실패 ({img_url}): {e}")

# JSON 데이터 저장
data_to_save = {
    "product_name": title,
    "url": URL,
    "prices": prices,
    "price_custom": price_custom_txt,
    "price_sale": price_sale_txt,
    "downloaded_images": downloaded_images
}

with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(data_to_save, f, ensure_ascii=False, indent=2)

print(f"JSON 저장 완료: {OUTPUT_JSON}")
