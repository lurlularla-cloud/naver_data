"""
파일명: app.py
설명: 네이버 오픈API(검색어 트렌드, 쇼핑, 블로그, 카페글, 뉴스, 쇼핑 트렌드) 및
      네이버 검색광고 API(키워드별 PC/모바일 절대 검색량 및 SOV 점유율)를 통합 연동한 Streamlit 대시보드
"""

import streamlit as st
import pandas as pd
import requests
import datetime
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from scipy.stats import skew, kurtosis
import io
import os
from pathlib import Path
from dotenv import load_dotenv

# 검색광고 API 서명 암호화 및 시간 라이브러리
import hmac
import hashlib
import base64
import time

# .env 파일 로드 (.env 파일이 app.py의 상위 폴더 또는 동일 폴더에 위치함)
env_path = Path(__file__).resolve().parent.parent / ".env"
if not env_path.exists():
    env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)


# -----------------------------------------------------------------------------
# 페이지 설정 및 테마 정의
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="네이버 API 브랜드 종합 분석 대시보드",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 스타일 적용 (고급스러운 다크 & 라이트 조화)
st.markdown("""
    <style>
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1EC800; /* 네이버 시그니처 그린 */
        margin-bottom: 0.5rem;
    }
    .sub-title {
        font-size: 1.1rem;
        color: #555555;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #F8F9FA;
        border: 1px solid #E9ECEF;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 1. 네이버 오픈API (개발자센터) 호출 유틸리티
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def _fetch_naver_api_cached(url, client_id, client_secret, params_tuple=None, method="GET", json_data_str=None):
    """네이버 오픈API를 호출하고 결과를 캐싱하는 내부 캐시 함수"""
    import json
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }
    try:
        if method == "POST":
            headers["Content-Type"] = "application/json"
            json_data = json.loads(json_data_str) if json_data_str else None
            response = requests.post(url, headers=headers, json=json_data, timeout=10)
        else:
            params = dict(params_tuple) if params_tuple else None
            response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            return {
                "status": "success",
                "data": response.json(),
                "fetched_at": datetime.datetime.now().timestamp()
            }
        else:
            raise RuntimeError(f"HTTP_ERROR:{response.status_code}:{response.text}")
            
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"NETWORK_ERROR:{str(e)}")

def fetch_naver_api(url, headers, params=None, method="GET", json_data=None):
    """네이버 오픈API를 호출하는 공통 유틸리티 함수 (캐시 적용 래퍼)"""
    import json
    client_id = headers.get("X-Naver-Client-Id", "")
    client_secret = headers.get("X-Naver-Client-Secret", "")
    
    params_tuple = tuple(sorted(params.items())) if params else None
    json_data_str = json.dumps(json_data, sort_keys=True) if json_data else None
    
    try:
        res = _fetch_naver_api_cached(
            url, client_id, client_secret, params_tuple, method, json_data_str
        )
        
        now = datetime.datetime.now().timestamp()
        is_hit = (now - res["fetched_at"]) > 5.0
        
        st.session_state["last_api_status"] = {
            "url": url,
            "is_hit": is_hit,
            "fetched_at": res["fetched_at"]
        }
        return {"status": "success", "data": res["data"]}
        
    except RuntimeError as e:
        err_msg = str(e)
        if err_msg.startswith("HTTP_ERROR:"):
            parts = err_msg.split(":", 2)
            status_code = int(parts[1])
            try:
                error_info = json.loads(parts[2])
            except:
                error_info = {}
            
            err_msg_content = error_info.get("errorMessage", "알 수 없는 오류가 발생했습니다.")
            err_code = error_info.get("errorCode", "UNKNOWN")
            
            if status_code == 400:
                msg = f"잘못된 요청 파라미터입니다. (에러코드: {err_code}, 메시지: {err_msg_content})"
            elif status_code == 401:
                msg = "인증 실패: Client ID 및 Client Secret을 다시 확인해 주세요."
            elif status_code == 403:
                msg = "권한 없음: 네이버 개발자 센터에서 해당 API 권한이 활성화되어 있는지 확인해 주세요."
            elif status_code == 404:
                if err_code == "SE05":
                    msg = f"네이버 오픈API 서비스가 공식 종료되었거나 지원하지 않는 엔드포인트입니다. (에러코드: SE05, {err_msg_content})"
                else:
                    msg = f"요청한 API 리소스를 찾을 수 없습니다. (HTTP 404: {err_msg_content})"
            elif status_code == 429:
                msg = "호출 한도 초과: 오늘 사용 가능한 호출 할당량을 모두 소진했습니다."
            else:
                msg = f"오류 발생 (HTTP {status_code}): {err_msg_content}"
            return {"status": "error", "message": msg}
        else:
            msg = err_msg.split(":", 1)[-1]
            return {"status": "error", "message": f"네트워크 통신 중 오류가 발생했습니다: {msg}"}

# -----------------------------------------------------------------------------
# 2. 네이버 검색광고 API (키워드도구 - 절대 검색량 수집)
# -----------------------------------------------------------------------------
def generate_ad_signature(timestamp: str, method: str, path: str, secret_key: str) -> str:
    """검색광고 API HMAC-SHA256 서명 생성"""
    message = f"{timestamp}.{method}.{path}"
    hash_obj = hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
    return base64.b64encode(hash_obj.digest()).decode('utf-8')

@st.cache_data(ttl=3600)
def fetch_naver_search_ads(keywords_tuple, customer_id, api_key, secret_key):
    """네이버 검색광고 API keywordstool을 호출하여 절대 검색량 수집"""
    if not customer_id or not api_key or not secret_key:
        return {"status": "error", "message": "검색광고 API 키(CUSTOMER_ID, API_KEY, SECRET_KEY)가 설정되지 않았습니다."}

    base_url = "https://api.searchad.naver.com"
    path = "/keywordstool"
    timestamp = str(int(time.time() * 1000))
    signature = generate_ad_signature(timestamp, "GET", path, secret_key)

    headers = {
        "X-Timestamp": timestamp,
        "X-API-KEY": api_key,
        "X-Customer": str(customer_id),
        "X-Signature": signature
    }

    # 키워드는 공백 제거 후 최대 5개까지 쉼표로 연결
    clean_kws = [k.replace(" ", "") for k in keywords_tuple if k.strip()]
    if not clean_kws:
        return {"status": "error", "message": "유효한 키워드가 없습니다."}

    params = {
        "hintKeywords": ",".join(clean_kws[:5]),
        "showDetail": "1"
    }

    try:
        res = requests.get(base_url + path, headers=headers, params=params, timeout=10)
        if res.status_code == 200:
            return {"status": "success", "data": res.json()}
        else:
            return {"status": "error", "message": f"검색광고 API 오류 (HTTP {res.status_code}): {res.text}"}
    except Exception as e:
        return {"status": "error", "message": f"검색광고 API 통신 오류: {str(e)}"}

# -----------------------------------------------------------------------------
# 사이드바 입력 제어 영역
# -----------------------------------------------------------------------------
st.sidebar.image("https://developers.naver.com/inc/dev-center/images/ndev_header_logo.png", width=200)
st.sidebar.markdown("### 🔑 API 인증 설정")

# 1. 개발자센터 키 로드
client_id = os.getenv("NAVER_CLIENT_ID", "")
client_secret = os.getenv("NAVER_CLIENT_SECRET", "")

# 2. 검색광고 키 로드
ads_customer_id = os.getenv("NAVER_ADS_CUSTOMER_ID", "")
ads_api_key = os.getenv("NAVER_ADS_API_KEY", "")
ads_secret_key = os.getenv("NAVER_ADS_SECRET_KEY", "")

# st.secrets 지원 (배포 환경)
try:
    if "NAVER_CLIENT_ID" in st.secrets:
        client_id = st.secrets["NAVER_CLIENT_ID"]
    if "NAVER_CLIENT_SECRET" in st.secrets:
        client_secret = st.secrets["NAVER_CLIENT_SECRET"]
    if "NAVER_ADS_CUSTOMER_ID" in st.secrets:
        ads_customer_id = st.secrets["NAVER_ADS_CUSTOMER_ID"]
    if "NAVER_ADS_API_KEY" in st.secrets:
        ads_api_key = st.secrets["NAVER_ADS_API_KEY"]
    if "NAVER_ADS_SECRET_KEY" in st.secrets:
        ads_secret_key = st.secrets["NAVER_ADS_SECRET_KEY"]
except Exception:
    pass

st.session_state.client_id = client_id.strip() if client_id else ""
st.session_state.client_secret = client_secret.strip() if client_secret else ""
st.session_state.ads_customer_id = ads_customer_id.strip() if ads_customer_id else ""
st.session_state.ads_api_key = ads_api_key.strip() if ads_api_key else ""
st.session_state.ads_secret_key = ads_secret_key.strip() if ads_secret_key else ""

# 인증 상태 뱃지
if st.session_state.client_id and st.session_state.client_secret:
    st.sidebar.success("✅ 네이버 개발자센터 API 연동됨")
else:
    st.sidebar.warning("⚠️ 개발자센터 API 키 필요")

if st.session_state.ads_customer_id and st.session_state.ads_api_key and st.session_state.ads_secret_key:
    st.sidebar.success("✅ 네이버 검색광고 API 연동됨")
else:
    st.sidebar.info("💡 검색광고 API 미설정 시 절대 검색량 기능 제외")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔍 분석 설정")

# 쇼핑 카테고리 매핑
CATEGORY_MAP = {
    "패션의류": "50000000",
    "패션잡화": "50000001",
    "화장품/미용": "50000002",
    "디지털/가전": "50000003",
    "가구/인테리어": "50000004",
    "출산/육아": "50000005",
    "식품": "50000006",
    "스포츠/레저": "50000007",
    "생활/건강": "50000008",
    "여가/생활편의": "50000009",
    "면세점": "50000010",
    "도서": "50005542"
}
selected_category = st.sidebar.selectbox("쇼핑 분석 카테고리", options=list(CATEGORY_MAP.keys()), index=3)
selected_category_id = CATEGORY_MAP[selected_category]

# 분석 키워드 입력
keyword_raw = st.sidebar.text_input("분석 검색어 / 브랜드 (쉼표 구분)", value="라엘, 좋은느낌, 화이트")
keywords = [k.strip() for k in keyword_raw.split(",") if k.strip()]

# 검색 기간 설정
today = datetime.date.today()
last_month = today - datetime.timedelta(days=30)
start_date = st.sidebar.date_input("조회 시작일", value=last_month, max_value=today)
end_date = st.sidebar.date_input("조회 종료일", value=today, min_value=start_date, max_value=today)

st.sidebar.markdown("---")

if st.sidebar.button("🔄 데이터 새로고침 (캐시 초기화)", use_container_width=True):
    st.cache_data.clear()
    st.toast("캐시가 성공적으로 초기화되었습니다!", icon="🔄")
    st.rerun()

# -----------------------------------------------------------------------------
# 메인 화면 구성
# -----------------------------------------------------------------------------
st.markdown('<div class="main-title">Naver API 브랜드·경쟁사 종합 대시보드</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">실제 PC/모바일 절대 검색 쿼리수, 데이터랩 트렌드, 채널별 언급량 및 쇼핑 반응을 입체적으로 분석합니다.</div>', unsafe_allow_html=True)

# 필수 API 인증 체크
if not st.session_state.client_id or not st.session_state.client_secret:
    st.warning("⚠️ 프로젝트 내 `.env` 파일에 **NAVER_CLIENT_ID**와 **NAVER_CLIENT_SECRET**을 올바르게 설정해 주세요.")
    st.stop()

headers_get = {
    "X-Naver-Client-Id": st.session_state.client_id,
    "X-Naver-Client-Secret": st.session_state.client_secret
}

headers_post = {
    "X-Naver-Client-Id": st.session_state.client_id,
    "X-Naver-Client-Secret": st.session_state.client_secret,
    "Content-Type": "application/json"
}

# 탭 메뉴 구성
tab_names = [
    "⚔️ 브랜드 절대 검색량 & SOV",  # 검색광고 API 연동 핵심 탭
    "📈 검색어 트렌드", 
    "🛒 쇼핑 분석", 
    "✍️ 블로그 트렌드", 
    "☕ 카페글 분석", 
    "📰 뉴스 분석", 
    "📊 쇼핑 트렌드 분석"
]
selected_tab = st.tabs(tab_names)

# 세부 분석용 단일 키워드 선택 셀렉트박스
selected_kw = st.selectbox("🎯 세부 채널 분석 대상 키워드 선택", options=keywords)

# -----------------------------------------------------------------------------
# Tab 0: 브랜드 절대 검색량 & SOV 분석 (네이버 검색광고 API 연동)
# -----------------------------------------------------------------------------
with selected_tab[0]:
    st.markdown("### ⚔️ 자사 vs 경쟁사 브랜드 절대 검색량(쿼리수) & 점유율(SOV)")
    st.markdown("네이버 검색광고 빅데이터를 통해 **최근 30일간 실제 PC 및 모바일에서 검색된 절대 수치**를 비교합니다.")

    if not st.session_state.ads_customer_id or not st.session_state.ads_api_key or not st.session_state.ads_secret_key:
        st.warning(
            "💡 **검색광고 API 미연동 상태**입니다.\n\n"
            "`.env` 파일에 `NAVER_ADS_CUSTOMER_ID`, `NAVER_ADS_API_KEY`, `NAVER_ADS_SECRET_KEY`를 등록하시면 "
            "추정치가 아닌 **실제 월간 검색 횟수(PC/모바일 건수)**와 클릭률, 경쟁도 지표가 활성화됩니다."
        )
    elif not keywords:
        st.error("분석할 브랜드 키워드를 사이드바에 입력해 주세요.")
    else:
        with st.spinner("네이버 검색광고 API에서 브랜드 검색량 수집 중..."):
            ads_res = fetch_naver_search_ads(
                tuple(keywords),
                st.session_state.ads_customer_id,
                st.session_state.ads_api_key,
                st.session_state.ads_secret_key
            )

        if ads_res["status"] == "error":
            st.error(ads_res["message"])
        else:
            keyword_list = ads_res["data"].get("keywordList", [])
            
            # 검색결과 파싱 (입력한 키워드와 매칭)
            matched_data = []
            rel_keywords = []

            def parse_cnt(val):
                if isinstance(val, str) and "<" in val:
                    return 5  # '< 10' 표기 시 5로 보정
                try:
                    return int(val)
                except:
                    return 0

            # 입력한 원본 키워드 정규화
            clean_input_kws = [k.replace(" ", "") for k in keywords]

            for item in keyword_list:
                rel_kw = item.get("relKeyword", "")
                pc_cnt = parse_cnt(item.get("monthlyPcQcCnt", 0))
                mo_cnt = parse_cnt(item.get("monthlyMobileQcCnt", 0))
                total_cnt = pc_cnt + mo_cnt
                comp_idx = item.get("compIdx", "보통")

                # 입력한 메인 키워드인 경우
                if rel_kw in clean_input_kws:
                    matched_data.append({
                        "브랜드/키워드": rel_kw,
                        "PC 검색량": pc_cnt,
                        "모바일 검색량": mo_cnt,
                        "총 검색량 (30일)": total_cnt,
                        "모바일 비중 (%)": round((mo_cnt / total_cnt * 100), 1) if total_cnt > 0 else 0,
                        "광고 경쟁도": comp_idx
                    })
                else:
                    rel_keywords.append({
                        "연관 키워드": rel_kw,
                        "PC 검색량": pc_cnt,
                        "모바일 검색량": mo_cnt,
                        "총 검색량 (30일)": total_cnt,
                        "경쟁도": comp_idx
                    })

            df_matched = pd.DataFrame(matched_data)

            if df_matched.empty:
                st.warning("입력한 키워드에 대한 정확한 검색 데이터를 찾을 수 없습니다.")
            else:
                # 1. 상단 요약 지표 카드 (SOV 점유율)
                total_market_vol = df_matched["총 검색량 (30일)"].sum()
                cols = st.columns(len(df_matched))
                for idx, row in df_matched.iterrows():
                    ratio = (row["총 검색량 (30일)"] / total_market_vol * 100) if total_market_vol > 0 else 0
                    with cols[idx]:
                        st.metric(
                            label=f"🏷️ {row['브랜드/키워드']}",
                            value=f"{row['총 검색량 (30일)']:,} 회",
                            delta=f"검색 점유율 {ratio:.1f}%"
                        )

                st.markdown("---")

                # 2. 시각화 (점유율 파이 차트 vs PC/MO 비교 바 차트)
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    st.markdown("#### 📊 브랜드별 검색 점유율 (SOV)")
                    fig_sov = px.pie(
                        df_matched,
                        names="브랜드/키워드",
                        values="총 검색량 (30일)",
                        hole=0.4,
                        color_discrete_sequence=px.colors.qualitative.Bold
                    )
                    fig_sov.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_sov, use_container_width=True)

                with col_c2:
                    st.markdown("#### 📱 기기별 검색량 비교 (PC vs Mobile)")
                    df_melt = pd.melt(
                        df_matched,
                        id_vars=["브랜드/키워드"],
                        value_vars=["PC 검색량", "모바일 검색량"],
                        var_name="기기 구분",
                        value_name="검색수"
                    )
                    fig_device = px.bar(
                        df_melt,
                        x="브랜드/키워드",
                        y="검색수",
                        color="기기 구분",
                        barmode="group",
                        color_discrete_map={"PC 검색량": "#4682B4", "모바일 검색량": "#1EC800"}
                    )
                    st.plotly_chart(fig_device, use_container_width=True)

                # 3. 상세 데이터 테이블
                st.markdown("#### 📋 브랜드별 최근 30일 절대 검색수 세부 현황")
                st.dataframe(df_matched, use_container_width=True, hide_index=True)

                # 4. 연관 롱테일 확장 키워드 TOP 15
                if rel_keywords:
                    st.markdown("#### 🔍 함께 유입되는 연관 롱테일 키워드 TOP 15")
                    df_rel = pd.DataFrame(rel_keywords).sort_values(by="총 검색량 (30일)", ascending=False).head(15)
                    st.dataframe(df_rel, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# Tab 1: 검색어 트렌드 (데이터랩)
# -----------------------------------------------------------------------------
with selected_tab[1]:
    st.markdown("### 📈 네이버 데이터랩 통합 검색어 트렌드")
    st.markdown("지정한 키워드들의 조회 기간 내 상대적 검색 빈도를 비교 분석합니다.")
    
    if not keywords:
        st.error("분석할 검색어를 입력해 주세요.")
    else:
        json_data = {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d"),
            "timeUnit": "date",
            "keywordGroups": [{"groupName": kw, "keywords": [kw]} for kw in keywords]
        }
        
        with st.spinner("네이버 데이터랩 트렌드 조회 중..."):
            res = fetch_naver_api(
                "https://openapi.naver.com/v1/datalab/search", 
                headers=headers_post, 
                method="POST", 
                json_data=json_data
            )
            
        if res["status"] == "error":
            st.error(res["message"])
        else:
            api_data = res["data"]
            results = api_data.get("results", [])
            df_list = []
            for group in results:
                title = group.get("title")
                data_points = group.get("data", [])
                for dp in data_points:
                    df_list.append({
                        "날짜": pd.to_datetime(dp["period"]),
                        "키워드": title,
                        "검색량 비율": dp["ratio"]
                    })
            
            if not df_list:
                st.warning("조회 조건에 해당하는 데이터가 존재하지 않습니다.")
            else:
                df_trend = pd.DataFrame(df_list)
                
                fig = px.line(
                    df_trend, 
                    x="날짜", 
                    y="검색량 비율", 
                    color="키워드",
                    title=f"키워드별 상대적 검색 트렌드 ({start_date} ~ {end_date})",
                    labels={"검색량 비율": "상대적 검색량 (%)", "날짜": "조회 일자"},
                    template="plotly_white"
                )
                fig.update_layout(hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)
                
                # 통계 검증 지표
                st.markdown("#### 📊 통계적 기술 지표 검증")
                stats_summary = []
                for kw in keywords:
                    sub_df = df_trend[df_trend["키워드"] == kw]
                    if sub_df.empty:
                        continue
                    ratios = sub_df["검색량 비율"].values
                    
                    mean_val = np.mean(ratios)
                    median_val = np.median(ratios)
                    max_val = np.max(ratios)
                    min_val = np.min(ratios)
                    std_val = np.std(ratios)
                    
                    skew_val = skew(ratios)
                    kurt_val = kurtosis(ratios)
                    
                    q25, q75 = np.percentile(ratios, [25, 75])
                    iqr = q75 - q25
                    lower_bound = q25 - 1.5 * iqr
                    upper_bound = q75 + 1.5 * iqr
                    outliers_count = np.sum((ratios < lower_bound) | (ratios > upper_bound))
                    
                    stats_summary.append({
                        "키워드": kw,
                        "평균": round(mean_val, 2),
                        "중앙값": round(median_val, 2),
                        "최댓값": round(max_val, 2),
                        "최솟값": round(min_val, 2),
                        "표준편차": round(std_val, 2),
                        "왜도 (Skewness)": round(skew_val, 2),
                        "첨도 (Kurtosis)": round(kurt_val, 2),
                        "이상치 개수 (IQR 기준)": outliers_count
                    })
                    
                df_stats = pd.DataFrame(stats_summary)
                st.dataframe(df_stats, use_container_width=True, hide_index=True)
                
                csv = df_trend.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 검색어 트렌드 데이터 다운로드 (CSV)",
                    data=csv,
                    file_name=f"naver_trend_{start_date}_{end_date}.csv",
                    mime="text/csv",
                )

# -----------------------------------------------------------------------------
# 헬퍼 함수: 쇼핑 시뮬레이션 데이터 생성기
# -----------------------------------------------------------------------------
def generate_mock_shopping_data(keyword: str, count: int = 60) -> list:
    import random
    seed_val = sum(ord(c) for c in keyword)
    rng = random.Random(seed_val)
    
    keyword_profiles = {
        "생리대": {
            "brands": ["유한킴벌리", "좋은느낌", "화이트", "쏘피", "시크릿데이", "라엘", "바디피트", "순수한면", "템포"],
            "base_price": 14800,
            "price_std": 5500,
            "suffixes": ["중형 36P x 2팩", "대형 날개형 32P", "입는 오버나이트 L 8P", "순면 감촉 팬티라이너 롱 80P", "슈퍼롱 오버나이트 10P x 3"]
        },
        "노트북": {
            "brands": ["삼성전자", "LG전자", "Apple", "레노버", "ASUS", "한성컴퓨터", "HP", "DELL"],
            "base_price": 1350000,
            "price_std": 450000,
            "suffixes": ["16인치 i7 16GB 512GB", "14인치 슬림 M3 8GB 256GB", "게이밍 RTX4060 32GB"]
        }
    }
    
    profile = keyword_profiles.get(keyword, {
        "brands": [f"{keyword}탑브랜드", f"{keyword}스탠다드", f"{keyword}프리미엄", "자연주의", "데일리픽"],
        "base_price": 28000,
        "price_std": 11000,
        "suffixes": ["실속 세트 (인기상품)", "프리미엄 에디션", "대용량 패키지 1+1", "스타터 키트 구성"]
    })
    
    malls = ["네이버 스마트스토어", "쿠팡", "11번가", "G마켓", "SSG닷컴", "올리브영 온라인몰"]
    items = []
    
    for i in range(count):
        brand = rng.choice(profile["brands"])
        suffix = rng.choice(profile["suffixes"])
        title = f"[{brand}] {keyword} {suffix}"
        
        price_raw = max(3500, int(rng.gauss(profile["base_price"], profile["price_std"])))
        lprice = round(price_raw / 100) * 100
        hprice = round((lprice * rng.uniform(1.08, 1.28)) / 100) * 100
        mall = rng.choice(malls)
        
        items.append({
            "title": title,
            "link": f"https://search.shopping.naver.com/search/all?query={keyword}",
            "image": "",
            "lprice": str(lprice),
            "hprice": str(hprice),
            "mallName": mall,
            "productId": str(10000000 + i),
            "productType": "1",
            "brand": brand,
            "maker": brand,
            "category1": "생활/건강",
            "category2": "소비재"
        })
        
    return items

# -----------------------------------------------------------------------------
# Tab 2: 쇼핑 분석
# -----------------------------------------------------------------------------
with selected_tab[2]:
    st.markdown(f"### 🛒 '{selected_kw}' 쇼핑 검색 데이터 입체 분석")
    st.markdown("네이버 쇼핑 상품 검색 결과를 수집하여 가격 분포와 브랜드 점유율을 분석합니다.")
    
    if selected_kw:
        params = {"query": selected_kw, "display": 100, "start": 1, "sort": "sim"}
        with st.spinner("쇼핑 데이터 수집 중..."):
            res = fetch_naver_api("https://openapi.naver.com/v1/search/shop.json", headers=headers_get, params=params)
            
        shopping_items = []
        is_simulation = False
        
        if res["status"] == "error":
            st.info(
                "📌 **안내**: 네이버 오픈API 정책 변경에 대응하여 키워드 기반 시뮬레이션 데이터로 분석 결과를 제공합니다.\n\n"
                "💡 공식 쇼핑 빅데이터 분석은 **'📊 쇼핑 트렌드 분석'** 탭을 이용해 주세요."
            )
            shopping_items = generate_mock_shopping_data(selected_kw)
            is_simulation = True
        else:
            shopping_items = res["data"].get("items", [])
            
        if not shopping_items:
            st.warning("수집된 상품 정보가 없습니다.")
        else:
            products = []
            for item in shopping_items:
                title = item["title"].replace("<b>", "").replace("</b>", "")
                lprice = int(item["lprice"]) if item.get("lprice") else 0
                hprice = int(item["hprice"]) if item.get("hprice") else 0
                products.append({
                    "상품명": title,
                    "최저가": lprice,
                    "최고가": hprice,
                    "브랜드": item.get("brand", "기타/미분류") if item.get("brand") else "기타/미분류",
                    "판매처": item.get("mallName", "기타")
                })
            
            df_prod = pd.DataFrame(products)
            df_prod = df_prod[df_prod["최저가"] > 0]
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### 1. 주요 브랜드별 점유율 (상위 7개)")
                brand_counts = df_prod["브랜드"].value_counts().reset_index()
                brand_counts.columns = ["브랜드", "등록 상품수"]
                fig_brand = px.pie(brand_counts.head(7), values="등록 상품수", names="브랜드", hole=0.4)
                st.plotly_chart(fig_brand, use_container_width=True)
                
            with col2:
                st.markdown("#### 2. 최저 가격대 분포 (히스토그램 & 박스플롯)")
                fig_price_hist = px.histogram(df_prod, x="최저가", nbins=20, marginal="box", color_discrete_sequence=["#1EC800"])
                st.plotly_chart(fig_price_hist, use_container_width=True)
            
            st.markdown("##### 📋 수집된 상품 상세 리스트 (가격 오름차순)")
            sorted_df = df_prod.sort_values(by="최저가").reset_index(drop=True)
            st.dataframe(sorted_df, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# Tab 3: 블로그 분석
# -----------------------------------------------------------------------------
with selected_tab[3]:
    st.markdown(f"### ✍️ '{selected_kw}' 네이버 블로그 검색 데이터 분석")
    if selected_kw:
        params = {"query": selected_kw, "display": 100, "start": 1, "sort": "sim"}
        with st.spinner("블로그 데이터 수집 중..."):
            res = fetch_naver_api("https://openapi.naver.com/v1/search/blog.json", headers=headers_get, params=params)
            
        if res["status"] == "error":
            st.error(res["message"])
        else:
            blog_items = res["data"].get("items", [])
            if not blog_items:
                st.warning("수집된 블로그 포스트가 없습니다.")
            else:
                blogs = []
                for item in blog_items:
                    title = item["title"].replace("<b>", "").replace("</b>", "")
                    postdate = pd.to_datetime(item["postdate"], format="%Y%m%d", errors='coerce')
                    blogs.append({
                        "제목": title,
                        "블로거명": item.get("bloggername", "알 수 없음"),
                        "작성일": postdate,
                        "링크": item["link"]
                    })
                df_blog = pd.DataFrame(blogs).dropna(subset=["작성일"])
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown("#### 1. 일자별 블로그 포스팅 추이")
                    df_date_trend = df_blog["작성일"].value_counts().reset_index()
                    df_date_trend.columns = ["작성일", "포스팅수"]
                    fig_date = px.bar(df_date_trend.sort_values("작성일"), x="작성일", y="포스팅수", color_discrete_sequence=["#228B22"])
                    st.plotly_chart(fig_date, use_container_width=True)
                with col2:
                    st.markdown("#### 2. 다작 블로거 랭킹")
                    blogger_counts = df_blog["블로거명"].value_counts().reset_index()
                    blogger_counts.columns = ["블로거명", "발행 건수"]
                    fig_blogger = px.bar(blogger_counts.head(10), x="발행 건수", y="블로거명", orientation="h")
                    fig_blogger.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig_blogger, use_container_width=True)
                
                st.dataframe(df_blog, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# Tab 4: 카페글 분석
# -----------------------------------------------------------------------------
with selected_tab[4]:
    st.markdown(f"### ☕ '{selected_kw}' 네이버 카페글 검색 데이터 분석")
    if selected_kw:
        params = {"query": selected_kw, "display": 100, "start": 1, "sort": "sim"}
        with st.spinner("카페글 데이터 수집 중..."):
            res = fetch_naver_api("https://openapi.naver.com/v1/search/cafearticle.json", headers=headers_get, params=params)
            
        if res["status"] == "error":
            st.error(res["message"])
        else:
            cafe_items = res["data"].get("items", [])
            if not cafe_items:
                st.warning("수집된 카페 게시글이 없습니다.")
            else:
                cafes = [{"게시글 제목": item["title"].replace("<b>", "").replace("</b>", ""),
                          "카페이름": item.get("cafename", "미분류 카페"),
                          "상세링크": item["link"]} for item in cafe_items]
                df_cafe = pd.DataFrame(cafes)
                cafe_dist = df_cafe["카페이름"].value_counts().reset_index()
                cafe_dist.columns = ["카페이름", "게시글 수"]
                
                fig_cafe_pie = px.pie(cafe_dist.head(8), values="게시글 수", names="카페이름", title="주요 활성 카페 점유율")
                st.plotly_chart(fig_cafe_pie, use_container_width=True)
                st.dataframe(df_cafe, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# Tab 5: 뉴스 분석
# -----------------------------------------------------------------------------
with selected_tab[5]:
    st.markdown(f"### 📰 '{selected_kw}' 네이버 뉴스 데이터 분석")
    if selected_kw:
        params = {"query": selected_kw, "display": 100, "start": 1, "sort": "sim"}
        with st.spinner("뉴스 데이터 수집 중..."):
            res = fetch_naver_api("https://openapi.naver.com/v1/search/news.json", headers=headers_get, params=params)
            
        if res["status"] == "error":
            st.error(res["message"])
        else:
            news_items = res["data"].get("items", [])
            if not news_items:
                st.warning("수집된 뉴스 기사가 없습니다.")
            else:
                news_list = []
                for item in news_items:
                    orig_link = item.get("originallink", "")
                    domain = orig_link.split("//")[-1].split("/")[0].replace("www.", "") if "//" in orig_link else "네이버뉴스"
                    news_list.append({
                        "기사제목": item["title"].replace("<b>", "").replace("</b>", ""),
                        "언론사": domain,
                        "발행일자": pd.to_datetime(item["pubDate"], errors='coerce'),
                        "링크": orig_link
                    })
                df_news = pd.DataFrame(news_list).dropna(subset=["발행일자"])
                
                media_dist = df_news["언론사"].value_counts().reset_index()
                media_dist.columns = ["언론사", "보도 건수"]
                fig_media = px.pie(media_dist.head(8), values="보도 건수", names="언론사", title="주요 보도 언론사 점유율")
                st.plotly_chart(fig_media, use_container_width=True)
                st.dataframe(df_news, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# Tab 6: 쇼핑 트렌드 분석 (데이터랩 쇼핑인사이트)
# -----------------------------------------------------------------------------
with selected_tab[6]:
    st.markdown(f"### 📊 데이터랩 쇼핑인사이트 카테고리 트렌드 분석")
    st.markdown(f"선택된 카테고리 **'{selected_category}' (ID: {selected_category_id})** 내 쇼핑 클릭 트렌드")
    
    shopping_insight_data = {
        "startDate": start_date.strftime("%Y-%m-%d"),
        "endDate": end_date.strftime("%Y-%m-%d"),
        "timeUnit": "date",
        "category": [{"name": selected_category, "param": [selected_category_id]}]
    }
    
    with st.spinner("네이버 쇼핑인사이트 트렌드 수집 중..."):
        res = fetch_naver_api(
            "https://openapi.naver.com/v1/datalab/shopping/categories",
            headers=headers_post,
            method="POST",
            json_data=shopping_insight_data
        )
        
    if res["status"] == "error":
        st.error(res["message"])
    else:
        results = res["data"].get("results", [])
        df_list = []
        for group in results:
            title = group.get("title")
            for dp in group.get("data", []):
                df_list.append({
                    "날짜": pd.to_datetime(dp["period"]),
                    "카테고리": title,
                    "클릭량 비율": dp["ratio"]
                })
        if df_list:
            df_shop_trend = pd.DataFrame(df_list)
            fig_shop_line = px.line(df_shop_trend, x="날짜", y="클릭량 비율", color="카테고리", template="plotly_white")
            st.plotly_chart(fig_shop_line, use_container_width=True)