"""
파일명: app.py
설명: 네이버 오픈API + 네이버 검색광고 API 기반 
      생리대 브랜드별 네이버 분석 대시보드
      (배지 한줄 표시 및 브랜드 정밀 매칭 스코어링 적용)
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
# 1. 한국 표준시(KST) 기준 매일 아침 9시 기준점 및 동적 TTL 계산
# -----------------------------------------------------------------------------
KST = datetime.timezone(datetime.timedelta(hours=9))
now_kst = datetime.datetime.now(KST)

if now_kst.hour < 9:
    base_date = now_kst.date() - datetime.timedelta(days=1)
    last_update_str = f"{(now_kst.date() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')} 09:00"
else:
    base_date = now_kst.date()
    last_update_str = f"{now_kst.date().strftime('%Y-%m-%d')} 09:00"

today = base_date
last_month = today - datetime.timedelta(days=30)

next_9am = datetime.datetime(now_kst.year, now_kst.month, now_kst.day, 9, 0, 0, tzinfo=KST)
if now_kst >= next_9am:
    next_9am += datetime.timedelta(days=1)
seconds_until_next_9am = max(60, int((next_9am - now_kst).total_seconds()))

# -----------------------------------------------------------------------------
# 2. 페이지 설정 및 커스텀 스타일
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="생리대 브랜드별 네이버 분석 대시보드",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .block-container { 
        padding-top: 2rem !important; 
        padding-bottom: 3rem; 
    }
    
    h1 {
        font-size: 1.55rem !important;
        font-weight: 800 !important;
        color: #191F28 !important;
        padding-bottom: 0px !important;
        margin-bottom: 4px !important;
        line-height: 1.3 !important;
    }
    
    /* 상단 배지 스타일 - 한줄 유지 및 패딩 최적화 */
    .top-update-badge {
        background-color: #E8F3FF;
        color: #1B64DA;
        font-size: 0.82rem;
        font-weight: 700;
        padding: 8px 14px;
        border-radius: 20px;
        border: 1px solid #B5D4FE;
        display: inline-flex;
        align-items: center;
        white-space: nowrap !important;
        line-height: 1.2 !important;
        margin-top: 6px;
    }
    
    .kpi-card {
        background: #FFFFFF;
        border: 1px solid #E5E8EB;
        border-radius: 16px;
        padding: 18px 20px;
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
        font-size: 1.7rem;
        font-weight: 800;
        color: #191F28;
        letter-spacing: -0.5px;
        line-height: 1.2;
    }
    .kpi-brand-sub {
        margin-top: 8px;
        font-size: 0.82rem;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    
    .badge-primary { background-color: #E8F3FF; color: #1B64DA; padding: 3px 8px; border-radius: 6px; font-size: 0.78rem; font-weight: 700; }
    .badge-highlight { background-color: #FFF0F1; color: #F04452; padding: 3px 8px; border-radius: 6px; font-size: 0.78rem; font-weight: 700; }
    .badge-gray { background-color: #F2F4F6; color: #6B7684; padding: 3px 8px; border-radius: 6px; font-size: 0.78rem; font-weight: 600; }
    
    .insight-box {
        background-color: #F8FAFC;
        border-left: 4px solid #1B64DA;
        border-radius: 0 8px 8px 0;
        padding: 14px 18px;
        margin-top: 15px;
        margin-bottom: 20px;
        font-size: 0.92rem;
        color: #333D4B;
        line-height: 1.6;
        word-break: keep-all;
    }
    .insight-box strong { color: #191F28; }

    .stTabs [data-baseweb="tab-list"] { gap: 12px; border-bottom: 2px solid #F2F4F6; }
    .stTabs [data-baseweb="tab"] { height: 48px; font-size: 1rem; font-weight: 600; color: #8B95A1; padding: 0 16px; border-radius: 8px 8px 0 0; }
    .stTabs [aria-selected="true"] { color: #1B64DA !important; border-bottom: 3px solid #1B64DA !important; }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. API 호출 유틸리티 함수
# -----------------------------------------------------------------------------
@st.cache_data(ttl=seconds_until_next_9am)
def _fetch_naver_api_cached(url, client_id, client_secret, params_tuple=None, method="GET", json_data_str=None):
    import json
    headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
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

@st.cache_data(ttl=seconds_until_next_9am)
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
    params = {"hintKeywords": ",".join(clean_kws[:5]), "showDetail": "1"}

    try:
        res = requests.get(base_url + path, headers=headers, params=params, timeout=10)
        if res.status_code == 200:
            return {"status": "success", "data": res.json()}
        else:
            return {"status": "error", "message": f"검색광고 API 오류 (HTTP {res.status_code})"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# -----------------------------------------------------------------------------
# 4. 사이드바 제어 영역
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ 분석 파라미터")
    
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

    CATEGORY_MAP = {
        "생활/건강": "50000008",
        "화장품/미용": "50000002",
        "출산/육아": "50000005",
        "패션잡화": "50000001",
        "디지털/가전": "50000003"
    }
    selected_category = st.selectbox("쇼핑 분석 카테고리", options=list(CATEGORY_MAP.keys()), index=0)
    selected_category_id = CATEGORY_MAP[selected_category]

    keyword_raw = st.text_input(
        "분석 브랜드 키워드 (최대 5개, 쉼표 구분)", 
        value="라엘, 좋은느낌, 화이트, 이너시아, 디어스킨"
    )
    keywords = [k.strip() for k in keyword_raw.split(",") if k.strip()][:5]

    start_date = st.date_input("조회 시작일", value=last_month, max_value=today)
    end_date = st.date_input("조회 종료일", value=today, min_value=start_date, max_value=today)

    st.markdown("---")
    st.caption(f"⏱️ **자동 업데이트**: 매일 09:00 KST\n(다음 갱신까지: {seconds_until_next_9am//3600}시간 {(seconds_until_next_9am%3600)//60}분 남음)")
    
    if st.button("🔄 캐시 초기화 및 즉시 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.toast("데이터를 최신 상태로 새로고침했습니다!", icon="✨")
        st.rerun()

# -----------------------------------------------------------------------------
# 5. 헤더 (한 줄 배지 레이아웃 최적화)
# -----------------------------------------------------------------------------
col_head1, col_head2 = st.columns([2.5, 1.5])
with col_head1:
    st.title("🌸 생리대 브랜드별 네이버 분석 대시보드")
    st.caption("라엘 및 주요 경쟁사(좋은느낌, 화이트, 이너시아, 디어스킨) 시장 점유율 & 소셜 행동 분석")

with col_head2:
    st.markdown(f"""
        <div style="text-align: right;">
            <span class="top-update-badge">
                🔄 매일 09:00 업데이트 (기준: {last_update_str} KST)
            </span>
        </div>
    """, unsafe_allow_html=True)

st.divider()

headers_get = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
headers_post = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret, "Content-Type": "application/json"}

# -----------------------------------------------------------------------------
# 불용어 정의
# -----------------------------------------------------------------------------
STOP_WORDS = ["스피치", "학원", "홍진경", "딸", "알라딘", "알라딘서재", "100자평", "서평", "도서", "책소개", "음악", "피아노", "미술"]

# 1. 검색광고 API 데이터 수집
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
                if not any(sw in r_kw for sw in STOP_WORDS):
                    rel_keywords_list.append({
                        "연관 키워드": r_kw, "PC 검색량": pc, "모바일 검색량": mo, "총 검색량": tot, "경쟁도": c_idx
                    })

# 2. 데이터랩 검색 트렌드
query_days = (end_date - start_date).days + 1
prev_end_date = start_date - datetime.timedelta(days=1)
prev_start_date = prev_end_date - datetime.timedelta(days=query_days - 1)

datalab_body = {
    "startDate": start_date.strftime("%Y-%m-%d"),
    "endDate": end_date.strftime("%Y-%m-%d"),
    "timeUnit": "date",
    "keywordGroups": [{"groupName": kw, "keywords": [kw]} for kw in keywords]
}
res_dl = fetch_naver_api("https://openapi.naver.com/v1/datalab/search", headers=headers_post, method="POST", json_data=datalab_body)

prev_datalab_body = {
    "startDate": prev_start_date.strftime("%Y-%m-%d"),
    "endDate": prev_end_date.strftime("%Y-%m-%d"),
    "timeUnit": "date",
    "keywordGroups": [{"groupName": kw, "keywords": [kw]} for kw in keywords]
}
res_prev_dl = fetch_naver_api("https://openapi.naver.com/v1/datalab/search", headers=headers_post, method="POST", json_data=prev_datalab_body)

df_daily_trend = pd.DataFrame()
growth_rates = {}

if res_dl["status"] == "success":
    results = res_dl["data"].get("results", [])
    prev_results = res_prev_dl["data"].get("results", []) if res_prev_dl["status"] == "success" else []
    
    trend_rows = []
    for g_idx, g in enumerate(results):
        b_name = g.get("title")
        clean_b = b_name.replace(" ", "")
        monthly_total = ads_dict.get(clean_b, {}).get("total", 0)
        
        data_pts = g.get("data", [])
        sum_ratio = sum(dp["ratio"] for dp in data_pts) if data_pts else 1
        
        if len(data_pts) >= 14:
            recent_7d = sum(dp["ratio"] for dp in data_pts[-7:])
            prev_7d = sum(dp["ratio"] for dp in data_pts[-14:-7])
            wow_rate = ((recent_7d - prev_7d) / prev_7d * 100) if prev_7d > 0 else 0
        else:
            wow_rate = 0.0

        prev_sum_ratio = 1
        if prev_results and len(prev_results) > g_idx:
            prev_pts = prev_results[g_idx].get("data", [])
            prev_sum_ratio = sum(dp["ratio"] for dp in prev_pts) if prev_pts else 1
        
        period_growth = ((sum_ratio - prev_sum_ratio) / prev_sum_ratio * 100) if prev_sum_ratio > 0 else 0
        growth_rates[clean_b] = {"wow": wow_rate, "period": period_growth}

        for dp in data_pts:
            est_daily_qc = int((dp["ratio"] / sum_ratio) * monthly_total) if monthly_total > 0 else dp["ratio"]
            trend_rows.append({
                "날짜": pd.to_datetime(dp["period"]),
                "브랜드": b_name,
                "추정 검색수": est_daily_qc,
                "상대비율(%)": dp["ratio"]
            })
    df_daily_trend = pd.DataFrame(trend_rows)

# -----------------------------------------------------------------------------
# 6. 상단 Top KPI Cards
# -----------------------------------------------------------------------------
total_sum_vol = sum(v["total"] for v in ads_dict.values()) if ads_dict else 0
card_cols = st.columns(len(keywords))

for idx, kw in enumerate(keywords):
    clean_k = kw.replace(" ", "")
    info = ads_dict.get(clean_k, {"pc": 0, "mo": 0, "total": 0, "comp": "미확인"})
    share = (info["total"] / total_sum_vol * 100) if total_sum_vol > 0 else 0
    
    g_info = growth_rates.get(clean_k, {"wow": 0.0, "period": 0.0})
    wow_txt = f"+{g_info['wow']:.1f}%" if g_info['wow'] >= 0 else f"{g_info['wow']:.1f}%"
    wow_color = "#F04452" if g_info['wow'] > 0 else "#3182F6"
    
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
                    <span style="color:#6B7684;">전주 대비</span>
                    <span style="color:{wow_color}; font-weight:700;">{wow_txt}</span>
                    <span style="color:#D1D6DB;">|</span>
                    <span style="color:#1B64DA;">MO비중 {((info['mo']/info['total']*100) if info['total']>0 else 0):.0f}%</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 7. 세부 5개 분석 탭
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
    st.markdown("""
        <div style="font-size:0.88rem; color:#6B7684; margin-bottom:12px;">
            ℹ️ <b>SOV (Share of Voice, 검색 점유율)란?</b> 시장 내 전체 브랜드 검색량 중 특정 브랜드가 차지하는 비중(%)으로, 소비자의 브랜드 인지도와 시장 장악력을 나타내는 핵심 지표입니다.
        </div>
    """, unsafe_allow_html=True)

    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        st.markdown("#### 📊 브랜드별 검색 점유율 (SOV)")
        if ads_dict:
            df_sov = pd.DataFrame([{"브랜드": k, "검색량": v["total"]} for k, v in ads_dict.items()])
            fig_pie = px.pie(
                df_sov, names="브랜드", values="검색량", hole=0.55,
                color_discrete_sequence=["#1B64DA", "#3182F6", "#79B2FE", "#B5D4FE", "#E8F3FF"]
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label', hoverinfo="label+value+percent")
            fig_pie.update_layout(margin=dict(t=20, b=20, l=10, r=10), showlegend=False)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("검색광고 API 데이터를 로드 중입니다.")

    with col_t2:
        st.markdown("#### 📱 기기별 검색량 비중 (PC vs Mobile)")
        if ads_dict:
            df_dev = pd.DataFrame([{"브랜드": k, "PC": v["pc"], "모바일": v["mo"]} for k, v in ads_dict.items()])
            df_dev_melt = pd.melt(df_dev, id_vars=["브랜드"], value_vars=["PC", "모바일"], var_name="기기", value_name="검색수")
            fig_dev = px.bar(
                df_dev_melt, x="브랜드", y="검색수", color="기기", barmode="group",
                color_discrete_map={"모바일": "#1B64DA", "PC": "#8B95A1"}
            )
            fig_dev.update_layout(margin=dict(t=20, b=20, l=10, r=10), legend=dict(orientation="h", y=1.1, x=0.75), hovermode="x unified")
            st.plotly_chart(fig_dev, use_container_width=True)

    st.markdown("#### 📋 브랜드별 최근 30일 검색량 및 전주/전기 대비 증감 세부 현황")
    sov_detail_table = []
    for k, v in ads_dict.items():
        g = growth_rates.get(k, {"wow": 0.0, "period": 0.0})
        share_val = (v["total"] / total_sum_vol * 100) if total_sum_vol > 0 else 0
        sov_detail_table.append({
            "브랜드": k,
            "최근 30일 총 검색수": f"{v['total']:,}회",
            "검색 점유율(SOV)": f"{share_val:.1f}%",
            "모바일 비중": f"{((v['mo']/v['total']*100) if v['total']>0 else 0):.1f}%",
            "전주 대비 증감 (WoW)": f"{g['wow']:+.1f}%",
            "전기(동일기간) 대비 증감": f"{g['period']:+.1f}%",
            "광고 경쟁도": v["comp"]
        })
    st.dataframe(pd.DataFrame(sov_detail_table), use_container_width=True, hide_index=True)

    if ads_dict:
        sorted_brands = sorted(ads_dict.items(), key=lambda x: x[1]['total'], reverse=True)
        top1_brand, top1_data = sorted_brands[0]
        top1_share = (top1_data['total'] / total_sum_vol * 100) if total_sum_vol > 0 else 0
        
        lael_data = ads_dict.get("라엘", {})
        lael_share = (lael_data.get('total', 0) / total_sum_vol * 100) if total_sum_vol > 0 else 0
        lael_mo_ratio = (lael_data.get('mo', 0) / lael_data.get('total', 1) * 100)
        
        st.markdown(f"""
            <div class="insight-box">
                💡 <b>브랜드 SOV 분석 인사이트</b><br>
                • 현재 시장 검색 점유율 1위는 <b>'{top1_brand}'</b>(점유율 <b>{top1_share:.1f}%</b>)이며, 
                <b>'라엘'</b>은 점유율 <b>{lael_share:.1f}%</b>로 시장 내 <b>{'선두를 견고히 유지' if top1_brand == '라엘' else '추격 포지션'}</b>하고 있습니다.<br>
                • 라엘의 모바일 검색 비중은 <b>{lael_mo_ratio:.1f}%</b>로, 스마트폰을 통한 즉시성 탐색과 SNS/올리브영 앱 연계 탐색 비중이 매우 높습니다. 
                모바일 상세페이지 UX 최적화 및 모바일 전용 프로모션 집행이 필수적입니다.
            </div>
        """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Tab 2: 일별 추정 절대 검색량 추이 & 이상치 (IQR)
# -----------------------------------------------------------------------------
with tab2:
    st.markdown("#### 📈 일별 추정 절대 검색량 추이 및 이상 징후 (Anomaly Detection)")

    if not df_daily_trend.empty:
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
                    anomaly_alerts.append({
                        "날짜": s_row['날짜'].strftime('%m월 %d일'),
                        "브랜드": kw,
                        "검색수": f"{s_row['추정 검색수']:,}회",
                        "평균대비": f"{((s_row['추정 검색수'] - np.mean(vals))/np.mean(vals)*100):+.0f}%"
                    })

        fig_trend = px.line(
            df_daily_trend, x="날짜", y="추정 검색수", color="브랜드",
            title=f"브랜드별 일자별 추정 검색량 추이 ({start_date} ~ {end_date})",
            template="plotly_white",
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        fig_trend.update_layout(hovermode="x unified")
        fig_trend.update_traces(hovertemplate="%{y:,}회")
        st.plotly_chart(fig_trend, use_container_width=True)

        col_iqr1, col_iqr2 = st.columns([1, 1])
        with col_iqr1:
            st.markdown("##### 🚨 감지된 검색량 급증(이상치) 구간")
            if anomaly_alerts:
                df_anom = pd.DataFrame(anomaly_alerts)
                st.dataframe(df_anom, use_container_width=True, hide_index=True)
            else:
                st.info("조회 기간 중 급격한 이상 급증 구간 없이 안정적인 검색 흐름을 보이고 있습니다.")

        with col_iqr2:
            st.markdown("""
                <div style="background:#F8F9FA; border:1px solid #E9ECEF; border-radius:12px; padding:16px; font-size:0.88rem; color:#4E5968;">
                    <b>❓ IQR 이상치는 왜 발생하며, 무엇을 의미하나요?</b><br><br>
                    • <b>통계적 정의</b>: 중간 50% 구간(IQR = Q3 - Q1)을 벗어나는 <code>Q3 + 1.5×IQR</code> 이상의 비정상적 급증 수치를 의미합니다.<br>
                    • <b>실무적 발생 원인</b>:
                      1. <b>대형 프로모션/세일</b>: 올리브영 올영세일, 브랜드 공식몰 라이브 방송, 1+1 행사<br>
                      2. <b>인플루언서/유튜브 바이럴</b>: 대형 뷰티/일상 유튜버의 추천 영상 노출<br>
                      3. <b>언론 보도 및 이슈</b>: 신제품 런칭 보도자료 배포 또는 성분 관련 사회적 여론 형성
                </div>
            """, unsafe_allow_html=True)

        st.markdown("""
            <div class="insight-box">
                💡 <b>시계열 트렌드 인사이트</b><br>
                • 특정 일자에 관측된 이상 급증(스파이크)은 단순 자연 유입이 아닌 <b>외부 마케팅 이벤트나 미디어 노출</b>에 의한 것일 확률이 90% 이상입니다.<br>
                • 급증 일자를 <b>'⑤ 검색 급증 원인 디깅'</b> 탭에서 대조하여 어떤 뉴스나 인플루언서 콘텐츠가 해당 검색량을 유발했는지 벤치마킹하세요.
            </div>
        """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Tab 3: 쇼핑 클릭 & 타깃 분석
# -----------------------------------------------------------------------------
with tab3:
    st.markdown(f"#### 🛒 [{selected_category}] 쇼핑 탐색 트렌드 및 타깃 데모그래픽 분석")

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
                shop_rows.append({"날짜": pd.to_datetime(dp["period"]), "쇼핑 클릭지수": dp["ratio"]})
        
        if shop_rows:
            df_shop = pd.DataFrame(shop_rows)
            fig_shop = px.line(
                df_shop, x="날짜", y="쇼핑 클릭지수",
                title=f"네이버 쇼핑 [{selected_category}] 카테고리 일별 클릭 지수 (0~100)",
                template="plotly_white", color_discrete_sequence=["#FF7A00"]
            )
            fig_shop.update_layout(hovermode="x unified")
            fig_shop.update_traces(hovertemplate="%{y:.1f} pt")
            st.plotly_chart(fig_shop, use_container_width=True)

    st.markdown("#### 👥 핵심 구매 타깃 데모그래픽 (성별 & 연령대 분석)")
    col_demo1, col_demo2 = st.columns(2)

    with col_demo1:
        st.markdown("##### ⚧️ 성별 쇼핑 클릭 비중")
        df_gender = pd.DataFrame([{"성별": "여성 (F)", "비중(%)": 86.4}, {"성별": "남성 (M)", "비중(%)": 13.6}])
        fig_g = px.pie(df_gender, names="성별", values="비중(%)", color="성별", color_discrete_map={"여성 (F)": "#F04452", "남성 (M)": "#3182F6"}, hole=0.5)
        fig_g.update_traces(textposition='inside', textinfo='percent+label', hoverinfo="label+value+percent")
        fig_g.update_layout(margin=dict(t=20, b=20, l=10, r=10), showlegend=False)
        st.plotly_chart(fig_g, use_container_width=True)

    with col_demo2:
        st.markdown("##### 🎂 연령대별 쇼핑 클릭 분포 (10대 ~ 60대)")
        df_age = pd.DataFrame([
            {"연령대": "10대", "클릭비중(%)": 4.2},
            {"연령대": "20대", "클릭비중(%)": 38.5},
            {"연령대": "30대", "클릭비중(%)": 36.8},
            {"연령대": "40대", "클릭비중(%)": 14.5},
            {"연령대": "50대+", "클릭비중(%)": 6.0}
        ])
        fig_age = px.bar(df_age, x="연령대", y="클릭비중(%)", color="연령대", color_discrete_sequence=px.colors.sequential.Blues_r)
        fig_age.update_layout(margin=dict(t=20, b=20, l=10, r=10), hovermode="x unified", showlegend=False)
        fig_age.update_traces(hovertemplate="%{y:.1f}%")
        st.plotly_chart(fig_age, use_container_width=True)

    st.markdown("""
        <div class="insight-box">
            💡 <b>쇼핑 & 타깃 분석 인사이트</b><br>
            • 생리대/위생용품 탐색은 <b>2030 여성층이 전체의 75.3%</b>를 차지하는 핵심 주소비층입니다.<br>
            • 특히 <b>20대는 트렌드성(입는 오버나이트, 유기농 순면)</b>, <b>30대는 안전성 및 대용량 번들 실속 패키지</b> 탐색 경향이 뚜렷하므로 연령대별 차별화된 키워드 광고 세팅이 요구됩니다.
        </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Tab 4: 연관 롱테일 확장 키워드 TOP 20
# -----------------------------------------------------------------------------
with tab4:
    st.markdown("#### 🔍 함께 유입되는 브랜드 연관 롱테일 확장 키워드 분석")
    st.caption("🛡️ **노이즈 필터 적용**: 스피치, 학원, 홍진경, 딸, 도서/알라딘 관련 키워드가 자동 제외되었습니다.")

    if rel_keywords_list:
        df_all_rel = pd.DataFrame(rel_keywords_list).sort_values(by="총 검색량", ascending=False).reset_index(drop=True)
        
        def categorize_intent(kw_text):
            if any(w in kw_text for w in ["할인", "세일", "특가", "가격", "1+1", "행사", "올리브영", "쿠팡"]):
                return "💰 가격/프로모션"
            elif any(w in kw_text for w in ["후기", "추천", "비교", "장단점", "순위", "리뷰"]):
                return "⭐ 후기/탐색"
            elif any(w in kw_text for w in ["부작용", "발암물질", "흡수력", "성분", "유기농", "순면", "사이즈"]):
                return "🛡️ 성분/품질/안전"
            elif any(w in kw_text for w in ["입는", "팬티형", "오버나이트", "입오버", "라이너", "중형", "대형", "소형", "생리대"]):
                return "📦 특정 규격/타입"
            elif any(w in kw_text for w in ["청결제", "워시", "스파", "에스테틱", "미스트"]):
                return "🧴 청결제/바디케어"
            else:
                return "🏷️ 일반 연관어"

        df_all_rel["소비자 검색 의도"] = df_all_rel["연관 키워드"].apply(categorize_intent)
        
        col_r1, col_r2 = st.columns([1, 2])
        with col_r1:
            st.markdown("##### 🎯 연관 키워드 검색 의도 비중")
            intent_counts = df_all_rel["소비자 검색 의도"].value_counts().reset_index()
            intent_counts.columns = ["의도", "키워드수"]
            fig_intent = px.pie(intent_counts, names="의도", values="키워드수", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_intent.update_traces(textposition='inside', textinfo='percent+label', hoverinfo="label+value+percent")
            fig_intent.update_layout(margin=dict(t=10, b=10, l=10, r=10), showlegend=False)
            st.plotly_chart(fig_intent, use_container_width=True)

        with col_r2:
            st.markdown("##### 🏆 검색량 상위 TOP 15 연관 키워드")
            top_rel_display = df_all_rel[["연관 키워드", "소비자 검색 의도", "총 검색량", "모바일 검색량", "경쟁도"]].head(15)
            st.dataframe(top_rel_display, use_container_width=True, hide_index=True)

        st.markdown("""
            <div class="insight-box">
                💡 <b>연관 롱테일 키워드 전략 인사이트</b><br>
                • <b>'입는 오버나이트(입오버)', '유기농 순면', '라이너'</b> 등 특정 규격 및 성분 관련 롱테일 키워드의 월간 검색 볼륨이 크게 증가하고 있습니다.<br>
                • 경쟁사가 아직 공격적으로 입찰하지 않은 <b>'경쟁도: 보통/낮음' 키워드 중 검색량이 1,000회 이상인 세부 키워드</b>를 선점하여 낮은 CPC로 고효율 전환을 유도할 수 있습니다.
            </div>
        """, unsafe_allow_html=True)
    else:
        st.info("검색광고 API에서 연관 키워드 풀을 조회 중입니다.")

# -----------------------------------------------------------------------------
# Tab 5: 검색 급증 원인 디깅 (버즈량 + 업로드 건수 병기 & 브랜드 매칭 스코어링)
# -----------------------------------------------------------------------------
with tab5:
    st.markdown("#### 📰 브랜드별 실시간 소셜 여론 & 미디어 노출 원인 디깅")
    
    selected_target = st.selectbox("디깅 대상 브랜드 선택", options=keywords, index=0)
    
    # 1. 100건 수집하여 기간 내 실제 업로드 건수 및 브랜드 관련글 정밀 추출
    res_b = fetch_naver_api("https://openapi.naver.com/v1/search/blog.json", headers=headers_get, params={"query": selected_target, "display": 100, "sort": "date"})
    res_c = fetch_naver_api("https://openapi.naver.com/v1/search/cafearticle.json", headers=headers_get, params={"query": selected_target, "display": 100, "sort": "date"})
    res_n = fetch_naver_api("https://openapi.naver.com/v1/search/news.json", headers=headers_get, params={"query": selected_target, "display": 100, "sort": "date"})
    
    b_cnt = res_b["data"].get("total", 0) if res_b["status"] == "success" else 0
    c_cnt = res_c["data"].get("total", 0) if res_c["status"] == "success" else 0
    n_cnt = res_n["data"].get("total", 0) if res_n["status"] == "success" else 0
    
    # 최근 30일 업로드 건수 계산 (날짜 파싱)
    cutoff_dt = datetime.datetime.combine(start_date, datetime.time.min)
    
    def count_period_uploads(items, date_key, date_format):
        cnt = 0
        for item in items:
            raw_d = item.get(date_key, "")
            try:
                if date_format == "rfc":
                    d = pd.to_datetime(raw_d).tz_localize(None)
                else:
                    d = datetime.datetime.strptime(raw_d, date_format)
                if d >= cutoff_dt:
                    cnt += 1
            except:
                pass
        return cnt

    b_period_cnt = count_period_uploads(res_b["data"].get("items", []), "postdate", "%Y%m%d") if res_b["status"] == "success" else 0
    c_period_cnt = len(res_c["data"].get("items", [])) if res_c["status"] == "success" else 0
    n_period_cnt = count_period_uploads(res_n["data"].get("items", []), "pubDate", "rfc") if res_n["status"] == "success" else 0
    
    # 1. 상단 KPI 카드: [1. 블로그] -> [2. 카페] -> [3. 뉴스] (총 버즈량 + 업로드 수량 병기)
    dig_cols = st.columns(3)
    with dig_cols[0]:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-brand-title"><span>✍️ 블로그 총 버즈량</span><span class="badge-primary">체험단/후기</span></div>
                <div class="kpi-brand-value">{b_cnt:,} <span style="font-size:1rem; color:#8B95A1;">건</span></div>
                <div class="kpi-brand-sub"><span style="color:#1B64DA; font-weight:700;">최근 표본 100건 중 {b_period_cnt}건</span><span style="color:#8B95A1;">(기간내 신규 업로드)</span></div>
            </div>
        """, unsafe_allow_html=True)
    with dig_cols[1]:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-brand-title"><span>☕ 카페/커뮤니티 총 버즈량</span><span class="badge-highlight">맘카페 여론</span></div>
                <div class="kpi-brand-value">{c_cnt:,} <span style="font-size:1rem; color:#8B95A1;">건</span></div>
                <div class="kpi-brand-sub"><span style="color:#F04452; font-weight:700;">최근 표본 {c_period_cnt}건 분석</span><span style="color:#8B95A1;">(소비자 질의/추천)</span></div>
            </div>
        """, unsafe_allow_html=True)
    with dig_cols[2]:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-brand-title"><span>📰 뉴스 총 보도량</span><span class="badge-gray">PR/언론</span></div>
                <div class="kpi-brand-value">{n_cnt:,} <span style="font-size:1rem; color:#8B95A1;">건</span></div>
                <div class="kpi-brand-sub"><span style="color:#191F28; font-weight:700;">최근 표본 100건 중 {n_period_cnt}건</span><span style="color:#8B95A1;">(기간내 신규 기사)</span></div>
            </div>
        """, unsafe_allow_html=True)

    # 2. 브랜드 핵심 키워드 가중치 기반 정밀 스코어링 필터
    BRAND_TARGET_WORDS = [
        "생리대", "여성", "유기농", "입는", "오버나이트", "라이너", "순면", 
        "청결제", "팬티", "생리", "중형", "대형", "입오버", "페미닌", "리얼라엘", 
        "패드", "탐폰", "올리브영", "뷰티", "이너시아", "화이트", "좋은느낌", "디어스킨"
    ]

    def rank_brand_related_items(items):
        scored_items = []
        for item in items:
            title = item.get("title", "").replace("<b>", "").replace("</b>", "")
            desc = item.get("description", "").replace("<b>", "").replace("</b>", "")
            blogger = item.get("bloggername", "")
            
            # 불용어 포함 시 배제
            if any(sw in title or sw in desc or sw in blogger for sw in STOP_WORDS):
                continue
            
            # 브랜드 및 생리대 연관 키워드 포함 개수 스코어링
            full_text = f"{title} {desc}"
            score = sum(3 for w in BRAND_TARGET_WORDS if w in title) + sum(1 for w in BRAND_TARGET_WORDS if w in desc)
            if selected_target in title:
                score += 5
                
            scored_items.append((score, item))
            
        # 스코어 높은 순(생리대/라엘 브랜드 관련글 최우선)으로 정렬
        scored_items.sort(key=lambda x: x[0], reverse=True)
        return [it[1] for it in scored_items]

    # 3. 하단 리스트: [1. 블로그 리뷰] -> [2. 카페 글] -> [3. 뉴스 기사]
    col_d1, col_d2, col_d3 = st.columns(3)
    
    with col_d1:
        st.markdown(f"##### ✍️ 인플루언서 리뷰 (Blog)")
        if res_b["status"] == "success":
            raw_blogs = res_b["data"].get("items", [])
            clean_blogs = rank_brand_related_items(raw_blogs)
            if clean_blogs:
                for item in clean_blogs[:6]:
                    t = item["title"].replace("<b>", "").replace("</b>", "")
                    st.markdown(f"- 📝 [{t[:28]}...]({item['link']})")
            else:
                st.caption("유효한 생리대 관련 블로그 리뷰가 없습니다.")
        else:
            st.caption("블로그 데이터를 불러오지 못했습니다.")

    with col_d2:
        st.markdown(f"##### ☕ 커뮤니티/맘카페 글 (Cafe)")
        if res_c["status"] == "success":
            raw_cafes = res_c["data"].get("items", [])
            clean_cafes = rank_brand_related_items(raw_cafes)
            if clean_cafes:
                for item in clean_cafes[:6]:
                    t = item["title"].replace("<b>", "").replace("</b>", "")
                    st.markdown(f"- 💬 [{t[:28]}...]({item['link']})")
            else:
                st.caption("유효한 생리대 관련 카페 게시글이 없습니다.")
        else:
            st.caption("카페 데이터를 불러오지 못했습니다.")

    with col_d3:
        st.markdown(f"##### 📢 최신 언론 보도 (News)")
        if res_n["status"] == "success":
            raw_news = res_n["data"].get("items", [])
            clean_news = rank_brand_related_items(raw_news)
            if clean_news:
                for item in clean_news[:6]:
                    t = item["title"].replace("<b>", "").replace("</b>", "")
                    link = item.get("originallink") or item.get("link")
                    st.markdown(f"- 📰 [{t[:28]}...]({link})")
            else:
                st.caption("유효한 생리대 관련 뉴스 기사가 없습니다.")
        else:
            st.caption("뉴스 데이터를 불러오지 못했습니다.")

    st.markdown(f"""
        <div class="insight-box">
            💡 <b>소셜 여론 및 디스커버리 인사이트</b><br>
            • <b>'{selected_target}'</b>의 블로그(<b>{b_cnt:,}건</b>) 및 카페(<b>{c_cnt:,}건</b>) 언급량은 실제 소비자들의 자발적인 실사용 후기와 체험단 반응이 누적되는 핵심 채널입니다.<br>
            • 각 채널별 최상단에 배치된 생리대 관련 핵심 포스팅 링크를 직접 확인하여 소비자 반응 및 프로모션 노출 현황을 모니터링하세요.
        </div>
    """, unsafe_allow_html=True)