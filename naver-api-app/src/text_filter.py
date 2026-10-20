"""
파일명: text_filter.py
설명: 네이버/유튜브 수집 데이터 공통 텍스트 정제 모듈
      - 브랜드 무관 노이즈 기본 제외어 정의
      - 대소문자/공백을 무시한 포함어·제외어 매칭 (제목/본문/채널명 검사)
"""

import re
import unicodedata

import pandas as pd

# 브랜드와 무관하게 검색 결과에 섞여 들어오는 노이즈 단어
DEFAULT_EXCLUDE_WORDS = [
    # 도서/교육/생활 일반
    "스피치", "학원", "홍진경", "딸", "알라딘", "알라딘서재", "100자평", "서평",
    "도서", "책소개", "음악", "피아노", "미술", "부고", "감자요리", "숲정원",
    # 드라마/배우/방송
    "정라엘", "7인의탈출", "7인의 탈출", "이유비", "드라마", "drama", "배우",
    "방송", "예능", "SBS", "스브스",
    # 음악/가수
    "트로트", "세미트롯", "신곡", "음원", "뮤직비디오", "MV", "노래",
]

# 제외어 검사 대상 컬럼 (데이터프레임에 없는 컬럼은 자동으로 건너뜀)
NOISE_CHECK_COLUMNS = ("title", "description", "channel_title")

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(text):
    """매칭용 정규화: 유니코드 NFKC 통일 → 소문자 변환 → 모든 공백 제거.

    예) "알라딘 서재" / "알라딘서재" / "ALADIN  서재" 계열을 같은 형태로 맞춘다.
    """
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    return _WHITESPACE_RE.sub("", unicodedata.normalize("NFKC", str(text)).lower())


def parse_word_list(raw):
    """쉼표/줄바꿈으로 구분된 입력 문자열을 단어 리스트로 변환한다."""
    return [w.strip() for w in re.split(r"[,\n]", raw or "") if w.strip()]


def _normalized_words(words):
    return [w for w in (normalize_text(w) for w in words or []) if w]


def _combined_text(df, text_columns):
    """검사 대상 컬럼들을 각각 정규화해 행 단위로 이어 붙인다."""
    text = pd.Series("", index=df.index)
    for col in text_columns:
        if col in df.columns:
            # 컬럼 경계에서 단어가 이어 붙어 오탐되지 않도록 구분자 삽입
            text = text + "\x00" + df[col].map(normalize_text)
    return text


def drop_noise_rows(df, exclude_words=DEFAULT_EXCLUDE_WORDS, text_columns=NOISE_CHECK_COLUMNS):
    """title/description/channel_title 중 어느 한 곳이라도 제외어가 포함된 행을 제거한다."""
    words = _normalized_words(exclude_words)
    if df.empty or not words:
        return df.reset_index(drop=True)

    text = _combined_text(df, text_columns)
    noise = pd.Series(False, index=df.index)
    for word in words:
        noise |= text.str.contains(word, regex=False)
    return df[~noise].reset_index(drop=True)


def keep_rows_with_all(df, must_include_words, text_columns=("title", "description")):
    """title/description 어딘가에 포함어가 모두 들어 있는 행만 남긴다."""
    words = _normalized_words(must_include_words)
    if df.empty or not words:
        return df.reset_index(drop=True)

    text = _combined_text(df, text_columns)
    keep = pd.Series(True, index=df.index)
    for word in words:
        keep &= text.str.contains(word, regex=False)
    return df[keep].reset_index(drop=True)
