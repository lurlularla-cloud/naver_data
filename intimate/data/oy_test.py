"""
올리브영 상세페이지 AJAX 엔드포인트 테스트 스크립트.
다양한 URL 패턴으로 접속하여 응답 상태와 텍스트 내용을 출력합니다.
"""
import sys, io, requests
from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

GOODS_NO = "A000000228164"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": f"https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo={GOODS_NO}",
    "X-Requested-With": "XMLHttpRequest",
}

urls = [
    f"https://www.oliveyoung.co.kr/store/goods/getGoodsArtcTabAjax.do?goodsNo={GOODS_NO}",
    f"https://www.oliveyoung.co.kr/store/goods/getGoodsDetailDescription.do?goodsNo={GOODS_NO}",
    f"https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo={GOODS_NO}&isAjax=Y",
    f"https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo={GOODS_NO}",
]

for url in urls:
    try:
        r = requests.get(url, headers=headers, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        texts = []
        for e in soup.find_all(["p","td","th","dt","dd","li","h1","h2","h3","h4","span"]):
            t = e.get_text(" ", strip=True)
            if 5 < len(t) < 500 and t not in texts:
                texts.append(t)
        imgs = []
        for img in soup.find_all("img"):
            src = img.get("src","")
            if src and "data:" not in src:
                imgs.append({"src": src, "alt": img.get("alt","")})

        short_url = url.split("do?")[0].split("/")[-1] if "do?" in url else url[-30:]
        print(f"=== {short_url} ===")
        print(f"  status={r.status_code} size={len(r.text)} texts={len(texts)} imgs={len(imgs)}")
        for t in texts[:20]:
            print(f"  TEXT: {t}")
        for i in imgs[:5]:
            print(f"  IMG: {i['src'][:90]}")
        print()
    except Exception as ex:
        print(f"ERROR {url}: {ex}")
