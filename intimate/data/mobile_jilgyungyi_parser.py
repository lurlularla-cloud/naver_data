"""
질경이 모바일 스마트스토어 엔드포인트 및 API를 통한 상품 정보/상세페이지 추출 스크립트.
"""
import sys
import io
import os
import re
import json
import requests
from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

URL = "https://m.smartstore.naver.com/jilgyungyi/products/10364943970"
headers = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

print(f"모바일 요청 중: {URL}")
r = requests.get(URL, headers=headers, timeout=10)
print(f"상태코드: {r.status_code}, 크기: {len(r.text):,}b")

# __PRELOADED_STATE__ 검색
match = re.search(r"window\.__PRELOADED_STATE__\s*=\s*({.+?});\s*</script>", r.text)
if not match:
    match = re.search(r"__PRELOADED_STATE__\s*=\s*({.+?});", r.text)

if match:
    try:
        data = json.loads(match.group(1))
        # 상품 세부 정보 탐색
        print("PRELOADED STATE 키:", list(data.keys()))
        prod = data.get("product", {}).get("A", {}) or data.get("simpleProduct", {})
        print("상품명:", prod.get("name"))
        print("판매가:", prod.get("price"), "할인가:", prod.get("discountedSalePrice"))
        
        # 상세 내용 HTML
        detail_html = prod.get("renderDetailContent", "") or prod.get("detailContent", "")
        print("상세 HTML 크기:", len(detail_html))
        
        # 상세 이미지 추출
        soup = BeautifulSoup(detail_html, "html.parser")
        imgs = soup.find_all("img")
        print(f"상세 이미지 태그 수: {len(imgs)}")
        
        os.makedirs("intimate/images/jilgyungyi", exist_ok=True)
        downloaded = []
        for i, img in enumerate(imgs[:8]):
            src = img.get("src") or img.get("data-src") or ""
            if src:
                clean_src = src.split("?")[0]
                im_r = requests.get(clean_src, headers=headers, timeout=10)
                if len(im_r.content) > 15000:
                    spath = f"intimate/images/jilgyungyi/jilgyungyi_img_{i+1:02d}.jpg"
                    with open(spath, "wb") as f:
                        f.write(im_r.content)
                    downloaded.append({"index": i+1, "url": clean_src, "path": spath, "bytes": len(im_r.content)})
                    print(f"[{i+1}] 다운로드: {spath} ({len(im_r.content):,}b)")
        
        with open("intimate/data/jilgyungyi.json", "w", encoding="utf-8") as f:
            json.dump({
                "product_name": prod.get("name"),
                "prices": {
                    "price": prod.get("price"),
                    "discountedSalePrice": prod.get("discountedSalePrice"),
                    "discountRate": prod.get("discountRate")
                },
                "options": prod.get("options", []),
                "detail_text_preview": soup.get_text(" ", strip=True)[:1000],
                "downloaded_images": downloaded
            }, f, ensure_ascii=False, indent=2)
            print("데이터 저장 완료: intimate/data/jilgyungyi.json")
    except Exception as e:
        print("JSON 파싱 에러:", e)
else:
    print("PRELOADED STATE 매칭 실패")
