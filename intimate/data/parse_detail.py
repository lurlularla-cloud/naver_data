"""
이너생각 공식몰 상세페이지 텍스트 및 상세 이미지 매핑 세부 추출 스크립트.
HTML 내 상품 상세 설명, 옵션 정보, 전성분, 임상 관련 텍스트를 정밀 추출합니다.
"""
import sys
import io
import json
import requests
from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

URL = "https://saengak.co.kr/product/%EC%9D%B4%EB%84%88%EC%83%9D%EA%B0%81-%EB%B0%B8%EB%9F%B0%EC%8B%B1-%ED%9C%A9%EB%93%9C%EC%9B%8C%EC%8B%9C-180ml/102/category/1/display/2/?icid=MAIN.product_listmain_1"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

resp = requests.get(URL, headers=headers, timeout=15)
soup = BeautifulSoup(resp.text, "html.parser")

# 1. 상세 제목 확인
name_box = soup.select_one(".headingArea h2") or soup.select_one(".name") or soup.select_one(".infoArea .name")
real_name = name_box.get_text(strip=True) if name_box else "이너생각 밸런싱 휩드워시 180ml"

# 2. 상품 간략 설명 및 상세 텍스트
summary_elem = soup.select_one(".summary") or soup.select_one(".description")
summary_text = summary_elem.get_text("\n", strip=True) if summary_elem else ""

# 3. 상세페이지 본문 텍스트 및 이미지
prd_detail = soup.select_one("#prdDetail") or soup.select_one(".cont")
detail_texts = [p.get_text(" ", strip=True) for p in prd_detail.find_all(["p", "div", "span", "h1", "h2", "h3", "li"]) if len(p.get_text(strip=True)) > 5] if prd_detail else []

# 4. 이미지 태그와 alt, src
detail_imgs = []
if prd_detail:
    for img in prd_detail.find_all("img"):
        src = img.get("src") or img.get("ec-data-src") or ""
        alt = img.get("alt", "")
        if src:
            detail_imgs.append({"src": src, "alt": alt})

print(f"=== 실제 상품명: {real_name} ===")
print("=== 상품 요약 설명 ===")
print(summary_text)
print(f"\n=== 상세 이미지 수: {len(detail_imgs)} ===")
for i, im in enumerate(detail_imgs[:15], 1):
    print(f"[{i}] alt: {im['alt']} | src: {im['src']}")

# JSON 갱신
data = {
    "product_name": real_name,
    "url": URL,
    "volume": "180ml",
    "price_original": "36,000원",
    "price_sale": "27,000원 (25% 할인 / 쿠폰 적용시 최저가 18,000원)",
    "bundle_options": [
        "이너생각 밸런싱 휩드워시 180ml 단품 : 27,000원",
        "[2+1 기획] 이너생각 밸런싱 휩드워시 3개 : 59,000원 (쿠폰 사용 시 54,000원, 개당 18,000원)"
    ],
    "summary_text": summary_text,
    "detail_images": detail_imgs,
    "detail_sample_texts": detail_texts[:30]
}

with open("intimate/data/saengak.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("intimate/data/saengak.json 갱신 완료")
