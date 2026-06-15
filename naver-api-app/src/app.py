"""
파일명: app.py
설명: 네이버 오픈API(검색어 트렌드, 쇼핑, 블로그, 카페글, 뉴스, 쇼핑 트렌드)를 통합 연동하여
      데이터를 분석하고 Plotly를 활용해 시각화하는 Streamlit 대시보드 메인 프로그램입니다.
생성일: 2026-06-08
수정일: 2026-06-15 (성능 최적화를 위한 API 캐싱 기능 및 새로고침 UI 추가)
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

# .env 파일 로드 (.env 파일이 app.py의 상위 폴더인 naver-api-app에 위치함)
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


# -----------------------------------------------------------------------------
# 페이지 설정 및 테마 정의
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="네이버 API 종합 분석 대시보드",
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
# API 호출 공통 유틸리티 함수
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
    
    # 딕셔너리를 캐시 가능한 형태(정렬된 튜플)로 변환
    params_tuple = tuple(sorted(params.items())) if params else None
    json_data_str = json.dumps(json_data, sort_keys=True) if json_data else None
    
    try:
        # 캐싱된 내부 함수 호출
        res = _fetch_naver_api_cached(
            url, client_id, client_secret, params_tuple, method, json_data_str
        )
        
        # 캐시 Hit/Miss 판별 (5초 경과 여부 기준)
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
            elif status_code == 429:
                msg = "호출 한도 초과: 오늘 사용 가능한 호출 할당량을 모두 소진했습니다."
            else:
                msg = f"오류 발생 (HTTP {status_code}): {err_msg_content}"
            return {"status": "error", "message": msg}
        else:
            msg = err_msg.split(":", 1)[-1]
            return {"status": "error", "message": f"네트워크 통신 중 오류가 발생했습니다: {msg}"}

# -----------------------------------------------------------------------------
# 사이드바 입력 제어 영역 (API Key & 검색 파라미터)
# -----------------------------------------------------------------------------
st.sidebar.image("https://developers.naver.com/inc/dev-center/images/ndev_header_logo.png", width=200)
st.sidebar.markdown("### 🔑 API 인증 설정")

# Streamlit 배포 환경 및 로컬 환경변수 통합 로드
client_id = ""
client_secret = ""

# 1. st.secrets에 등록된 값이 있을 경우 우선 사용
if "NAVER_CLIENT_ID" in st.secrets:
    client_id = st.secrets["NAVER_CLIENT_ID"]
else:
    client_id = os.getenv("NAVER_CLIENT_ID", "")

if "NAVER_CLIENT_SECRET" in st.secrets:
    client_secret = st.secrets["NAVER_CLIENT_SECRET"]
else:
    client_secret = os.getenv("NAVER_CLIENT_SECRET", "")

# 세션 상태 반영 (대시보드 UI에 노출되지 않도록 처리)
st.session_state.client_id = client_id.strip()
st.session_state.client_secret = client_secret.strip()

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔍 분석 설정")

# 쇼핑 카테고리 매핑 (data-cid 기반)
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

# 검색 키워드 입력 (,로 구분)
keyword_raw = st.sidebar.text_input("분석 검색어 (쉼표로 구분)", value="무선이어폰, 스마트워치, 보조배터리")
keywords = [k.strip() for k in keyword_raw.split(",") if k.strip()]

# 검색 기간 설정 (기본 최근 1개월)
today = datetime.date.today()
last_month = today - datetime.timedelta(days=30)
start_date = st.sidebar.date_input("조회 시작일", value=last_month, max_value=today)
end_date = st.sidebar.date_input("조회 종료일", value=today, min_value=start_date, max_value=today)

st.sidebar.markdown("---")

if st.sidebar.button("🔄 데이터 새로고침 (캐시 초기화)", use_container_width=True):
    st.cache_data.clear()
    st.toast("캐시가 성공적으로 초기화되었습니다!", icon="🔄")
    st.rerun()

st.sidebar.info("💡 **가이드**: 인증 정보를 입력하고 분석 키워드 및 쇼핑 카테고리를 지정하면 실시간 네이버 OpenAPI 데이터를 수집하고 시각화합니다.")

# -----------------------------------------------------------------------------
# 메인 화면 구성
# -----------------------------------------------------------------------------
st.markdown('<div class="main-title">Naver OpenAPI 종합 데이터 대시보드</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">오픈API 데이터를 기반으로 검색 트렌드, 블로그, 카페글, 뉴스, 쇼핑 데이터 분석 정보를 시각화합니다.</div>', unsafe_allow_html=True)

# API 인증 여부 사전 체크
if not st.session_state.client_id or not st.session_state.client_secret:
    st.warning("⚠️ 프로젝트 내 `.env` 파일에 네이버 OpenAPI **NAVER_CLIENT_ID**와 **NAVER_CLIENT_SECRET**을 올바르게 설정했는지 확인해 주세요.")
    st.stop()

# 공통 헤더 구성 (GET 및 POST 분리)
headers_get = {
    "X-Naver-Client-Id": st.session_state.client_id,
    "X-Naver-Client-Secret": st.session_state.client_secret
}

headers_post = {
    "X-Naver-Client-Id": st.session_state.client_id,
    "X-Naver-Client-Secret": st.session_state.client_secret,
    "Content-Type": "application/json"
}

# 탭 메뉴 설정
tab_names = [
    "📈 검색어 트렌드", 
    "🛒 쇼핑 분석", 
    "✍️ 블로그 트렌드", 
    "☕ 카페글 분석", 
    "📰 뉴스 분석", 
    "📊 쇼핑 트렌드 분석"
]
selected_tab = st.tabs(tab_names)

# 분석용 대표 키워드 선택 (쇼핑, 블로그, 카페, 뉴스 등 단일 키워드 쿼리용)
selected_kw = st.selectbox("🎯 세부 분석 대상 키워드 선택", options=keywords)

# 마지막 API 호출에 대한 캐시 상태 안내 UI
if "last_api_status" in st.session_state:
    status_info = st.session_state["last_api_status"]
    dt = datetime.datetime.fromtimestamp(status_info["fetched_at"])
    time_str = dt.strftime("%H:%M:%S")
    if status_info["is_hit"]:
        st.info(f"💡 **캐시 데이터 사용 중**: 최근 1시간 이내에 캐싱된 데이터를 표시하고 있습니다. (마지막 수집 시간: {time_str})")
    else:
        st.success(f"🔄 **실시간 데이터 로드 완료**: 원격 네이버 API를 통해 실시간 데이터를 직접 호출했습니다. (수집 시간: {time_str})")

# -----------------------------------------------------------------------------
# Tab 1: 검색어 트렌드 (데이터랩)
# -----------------------------------------------------------------------------
with selected_tab[0]:
    st.markdown("### 📈 네이버 데이터랩 통합 검색어 트렌드")
    st.markdown("지정한 키워드들의 조회 기간 내 상대적 검색 빈도를 비교 분석합니다.")
    
    if not keywords:
        st.error("분석할 검색어를 입력해 주세요.")
    else:
        # 데이터랩 API 요청 형식 구성
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
            # 데이터프레임 변환
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
                
                # Plotly 라인 차트 구현
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
                
                # 통계 검증 분석 (IQR, 이상치, 평균, 왜도, 첨도)
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
                    
                    # 왜도 및 첨도
                    skew_val = skew(ratios)
                    kurt_val = kurtosis(ratios)
                    
                    # 이상치 탐지 (IQR)
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
                
                # 데이터 인사이트 자동 생성
                st.markdown("##### 💡 데이터 트렌드 요약 리포트")
                for index, row in df_stats.iterrows():
                    kw = row["키워드"]
                    skew_txt = "우측으로 꼬리가 긴(오른쪽 비대칭)" if row["왜도 (Skewness)"] > 0.5 else ("좌측으로 꼬리가 긴(왼쪽 비대칭)" if row["왜도 (Skewness)"] < -0.5 else "대칭적인")
                    outlier_txt = f"총 {row['이상치 개수 (IQR 기준)']}개의 이상치(급격한 검색 급증/급감 구간)가 관측되었습니다." if row['이상치 개수 (IQR 기준)'] > 0 else "이상치 구간이 거의 없어 비교적 안정적인 검색 흐름을 보입니다."
                    st.write(f"- **{kw}** 키워드는 평균 검색량 비율 **{row['평균']}%**, 최댓값 **{row['최댓값']}%**을 기록했습니다. 분포 형태는 **{skew_txt}** 구조이며, {outlier_txt}")

                # CSV 다운로드 버튼
                csv = df_trend.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 검색어 트렌드 데이터 다운로드 (CSV)",
                    data=csv,
                    file_name=f"naver_trend_{start_date}_{end_date}.csv",
                    mime="text/csv",
                )

# -----------------------------------------------------------------------------
# Tab 2: 쇼핑 분석
# -----------------------------------------------------------------------------
with selected_tab[1]:
    st.markdown(f"### 🛒 '{selected_kw}' 쇼핑 검색 데이터 입체 분석")
    st.markdown("네이버 쇼핑 상품 검색 결과를 수집하여 가격 분포와 브랜드 점유율을 분석합니다.")
    
    if selected_kw:
        params = {
            "query": selected_kw,
            "display": 100,  # 최대 수집 개수
            "start": 1,
            "sort": "sim"
        }
        with st.spinner("쇼핑 데이터 수집 중..."):
            res = fetch_naver_api(
                "https://openapi.naver.com/v1/search/shop.json", 
                headers=headers_get, 
                params=params
            )
            
        if res["status"] == "error":
            st.error(res["message"])
        else:
            shopping_items = res["data"].get("items", [])
            if not shopping_items:
                st.warning("수집된 상품 정보가 없습니다.")
            else:
                # 데이터 가공
                products = []
                for item in shopping_items:
                    # HTML 태그 제거
                    title = item["title"].replace("<b>", "").replace("</b>", "")
                    lprice = int(item["lprice"]) if item.get("lprice") else 0
                    hprice = int(item["hprice"]) if item.get("hprice") else 0
                    
                    products.append({
                        "상품명": title,
                        "최저가": lprice,
                        "최고가": hprice,
                        "브랜드": item.get("brand", "기타/미분류") if item.get("brand") else "기타/미분류",
                        "제조사": item.get("maker", "기타/미분류") if item.get("maker") else "기타/미분류",
                        "판매처": item.get("mallName", "기타")
                    })
                
                df_prod = pd.DataFrame(products)
                df_prod = df_prod[df_prod["최저가"] > 0]  # 가격 유효 데이터만 필터링
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### 1. 주요 브랜드별 점유율 (상위 7개)")
                    brand_counts = df_prod["브랜드"].value_counts().reset_index()
                    brand_counts.columns = ["브랜드", "등록 상품수"]
                    
                    # 상위 7개 이외는 '기타'로 합산
                    if len(brand_counts) > 7:
                        top_brands = brand_counts.iloc[:7]
                        other_sum = brand_counts.iloc[7:]["등록 상품수"].sum()
                        top_brands = pd.concat([top_brands, pd.DataFrame([{"브랜드": "기타", "등록 상품수": other_sum}])], ignore_index=True)
                    else:
                        top_brands = brand_counts
                    
                    fig_brand = px.pie(
                        top_brands, 
                        values="등록 상품수", 
                        names="브랜드", 
                        hole=0.4, 
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    st.plotly_chart(fig_brand, use_container_width=True)
                    
                with col2:
                    st.markdown("#### 2. 최저 가격대 분포 (히스토그램)")
                    fig_price_hist = px.histogram(
                        df_prod, 
                        x="최저가", 
                        nbins=20, 
                        color_discrete_sequence=["#1EC800"],
                        labels={"최저가": "최저가 (원)"},
                        marginal="box" # 상단에 박스플롯 추가하여 이상치 및 분위 확인 지원
                    )
                    st.plotly_chart(fig_price_hist, use_container_width=True)
                
                # 쇼핑 기술통계량 분석
                st.markdown("#### 📊 상품 최저가 요약 통계 정보")
                
                price_mean = df_prod["최저가"].mean()
                price_median = df_prod["최저가"].median()
                price_max = df_prod["최저가"].max()
                price_min = df_prod["최저가"].min()
                price_std = df_prod["최저가"].std()
                
                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                col_m1.metric("평균 가격 (원)", f"{int(price_mean):,}")
                col_m2.metric("중앙값 가격 (원)", f"{int(price_median):,}")
                col_m3.metric("최저가 (원)", f"{int(price_min):,}")
                col_m4.metric("최고가 (원)", f"{int(price_max):,}")
                
                st.markdown("##### 📋 수집된 상품 상세 리스트 (가격 오름차순)")
                st.dataframe(df_prod.sort_values(by="최저가"), use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# Tab 3: 블로그 분석
# -----------------------------------------------------------------------------
with selected_tab[2]:
    st.markdown(f"### ✍️ '{selected_kw}' 네이버 블로그 검색 데이터 분석")
    st.markdown("최신 블로그 포스팅 목록을 분석하여 게시 시점 및 출처 분포를 분석합니다.")
    
    if selected_kw:
        params = {
            "query": selected_kw,
            "display": 100,
            "start": 1,
            "sort": "sim"
        }
        with st.spinner("블로그 데이터 수집 중..."):
            res = fetch_naver_api(
                "https://openapi.naver.com/v1/search/blog.json", 
                headers=headers_get, 
                params=params
            )
            
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
                    bloggerlink = item.get("bloggerlink", "")
                    
                    blogs.append({
                        "제목": title,
                        "블로거명": item.get("bloggername", "알 수 없음"),
                        "작성일": postdate,
                        "링크": item["link"]
                    })
                
                df_blog = pd.DataFrame(blogs).dropna(subset=["작성일"])
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown("#### 1. 작성일별 포스팅 수 추이 (시계열 바 차트)")
                    df_date_trend = df_blog["작성일"].value_counts().reset_index()
                    df_date_trend.columns = ["작성일", "포스팅수"]
                    df_date_trend = df_date_trend.sort_values("작성일")
                    
                    fig_date = px.bar(
                        df_date_trend, 
                        x="작성일", 
                        y="포스팅수", 
                        color_discrete_sequence=["#228B22"],
                        title="일자별 신규 블로그 발행 트렌드"
                    )
                    st.plotly_chart(fig_date, use_container_width=True)
                    
                with col2:
                    st.markdown("#### 2. 다작 블로거 랭킹")
                    blogger_counts = df_blog["블로거명"].value_counts().reset_index()
                    blogger_counts.columns = ["블로거명", "발행 건수"]
                    fig_blogger = px.bar(
                        blogger_counts.head(10), 
                        x="발행 건수", 
                        y="블로거명", 
                        orientation="h",
                        color_discrete_sequence=["#4682B4"],
                        title="탑 블로거별 수집 게시글 수"
                    )
                    fig_blogger.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig_blogger, use_container_width=True)
                
                st.markdown("##### 📋 수집된 블로그 상세 포스트 목록")
                st.dataframe(df_blog, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# Tab 4: 카페글 분석
# -----------------------------------------------------------------------------
with selected_tab[3]:
    st.markdown(f"### ☕ '{selected_kw}' 네이버 카페글 검색 데이터 분석")
    st.markdown("네이버 카페에 등록된 공개 게시글의 데이터를 수집하여 주요 활동 카페 정보를 분석합니다.")
    
    if selected_kw:
        params = {
            "query": selected_kw,
            "display": 100,
            "start": 1,
            "sort": "sim"
        }
        with st.spinner("카페글 데이터 수집 중..."):
            res = fetch_naver_api(
                "https://openapi.naver.com/v1/search/cafearticle.json", 
                headers=headers_get, 
                params=params
            )
            
        if res["status"] == "error":
            st.error(res["message"])
        else:
            cafe_items = res["data"].get("items", [])
            if not cafe_items:
                st.warning("수집된 카페 게시글이 없습니다.")
            else:
                cafes = []
                for item in cafe_items:
                    title = item["title"].replace("<b>", "").replace("</b>", "")
                    cafes.append({
                        "게시글 제목": title,
                        "카페이름": item.get("cafename", "미분류 카페"),
                        "카페주소": item.get("cafeurl", ""),
                        "상세링크": item["link"]
                    })
                
                df_cafe = pd.DataFrame(cafes)
                
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.markdown("#### 1. 카페별 게시글 분포 점유율")
                    cafe_dist = df_cafe["카페이름"].value_counts().reset_index()
                    cafe_dist.columns = ["카페이름", "게시글 수"]
                    
                    if len(cafe_dist) > 8:
                        top_cafes = cafe_dist.iloc[:8]
                        other_sum = cafe_dist.iloc[8:]["게시글 수"].sum()
                        top_cafes = pd.concat([top_cafes, pd.DataFrame([{"카페이름": "기타 카페", "게시글 수": other_sum}])], ignore_index=True)
                    else:
                        top_cafes = cafe_dist
                    
                    fig_cafe_pie = px.pie(
                        top_cafes, 
                        values="게시글 수", 
                        names="카페이름", 
                        title="주요 활성 네이버 카페 점유율",
                        color_discrete_sequence=px.colors.qualitative.Safe
                    )
                    st.plotly_chart(fig_cafe_pie, use_container_width=True)
                    
                with col2:
                    st.markdown("#### 2. 주요 커뮤니티 분포 목록")
                    st.dataframe(cafe_dist, use_container_width=True, hide_index=True)
                
                st.markdown("##### 📋 카페 검색결과 게시글 리스트")
                st.dataframe(df_cafe, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# Tab 5: 뉴스 분석
# -----------------------------------------------------------------------------
with selected_tab[4]:
    st.markdown(f"### 📰 '{selected_kw}' 네이버 뉴스 데이터 분석")
    st.markdown("최신 관련 뉴스 데이터를 분석하여 보도 매체(언론사) 및 보도 시점의 통계 트렌드를 제시합니다.")
    
    if selected_kw:
        params = {
            "query": selected_kw,
            "display": 100,
            "start": 1,
            "sort": "sim"
        }
        with st.spinner("뉴스 데이터 수집 중..."):
            res = fetch_naver_api(
                "https://openapi.naver.com/v1/search/news.json", 
                headers=headers_get, 
                params=params
            )
            
        if res["status"] == "error":
            st.error(res["message"])
        else:
            news_items = res["data"].get("items", [])
            if not news_items:
                st.warning("수집된 뉴스 기사가 없습니다.")
            else:
                news_list = []
                for item in news_items:
                    title = item["title"].replace("<b>", "").replace("</b>", "")
                    description = item["description"].replace("<b>", "").replace("</b>", "")
                    # 언론사 정보 파싱 (간단히 originallink의 도메인 추출 혹은 알려진 패턴 기준)
                    orig_link = item.get("originallink", "")
                    media_name = "기타 언론사"
                    if "naver.com" in orig_link:
                        media_name = "네이버뉴스 직접제공"
                    else:
                        domain = orig_link.split("//")[-1].split("/")[0] if "//" in orig_link else ""
                        media_name = domain.replace("www.", "") if domain else "기타"
                        
                    pub_date = pd.to_datetime(item["pubDate"], errors='coerce')
                    
                    news_list.append({
                        "기사제목": title,
                        "언론사(도메인)": media_name,
                        "발행일자": pub_date,
                        "원문링크": orig_link,
                        "기사내용 요약": description
                    })
                    
                df_news = pd.DataFrame(news_list).dropna(subset=["발행일자"])
                
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.markdown("#### 1. 주요 보도 언론사 점유율")
                    media_dist = df_news["언론사(도메인)"].value_counts().reset_index()
                    media_dist.columns = ["언론사(도메인)", "보도 건수"]
                    
                    if len(media_dist) > 8:
                        top_media = media_dist.iloc[:8]
                        other_sum = media_dist.iloc[8:]["보도 건수"].sum()
                        top_media = pd.concat([top_media, pd.DataFrame([{"언론사(도메인)": "기타 언론사 합산", "보도 건수": other_sum}])], ignore_index=True)
                    else:
                        top_media = media_dist
                        
                    fig_media = px.pie(
                        top_media, 
                        values="보도 건수", 
                        names="언론사(도메인)", 
                        color_discrete_sequence=px.colors.qualitative.Bold
                    )
                    st.plotly_chart(fig_media, use_container_width=True)
                    
                with col2:
                    st.markdown("#### 2. 날짜별 보도 건수 추이")
                    # 날짜 단위로 변환 후 카운트
                    df_news["날짜(일)"] = df_news["발행일자"].dt.date
                    news_date_trend = df_news["날짜(일)"].value_counts().reset_index()
                    news_date_trend.columns = ["날짜(일)", "기사 수"]
                    news_date_trend = news_date_trend.sort_values("날짜(일)")
                    
                    fig_news_trend = px.line(
                        news_date_trend, 
                        x="날짜(일)", 
                        y="기사 수", 
                        color_discrete_sequence=["#FF4500"],
                        markers=True
                    )
                    st.plotly_chart(fig_news_trend, use_container_width=True)
                    
                st.markdown("##### 📋 뉴스 검색 결과 상세 목록")
                st.dataframe(df_news, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# Tab 6: 쇼핑 트렌드 분석 (데이터랩 쇼핑인사이트 카테고리 연동)
# -----------------------------------------------------------------------------
with selected_tab[5]:
    st.markdown(f"### 📊 데이터랩 쇼핑인사이트 카테고리 트렌드 분석")
    st.markdown(f"선택된 카테고리 **'{selected_category}' (ID: {selected_category_id})** 내에서 지정한 검색어들의 쇼핑 트렌드(클릭량 추이)를 분석합니다.")
    
    if not keywords:
        st.error("분석할 검색어를 입력해 주세요.")
    else:
        # 데이터랩 쇼핑인사이트 API 요청 바디 구성
        # /v1/datalab/shopping/categories API는 category 배열에 카테고리 정보를 전달해야 합니다
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
            api_data = res["data"]
            results = api_data.get("results", [])
            df_list = []
            
            for group in results:
                title = group.get("title")
                data_points = group.get("data", [])
                for dp in data_points:
                    df_list.append({
                        "날짜": pd.to_datetime(dp["period"]),
                        "카테고리": title,
                        "클릭량 비율": dp["ratio"]
                    })
            
            if not df_list:
                st.warning("선택한 카테고리에 해당하는 쇼핑 클릭 데이터가 없습니다.")
            else:
                df_shop_trend = pd.DataFrame(df_list)
                
                # Plotly 라인 차트 시각화
                fig_shop_line = px.line(
                    df_shop_trend,
                    x="날짜",
                    y="클릭량 비율",
                    color="카테고리",
                    title=f"카테고리 [{selected_category}] 쇼핑 클릭 트렌드 ({start_date} ~ {end_date})",
                    labels={"클릭량 비율": "상대적 클릭량 비율 (%)", "날짜": "조회 일자"},
                    template="plotly_white"
                )
                fig_shop_line.update_layout(hovermode="x unified")
                st.plotly_chart(fig_shop_line, use_container_width=True)
                
                # 통계 검증 분석 (평균, 중앙값, 왜도, 첨도, 분산)
                st.markdown("#### 📊 쇼핑 클릭 트렌드 기술 통계 지표")
                
                stats_summary = []
                # 카테고리별 통계 계산 (API 응답의 title 기반)
                for cat_name in df_shop_trend["카테고리"].unique():
                    sub_df = df_shop_trend[df_shop_trend["카테고리"] == cat_name]
                    if sub_df.empty:
                        continue
                    ratios = sub_df["클릭량 비율"].values
                    
                    mean_val = np.mean(ratios)
                    median_val = np.median(ratios)
                    max_val = np.max(ratios)
                    min_val = np.min(ratios)
                    std_val = np.std(ratios)
                    
                    skew_val = skew(ratios)
                    kurt_val = kurtosis(ratios)
                    
                    # 이상치 탐지 (IQR)
                    q25, q75 = np.percentile(ratios, [25, 75])
                    iqr = q75 - q25
                    lower_bound = q25 - 1.5 * iqr
                    upper_bound = q75 + 1.5 * iqr
                    outliers_count = np.sum((ratios < lower_bound) | (ratios > upper_bound))
                    
                    stats_summary.append({
                        "카테고리": cat_name,
                        "평균 클릭비율": round(mean_val, 2),
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
                
                # 쇼핑 카테고리 트렌드 진단 리포트
                st.markdown("#### 🧐 카테고리 트렌드 분석 진단 리포트")
                
                if not df_stats.empty:
                    row = df_stats.iloc[0]
                    cat_name = row["카테고리"]
                    avg_val = row["평균 클릭비율"]
                    std_v = row["표준편차"]
                    skew_v = row["왜도 (Skewness)"]
                    outlier_cnt = row["이상치 개수 (IQR 기준)"]
                    
                    skew_txt = "우측으로 꼬리가 긴(오른쪽 비대칭)" if skew_v > 0.5 else ("좌측으로 꼬리가 긴(왼쪽 비대칭)" if skew_v < -0.5 else "대칭적인")
                    outlier_txt = f"총 {outlier_cnt}개의 이상치(급격한 클릭 급증/급감 구간)가 관측되었습니다." if outlier_cnt > 0 else "이상치 구간이 거의 없어 비교적 안정적인 클릭 흐름을 보입니다."
                    
                    st.write(f"- **'{cat_name}'** 카테고리의 평균 클릭 비율은 **{avg_val}%**, 표준편차는 **{std_v}**입니다.")
                    st.write(f"- 분포 형태는 **{skew_txt}** 구조이며, {outlier_txt}")

                # CSV 다운로드 제공
                csv_data = df_shop_trend.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 쇼핑 트렌드 데이터 다운로드 (CSV)",
                    data=csv_data,
                    file_name=f"naver_shopping_trend_{selected_category_id}_{start_date}_{end_date}.csv",
                    mime="text/csv"
                )

