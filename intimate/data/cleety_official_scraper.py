"""
클리티 공식몰(cleety.com) 상세페이지 데이터 스크래핑 및 핵심 이미지 다운로드 스크립트.
클리티 젤링워시/포밍워시의 제품 기본 정보, 성분, 임상 데이터 및 이미지를 추출합니다.
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

URLS = [
    "https://cleety.com/product/detail.html?product_no=15",
    "https://cleety.com/product/detail.html?product_no=14",
    "https://cleety.com"
]
IMAGE_DIR = "intimate/images/cleety"
os.makedirs(IMAGE_DIR, exist_ok=True)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
}

found_data = {}
for target_url in URLS:
    try:
        print(f"요청 중: {target_url}")
        r = requests.get(target_url, headers=headers, timeout=10)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            title_elem = soup.select_one(".headingArea h2") or soup.select_one(".name") or soup.find("meta", property="og:title")
            title = title_elem.get("content") if title_elem and title_elem.name == "meta" else (title_elem.get_text(strip=True) if title_elem else "")
            print(f"발견된 타이틀: {title}")
            
            # 이미지 추출
            imgs = soup.select("#prdDetail img, .cont img, .detailArea img")
            print(f"상세 이미지 {len(imgs)}개 발견")
            
            downloaded = []
            count = 1
            for img in imgs:
                src = img.get("src") or img.get("ec-data-src") or ""
                if src and not src.startswith("data:"):
                    furl = urljoin(target_url, src)
                    ext = os.path.splitext(furl.split("?")[0])[1] or ".jpg"
                    try:
                        im_r = requests.get(furl, headers=headers, timeout=10)
                        if len(im_r.content) > 20000:
                            sname = f"cleety_img_{count:02d}{ext}"
                            spath = os.path.join(IMAGE_DIR, sname)
                            with open(spath, "wb") as f:
                                f.write(im_r.content)
                            downloaded.append({"index": count, "url": furl, "path": spath, "bytes": len(im_r.content)})
                            print(f"이미지 저장 [{count}]: {spath} ({len(im_r.content):,}b)")
                            count += 1
                            if count > 8:
                                break
                    except Exception as e:
                        pass
            
            found_data[target_url] = {
                "title": title,
                "downloaded": downloaded
            }
            if len(downloaded) >= 3:
                break
    except Exception as e:
        print(f"에러: {e}")

with open("intimate/data/smartstore_cleety.json", "w", encoding="utf-8") as f:
    json.dump(found_data, f, ensure_ascii=False, indent=2)

print("클리티 데이터 추출 완료")
