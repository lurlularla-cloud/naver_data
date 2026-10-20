"""
파일명: youtube_search.py
설명: YouTube Data API v3 연동 모듈
      - 키워드로 동영상 검색 후 영상 통계(조회수/좋아요/댓글) 일괄 조회
      - 채널 구독자 수 매핑
      - 인증 키는 st.secrets → .env(환경변수) 순서로 조회
"""

import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from googleapiclient.discovery import build

from text_filter import DEFAULT_EXCLUDE_WORDS, drop_noise_rows

# .env 파일 로드 (프로젝트 루트 우선, 없으면 src 폴더)
env_path = Path(__file__).resolve().parent.parent / ".env"
if not env_path.exists():
    env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

COLUMNS = [
    "video_id", "title", "description", "channel_title", "published_at", "thumbnail_url",
    "view_count", "like_count", "comment_count", "subscriber_count", "video_url",
]

MAX_IDS_PER_CALL = 50  # videos/channels/search API 1회 호출당 최대 개수

# 검색어 뒤에 "-단어"로 붙여 API 단계에서 먼저 걸러낼 단어 (YouTube 검색 NOT 연산자)
# 쿼리가 너무 길어지지 않도록 노이즈 빈도가 높은 대표 단어만 사용하고, 나머지는 drop_noise_rows로 후처리한다.
YOUTUBE_NEGATIVE_KEYWORDS = (
    "드라마", "노래", "SBS", "정라엘", "7인의탈출", "이유비",
    "예능", "트로트", "세미트롯", "뮤직비디오", "MV",
)


# -----------------------------------------------------------------------------
# 1. 인증 키 조회 (st.secrets / .env 모두 지원)
# -----------------------------------------------------------------------------
def get_youtube_api_key():
    """st.secrets에서 YOUTUBE_API_KEY를 찾고, 없으면 환경변수(.env)에서 찾는다."""
    api_key = None
    try:
        api_key = st.secrets.get("YOUTUBE_API_KEY")
    except Exception:
        # secrets.toml 없음/비어 있음
        pass
    api_key = api_key or os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "YOUTUBE_API_KEY가 설정되지 않았습니다. "
            ".env 파일 또는 .streamlit/secrets.toml에 추가해주세요."
        )
    return api_key


def _chunks(items, size=MAX_IDS_PER_CALL):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _best_thumbnail(thumbnails):
    """고화질 → 중화질 → 기본 순서로 썸네일 URL을 고른다."""
    for size in ("high", "medium", "default"):
        if size in thumbnails:
            return thumbnails[size].get("url", "")
    return ""


# -----------------------------------------------------------------------------
# 2. 검색 및 상세 데이터 수집
# -----------------------------------------------------------------------------
def build_search_query(keyword, negative_keywords=YOUTUBE_NEGATIVE_KEYWORDS):
    """'라엘' → '라엘 -드라마 -노래 -SBS ...' 형태의 검색 쿼리를 만든다.

    공백이 들어간 제외어는 따옴표로 묶어 구문 단위로 제외한다.
    """
    terms = [keyword.strip()]
    for word in negative_keywords or []:
        word = word.strip()
        if word:
            terms.append(f'-"{word}"' if " " in word else f"-{word}")
    return " ".join(terms)


def _search_video_ids(youtube, keyword, max_results):
    """search().list로 동영상 ID를 max_results개까지 수집한다. (50개 초과 시 페이징)"""
    video_ids = []
    page_token = None
    while len(video_ids) < max_results:
        response = youtube.search().list(
            q=keyword,
            part="id",
            type="video",
            maxResults=min(MAX_IDS_PER_CALL, max_results - len(video_ids)),
            pageToken=page_token,
        ).execute()
        video_ids += [item["id"]["videoId"] for item in response.get("items", [])]
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return list(dict.fromkeys(video_ids))  # 순서 유지 중복 제거


def _fetch_videos(youtube, video_ids):
    videos = []
    for chunk in _chunks(video_ids):
        response = youtube.videos().list(part="snippet,statistics", id=",".join(chunk)).execute()
        videos += response.get("items", [])
    return videos


def _fetch_subscriber_counts(youtube, channel_ids):
    """채널 ID → 구독자 수 딕셔너리. 구독자 수 비공개 채널은 매핑되지 않는다."""
    subscribers = {}
    for chunk in _chunks(channel_ids):
        response = youtube.channels().list(part="snippet,statistics", id=",".join(chunk)).execute()
        for ch in response.get("items", []):
            stats = ch.get("statistics", {})
            if not stats.get("hiddenSubscriberCount"):
                subscribers[ch["id"]] = stats.get("subscriberCount")
    return subscribers


@st.cache_data(ttl=3600)
def _fetch_youtube_raw(keyword, max_results, negative_keywords):
    """API 호출 결과(정제 전)를 1시간 캐싱한다. 제외어를 바꿔도 API를 다시 호출하지 않는다."""
    youtube = build("youtube", "v3", developerKey=get_youtube_api_key(), cache_discovery=False)

    video_ids = _search_video_ids(youtube, build_search_query(keyword, negative_keywords), max_results)
    if not video_ids:
        return pd.DataFrame(columns=COLUMNS)

    videos = _fetch_videos(youtube, video_ids)
    channel_ids = list({v["snippet"]["channelId"] for v in videos})
    subscribers = _fetch_subscriber_counts(youtube, channel_ids)

    rows = []
    for v in videos:
        snippet = v.get("snippet", {})
        stats = v.get("statistics", {})
        rows.append({
            "video_id": v["id"],
            "title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
            "channel_title": snippet.get("channelTitle", ""),
            "published_at": snippet.get("publishedAt"),
            "thumbnail_url": _best_thumbnail(snippet.get("thumbnails", {})),
            "view_count": stats.get("viewCount"),
            "like_count": stats.get("likeCount"),
            "comment_count": stats.get("commentCount"),
            "subscriber_count": subscribers.get(snippet.get("channelId")),
            "video_url": f"https://www.youtube.com/watch?v={v['id']}",
        })

    df = pd.DataFrame(rows, columns=COLUMNS)
    for col in ["view_count", "like_count", "comment_count", "subscriber_count"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype("int64")
    df["published_at"] = pd.to_datetime(df["published_at"], utc=True).dt.tz_convert("Asia/Seoul")
    return df


def fetch_youtube_data(keyword, max_results=20, exclude_words=DEFAULT_EXCLUDE_WORDS,
                       negative_keywords=YOUTUBE_NEGATIVE_KEYWORDS):
    """키워드로 YouTube 동영상을 검색해 영상/채널 통계를 하나의 DataFrame으로 반환한다.

    컬럼: video_id, title, description, channel_title, published_at(KST), thumbnail_url,
          view_count, like_count, comment_count, subscriber_count, video_url
    좋아요/댓글 비공개 영상과 구독자 수 비공개 채널은 해당 값이 0으로 채워진다.
    - negative_keywords: 검색어 뒤에 '-단어'로 붙여 API 단계에서 1차 차단
    - exclude_words: title/description/channel_title에 하나라도 포함되면 2차 제외 (빈 리스트면 정제 안 함)
    """
    raw = _fetch_youtube_raw(keyword, max_results, tuple(negative_keywords or ()))
    return drop_noise_rows(raw, exclude_words)


if __name__ == "__main__":
    raw = fetch_youtube_data("생리대", max_results=10, exclude_words=[])
    cleaned = drop_noise_rows(raw)
    print(f"수집 {len(raw)}건 → 노이즈 제외 후 {len(cleaned)}건")
    print(cleaned[["title", "channel_title", "view_count"]].to_string())
