"""
이너생각 공식몰 상세페이지 데이터 스크래핑 및 이미지 다운로드 스크립트.
제품 기본 정보(제품명, 가격, 옵션, 상세 이미지 URL)를 추출하여 JSON 저장 및 이미지를 다운로드합니다.
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

URL = "https://saengak.co.kr/product/%EC%9D%B4%EB%84%88%EC%83%9D%EA%B0%81-%EB%B0%B8%EB%9F%B0%EC%8B%B1-%ED%9C%A9%EB%93%9C%EC%9B%8C%EC%8B%9C-180ml/102/category/1/display/2/?icid=MAIN.product_listmain_1"
OUTPUT_JSON = "intimate/data/saengak.json"
IMAGE_DIR = "intimate/images/saengak"

os.makedirs("intimate/data", exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
}

print(f"[1/4] URL 요청 중: {URL}")
resp = requests.get(URL, headers=headers, timeout=15)
print(f"상태코드: {resp.status_code}, 크기: {len(resp.text):,} bytes")

soup = BeautifulSoup(resp.text, "html.parser")

# 기본 정보 추출
# 1. 제품명
name_elem = soup.select_one(".name") or soup.select_one(".prd_name") or soup.select_one("h2") or soup.find("meta", property="og:title")
title = name_elem.get("content") if name_elem and name_elem.name == "meta" else (name_elem.get_text(strip=True) if name_elem else "")

# 2. 가격
price_elems = soup.select(".price, .price_custom, .product_price, td")
prices = {}
for p in price_elems:
    txt = p.get_text(strip=True)
    if "원" in txt or "KRW" in txt:
        # parent or label check
        parent = p.find_parent("tr")
        if parent:
            th = parent.find("th")
            if th:
                prices[th.get_text(strip=True)] = txt

# 3. 상세페이지 본문 이미지
detail_container = soup.select_one("#prdDetail") or soup.select_one(".detail_area") or soup.select_one(".cont") or soup.select_one(".detail-area") or soup
images = []
for img in detail_container.find_all("img"):
    src = img.get("src") or img.get("ec-data-src") or img.get("data-src") or ""
    if src and not src.startswith("data:"):
        full_src = urljoin(URL, src)
        if any(ext in full_src.lower() for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]):
            if full_src not in [im['src'] for im in images]:
                images.append({"src": full_src, "alt": img.get("alt", "")})

print(f"추출된 제품명: {title}")
print(f"추출된 가격정보: {prices}")
print(f"상세 이미지 총 {len(images)}개 발견")

# 상위 이미지 다운로드 (핵심 컷 1~6개)
downloaded_images = []
for idx, img_info in enumerate(images[:10], 1):
    img_url = img_info["src"]
    # 작은 아이콘이나 불필요한 배너 필터링
    try:
        ext = os.path.splitext(img_url.split("?")[0])[1] or ".jpg"
        img_resp = requests.get(img_url, headers=headers, timeout=10)
        if len(img_resp.content) > 10000:  # 10KB 이상만 의미있는 상세 이미지로 취급
            save_name = f"saengak_img_{idx:02d}{ext}"
            save_path = os.path.join(IMAGE_DIR, save_name)
            with open(save_path, "wb") as f:
                f.write(img_resp.content)
            downloaded_images.append({
                "index": idx,
                "url": img_url,
                "local_path": save_path,
                "size_bytes": len(img_resp.content)
            })
            print(f"이미지 다운로드 완료 [{idx}]: {save_path} ({len(img_resp.content):,} bytes)")
    except Exception as e:
        print(f"이미지 다운로드 실패 [{idx}] {img_url}: {e}")

# JSON 데이터 저장
data_to_save = {
    "url": URL,
    "product_name": title,
    "prices": prices,
    "all_image_urls": [im["src"] for im in images],
    "downloaded_images": downloaded_images
}

with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(data_to_save, f, ensure_ascii=False, indent=2)

print(f"JSON 저장 완료: {OUTPUT_JSON}")
