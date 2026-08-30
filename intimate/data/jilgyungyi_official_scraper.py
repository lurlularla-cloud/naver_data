"""
질경이 공식 쇼핑몰(jilgyungyi.com) 데일리 에코아 워시 및 대표 여성청결제 데이터 크롤링 스크립트.
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
    "https://jilgyungyi.com/product/detail.html?product_no=187",
    "https://jilgyungyi.com/product/detail.html?product_no=211",
    "https://jilgyungyi.com/product/detail.html?product_no=14",
    "https://jilgyungyi.com/category/%EC%9B%8C%EC%8B%9C/42/"
]
IMAGE_DIR = "intimate/images/jilgyungyi"
os.makedirs(IMAGE_DIR, exist_ok=True)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
}

found_info = {}
for u in URLS:
    try:
        print(f"질경이 공식몰 요청: {u}")
        r = requests.get(u, headers=headers, timeout=10)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            name_elem = soup.select_one(".headingArea h2") or soup.select_one(".name") or soup.find("meta", property="og:title")
            name = name_elem.get("content") if name_elem and name_elem.name == "meta" else (name_elem.get_text(strip=True) if name_elem else "")
            print(f"발견된 상품명: {name}")
            
            # 상세 이미지 다운로드
            imgs = soup.select("#prdDetail img, .detailArea img, .cont img")
            print(f"상세 이미지 {len(imgs)}개")
            
            downloaded = []
            cnt = 1
            for img in imgs:
                src = img.get("src") or img.get("ec-data-src") or ""
                if src and not src.startswith("data:"):
                    furl = urljoin(u, src)
                    ext = os.path.splitext(furl.split("?")[0])[1] or ".jpg"
                    try:
                        im_r = requests.get(furl, headers=headers, timeout=10)
                        if len(im_r.content) > 15000:
                            sname = f"jilgyungyi_img_{cnt:02d}{ext}"
                            spath = os.path.join(IMAGE_DIR, sname)
                            with open(spath, "wb") as f:
                                f.write(im_r.content)
                            downloaded.append({"index": cnt, "url": furl, "path": spath, "bytes": len(im_r.content)})
                            print(f"[{cnt}] 다운로드: {sname} ({len(im_r.content):,}b)")
                            cnt += 1
                            if cnt > 6:
                                break
                    except Exception as e:
                        pass
            found_info[u] = {"name": name, "downloaded": downloaded}
            if len(downloaded) >= 3:
                break
    except Exception as e:
        print(f"에러: {e}")

with open("intimate/data/jilgyungyi.json", "w", encoding="utf-8") as f:
    json.dump(found_info, f, ensure_ascii=False, indent=2)

print("질경이 크롤링 완료")
