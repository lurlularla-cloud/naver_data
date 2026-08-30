"""
네이버 스마트스토어 클리티(cleety) 여성청결제 상세페이지 스크래핑 및 이미지 다운로드 스크립트.
제품 기본 정보(제품명, 가격, 옵션, 텍스트)를 추출하여 JSON 저장 및 상세페이지 상단 핵심 이미지를 다운로드합니다.
"""
import sys
import io
import os
import re
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

URL = "https://smartstore.naver.com/cleety/products/10133225070"
OUTPUT_JSON = "intimate/data/smartstore_cleety.json"
IMAGE_DIR = "intimate/images/cleety"

os.makedirs("intimate/data", exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
}

print(f"[1/3] 스마트스토어 요청 중: {URL}")
resp = requests.get(URL, headers=headers, timeout=15)
print(f"상태코드: {resp.status_code}, 크기: {len(resp.text):,} bytes")

soup = BeautifulSoup(resp.text, "html.parser")

# 1. 제품명 및 기본 가격
title_elem = soup.select_one("h3._22kNQuEXmb") or soup.select_one(".prd_title") or soup.find("meta", property="og:title")
title = title_elem.get("content") if title_elem and title_elem.name == "meta" else (title_elem.get_text(strip=True) if title_elem else "")

# window.__PRELOADED_STATE__ 파싱 시도
product_data = {}
script_match = re.search(r"window\.__PRELOADED_STATE__\s*=\s*({.+?});?</script>", resp.text)
if script_match:
    try:
        preloaded = json.loads(script_match.group(1))
        # 상품 상세 정보 추출
        product_detail = preloaded.get("product", {}).get("A", {}) or preloaded.get("simpleProduct", {})
        if product_detail:
            title = product_detail.get("name", title)
            prices_info = {
                "price": product_detail.get("price"),
                "discountedSalePrice": product_detail.get("discountedSalePrice"),
                "discountRate": product_detail.get("discountRate"),
                "benefits": product_detail.get("benefitsView", {})
            }
            product_data["preloaded_prices"] = prices_info
    except Exception as e:
        print(f"PRELOADED_STATE 파싱 예외: {e}")

print(f"추출된 제품명: {title}")

# 2. 상세페이지 이미지 추출 (.se-main-container or general)
images = []
se_container = soup.select_one(".se-main-container") or soup.select_one("#content") or soup
for img in se_container.find_all("img"):
    src = img.get("src") or img.get("data-src") or img.get("data-original") or ""
    if src and not src.startswith("data:"):
        full_src = urljoin(URL, src)
        # 스마트스토어 이미지 최적화 파라미터 처리
        clean_url = full_src.split("?")[0] if "type=" in full_src else full_src
        if clean_url not in [im['src'] for im in images]:
            images.append({"src": clean_url, "alt": img.get("alt", "")})

print(f"상세 이미지 총 {len(images)}개 발견")

# 상위 이미지 다운로드 (핵심 컷 1~8개)
downloaded_images = []
count = 1
for img_info in images:
    img_url = img_info["src"]
    try:
        ext = os.path.splitext(img_url.split("?")[0])[1] or ".jpg"
        if not ext.lower() in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
            ext = ".jpg"
        img_resp = requests.get(img_url, headers=headers, timeout=10)
        if len(img_resp.content) > 20000:  # 20KB 이상 유의미한 상세 이미지
            save_name = f"cleety_img_{count:02d}{ext}"
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
            if count > 8:
                break
    except Exception as e:
        print(f"다운로드 실패 ({img_url}): {e}")

# JSON 데이터 저장
data_to_save = {
    "product_name": title,
    "url": URL,
    "product_data": product_data,
    "downloaded_images": downloaded_images
}

with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(data_to_save, f, ensure_ascii=False, indent=2)

print(f"JSON 저장 완료: {OUTPUT_JSON}")
