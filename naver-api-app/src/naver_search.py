"""
파일명: naver_search.py
설명: 네이버 검색 API(블로그/뉴스/카페) 연동 모듈
      - 채널별 검색 결과를 하나의 통일된 DataFrame으로 병합
      - 포함어/제외어 기반 필터링
      - 인증 키는 st.secrets → .env(환경변수) 순서로 조회
"""

import email.utils
import html
import os
import re
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

from text_filter import DEFAULT_EXCLUDE_WORDS, drop_noise_rows, keep_rows_with_all

# .env 파일 로드 (프로젝트 루트 우선, 없으면 src 폴더)
env_path = Path(__file__).resolve().parent.parent / ".env"
if not env_path.exists():
    env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

SEARCH_URL = "https://openapi.naver.com/v1/search/{endpoint}.json"

# 채널명 → 검색 API 엔드포인트
CHANNELS = {
    "블로그": "blog",
    "뉴스": "news",
    "카페": "cafearticle",
}

COLUMNS = ["title", "description", "link", "postdate", "channel"]

_TAG_RE = re.compile(r"<[^>]+>")


# -----------------------------------------------------------------------------
# 1. 인증 키 조회 (st.secrets / .env 모두 지원)
# -----------------------------------------------------------------------------
def _get_secret(key):
    """st.secrets에서 키를 찾고, 없으면 환경변수(.env)에서 찾는다.

    st.secrets는 최상위 키(NAVER_CLIENT_ID)와
    [naver] 섹션(client_id) 형식을 모두 지원한다.
    """
    try:
        import streamlit as st

        if key in st.secrets:
            return st.secrets[key]
        section = st.secrets.get("naver", {})
        short_key = key.replace("NAVER_", "").lower()
        if short_key in section:
            return section[short_key]
    except Exception:
        # streamlit 미설치 또는 secrets.toml 없음/비어 있음
        pass
    return os.getenv(key)


def get_naver_credentials():
    """네이버 개발자센터 Client ID / Secret을 반환한다."""
    client_id = _get_secret("NAVER_CLIENT_ID")
    client_secret = _get_secret("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError(
            "NAVER_CLIENT_ID / NAVER_CLIENT_SECRET이 설정되지 않았습니다. "
            ".env 파일 또는 .streamlit/secrets.toml에 추가해주세요."
        )
    return client_id, client_secret


# -----------------------------------------------------------------------------
# 2. 텍스트/날짜 정규화
# -----------------------------------------------------------------------------
def clean_html(text):
    """HTML 태그(<b> 등)를 제거하고 HTML 엔티티(&quot; 등)를 디코딩한다."""
    if not text:
        return ""
    return html.unescape(_TAG_RE.sub("", text)).strip()


def normalize_date(value):
    """YYYYMMDD(블로그) 또는 RFC 822(뉴스) 날짜를 YYYY-MM-DD로 변환한다."""
    if not value:
        return None
    value = str(value).strip()
    if re.fullmatch(r"\d{8}", value):
        return f"{value[:4]}-{value[4:6]}-{value[6:]}"
    try:
        return email.utils.parsedate_to_datetime(value).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return None


# -----------------------------------------------------------------------------
# 3. 검색 API 호출
# -----------------------------------------------------------------------------
def _search(endpoint, keyword, display, sort, headers):
    """단일 채널 검색 API를 호출해 items 리스트를 반환한다."""
    params = {
        "query": keyword,
        "display": max(10, min(int(display), 100)),  # API 허용 범위 10~100
        "start": 1,
        "sort": sort,
    }
    response = requests.get(
        SEARCH_URL.format(endpoint=endpoint), headers=headers, params=params, timeout=10
    )
    response.raise_for_status()
    return response.json().get("items", [])


def fetch_naver_data(keyword, display=100, sort="date", exclude_words=DEFAULT_EXCLUDE_WORDS):
    """블로그/뉴스/카페 검색 결과를 하나의 DataFrame으로 병합해 반환한다.

    컬럼: title, description, link, postdate(YYYY-MM-DD), channel('블로그'/'뉴스'/'카페')
    카페 검색 API는 작성일을 제공하지 않으므로 카페 글의 postdate는 None이다.
    한 채널의 호출이 실패해도 나머지 채널 결과는 반환한다.
    title/description에 exclude_words가 하나라도 포함된 행은 제외된다. (빈 리스트면 정제 안 함)
    """
    client_id, client_secret = get_naver_credentials()
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }

    rows = []
    for channel, endpoint in CHANNELS.items():
        try:
            items = _search(endpoint, keyword, display, sort, headers)
        except requests.RequestException as e:
            print(f"[naver_search] {channel} 검색 실패: {e}")
            continue

        for item in items:
            rows.append({
                "title": clean_html(item.get("title")),
                "description": clean_html(item.get("description")),
                "link": item.get("link") or item.get("originallink", ""),
                "postdate": normalize_date(item.get("postdate") or item.get("pubDate")),
                "channel": channel,
            })

    df = pd.DataFrame(rows, columns=COLUMNS)
    return drop_noise_rows(df, exclude_words)


# -----------------------------------------------------------------------------
# 4. 포함어/제외어 필터링
# -----------------------------------------------------------------------------
def filter_by_words(df, must_include_words=None, exclude_words=None):
    """제목+본문 기준으로 포함어/제외어 필터링한다. (대소문자·공백 무시)

    - must_include_words: 모든 단어가 제목 또는 본문에 포함되어야 함
    - exclude_words: 하나라도 제목 또는 본문에 포함되면 제외
    """
    df = keep_rows_with_all(df, must_include_words)
    return drop_noise_rows(df, exclude_words)


if __name__ == "__main__":
    raw = fetch_naver_data("생리대", display=10, exclude_words=[])
    cleaned = drop_noise_rows(raw)
    print(f"수집 {len(raw)}건 → 노이즈 제외 후 {len(cleaned)}건")
    print(cleaned.groupby("channel").size())
