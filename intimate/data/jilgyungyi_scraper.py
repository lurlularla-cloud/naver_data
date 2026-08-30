"""
질경이 네이버 브랜드스토어 및 공식몰 상세페이지 데이터 추출 스크립트.
"""
import sys
import io
import os
import json
import re
import requests
from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

URL = "https://brand.naver.com/jilgyungyi/products/10364943970"
IMAGE_DIR = "intimate/images/jilgyungyi"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

print(f"요청 중: {URL}")
r = requests.get(URL, headers=headers, timeout=10)
print(f"상태코드: {r.status_code}, 크기: {len(r.text):,}b")

title = ""
# PRELOADED_STATE 파싱
script_match = re.search(r"window\.__PRELOADED_STATE__\s*=\s*({.+?});?</script>", r.text)
product_info = {}
if script_match:
    try:
        data = json.loads(script_match.group(1))
        p = data.get("product", {}).get("A", {})
        title = p.get("name", "")
        print(f"PRELOADED 상품명: {title}")
        print(f"가격: {p.get('price')} / 할인가: {p.get('discountedSalePrice')}")
        product_info = p
    except Exception as e:
        print(f"파싱 예외: {e}")

if not title:
    soup = BeautifulSoup(r.text, "html.parser")
    title_elem = soup.find("meta", property="og:title")
    title = title_elem.get("content") if title_elem else ""
    print(f"og:title 상품명: {title}")

# 상세 이미지 추출
soup = BeautifulSoup(r.text, "html.parser")
imgs = soup.select(".se-main-container img, #content img, .detailArea img")
print(f"발견된 상세 이미지: {len(imgs)}개")

count = 1
downloaded = []
for im in imgs:
    src = im.get("src") or im.get("data-src") or ""
    if src and not src.startswith("data:"):
        ext = os.path.splitext(src.split("?")[0])[1] or ".jpg"
        try:
            im_r = requests.get(src, headers=headers, timeout=10)
            if len(im_r.content) > 15000:
                sname = f"jilgyungyi_img_{count:02d}{ext}"
                spath = os.path.join(IMAGE_DIR, sname)
                with open(spath, "wb") as f:
                    f.write(im_r.content)
                downloaded.append({"index": count, "url": src, "path": spath, "bytes": len(im_r.content)})
                print(f"[{count}] 저장: {spath} ({len(im_r.content):,}b)")
                count += 1
                if count > 8:
                    break
        except Exception as e:
            pass

with open("intimate/data/jilgyungyi.json", "w", encoding="utf-8") as f:
    json.dump({
        "url": URL,
        "title": title,
        "product_info": product_info,
        "downloaded_images": downloaded
    }, f, ensure_ascii=False, indent=2)

print("질경이 데이터 저장 완료")
