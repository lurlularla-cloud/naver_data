"""
파일명: app.py
설명: 네이버 오픈API + 네이버 검색광고 API 기반 
      생리대/위생용품 브랜드·경쟁사 종합 인텔리전스 전략 대시보드
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

import hmac
import hashlib
import base64
import time

# .env 파일 로드
env_path = Path(__file__).resolve().parent.parent / ".env"
if not env_path.exists():
    env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

# -----------------------------------------------------------------------------
# 1. 페이지 설정 및 모던 커스텀 테마 CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="위생용품 브랜드 경쟁 인텔리전스 대시보드",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 모던 SaaS 대시보드 커스텀 스타일 (첨부 이미지 레퍼런스 스타일)
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    * {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
    }
    
    /* 메인 배경 및 레이아웃 */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    
    /* 상단 헤더 스타일 */
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #EDEDF0;
        padding-bottom: 1rem;
        margin-bottom: 1.5rem;
    }
    .header-title {
        font-size: 1.85rem;
        font-weight: 800;
        color: #191F28;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .header-badge {
        background-color: #F2F4F6;
        color: #4E5968;
        font-size: 0.85rem;
        font-weight: 600;
        padding: 6px 14px;
        border-radius: 20px;
        border: 1px solid #E5E8EB;
    }
    
    /* 카드 컴포넌트 */
    .kpi-card {
        background: #FFFFFF;
        border: 1px solid #E5E8EB;
        border-radius: 16px;
        padding: 20px 22px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        margin-bottom: 1rem;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
    }
    .kpi-brand-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: #8B95A1;
        margin-bottom: 6px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .kpi-brand-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: #191F28;
        letter-spacing: -0.5px;
    }
    .kpi-brand-sub {
        margin-top: 8px;
        font-size: 0.85rem;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .badge-primary {
        background-color: #E8F3FF;
        color: #1B64DA;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.8rem;
    }
    .badge-highlight {
        background-color: #FFF0F1;
        color: #F04452;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.8rem;
    }

    /* 탭 디자인 커스텀 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        border-bottom: 2px solid #F2F4F6;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        font-size: 1rem;
        font-weight: 600;
        color: #8B95A1;
        padding: 0 16px;
        border-radius: 8px 8px 0 0;
    }
    .stTabs [aria-selected="true"] {
        color: #1B64DA !important;
        border-bottom: 3px solid #1B64DA !important;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 네이버 오픈API & 검색광고 API 통신 함수
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def _fetch_naver_api_cached(url, client_id, client_secret, params_tuple=None, method="GET", json_data_str=None):
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
            return {"status": "success", "data": response.json()}
        else:
            return {"status": "error", "message": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def fetch_naver_api(url, headers, params=None, method="GET", json_data=None):
    import json
    client_id = headers.get("X-Naver-Client-Id", "")
    client_secret = headers.get("X-Naver-Client-Secret", "")
    params_tuple = tuple(sorted(params.items())) if params else None
    json_data_str = json.dumps(json_data, sort_keys=True) if json_data else None
    return _fetch_naver_api_cached(url, client_id, client_secret, params_tuple, method, json_data_str)

def generate_ad_signature(timestamp: str, method: str, path: str, secret_key: str) -> str:
    message = f"{timestamp}.{method}.{path}"
    hash_obj = hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
    return base64.b64encode(hash_obj.digest()).decode('utf-8')

@st.cache_data(ttl=3600)
def fetch_naver_search_ads(keywords_tuple, customer_id, api_key, secret_key):
    if not customer_id or not api_key or not secret_key:
        return {"status": "error", "message": "검색광고 API 인증 키가 누락되었습니다."}

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

    clean_kws = [k.replace(" ", "") for k in keywords_tuple if k.strip()]
    params = {
        "hintKeywords": ",".join(clean_kws[:5]),
        "showDetail": "1"
    }

    try:
        res = requests.get(base_url + path, headers=headers, params=params, timeout=10)
        if res.status_code == 200:
            return {"status": "success", "data": res.json()}
        else:
            return {"status": "error", "message": f"검색광고 API 오류 (HTTP {res.status_code})"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# -----------------------------------------------------------------------------
# 3. 사이드바 제어 영역 (기본값: 라엘 중심 생리대 브랜드)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ 분석 파라미터")
    
    # 1. API 키 로드
    client_id = os.getenv("NAVER_CLIENT_ID", "")
    client_secret = os.getenv("NAVER_CLIENT_SECRET", "")
    ads_customer_id = os.getenv("NAVER_ADS_CUSTOMER_ID", "")
    ads_api_key = os.getenv("NAVER_ADS_API_KEY", "")
    ads_secret_key = os.getenv("NAVER_ADS_SECRET_KEY", "")

    try:
        if "NAVER_CLIENT_ID" in st.secrets: client_id = st.secrets["NAVER_CLIENT_ID"]
        if "NAVER_CLIENT_SECRET" in st.secrets: client_secret = st.secrets["NAVER_CLIENT_SECRET"]
        if "NAVER_ADS_CUSTOMER_ID" in st.secrets: ads_customer_id = st.secrets["NAVER_ADS_CUSTOMER_ID"]
        if "NAVER_ADS_API_KEY" in st.secrets: ads_api_key = st.secrets["NAVER_ADS_API_KEY"]
        if "NAVER_ADS_SECRET_KEY" in st.secrets: ads_secret_key = st.secrets["NAVER_ADS_SECRET_KEY"]
    except:
        pass

    # 2. 쇼핑 카테고리 (생활/건강 기본 선택)
    CATEGORY_MAP = {
        "생활/건강": "50000008",
        "화장품/미용": "50000002",
        "출산/육아": "50000005",
        "패션잡화": "50000001",
        "디지털/가전": "50000003"
    }
    selected_category = st.selectbox("쇼핑 분석 카테고리", options=list(CATEGORY_MAP.keys()), index=0)
    selected_category_id = CATEGORY_MAP[selected_category]

    # 3. 분석 키워드 (라엘 중심 기본값 세팅)
    keyword_raw = st.text_input(
        "분석 브랜드 키워드 (최대 5개, 쉼표 구분)", 
        value="라엘, 좋은느낌, 화이트, 이너시아, 디어스킨"
    )
    keywords = [k.strip() for k in keyword_raw.split(",") if k.strip()][:5]

    # 4. 분석 기간
    today = datetime.date.today()
    last_month = today - datetime.timedelta(days=30)
    start_date = st.date_input("조회 시작일", value=last_month, max_value=today)
    end_date = st.date_input("조회 종료일", value=today, min_value=start_date, max_value=today)

    st.markdown("---")
    if st.button("🔄 캐시 초기화 및 데이터 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.toast("데이터를 새로고침했습니다!", icon="✨")
        st.rerun()

# -----------------------------------------------------------------------------
# 4. 메인 화면 상단 헤더 & Top KPI Cards
# -----------------------------------------------------------------------------
st.markdown(f"""
    <div class="header-container">
        <div>
            <div class="header-title">🌸 위생용품 브랜드 경쟁 인텔리전스</div>
            <div style="color: #6B7684; font-size: 0.95rem; margin-top: 4px;">
                네이버 검색광고 실제 쿼리수 및 데이터랩 쇼핑·검색 행동 기반 경쟁사 분석 대시보드
            </div>
        </div>
        <div class="header-badge">
            🟢 실시간 데이터 기준: {today.strftime('%Y-%m-%d')}
        </div>
    </div>
""", unsafe_allow_html=True)

headers_get = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
headers_post = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret, "Content-Type": "application/json"}

# -----------------------------------------------------------------------------
# 검색광고 API 데이터 수집 및 Top KPI 카드 렌더링
# -----------------------------------------------------------------------------
ads_dict = {}
rel_keywords_list = []

if ads_customer_id and ads_api_key and ads_secret_key:
    ads_res = fetch_naver_search_ads(tuple(keywords), ads_customer_id, ads_api_key, ads_secret_key)
    if ads_res["status"] == "success":
        kw_list = ads_res["data"].get("keywordList", [])
        clean_input_kws = [k.replace(" ", "") for k in keywords]
        
        def parse_cnt(v):
            if isinstance(v, str) and "<" in v: return 5
            try: return int(v)
            except: return 0

        for item in kw_list:
            r_kw = item.get("relKeyword", "")
            pc = parse_cnt(item.get("monthlyPcQcCnt", 0))
            mo = parse_cnt(item.get("monthlyMobileQcCnt", 0))
            tot = pc + mo
            c_idx = item.get("compIdx", "보통")
            
            if r_kw in clean_input_kws:
                ads_dict[r_kw] = {"pc": pc, "mo": mo, "total": tot, "comp": c_idx}
            else:
                rel_keywords_list.append({
                    "연관 키워드": r_kw, "PC 검색량": pc, "모바일 검색량": mo, "총 검색량": tot, "경쟁도": c_idx
                })

# 상단 요약 카드 (Top Cards) 렌더링
total_sum_vol = sum(v["total"] for v in ads_dict.values()) if ads_dict else 0
card_cols = st.columns(len(keywords))

for idx, kw in enumerate(keywords):
    clean_k = kw.replace(" ", "")
    info = ads_dict.get(clean_k, {"pc": 0, "mo": 0, "total": 0, "comp": "미확인"})
    share = (info["total"] / total_sum_vol * 100) if total_sum_vol > 0 else 0
    
    # 1위 브랜드 하이라이트
    badge_class = "badge-highlight" if idx == 0 else "badge-primary"
    
    with card_cols[idx]:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-brand-title">
                    <span>{kw}</span>
                    <span class="{badge_class}">SOV {share:.1f}%</span>
                </div>
                <div class="kpi-brand-value">{info['total']:,} <span style="font-size:1rem; font-weight:600; color:#8B95A1;">회</span></div>
                <div class="kpi-brand-sub">
                    <span style="color:#6B7684;">모바일 {info['mo']:,}회</span>
                    <span style="color:#D1D6DB;">|</span>
                    <span style="color:#1B64DA;">PC {info['pc']:,}회</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 5. 핵심 5개 단계별 분석 탭
# -----------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "⚔️ ① 브랜드 검색량 & SOV",
    "📈 ② 일별 추정 검색량 & 이상치",
    "🛒 ③ 쇼핑 클릭 & 타깃 분석",
    "🔍 ④ 연관 롱테일 키워드 (Top 20)",
    "📰 ⑤ 검색 급증 원인 디깅"
])

# -----------------------------------------------------------------------------
# Tab 1: 브랜드 절대 검색량 & SOV
# -----------------------------------------------------------------------------
with tab1:
    col_t1, col_t2 = st.columns(2)
    
    # SOV 도넛 차트
    with col_t1:
        st.markdown("#### 📊 브랜드 검색 점유율 (SOV)")
        if ads_dict:
            df_sov = pd.DataFrame([{"브랜드": k, "검색량": v["total"]} for k, v in ads_dict.items()])
            fig_pie = px.pie(
                df_sov, names="브랜드", values="검색량", hole=0.55,
                color_discrete_sequence=["#1B64DA", "#3182F6", "#79B2FE", "#B5D4FE", "#E8F3FF"]
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie.update_layout(margin=dict(t=20, b=20, l=10, r=10), showlegend=False)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("검색광고 API 키를 입력하면 정확한 점유율 차트가 표시됩니다.")

    # PC vs Mobile 유입 비중
    with col_t2:
        st.markdown("#### 📱 기기별 검색량 비중 (PC vs Mobile)")
        if ads_dict:
            df_dev = pd.DataFrame([
                {"브랜드": k, "PC": v["pc"], "모바일": v["mo"]} for k, v in ads_dict.items()
            ])
            df_dev_melt = pd.melt(df_dev, id_vars=["브랜드"], value_vars=["PC", "모바일"], var_name="기기", value_name="검색수")
            fig_dev = px.bar(
                df_dev_melt, x="브랜드", y="검색수", color="기기", barmode="group",
                color_discrete_map={"모바일": "#1B64DA", "PC": "#8B95A1"}
            )
            fig_dev.update_layout(margin=dict(t=20, b=20, l=10, r=10), legend=dict(orientation="h", y=1.1, x=0.8))
            st.plotly_chart(fig_dev, use_container_width=True)

# -----------------------------------------------------------------------------
# Tab 2: 일별 추정 절대 검색량 & 이상치 알림
# -----------------------------------------------------------------------------
with tab2:
    st.markdown("#### 📈 일별 추정 절대 검색량 환산 추이 및 이상 징후 (IQR)")
    
    # 데이터랩 상대 트렌드 호출
    datalab_body = {
        "startDate": start_date.strftime("%Y-%m-%d"),
        "endDate": end_date.strftime("%Y-%m-%d"),
        "timeUnit": "date",
        "keywordGroups": [{"groupName": kw, "keywords": [kw]} for kw in keywords]
    }
    res_dl = fetch_naver_api("https://openapi.naver.com/v1/datalab/search", headers=headers_post, method="POST", json_data=datalab_body)
    
    if res_dl["status"] == "success":
        results = res_dl["data"].get("results", [])
        trend_rows = []
        
        for g in results:
            b_name = g.get("title")
            clean_b = b_name.replace(" ", "")
            monthly_total = ads_dict.get(clean_b, {}).get("total", 0)
            
            # 30일 상대 ratio 합산
            data_pts = g.get("data", [])
            sum_ratio = sum(dp["ratio"] for dp in data_pts) if data_pts else 1
            
            for dp in data_pts:
                # 일별 절대 검색량 추정식: (일일 ratio / 기간 ratio 총합) * 월간 절대 검색수
                est_daily_qc = int((dp["ratio"] / sum_ratio) * monthly_total) if monthly_total > 0 else dp["ratio"]
                trend_rows.append({
                    "날짜": pd.to_datetime(dp["period"]),
                    "브랜드": b_name,
                    "추정 검색수": est_daily_qc,
                    "상대비율(%)": dp["ratio"]
                })
                
        df_daily_trend = pd.DataFrame(trend_rows)
        
        # 이상치(Anomaly) 계산
        anomaly_alerts = []
        for kw in keywords:
            sub = df_daily_trend[df_daily_trend["브랜드"] == kw]
            if not sub.empty:
                vals = sub["추정 검색수"].values
                q25, q75 = np.percentile(vals, [25, 75])
                iqr = q75 - q25
                upper_limit = q75 + (1.5 * iqr)
                spikes = sub[sub["추정 검색수"] > upper_limit]
                for _, s_row in spikes.iterrows():
                    anomaly_alerts.append(f"🚨 **{s_row['날짜'].strftime('%m월 %d일')}**: **{kw}** 검색량 급증 탐지 (추정 {s_row['추정 검색수']:,}건)")
        
        if anomaly_alerts:
            with st.expander("⚡ **이상치(검색 급증) 감지 리포트**", expanded=True):
                for alert in anomaly_alerts[:4]:
                    st.write(alert)

        # Plotly 라인 차트
        fig_trend = px.line(
            df_daily_trend, x="날짜", y="추정 검색수", color="브랜드",
            title="일자별 추정 검색량 추이 (상대 트렌드 × 절대 검색량 결합)",
            template="plotly_white",
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        fig_trend.update_layout(hovermode="x unified")
        st.plotly_chart(fig_trend, use_container_width=True)

# -----------------------------------------------------------------------------
# Tab 3: 쇼핑 클릭 & 타깃 분석
# -----------------------------------------------------------------------------
with tab3:
    st.markdown(f"#### 🛒 [{selected_category}] 카테고리 내 쇼핑 클릭 트렌드")
    shop_body = {
        "startDate": start_date.strftime("%Y-%m-%d"),
        "endDate": end_date.strftime("%Y-%m-%d"),
        "timeUnit": "date",
        "category": [{"name": selected_category, "param": [selected_category_id]}]
    }
    res_shop = fetch_naver_api("https://openapi.naver.com/v1/datalab/shopping/categories", headers=headers_post, method="POST", json_data=shop_body)
    
    if res_shop["status"] == "success":
        shop_results = res_shop["data"].get("results", [])
        shop_rows = []
        for g in shop_results:
            for dp in g.get("data", []):
                shop_rows.append({"날짜": pd.to_datetime(dp["period"]), "클릭지수": dp["ratio"]})
        
        if shop_rows:
            df_shop = pd.DataFrame(shop_rows)
            fig_shop = px.area(df_shop, x="날짜", y="클릭지수", color_discrete_sequence=["#FF7A00"], title="카테고리 전체 쇼핑 탐색 트렌드")
            fig_shop.update_layout(template="plotly_white")
            st.plotly_chart(fig_shop, use_container_width=True)

# -----------------------------------------------------------------------------
# Tab 4: 연관 롱테일 확장 키워드 TOP 20
# -----------------------------------------------------------------------------
with tab4:
    st.markdown("#### 🔍 함께 유입되는 브랜드 연관 롱테일 키워드 TOP 20")
    if rel_keywords_list:
        df_rel = pd.DataFrame(rel_keywords_list).sort_values(by="총 검색량", ascending=False).head(20).reset_index(drop=True)
        st.dataframe(df_rel, use_container_width=True)
    else:
        st.info("검색광고 API에서 연관 키워드를 불러옵니다.")

# -----------------------------------------------------------------------------
# Tab 5: 검색 급증 원인 디깅 (디스커버리)
# -----------------------------------------------------------------------------
with tab5:
    st.markdown("#### 📰 브랜드 여론 & 최근 이슈 기사 모니터링")
    selected_target = st.selectbox("분석 대상 브랜드 선택", options=keywords, index=0)
    
    col_d1, col_d2 = st.columns(2)
    
    # 1. 뉴스 헤드라인
    with col_d1:
        st.markdown(f"##### 📢 '{selected_target}' 관련 최신 뉴스 TOP 5")
        res_news = fetch_naver_api("https://openapi.naver.com/v1/search/news.json", headers=headers_get, params={"query": selected_target, "display": 5, "sort": "sim"})
        if res_news["status"] == "success":
            for item in res_news["data"].get("items", []):
                t = item["title"].replace("<b>", "").replace("</b>", "")
                st.markdown(f"- [{t}]({item['originallink'] or item['link']})")
                
    # 2. 카페 및 커뮤니티 반응
    with col_d2:
        st.markdown(f"##### ☕ '{selected_target}' 커뮤니티/카페글 TOP 5")
        res_cafe = fetch_naver_api("https://openapi.naver.com/v1/search/cafearticle.json", headers=headers_get, params={"query": selected_target, "display": 5, "sort": "sim"})
        if res_cafe["status"] == "success":
            for item in res_cafe["data"].get("items", []):
                t = item["title"].replace("<b>", "").replace("</b>", "")
                st.markdown(f"- [{t}]({item['link']}) `({item.get('cafename', '카페')})`")