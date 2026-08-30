"""
여성청결제 시장 상세페이지 벤치마킹 및 리뉴얼 전략 인터랙티브 Streamlit 대시보드.

이 대시보드는 18개 주요 브랜드(올리브영 입점 1위 및 D2C)의 상세페이지 분석 데이터, 2x2 포지셔닝 맵,
6대 벤치마킹 매트릭스, 올리브영 입점 브랜드 포함 실제 이미지 갤러리/비교 뷰어, Storyline 비교,
라엘(Target)의 심층 진단 및 타사 레퍼런스 2열 Side-by-Side 매칭, 7개 섹션 리뉴얼 와이어프레임을 시각화합니다.
모든 시각화는 Plotly를 독점적으로 사용하며, 상단 필수 KPI 카드를 제공합니다.
"""

import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# -------------------------------------------------------------
# 1. 페이지 설정 및 커스텀 스타일링
# -------------------------------------------------------------
st.set_page_config(
    page_title="여성청결제 시장 분석 & 상세페이지 리뉴얼 대시보드",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 모던 비즈니스 스타일 CSS 주입
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700;800&display=swap');
    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .metric-card {
        background: linear-gradient(135deg, #F8FAFC 0%, #F1F5F9 100%);
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: all 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }
    .metric-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: #0F172A;
        margin: 4px 0;
    }
    .metric-delta {
        font-size: 0.8rem;
        font-weight: 600;
        color: #0D9488;
    }
    .badge-target {
        background-color: #EEF2FF;
        color: #2563EB;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 700;
        border: 1px solid #BFDBFE;
    }
    .badge-white-space {
        background-color: #CCFBF1;
        color: #0F766E;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 700;
        border: 1px solid #99F6E4;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 18px;
        border-radius: 8px 8px 0 0;
        font-weight: 600;
    }
    .ref-box-problem {
        background: #FFF1F2;
        border-left: 4px solid #E11D48;
        padding: 16px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 16px;
    }
    .ref-box-solution {
        background: #F0FDF4;
        border-left: 4px solid #16A34A;
        padding: 16px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 16px;
    }
    .ref-box-oliveyoung {
        background: #F0F9FF;
        border-left: 4px solid #0284C7;
        padding: 16px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 2. 이미지 안전 로딩 헬퍼 함수
# -------------------------------------------------------------
def get_safe_image_path(rel_path):
    """
    로컬 실행 또는 Streamlit Cloud 배포 환경 어디서든
    상대 경로를 안전하게 탐색하여 파일 존재 여부를 검증하고 절대/상대 경로를 반환합니다.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        rel_path,
        os.path.join(base_dir, rel_path),
        os.path.join(base_dir, "images", os.path.basename(os.path.dirname(rel_path)), os.path.basename(rel_path)),
        os.path.join("intimate", rel_path),
        os.path.join("..", rel_path)
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

# -------------------------------------------------------------
# 3. 데이터 로드 및 전처리 (Caching)
# -------------------------------------------------------------
@st.cache_data
def load_market_data():
    data = [
        {
            "brand": "라엘 (Rael)",
            "product_name": "라엘 천연 여성청결제",
            "cluster": "클린/비건 오가닉형",
            "is_target": True,
            "orig_price": 18000,
            "sale_price": 12900,
            "volume_ml": 150,
            "unit_price_100ml": 8600,
            "texture": "마일드 버블 폼",
            "scent": "100% 무향",
            "x_score": 8.5,
            "y_score": 3.0,
            "main_copy": "단 8가지 전성분, COSMOS 천연 인증 순한 청결제",
            "key_ingredient": "단 8가지 전성분 (코코베타인, 락틱애씨드 등)",
            "mechanism": "불필요한 성분을 배제한 극단적 미니멀 처방",
            "clinical_proof": "피부 저자극 테스트 0.00 (항균/탈취 수치 미표기)",
            "bundle": "150ml 본품 단품 & 청결티슈 기획",
            "hooking": "경피 흡수율 높은 점막에 닿는 화학 성분 공포",
            "strengths": "COSMOS 천연 유기농 인증, 단 8가지 성분, 아마존 1위 생리대 신뢰도",
            "weaknesses": "칸디다 99.9% 항균 및 99% 탈취 등 정량 수치 부재로 고민해결력 약함"
        },
        {
            "brand": "바솔 (BASOL)",
            "product_name": "이너 밸런싱 포밍 워시",
            "cluster": "클린/비건 웰니스형",
            "is_target": False,
            "orig_price": 36000,
            "sale_price": 23900,
            "volume_ml": 300,
            "unit_price_100ml": 7960,
            "texture": "소프트 마이크로 버블 폼",
            "scent": "천연 티트리 에센셜",
            "x_score": 7.5,
            "y_score": 6.8,
            "main_copy": "올리브영 W케어 1등! 락토바실러스와 티트리의 산뜻 밸런스",
            "key_ingredient": "락토바실러스 발효용해물, 호주산 티트리잎 오일, 병풀추출물",
            "mechanism": "유익균 보호 + 천연 티트리 소취 쿨링 + 버블 저자극",
            "clinical_proof": "칸디다 99.9% 항균, 2대 가스 소취 완료, 녹색소비자연대 적합",
            "bundle": "올리브영 단독 [본품 150ml + 리필 150ml] 기획",
            "hooking": "생리 전후 냄새와 땀 찝찝함, 손 문지름 마찰 자극",
            "strengths": "올리브영 W케어 1등 엠블럼, 산뜻한 티트리 잔향, 친환경 리필 파우치",
            "weaknesses": "특화 기능(안티에이징, 장벽보습 등)의 깊이 부족"
        },
        {
            "brand": "이너시아 (INERTIA)",
            "product_name": "더퓨어 3X 마이크로바이옴",
            "cluster": "메디컬 고기능 문제해결형",
            "is_target": False,
            "orig_price": 25900,
            "sale_price": 22900,
            "volume_ml": 150,
            "unit_price_100ml": 15260,
            "texture": "마이크로 포밍 폼",
            "scent": "천연 아로마 (라벤더/시트러스)",
            "x_score": 3.0,
            "y_score": 8.8,
            "main_copy": "KAIST 여성 과학자 설계, D-만노스 유해균 부착 차단",
            "key_ingredient": "캐나다 청정 빙하수 100%, D-만노스, 락토 신바이오틱스",
            "mechanism": "D-만노스가 유해균의 점막 섬모 흡착을 원천 차단 (Anti-Adhesion)",
            "clinical_proof": "99% 악취 소취, 24종 알러젠 0%, 자극 0.00%",
            "bundle": "150ml 본품 단품 (올리브영 최고가)",
            "hooking": "씻어도 반복되는 재발의 굴레 & 세균의 점막 고착화",
            "strengths": "KAIST 여성 과학자 R&D, 빙하수 베이스, 유해균 부착 차단 차별화",
            "weaknesses": "2만 원대 고가로 인한 가격 저항선"
        },
        {
            "brand": "아토팜 (ATOPALM)",
            "product_name": "매터니티 케어 마일드 앤 수딩",
            "cluster": "더마 약산성 마일드형",
            "is_target": False,
            "orig_price": 24000,
            "sale_price": 14900,
            "volume_ml": 150,
            "unit_price_100ml": 9930,
            "texture": "약산성 버블 폼",
            "scent": "100% 무향",
            "x_score": 3.2,
            "y_score": 4.2,
            "main_copy": "산부인과 테스트 완료! 임산부도 안심하는 7초 말끔 세정",
            "key_ingredient": "네오팜 특허 AMPamide™, 신바이오틱스, 전성분 EWG 그린",
            "mechanism": "피부 장벽 강화 세라마이드 특허 기술 & 잔여물 제로 퀵 린스",
            "clinical_proof": "산부인과 적합성 '아주 좋음', 7초 퀵 린스 잔여물 0%, 3종 유해균 99%",
            "bundle": "150ml 본품 단품 & 올리브영 세일 기획",
            "hooking": "임신/출산 전후 분비물 증가 및 세정 잔여물 자극 불안",
            "strengths": "산부인과 전문의 테스트 공신력, 7초 퀵 린스 실증, 아토팜 1등 민감케어",
            "weaknesses": "임산부 타깃으로 일반 여성 확장 시 한계"
        },
        {
            "brand": "쏘피 (SOFY)",
            "product_name": "쿨링프레쉬 여성청결제",
            "cluster": "클린/비건 웰니스형",
            "is_target": False,
            "orig_price": 16000,
            "sale_price": 9900,
            "volume_ml": 150,
            "unit_price_100ml": 6600,
            "texture": "마일드 쿨링 폼",
            "scent": "은은한 민트 쿨링향",
            "x_score": 7.0,
            "y_score": 6.5,
            "main_copy": "그날의 꿉꿉함을 시원하게 날리다! 은은한 마일드 쿨링 버블",
            "key_ingredient": "식물 유래 쿨링 복합체(멘톨 유도체, 유칼립투스), 락토바실러스",
            "mechanism": "쏘피 독자 리프레싱 쿨링 처방 (자극 없이 시원한 쿨링감)",
            "clinical_proof": "칸디다균 항균 완료, 생리혈/분비물 소취 완료, 피부 저자극 0.00",
            "bundle": "150ml 본품 단품 (올리브영 9천원대 행사)",
            "hooking": "생리대 착용으로 하루 종일 갇힌 열감과 땀, 꿉꿉함과 냄새",
            "strengths": "생리대 1위 쏘피 브랜드 신뢰, 확실한 마일드 쿨링감",
            "weaknesses": "여름철/생리 기간 외 상시 데일리 구매 유인 약함"
        },
        {
            "brand": "유리아쥬 (Uriage)",
            "product_name": "진피 마일드 젤",
            "cluster": "더마 약산성 마일드형",
            "is_target": False,
            "orig_price": 38000,
            "sale_price": 24900,
            "volume_ml": 500,
            "unit_price_100ml": 4980,
            "texture": "마일드 젤",
            "scent": "은은한 플로럴 더마향",
            "x_score": 2.0,
            "y_score": 3.5,
            "main_copy": "프랑스 산부인과 테스트 완료! 특허 글리코-진과 온천수",
            "key_ingredient": "특허 GLYCO-GYN, 프랑스 천연 등장액 온천수",
            "mechanism": "Soap-Free 약산성 pH 5.5 & 글리코-진 점막 보호막 테크",
            "clinical_proof": "프랑스 산부인과 임상 완료, 92% 점막 자극 완화 만족도, 만 4세 승인",
            "bundle": "500ml 메가 대용량 단품 및 200ml 1+1 더블 기획",
            "hooking": "점막 세정 시 따가움과 건조함, 비누 성분(Soap)의 점막 파괴",
            "strengths": "프랑스 온천수 오리진, 글로벌 산부인과 추천 신뢰도",
            "weaknesses": "특유의 향에 대한 호불호"
        },
        {
            "brand": "일리윤 (Illiyoon)",
            "product_name": "세라마이드 더마 페미닌 워시",
            "cluster": "더마 약산성 마일드형",
            "is_target": False,
            "orig_price": 22000,
            "sale_price": 15900,
            "volume_ml": 300,
            "unit_price_100ml": 5300,
            "texture": "약산성 버블 폼",
            "scent": "100% 무향",
            "x_score": 2.5,
            "y_score": 3.8,
            "main_copy": "아모레×일동 공동특허 녹차유래 락토스킨, 약산성 버블",
            "key_ingredient": "아모레퍼시픽×일동제약 특허 녹차 락토스킨, 세라마이드",
            "mechanism": "세라마이드 보습 캡슐 래핑 & 눈시림 없는 안자극 대체 공법",
            "clinical_proof": "안자극 대체 HET-CAM 완료, 하이포알러제닉 통과, 0.00 비자극",
            "bundle": "300ml 대용량 펌프 단품",
            "hooking": "극민감 피부의 세정 후 건조함, 따가움과 피부 장벽 손상",
            "strengths": "아모레퍼시픽 피부과학 연구소 공신력, 녹차 락토스킨 특허",
            "weaknesses": "무난한 기본템 이미지로 소구력 차별화 부족"
        },
        {
            "brand": "클리티 (Cleety)",
            "product_name": "락토 리쥬브네이팅 젤링워시",
            "cluster": "메디컬 고기능 문제해결형",
            "is_target": False,
            "orig_price": 29000,
            "sale_price": 18900,
            "volume_ml": 300,
            "unit_price_100ml": 6300,
            "texture": "수분 젤링 젤",
            "scent": "은은한 천연향",
            "x_score": 2.2,
            "y_score": 9.0,
            "main_copy": "5대 국내외 특허 & 동종업계 최다 8대 임상 완료",
            "key_ingredient": "특허 5종 (제주해수염, 코코넛유산균, 백미꽃, TEFLOSE®)",
            "mechanism": "바이오 세정 + 피부 장벽 보호 + 유익균 부착 증진",
            "clinical_proof": "칸디다 99.35%, 가드넬라 91.14%, 탈취 99.5%, 즉각보습 93.09%",
            "bundle": "300ml 대용량, 500ml 메가 대용량, 1+1 리필 번들",
            "hooking": "분비물 찝찝함, 씻어도 나는 냄새, 세정 후 속당김",
            "strengths": "5대 특허, 8대 임상 성적서 원본 공개, 코스맥스 제조 품질",
            "weaknesses": "신생 브랜드 인지도 극복 필요"
        },
        {
            "brand": "비레시피 (B.RECIPE)",
            "product_name": "리틀머메이드 프로바이오틱스 젤",
            "cluster": "메디컬 고기능 문제해결형",
            "is_target": False,
            "orig_price": 32000,
            "sale_price": 16900,
            "volume_ml": 300,
            "unit_price_100ml": 5630,
            "texture": "고농축 수분 젤",
            "scent": "무향에 가까운 은은향",
            "x_score": 2.8,
            "y_score": 8.7,
            "main_copy": "독일 더마 EXCELLENT! 2대 질염균 99.9% & 탈취 96.1%",
            "key_ingredient": "특허 Eve Solution™, 람노서스 유산균 3종, PHA",
            "mechanism": "질 유래 유산균 배양액 + 약산성 PHA 각질/분비물 정돈",
            "clinical_proof": "칸디다 99.99%, 가드넬라 99.84%, 탈취 96.1%, 2주 보습 30.79%",
            "bundle": "300ml 대용량, 카카오 30% 즉시 할인 쿠폰",
            "hooking": "생리 전후 불쾌취, 냉대하 분비물, 가려움증",
            "strengths": "2대 질염균 99.9% 실명 성적서, 독일 더마테스트 엑설런트",
            "weaknesses": "D2C 자사몰 중심 유통망"
        },
        {
            "brand": "이너생각 (Saengak)",
            "product_name": "밸런싱 휩드워시",
            "cluster": "메디컬 고기능 문제해결형",
            "is_target": False,
            "orig_price": 26000,
            "sale_price": 17900,
            "volume_ml": 180,
            "unit_price_100ml": 9940,
            "texture": "고밀도 에어로졸 생크림 휩",
            "scent": "자연 한방/티트리향",
            "x_score": 3.5,
            "y_score": 8.6,
            "main_copy": "사상자 추출물과 쫀쫀한 휘핑크림 폼! 효과 없으면 100% 환불",
            "key_ingredient": "한방 사상자(오스톨-논문 3편 인용), 락토 듀오",
            "mechanism": "에어로졸 캔 공법으로 완성한 고밀도 생크림 휩 텍스처",
            "clinical_proof": "칸디다 99.9%, 가려움증 67.5% 개선, 암모니아 89.3% 탈취",
            "bundle": "180ml 단품, 2개/3개 번들 구매 시 무료배송",
            "hooking": "씻어도 사라지지 않는 가려움증, 흐물거리는 거품의 마찰 자극",
            "strengths": "100% 전액 환불 보장제, 생크림 휩 텍스처, 가려움 개선 임상",
            "weaknesses": "가스 충전 에어로졸 캔 폐기 번거로움"
        },
        {
            "brand": "질경이 (Jilgyungyi)",
            "product_name": "데일리 에코아 워시 골드",
            "cluster": "메디컬 고기능 문제해결형",
            "is_target": False,
            "orig_price": 22000,
            "sale_price": 16900,
            "volume_ml": 150,
            "unit_price_100ml": 11260,
            "texture": "소프트 버블 폼",
            "scent": "자연 유래 에센셜",
            "x_score": 2.5,
            "y_score": 9.2,
            "main_copy": "단순 세정을 넘어선 Y존 안티에이징! 11개국 특허와 3대 임상",
            "key_ingredient": "11개국 특허 조성물, 바이옴-13, 하이드롤라이즈드 콜라겐",
            "mechanism": "질경이 13개 특허 기술 집약 & 13종 유익균 영양 래핑",
            "clinical_proof": "보습 66%↑, 진피 치밀도(탄력) 증가, 톤 브라이트닝, 칸디다 99.9%",
            "bundle": "150ml 단품 및 N+N 대량 번들 (최대 50% 할인)",
            "hooking": "탄력 저하, 칙칙한 톤, 건조함 등 Y존의 복합 노화",
            "strengths": "6,600만 개 신화, 11개국 특허, 3대 안티에이징 임상 독점",
            "weaknesses": "전통 브랜드 이미지로 20대 유입 장벽"
        },
        {
            "brand": "메디온 (MEDION)",
            "product_name": "락토리메디 포밍워시",
            "cluster": "메디컬 고기능 문제해결형",
            "is_target": False,
            "orig_price": 24000,
            "sale_price": 16900,
            "volume_ml": 150,
            "unit_price_100ml": 11260,
            "texture": "소프트 폼",
            "scent": "은은한 티트리향",
            "x_score": 2.6,
            "y_score": 8.5,
            "main_copy": "Y존 가려움·분비물·냄새 끝! 독자 락토리메디 포밍워시",
            "key_ingredient": "독자 특허 락토리메디(Lacto-Medi™), 티트리 오일",
            "mechanism": "질 내 유익균 환경 조성을 위한 독자 락토 콤플렉스 배합",
            "clinical_proof": "칸디다균 항균 시험 완료, 소취 시험 완료, 피부 저자극 완료",
            "bundle": "150ml 1+1 더블 번들 세트",
            "hooking": "알칼리성 세정으로 무너진 Y존 밸런스, 만성 가려움",
            "strengths": "D2C 질염 개선 1위 브랜드 인지도, 치료/케어 중심 직관적 후킹",
            "weaknesses": "특허 성분의 구체적 시험 수치 공개 부족"
        },
        {
            "brand": "아로마티카 (AROMATICA)",
            "product_name": "퓨어 앤 소프트 / 로즈",
            "cluster": "클린/비건 오가닉형",
            "is_target": False,
            "orig_price": 18000,
            "sale_price": 12000,
            "volume_ml": 170,
            "unit_price_100ml": 7050,
            "texture": "소프트 버블 폼",
            "scent": "100% 천연 에센셜 오일 / 무향",
            "x_score": 9.2,
            "y_score": 4.0,
            "main_copy": "민들레 디콕션 추출수 / 생달나무와 100% 천연 에센셜 오일",
            "key_ingredient": "민들레 추출수(퓨어), 생달나무잎 + 다마스크로즈 오일(로즈)",
            "mechanism": "전통 디콕션(Decoction) 저온 탕법 추출 & 아로마테라피",
            "clinical_proof": "칸디다균 99.9% 항균, 암모니아 99% 소취, 100% 비건 인증",
            "bundle": "170ml 본품 단품 & 올리브영 클린뷰티 기획",
            "hooking": "인공 향료와 유해 화학물질에 대한 불안감, 세정 후 건조",
            "strengths": "클린뷰티 1등 헤리티지, 100% 천연 에센셜 오일의 힐링 아로마",
            "weaknesses": "질염 등 문제성 해결에 대한 의학적 소구 미흡"
        },
        {
            "brand": "디어스킨 (Dearskin)",
            "product_name": "락토 여성청결제",
            "cluster": "클린/비건 오가닉형",
            "is_target": False,
            "orig_price": 17000,
            "sale_price": 11900,
            "volume_ml": 150,
            "unit_price_100ml": 7930,
            "texture": "저자극 버블 폼",
            "scent": "100% 무향",
            "x_score": 8.0,
            "y_score": 3.2,
            "main_copy": "100% 무향 & 21개 안심 성분, 만 4세부터 온 가족 락토 케어",
            "key_ingredient": "락토바실러스 발효용해물, 국내산 어성초 추출물, 14-Free",
            "mechanism": "전성분 21개 미니멀 처방 & 외음부 약산성 밸런싱",
            "clinical_proof": "피부 저자극 지수 0.00 (무자극 판정), 14-Free 유해물질 불검출",
            "bundle": "150ml 본품 단품",
            "hooking": "화학 성분 경피 흡수 불안, 인공 향료 알레르기",
            "strengths": "깨끗한나라 디어스킨 생리대 패밀리 라인업, 21개 안심 성분",
            "weaknesses": "라엘의 8가지 성분 대비 성분 미니멀 소구력 열세"
        },
        {
            "brand": "해피바스 (Happy Bath)",
            "product_name": "정말 순한 / 쑥 여성청결제",
            "cluster": "매스 가성비 데일리형",
            "is_target": False,
            "orig_price": 12000,
            "sale_price": 8900,
            "volume_ml": 300,
            "unit_price_100ml": 2960,
            "texture": "약산성 버블 폼 / 젤",
            "scent": "자연 쑥향 / 은은한 로즈향",
            "x_score": 4.5,
            "y_score": 2.0,
            "main_copy": "국내산 쑥/장미의 편안한 진정, pH 4.5 약산성 데일리 8천원대",
            "key_ingredient": "국내산 황해쑥잎수 / 다마스크 장미꽃수, 락토바실러스",
            "mechanism": "아모레퍼시픽 자연유래 원료 공법 & pH 4.5 약산성 밸런싱",
            "clinical_proof": "칸디다균 항균 완료, 안자극 대체 완료, 피부과 테스트 통과",
            "bundle": "300ml 폼 / 200g 젤 듀얼 라인업 (8천원대)",
            "hooking": "매일 쓰는 세정제의 가격 부담, 알칼리 세정 가려움",
            "strengths": "8~9천 원대 파격 최저가 가성비, 300ml 대용량",
            "weaknesses": "프리미엄 이미지 부재 및 낮은 마진"
        }
    ]
    return pd.DataFrame(data)

df = load_market_data()

# -------------------------------------------------------------
# 4. 헤더 및 필수 KPI 요약 카드 (Top Section)
# -------------------------------------------------------------
st.title("🌸 여성청결제 시장 분석 & 상세페이지 리뉴얼 대시보드")
st.caption("18개 주요 브랜드(올리브영 입점 1위 및 D2C) 전수 벤치마킹 데이터 기반 · 포지셔닝 맵 · 실제 컷 갤러리 · 라엘 리뉴얼 전략 뷰어")

st.markdown("---")

# 5개 핵심 KPI 카드 배치
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

total_brands = len(df)
avg_sale_price = df["sale_price"].mean()
avg_unit_price = df["unit_price_100ml"].mean()
antibacterial_ratio = 73.3
probiotics_ratio = 86.7

with kpi1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">총 분석 브랜드</div>
        <div class="metric-value">{total_brands}개</div>
        <div class="metric-delta">전수 벤치마킹 완료</div>
    </div>
    """, unsafe_allow_html=True)

with kpi2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">시장 평균 판매가</div>
        <div class="metric-value">{int(avg_sale_price):,}원</div>
        <div class="metric-delta">라엘: 12,900원 (적정가)</div>
    </div>
    """, unsafe_allow_html=True)

with kpi3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">100ml당 평균 단가</div>
        <div class="metric-value">{int(avg_unit_price):,}원</div>
        <div class="metric-delta">라엘: 8,600원</div>
    </div>
    """, unsafe_allow_html=True)

with kpi4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">칸디다 99.9% 항균 소구율</div>
        <div class="metric-value">{antibacterial_ratio}%</div>
        <div class="metric-delta">상위 1% 완판 필수 조건</div>
    </div>
    """, unsafe_allow_html=True)

with kpi5:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">유산균/바이옴 채택율</div>
        <div class="metric-value">{probiotics_ratio}%</div>
        <div class="metric-delta">카테고리 기본 스펙화</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# -------------------------------------------------------------
# 5. 사이드바 필터링 컨트롤
# -------------------------------------------------------------
st.sidebar.header("🔍 데이터 필터 및 탐색")
selected_cluster = st.sidebar.multiselect(
    "클러스터 필터",
    options=df["cluster"].unique(),
    default=df["cluster"].unique()
)

selected_texture = st.sidebar.multiselect(
    "제형 필터",
    options=df["texture"].unique(),
    default=df["texture"].unique()
)

price_range = st.sidebar.slider(
    "판매가 범위 (원)",
    min_value=int(df["sale_price"].min()),
    max_value=int(df["sale_price"].max()),
    value=(int(df["sale_price"].min()), int(df["sale_price"].max())),
    step=1000
)

# 필터링된 데이터프레임
filtered_df = df[
    (df["cluster"].isin(selected_cluster)) &
    (df["texture"].isin(selected_texture)) &
    (df["sale_price"] >= price_range[0]) &
    (df["sale_price"] <= price_range[1])
]

# -------------------------------------------------------------
# 6. 메인 6대 탭 구조 (올리브영 갤러리 포함)
# -------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 1. 시장 개요 & 가격 분석",
    "🗺️ 2. 2x2 포지셔닝 맵 (Interactive)",
    "🔍 3. 18개 브랜드 전수 비교 매트릭스",
    "🖼️ 4. 상세페이지 이미지 갤러리 & 비교 뷰어",
    "📑 5. 상세페이지 Storyline 전개 비교",
    "🚀 6. 라엘(Target) 심층 진단 & 레퍼런스 벤치마킹"
])

# -------------------------------------------------------------
# TAB 1: 시장 개요 & 가격 분석 (Plotly 독점)
# -------------------------------------------------------------
with tab1:
    st.subheader("📊 여성청결제 시장 가격대 및 용량별 단가 분석")
    st.caption("Plotly 차트를 활용하여 시장 내 브랜드별 가격 분포와 100ml당 단가 구조를 다각도로 비교합니다.")
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        fig_price = px.bar(
            filtered_df.sort_values(by="sale_price", ascending=False),
            x="brand",
            y="sale_price",
            color="cluster",
            text="sale_price",
            title="브랜드별 실판매가 비교 (단위: 원)",
            labels={"sale_price": "판매가 (원)", "brand": "브랜드명", "cluster": "클러스터"},
            color_discrete_map={
                "메디컬 고기능 문제해결형": "#0F172A",
                "더마 약산성 마일드형": "#3B82F6",
                "클린/비건 오가닉형": "#10B981",
                "클린/비건 웰니스형": "#14B8A6",
                "매스 가성비 데일리형": "#F59E0B"
            }
        )
        fig_price.update_traces(texttemplate='%{text:,.0f}원', textposition='outside')
        fig_price.update_layout(xaxis_tickangle=-45, plot_bgcolor="rgba(0,0,0,0)", height=450)
        st.plotly_chart(fig_price, use_container_width=True)
        
    with col_chart2:
        fig_scatter = px.scatter(
            filtered_df,
            x="volume_ml",
            y="unit_price_100ml",
            size="sale_price",
            color="cluster",
            hover_name="brand",
            text="brand",
            title="용량(ml) 대비 100ml당 단가 분포 (버블 크기: 판매가)",
            labels={"volume_ml": "용량 (ml)", "unit_price_100ml": "100ml당 단가 (원)"},
            color_discrete_map={
                "메디컬 고기능 문제해결형": "#0F172A",
                "더마 약산성 마일드형": "#3B82F6",
                "클린/비건 오가닉형": "#10B981",
                "클린/비건 웰니스형": "#14B8A6",
                "매스 가성비 데일리형": "#F59E0B"
            }
        )
        fig_scatter.update_traces(textposition='top center')
        fig_scatter.update_layout(plot_bgcolor="rgba(0,0,0,0)", height=450)
        st.plotly_chart(fig_scatter, use_container_width=True)

# -------------------------------------------------------------
# TAB 2: 인터랙티브 2x2 포지셔닝 맵 (Plotly Scatter)
# -------------------------------------------------------------
with tab2:
    st.subheader("🗺️ 여성청결제 시장 2x2 포지셔닝 맵 & Next White Space")
    st.caption("X축(더마/임상 과학 ↔ 클린/자연주의)과 Y축(문제성 해결 ↔ 데일리 마일드)에 따른 브랜드 분포와 라엘의 Next 목표 위치를 시각화합니다.")
    
    fig_map = go.Figure()
    
    fig_map.add_shape(type="rect", x0=1, y0=5.5, x1=5.5, y1=10, fillcolor="#F1F5F9", opacity=0.5, line_width=0, layer="below")
    fig_map.add_shape(type="rect", x0=5.5, y0=5.5, x1=10, y1=10, fillcolor="#CCFBF1", opacity=0.7, line_width=2, line_color="#0D9488", layer="below")
    fig_map.add_shape(type="rect", x0=1, y0=1, x1=5.5, y1=5.5, fillcolor="#F8FAFC", opacity=0.5, line_width=0, layer="below")
    fig_map.add_shape(type="rect", x0=5.5, y0=1, x1=10, y1=5.5, fillcolor="#FEF2F2", opacity=0.5, line_width=1, line_color="#E11D48", layer="below")
    
    fig_map.add_annotation(x=3.25, y=9.6, text="<b>클러스터 1: 메디컬 / 고기능 문제 해결형</b>", showarrow=False, font=dict(size=12, color="#1E293B"))
    fig_map.add_annotation(x=7.75, y=9.6, text="<b>★ Next White Space: 클린 사이언스 펨테크</b>", showarrow=False, font=dict(size=13, color="#0F766E"))
    fig_map.add_annotation(x=3.25, y=1.4, text="<b>클러스터 2: 더마 / 약산성 마일드형</b>", showarrow=False, font=dict(size=12, color="#1E293B"))
    fig_map.add_annotation(x=7.75, y=1.4, text="<b>클러스터 3: 클린뷰티 오가닉 미니멀형</b>", showarrow=False, font=dict(size=12, color="#991B1B"))
    
    comp_df = df[~df["is_target"]]
    fig_map.add_trace(go.Scatter(
        x=comp_df["x_score"],
        y=comp_df["y_score"],
        mode="markers+text",
        text=comp_df["brand"],
        textposition="top center",
        marker=dict(size=14, color="#334155", line=dict(width=1.5, color="#FFFFFF")),
        name="경쟁 브랜드",
        hovertemplate="<b>%{text}</b><br>카테고리: %{customdata[0]}<br>메인 카피: %{customdata[1]}<br>실판매가: %{customdata[2]:,}원<extra></extra>",
        customdata=comp_df[["cluster", "main_copy", "sale_price"]].values
    ))
    
    target_row = df[df["is_target"]].iloc[0]
    fig_map.add_trace(go.Scatter(
        x=[target_row["x_score"]],
        y=[target_row["y_score"]],
        mode="markers+text",
        text=["🔴 라엘 (현재 위치)"],
        textposition="bottom center",
        marker=dict(size=20, color="#E11D48", symbol="diamond", line=dict(width=2, color="#FFFFFF")),
        name="라엘 (현재)",
        hovertemplate="<b>%{text}</b><br>단 8가지 성분, COSMOS 인증<br>[한계] 항균/탈취 수치 부재로 고민해결 고객 이탈<extra></extra>"
    ))
    
    fig_map.add_trace(go.Scatter(
        x=[8.2],
        y=[8.8],
        mode="markers+text",
        text=["★ 라엘 (Next 목표 포지션)"],
        textposition="top center",
        marker=dict(size=24, color="#0D9488", symbol="star", line=dict(width=2, color="#FFFFFF")),
        name="라엘 (Next 목표)",
        hovertemplate="<b>★ 라엘 Next: 클린 사이언스 펨테크</b><br>COSMOS 천연 유기농 + D-만노스 부착 방어 + 칸디다 99.9% 항균<extra></extra>"
    ))
    
    fig_map.add_annotation(
        x=8.2, y=8.5,
        ax=target_row["x_score"], ay=target_row["y_score"],
        xref="x", yref="y", axref="x", ayref="y",
        showarrow=True,
        arrowhead=3,
        arrowsize=1.5,
        arrowwidth=3,
        arrowcolor="#0D9488"
    )
    
    fig_map.update_layout(
        title="여성청결제 시장 포지셔닝 매트릭스 및 라엘 리뉴얼 이동 경로",
        xaxis=dict(title="◄ 더마 / 임상 과학 (Science & Medical) ────────────── 클린 / 비건 / 자연주의 (Clean & Natural) ►", range=[0.5, 10.5], showgrid=False, zeroline=False),
        yaxis=dict(title="▼ 데일리 마일드 케어 (Daily Mild) ────────────── 문제성 집중 케어 (Problem-Solving) ▲", range=[0.5, 10.5], showgrid=False, zeroline=False),
        height=620,
        plot_bgcolor="#FFFFFF",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig_map, use_container_width=True)

# -------------------------------------------------------------
# TAB 3: 18개 브랜드 전수 비교 매트릭스 (라엘 최상단 고정)
# -------------------------------------------------------------
with tab3:
    st.subheader("🔍 18개 브랜드 1:1 상세 비교 매트릭스 & 상세 탐색기")
    st.caption("라엘(★ 기준 타깃)을 최상단으로 하여 18개 전 브랜드의 상세 분석 카드를 한 페이지에서 스크롤하여 전체 비교할 수 있습니다.")
    
    display_df = filtered_df[["brand", "product_name", "cluster", "sale_price", "volume_ml", "unit_price_100ml", "main_copy", "clinical_proof"]]
    st.dataframe(
        display_df.rename(columns={
            "brand": "브랜드명",
            "product_name": "제품명",
            "cluster": "포지셔닝 클러스터",
            "sale_price": "할인가 (원)",
            "volume_ml": "용량 (ml)",
            "unit_price_100ml": "100ml당 단가",
            "main_copy": "최상단 메인 헤드카피",
            "clinical_proof": "공인 임상/테스트 수치"
        }),
        use_container_width=True,
        height=300
    )
    
    st.markdown("---")
    st.markdown("### 📋 18개 전 브랜드 상세 소구점 & 6대 요소 전수 비교 (라엘 최상단)")
    
    target_df = filtered_df[filtered_df["is_target"]]
    non_target_df = filtered_df[~filtered_df["is_target"]]
    ordered_df = pd.concat([target_df, non_target_df])
    
    for idx, row in ordered_df.iterrows():
        is_target = row["is_target"]
        
        if is_target:
            card_border_style = "border: 2px solid #3B82F6; background: #F8FAFC; border-radius: 12px; padding: 20px; margin-bottom: 24px; box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.1);"
            badge_html = '<span style="background-color: #2563EB; color: white; padding: 4px 12px; border-radius: 20px; font-weight: 800; font-size: 0.85rem;">★ 분석 기준 타깃 제품 (Target)</span>'
        else:
            card_border_style = "border: 1px solid #E2E8F0; background: #FFFFFF; border-radius: 12px; padding: 18px 20px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);"
            badge_html = f'<span style="background-color: #F1F5F9; color: #475569; padding: 3px 10px; border-radius: 16px; font-weight: 600; font-size: 0.8rem;">{row["cluster"]}</span>'
            
        with st.container():
            st.markdown(f"""
            <div style="{card_border_style}">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <div style="font-size: 1.25rem; font-weight: 800; color: #0F172A;">
                        🏷️ {row['brand']} — <span style="font-size: 1.05rem; font-weight: 600; color: #334155;">{row['product_name']}</span>
                    </div>
                    <div>{badge_html}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            c_info, c_details = st.columns([1, 2.2])
            
            with c_info:
                st.markdown(f"""
                - **정상가 / 할인가**: {row['orig_price']:,}원 ──► **{row['sale_price']:,}원**
                - **용량 / 100ml 단가**: {row['volume_ml']}ml (**{row['unit_price_100ml']:,}원**)
                - **제형 & 향료**: {row['texture']} | {row['scent']}
                - **프로모션 구성**: {row['bundle']}
                """)
                
            with c_details:
                st.markdown(f"""
                - 🎯 **최상단 메인 카피**: *"{row['main_copy']}"*
                - 🪝 **도입부 후킹 포인트**: {row['hooking']}
                - 🌿 **핵심 유효 성분 & 포뮬러**: {row['key_ingredient']}
                - ⚙️ **기술 및 메커니즘**: {row['mechanism']}
                - 📊 **공인 임상 & 안전성 실증**: **{row['clinical_proof']}**
                - 🟢 **핵심 강점**: {row['strengths']}
                - 🔴 **보완점 / 한계점**: {row['weaknesses']}
                """)
                
            st.markdown("<hr style='margin: 10px 0 20px 0; border: 0; border-top: 1px dashed #CBD5E1;'>", unsafe_allow_html=True)

# -------------------------------------------------------------
# TAB 4: 상세페이지 이미지 갤러리 & 비교 뷰어 (올리브영 입점 브랜드 대폭 확장)
# -------------------------------------------------------------
with tab4:
    st.subheader("🖼️ 주요 브랜드 상세페이지 실제 컷 갤러리 & 소구 포인트 비교 뷰어")
    st.caption("올리브영 1등 입점 브랜드 및 상위 D2C 브랜드의 실제 상세페이지 컷과 벤치마킹 핵심 소구 포인트들을 심층 비교합니다.")
    
    brand_gallery_choice = st.selectbox(
        "상세페이지 실제 컷과 소구 포인트를 확인할 브랜드를 선택하세요:",
        options=[
            "🥇 바솔 (BASOL) - 올리브영 1등 W케어 & 리필 파우치 기획 [올영 1등]",
            "🔬 이너시아 (INERTIA) - KAIST 펨테크 & D-만노스 유해균 차단 [올영 고기능]",
            "🩺 아토팜 (ATOPALM) - 산부인과 테스트 & 7초 퀵 린스 [올영 더마/임산부]",
            "❄️ 쏘피 (SOFY) - 마일드 쿨링 폼 & 생리 꿉꿉함 해소 [올영 시즌/생리]",
            "💧 유리아쥬 (URIAGE) - 프랑스 온천수 & 특허 글리코-진 [올영 글로벌 더마]",
            "🌿 일리윤 (ILLIYOON) - 아모레×일동 녹차 락토스킨 & 안자극 0.00 [올영 대용량]",
            "💎 클리티 (Cleety) - 8대 임상 성적서 & 5대 특허 [D2C 임상 폭격]",
            "🧪 뷰티레시피 (B.RECIPE) - 2대 질염균 99.9% & 독일 더마 EXCELLENT [D2C 질염 해결]",
            "☁️ 이너생각 (Saengak) - 고밀도 생크림 휩 & 100% 무료 환불 [D2C 제형/전환율]",
            "★ 라엘 (Rael) - COSMOS 천연 인증 & 단 8가지 성분 [기준 타깃 현재 컷]"
        ]
    )
    
    # 1. 바솔 (올리브영 1등)
    if "바솔" in brand_gallery_choice:
        st.markdown("#### 🥇 바솔(BASOL) 이너 밸런싱 포밍 워시 [올리브영 W케어 1등]")
        st.markdown("""
        <div class="ref-box-oliveyoung">
            <h5 style="color: #0284C7; margin-top:0;">💡 올리브영 1등 바솔의 핵심 소구 포인트:</h5>
            <ul>
                <li><strong>올리브영 1등 엠블럼 선점:</strong> 상단 3초 존에 <strong>'올리브영 W케어 1등'</strong> 공식 뱃지를 배치하여 첫인상 압도적 신뢰 확보.</li>
                <li><strong>친환경 더블 번들 락인:</strong> <code>[본품 150ml + 친환경 리필 파우치 150ml]</code> 기획으로 플라스틱 절감과 객단가/재구매율 동시 확보.</li>
                <li><strong>티트리 에센셜 소취 쿨링:</strong> 락토바실러스 발효물과 호주산 티트리 오일로 냄새와 찝찝함을 산뜻하게 해결.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        g1, g2, g3 = st.columns(3)
        with g1:
            p = get_safe_image_path("images/basol/basol_detail_01.png")
            if p: st.image(p, caption="[Hero 컷] 올리브영 1등 엠블럼 & 리필 세트", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'올리브영 W케어 1등! 본품+리필 더블 기획'*\n\n📌 **포인트**: 1등 엠블럼과 리필 파우치의 친환경 가치 제시")
        with g2:
            p = get_safe_image_path("images/basol/basol_detail_02.png")
            if p: st.image(p, caption="[성분 컷] 락토 티트리 마일드 포뮬러", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'유익균 보호와 산뜻한 티트리 밸런스'*\n\n📌 **포인트**: 티트리 잎 오일과 락토바실러스 배합의 저자극 세정")
        with g3:
            p = get_safe_image_path("images/basol/basol_detail_03.png")
            if p: st.image(p, caption="[임상 컷] 칸디다균 99.9% 항균 실증", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'칸디다균 99.9% 항균 & 2대 악취 가스 소취'*\n\n📌 **포인트**: 공인 시험기관의 항균 및 소취 시험 결과 그래프")

    # 2. 이너시아 (KAIST 펨테크)
    elif "이너시아" in brand_gallery_choice:
        st.markdown("#### 🔬 이너시아(INERTIA) 더퓨어 3X 마이크로바이옴 [올리브영 최고가 펨테크]")
        st.markdown("""
        <div class="ref-box-oliveyoung">
            <h5 style="color: #0284C7; margin-top:0;">💡 KAIST 펨테크 이너시아의 핵심 소구 포인트:</h5>
            <ul>
                <li><strong>KAIST 여성 과학자 R&D 신뢰도:</strong> 정제수 대신 <strong>'캐나다 청정 빙하수 100%'</strong> 베이스를 사용해 22,900원 프리미엄 정당화.</li>
                <li><strong>D-만노스 유해균 점막 부착 방어 (Anti-Adhesion):</strong> 단순 살균이 아닌 <em>"세균의 점막 섬모 결합을 차단하여 소변/물과 함께 배출"</em>하는 과학적 기전 최초 도입.</li>
                <li><strong>24종 알러젠 0% & 99% 악취 소취:</strong> 천연 아로마 에센셜 블렌딩으로 냄새 완벽 케어.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        g1, g2, g3 = st.columns(3)
        with g1:
            p = get_safe_image_path("images/inertia/inertia_detail_01.png")
            if p: st.image(p, caption="[Hero 컷] KAIST 여성 과학자 설계 바이옴 워시", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'KAIST 여성 과학자가 설계한 3X 마이크로바이옴'*\n\n📌 **포인트**: 과학적 전문성과 펨테크 브랜드 오리진")
        with g2:
            p = get_safe_image_path("images/inertia/inertia_detail_02.png")
            if p: st.image(p, caption="[원리 컷] D-만노스 유해균 점막 부착 차단", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'유해균이 점막에 달라붙지 못하도록 원천 차단'*\n\n📌 **포인트**: 3D 바이오 메커니즘 일러스트레이션으로 기전 규명")
        with g3:
            p = get_safe_image_path("images/inertia/inertia_detail_03.png")
            if p: st.image(p, caption="[성분 컷] 캐나다 청정 빙하수 100%", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'정제수 0%, 캐나다 빙하수로 채운 깊은 진정'*\n\n📌 **포인트**: 베이스 원료의 극단적 차별화로 고가격 납득")

    # 3. 아토팜 (산부인과 & 7초 퀵린스)
    elif "아토팜" in brand_gallery_choice:
        st.markdown("#### 🩺 아토팜(ATOPALM) 매터니티 케어 마일드 앤 수딩 [산부인과 테스트 1위]")
        st.markdown("""
        <div class="ref-box-oliveyoung">
            <h5 style="color: #0284C7; margin-top:0;">💡 아토팜 매터니티 케어의 핵심 소구 포인트:</h5>
            <ul>
                <li><strong>산부인과 피부 사용 적합성 '아주 좋음':</strong> 임산부 및 극민감성 여성을 위한 최고 수준의 의학적 안전성 공인.</li>
                <li><strong>7초 퀵 린스(Quick Rinse) 인체적용시험:</strong> <em>"단 7초 만에 점막 잔여물 0%로 씻겨 내려가는 말끔함"</em>을 실증하여 잔여물 불안감 해소.</li>
                <li><strong>네오팜 독자 특허 진정 성분 AMPamide™:</strong> 세라마이드 피부 장벽 보호.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        g1, g2, g3 = st.columns(3)
        with g1:
            p = get_safe_image_path("images/atopalm/atopalm_detail_01.png")
            if p: st.image(p, caption="[Hero 컷] 산부인과 피부 사용 적합성 테스트 완료", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'산부인과 전문의 테스트 완료 아주 좋음 획득'*\n\n📌 **포인트**: 전문의 평가 엠블럼으로 임산부도 100% 안심")
        with g2:
            p = get_safe_image_path("images/atopalm/atopalm_detail_02.png")
            if p: st.image(p, caption="[임상 컷] 7초 퀵 린스 잔여물 0% 실증", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'7초 만에 잔여물 없이 말끔하게 씻기는 퀵 린스'*\n\n📌 **포인트**: 세정 잔여물이 점막에 남지 않는 초고속 워시아웃 증명")
        with g3:
            p = get_safe_image_path("images/atopalm/atopalm_detail_03.png")
            if p: st.image(p, caption="[성분 컷] 독자 특허 진정 성분 AMPamide™", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'네오팜 독자 특허 진정 성분과 신바이오틱스'*\n\n📌 **포인트**: 민감한 Y존 장벽을 무너뜨리지 않는 약산성 처방")

    # 4. 쏘피 (쿨링 폼)
    elif "쏘피" in brand_gallery_choice:
        st.markdown("#### ❄️ 쏘피(SOFY) 쿨링프레쉬 여성청결제 [생리 꿉꿉함 전문 케어]")
        st.markdown("""
        <div class="ref-box-oliveyoung">
            <h5 style="color: #0284C7; margin-top:0;">💡 쏘피 쿨링프레쉬의 핵심 소구 포인트:</h5>
            <ul>
                <li><strong>생리 기간 맞춤 쿨링 솔루션:</strong> 생리대 착용으로 하루 종일 갇힌 열감과 땀, 꿉꿉함을 <strong>'마일드 쿨링 버블'</strong>로 즉각 리프레시.</li>
                <li><strong>생리대 1위 브랜드 크로스셀링:</strong> 쏘피 생리대 고객층을 자연스럽게 Y존 청결제로 유입.</li>
                <li><strong>9천 원대 가성비 & 락토바실러스 발효물:</strong> 칸디다균 항균 및 생리혈 불쾌취 소취 완료.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        g1, g2, g3 = st.columns(3)
        with g1:
            p = get_safe_image_path("images/sofy/sofy_detail_01.png")
            if p: st.image(p, caption="[Hero 컷] 그날의 꿉꿉함을 시원하게 쿨링", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'답답하고 찝찝했던 그날, 상쾌한 쿨링으로 리셋'*\n\n📌 **포인트**: 생리 전후 고객의 직관적 불쾌감 타깃팅")
        with g2:
            p = get_safe_image_path("images/sofy/sofy_detail_02.png")
            if p: st.image(p, caption="[제형 컷] 은은한 쿨링 버블 폼", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'자극 없이 은은하게 퍼지는 마일드 쿨링감'*\n\n📌 **포인트**: 멘톨 유도체와 유칼립투스의 자극 없는 청량감")
        with g3:
            p = get_safe_image_path("images/sofy/sofy_detail_03.png")
            if p: st.image(p, caption="[임상 컷] 불쾌취 소취 & 칸디다균 항균", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'생리혈 냄새와 유해균을 깨끗하게'*\n\n📌 **포인트**: 탈취 및 저자극 테스트 0.00 비자극 인증")

    # 5. 유리아쥬
    elif "유리아쥬" in brand_gallery_choice:
        st.markdown("#### 💧 유리아쥬(URIAGE) 진피 마일드 젤 [프랑스 온천수 글로벌 더마]")
        st.markdown("""
        <div class="ref-box-oliveyoung">
            <h5 style="color: #0284C7; margin-top:0;">💡 유리아쥬 진피 마일드 젤의 핵심 소구 포인트:</h5>
            <ul>
                <li><strong>프랑스 천연 등장액 온천수:</strong> 세포와 삼투압이 동일하여 세정 시 따가움과 건조함이 없는 독보적 워터 베이스.</li>
                <li><strong>특허 GLYCO-GYN COMPLEX:</strong> 글리코 에스테르가 점막 건조를 방지하고 장벽 보호막 형성.</li>
                <li><strong>Soap-Free (무비누) & 만 4세 사용 승인:</strong> 유아부터 임산부까지 온 가족 패밀리 케어.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        g1, g2, g3 = st.columns(3)
        with g1:
            p = get_safe_image_path("images/uriage/uriage_detail_01.png")
            if p: st.image(p, caption="[Hero 컷] 프랑스 산부인과 테스트 완료", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'프랑스 여성청결제 1등, 특허 글리코-진과 온천수'*\n\n📌 **포인트**: 글로벌 더마코스메틱 브랜드 공신력")
        with g2:
            p = get_safe_image_path("images/uriage/uriage_detail_02.png")
            if p: st.image(p, caption="[성분 컷] Soap-Free & 천연 등장액 온천수", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'비누 성분 없이 자극 없는 마일드 클렌징'*\n\n📌 **포인트**: 외음부 점막을 자극하지 않는 순한 처방")
        with g3:
            p = get_safe_image_path("images/uriage/uriage_detail_03.png")
            if p: st.image(p, caption="[임상 컷] 92% 점막 자극 완화 만족도", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'만 4세 아이부터 임산부까지 온 가족 사용'*\n\n📌 **포인트**: 패밀리 대용량 락인을 이끄는 안전성")

    # 6. 일리윤
    elif "일리윤" in brand_gallery_choice:
        st.markdown("#### 🌿 일리윤(ILLIYOON) 세라마이드 더마 페미닌 워시 [대기업 더마 장벽]")
        st.markdown("""
        <div class="ref-box-oliveyoung">
            <h5 style="color: #0284C7; margin-top:0;">💡 일리윤 세라마이드 더마의 핵심 소구 포인트:</h5>
            <ul>
                <li><strong>아모레퍼시픽 × 일동제약 공동특허:</strong> <code>녹차 유래 락토스킨 콤플렉스™</code>로 프로바이오틱스 과학 입증.</li>
                <li><strong>안자극 대체 테스트 (HET-CAM) 통과:</strong> 눈에 들어가도 시리지 않을 만큼 순한 점막 자극 제로 실증.</li>
                <li><strong>100% 무향 & 300ml 대용량:</strong> 5천원대 극가성비 펌프 용기로 데일리 장악.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        g1, g2, g3 = st.columns(3)
        with g1:
            p = get_safe_image_path("images/illiyoon/illiyoon_detail_01.png")
            if p: st.image(p, caption="[Hero 컷] 녹차 유래 락토스킨 더마 워시", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'아모레퍼시픽×일동제약 공동개발 특허 락토스킨'*\n\n📌 **포인트**: 양대 대기업 R&D 신뢰도 전면 강조")
        with g2:
            p = get_safe_image_path("images/illiyoon/illiyoon_detail_02.png")
            if p: st.image(p, caption="[안전성 컷] 안자극 대체 HET-CAM 통과", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'눈시림 없는 안자극 대체 테스트 완료'*\n\n📌 **포인트**: 점막 민감도에 대한 극단적 안심 보증")
        with g3:
            p = get_safe_image_path("images/illiyoon/illiyoon_detail_03.png")
            if p: st.image(p, caption="[제형 컷] 100% 무향 약산성 버블", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'인공 향료 0%, 300ml 넉넉한 대용량'*\n\n📌 **포인트**: 무향 데일리 세정의 편안함")

    # 7. 클리티
    elif "클리티" in brand_gallery_choice:
        st.markdown("#### 💎 클리티(Cleety) 락토 리쥬브네이팅 젤링워시 [8대 임상 & 5대 특허]")
        st.info("💡 **소구 특징**: 5대 특허 엠블럼과 8대 공인 임상 성적서 원본을 상단 3초 존에 배치하여 압도적인 의학적 신뢰감을 조성합니다.")
        
        g1, g2, g3, g4 = st.columns(4)
        with g1:
            p = get_safe_image_path("images/cleety/cleety_detail_01.jpg")
            if p: st.image(p, caption="[Hero 컷] 5대 특허 & 8대 임상 엠블럼", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'단순한 세정이 아닌 Y존 리쥬브네이팅의 시작'*\n\n📌 **기법**: 3초 만에 시선을 사로잡는 특허 인증마크 전면 배치")
        with g2:
            p = get_safe_image_path("images/cleety/cleety_detail_02.jpg")
            if p: st.image(p, caption="[문제 공감 컷] Y존 7대 고민 자가진단표", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'씻어도 사라지지 않는 찝찝함과 냄새, 왜 그럴까요?'*\n\n📌 **기법**: 고객 결핍을 자극하는 체크리스트 전개")
        with g3:
            p = get_safe_image_path("images/cleety/cleety_detail_05.jpg")
            if p: st.image(p, caption="[임상 실증 컷] 칸디다 99.3% & 탈취 99.5%", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'숫자로 확인하는 놀라운 99.3% 유해균 케어'*\n\n📌 **기법**: 시험 성적서 원본 스캔본 및 균 배양 샬레 비교 컷")
        with g4:
            p = get_safe_image_path("images/cleety/cleety_detail_08.jpg")
            if p: st.image(p, caption="[성분 솔루션 컷] 제주해수염 & 유산균", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'특허 TEFLOSE®로 유해균 부착 원천 방어'*\n\n📌 **기법**: 3D 바이오 메커니즘 일러스트레이션")

    # 8. 뷰티레시피
    elif "뷰티레시피" in brand_gallery_choice:
        st.markdown("#### 🧪 뷰티레시피(B.RECIPE) 리틀머메이드 프로바이오틱스 젤 [99.9% 항균]")
        st.info("💡 **소구 특징**: 2대 질염 원인균(칸디다 99.99%, 가드넬라 99.84%) 실명 명시와 독일 더마테스트 EXCELLENT 마크로 구매 저항을 완벽 해소합니다.")
        
        g1, g2, g3, g4 = st.columns(4)
        with g1:
            p = get_safe_image_path("images/beautyrecipe/brecipe_img_01.jpg")
            if p: st.image(p, caption="[Hero 컷] 독일 더마 EXCELLENT & 99.9% 항균", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'독일 더마테스트 최고등급 획득 안심 포뮬러'*\n\n📌 **기법**: 글로벌 공신력 엠블럼 상단 즉각 노출")
        with g2:
            p = get_safe_image_path("images/beautyrecipe/brecipe_img_03.jpg")
            if p: st.image(p, caption="[임상 실증 컷] 2대 질염균 99.9% 성적서", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'칸디다균 99.99%, 가드넬라균 99.84% 실증'*\n\n📌 **기법**: 한국피부과학연구원 공인 시험성적서 원본 공개")
        with g3:
            p = get_safe_image_path("images/beautyrecipe/brecipe_img_06.jpg")
            if p: st.image(p, caption="[성분 컷] 특허 여성세정제 조성물 Eve Solution™", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'특허 제10-2061302호 항균/소취 독자 조성물'*\n\n📌 **기법**: 특허 등록 번호 명시를 통한 기술력 정당화")
        with g4:
            p = get_safe_image_path("images/beautyrecipe/brecipe_img_08.jpg")
            if p: st.image(p, caption="[제형 컷] 약산성 pH 3.5~4.5 수분 젤", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'건조함 없는 고농축 수분 젤 텍스처'*\n\n📌 **기법**: pH 리트머스 시험지 및 2주 보습 30.79% 개선 실증")

    # 9. 이너생각
    elif "이너생각" in brand_gallery_choice:
        st.markdown("#### ☁️ 이너생각(Saengak) 밸런싱 휩드워시 [생크림 휩 & 100% 환불]")
        st.info("💡 **소구 특징**: 에어로졸 캔 공법의 생크림 휩 텍스처, 가려움증 67.5% 개선 임상, '100% 무료 환불 보장제'로 전환율을 극대화합니다.")
        
        g1, g2, g3, g4 = st.columns(4)
        with g1:
            p = get_safe_image_path("images/saengak/saengak_detail_01.png")
            if p: st.image(p, caption="[Hero 컷] 생크림 휩 텍스처 & 가려움 개선", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'단 한 번의 펌핑으로 완성되는 쫀쫀한 생크림 휩'*\n\n📌 **기법**: 마찰 자극 없는 거품 볼륨감 시각화")
        with g2:
            p = get_safe_image_path("images/saengak/saengak_detail_06.jpg")
            if p: st.image(p, caption="[성분 컷] 한방 사상자 추출물 (오스톨)", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'조선왕실 비책 사상자의 놀라운 진정 효과'*\n\n📌 **기법**: SCI급 논문 3편 인용으로 전통 한방 원료의 과학적 입증")
        with g3:
            p = get_safe_image_path("images/saengak/saengak_detail_14.jpg")
            if p: st.image(p, caption="[임상 실증 컷] 가려움증 67.5% 개선 성적서", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'단 2주 만에 확인된 가려움증 67.5% 완화'*\n\n📌 **기법**: 고객 최다 고민인 가려움에 대한 정량 수치 그래프")
        with g4:
            p = get_safe_image_path("images/saengak/saengak_detail_25.png")
            if p: st.image(p, caption="[전환 장치 컷] 100% 무료 환불 보장제", use_container_width=True)
            st.caption("🎯 **핵심 카피**: *'사용 후 불만족 시 100% 환불해 드립니다'*\n\n📌 **기법**: 구매 저항선을 0으로 낮추는 강력한 리스크 리버설")

    # 10. 라엘 현재 컷
    else:
        st.markdown("#### ★ 라엘(Rael) 천연 여성청결제 [기준 제품 현재 상세페이지 컷]")
        st.warning("💡 **현재 소구 특징 및 한계**: COSMOS 천연 유기농 인증과 단 8가지 전성분을 강조하나, 고객의 '냄새/분비물/가려움' 해결 수치가 없어 전환율에 한계가 존재합니다.")
        
        g1, g2, g3 = st.columns(3)
        with g1:
            p = get_safe_image_path("images/target_rael/target_rael_detail_01.png")
            if p: st.image(p, caption="[Hero 컷] 단 8가지 전성분 천연 여성청결제", use_container_width=True)
            st.caption("🎯 **현재 카피**: *'단 8가지 전성분, COSMOS 천연 인증'*\n\n📌 **진단**: 제품 설명 위주로 냄새/가려움 고통 공감 부족")
        with g2:
            p = get_safe_image_path("images/target_rael/target_rael_detail_02.png")
            if p: st.image(p, caption="[성분 컷] 불필요한 성분을 배제한 미니멀 처방", use_container_width=True)
            st.caption("🎯 **현재 카피**: *'식물 유래 코코넛 계면활성제'*\n\n📌 **진단**: 순함은 증명되나, 세균 방어 메커니즘 부재")
        with g3:
            p = get_safe_image_path("images/target_rael/target_rael_detail_03.png")
            if p: st.image(p, caption="[인증 컷] COSMOS NATURAL 인증 마크", use_container_width=True)
            st.caption("🎯 **현재 카피**: *'피부 저자극 테스트 완료'*\n\n📌 **진단**: 99.9% 항균 성적서 결합 시 폭발적 전환 기대")

# -------------------------------------------------------------
# TAB 5: 상세페이지 전개 순서(Storyline) 비교 분석
# -------------------------------------------------------------
with tab5:
    st.subheader("📑 주요 브랜드 상세페이지 메시지 전개 순서(Top-to-Bottom) 비교")
    st.caption("상세페이지의 스크롤 흐름에 따른 5단계 전환 퍼널(Hero 후킹 ──► 문제 공감 ──► 기술 솔루션 ──► 임상 실증 ──► 가치 락인)을 대조합니다.")
    
    story_data = [
        {"브랜드": "★ [기준] 라엘", "1단계 (Hero 후킹)": "COSMOS 천연 인증\n단 8가지 전성분", "2단계 (문제 공감)": "성분 개수에 대한 의문\n복잡한 성분의 자극 우려", "3단계 (기술/포뮬러)": "단 8가지 전성분 공개\n코코넛 식물 유래 세정", "4단계 (임상/안전성)": "피부 저자극 테스트 완료\n(정량 시험수치 미표기)", "5단계 (가치 락인)": "150ml 본품 단품\n청결티슈 묶음 기획"},
        {"브랜드": "바솔 (올영 1등)", "1단계 (Hero 후킹)": "올리브영 W케어 1등\n산뜻 밸런스 선점", "2단계 (문제 공감)": "생리 전후 불쾌취/찝찝함\n손 문지름 마찰 자극", "3단계 (기술/포뮬러)": "락토바실러스 발효용해물\n+ 호주산 티트리 + 시카", "4단계 (임상/안전성)": "칸디다균 99.9% 항균\n녹색소비자연대 안전적합", "5단계 (가치 락인)": "[본품 150ml + 리필 150ml]\n올영 단독 더블 기획"},
        {"브랜드": "이너시아 (KAIST)", "1단계 (Hero 후킹)": "KAIST 여성 과학자 R&D\n펨테크 오리진", "2단계 (문제 공감)": "씻어도 반복되는 재발\n세균 점막 흡착 기전 규명", "3단계 (기술/포뮬러)": "3X 바이옴 (빙하수 100%\n+ 락토 + D-만노스)", "4단계 (임상/안전성)": "99% 악취 소취 성적서\n24종 알러젠 0% 불검출", "5단계 (가치 락인)": "프리미엄 단품\n라보셀 생리대 크로스셀"},
        {"브랜드": "아토팜 (산부인과)", "1단계 (Hero 후킹)": "산부인과 테스트 완료\n'아주 좋음' 엠블럼", "2단계 (문제 공감)": "임산부 분비물/자극 불안\n점막 잔여물 공포 환기", "3단계 (기술/포뮬러)": "독자 특허 AMPamide™\n신바이오틱스 EWG 그린", "4단계 (임상/안전성)": "7초 퀵 린스 잔여물 0%\n유해균 3종 99% 항균", "5단계 (가치 락인)": "올리브영 단독 세일 기획\n1등 민감케어 신뢰 락인"},
        {"브랜드": "클리티", "1단계 (Hero 후킹)": "5대 특허 엠블럼\n8대 임상 완료 선언", "2단계 (문제 공감)": "7가지 Y존 자가진단\n분비물/가려움/냄새 체크", "3단계 (기술/포뮬러)": "특허 5종 배합 (제주해수염\n+ TEFLOSE® 점막보호)", "4단계 (임상/안전성)": "칸디다 99.3%, 소취 99.5%\n즉각보습 93.09% 성적서", "5단계 (가치 락인)": "300/500ml 대용량\n1+1 리필 번들 파격할인"},
        {"브랜드": "질경이", "1단계 (Hero 후킹)": "6,600만 개 판매 신화\n단순 세정 脫피 선언", "2단계 (문제 공감)": "Y존 복합 노화 지적\n(탄력 저하, 칙칙함, 건조)", "3단계 (기술/포뮬러)": "11개국 특허 바이옴-13\n하이드롤라이즈드 콜라겐", "4단계 (임상/안전성)": "3대 안티에이징 임상\n(보습 66%, 탄력 치밀도)", "5단계 (가치 락인)": "N+N 대량 번들\n최대 50% 세트 할인"}
    ]
    
    st.table(pd.DataFrame(story_data))

# -------------------------------------------------------------
# TAB 6: 라엘(Target) 심층 진단 & 레퍼런스 벤치마킹
# -------------------------------------------------------------
with tab6:
    st.subheader("🚀 라엘(Rael) 여성청결제 심층 진단 및 타사 레퍼런스 비교 벤치마킹")
    st.caption("라엘의 현재 키메시지와 결핍을 진단하고, 올리브영 1등 및 D2C 타사 베스트 프랙티스 이미지 컷을 Side-by-Side로 대조하여 즉시 적용 가능한 리뉴얼 전략을 제시합니다.")
    
    # 1. 라엘 현재 키메시지 및 결핍 진단
    st.markdown("### 1️⃣ 라엘(Rael)의 현재 포지션 진단 및 결핍(Gap) 분석")
    
    diag_col1, diag_col2, diag_col3 = st.columns(3)
    
    with diag_col1:
        st.markdown("""
        <div class="ref-box-solution">
            <h4 style="color: #16A34A; margin-top: 0;">🟢 현재 메인 키메시지</h4>
            <ul>
                <li><strong>아마존 1위 글로벌 신뢰도:</strong> 페미닌 케어 전문 브랜드 헤리티지</li>
                <li><strong>COSMOS 천연 인증:</strong> 유기농·순한 성분 보증</li>
                <li><strong>비건 안심 처방:</strong> 100% 식물 유래 계면활성제</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
    with diag_col2:
        st.markdown("""
        <div class="ref-box-solution">
            <h4 style="color: #16A34A; margin-top: 0;">🟢 현재 후킹 포인트</h4>
            <ul>
                <li><strong>단 8가지 전성분 미니멀:</strong> 불필요한 화학 성분 배제</li>
                <li><strong>극민감 피부 저자극:</strong> 매일 쓰는 데일리 밸런싱</li>
                <li><strong>100% 무향 안심:</strong> 인공 향료 알레르기 제로</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
    with diag_col3:
        st.markdown("""
        <div class="ref-box-problem">
            <h4 style="color: #E11D48; margin-top: 0;">🔴 현재의 치명적 결핍 (Gap)</h4>
            <ul>
                <li><strong>직접적 신체 고민 해결력 부재:</strong> 냄새·분비물·가려움 개선 수치 결여</li>
                <li><strong>정량 항균/탈취 실증 성적서 부재:</strong> 칸디다 99.9% 등 수치 없음</li>
                <li><strong>'순하지만 기능은 약한 워시' 오인:</strong> 문제 해결형 고객 대거 이탈</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("---")
    
    # 2. 라엘 상세페이지 핵심 보완 전략 (Before & After)
    st.markdown("### 2️⃣ 라엘 상세페이지 핵심 보완 전략 & 헤드카피 Before & After")
    
    st.markdown("""
    | 보완 영역 | 기존 상세페이지 (Before) | 🌟 리뉴얼 개선 전략 (After) |
    | :--- | :--- | :--- |
    | **도입부 후킹** | *"단 8가지 전성분, COSMOS 천연 인증 순한 청결제"* (단순 스펙 설명) | **"씻어도 반복되는 찝찝함과 냄새, 단 8가지 천연 성분으로 말끔히 비워내다"** (고민 공감 + 해결) |
    | **임상/효능 실증** | 피부 저자극 테스트 완료 텍스트 1줄 (수치 없음) | **칸디다균 99.9% 항균 성적서 & 99% 소취 그래프 & 24시간 장벽 보습 수치 전면 배치** |
    | **글로벌 1위 엠블럼** | 하단 텍스트로 단순 언급 | **상단 3초 Hero 존에 [아마존 1위] + [COSMOS 천연] + [99.9% 항균] 골드 엠블럼 배치** |
    | **기획 오퍼** | 150ml 본품 단품 위주 | **[올리브영 단독] 본품 150ml + 친환경 리필 150ml 더블 기획 (19,900원)** |
    """)
    
    st.markdown("---")
    
    # 3. 타사 상세페이지 예시 이미지 벤치마킹 매칭 (Side-by-Side 2열 비교)
    st.markdown("### 3️⃣ 타사 상세페이지 예시 이미지 벤치마킹 매칭 (Side-by-Side 비교)")
    st.caption("올리브영 1등 및 D2C 타사 베스트 프랙티스 이미지 컷을 직접 대조하여 라엘 상세페이지의 구체적 구현 방안을 도출합니다.")
    
    # 레퍼런스 1: 올리브영 1등 엠블럼 & 리필 기획 (바솔 레퍼런스)
    st.markdown("#### ① [올리브영 1등 엠블럼 & 리필 기획] — 바솔(BASOL) 벤치마킹")
    col_ref0_img, col_ref0_text = st.columns([1.2, 1.8])
    
    with col_ref0_img:
        p_ref0 = get_safe_image_path("images/basol/basol_detail_01.png")
        if p_ref0:
            st.image(p_ref0, caption="[올리브영 1등 레퍼런스: 바솔] 올영 1등 엠블럼 & 리필 세트 기획 컷", use_container_width=True)
            
    with col_ref0_text:
        st.markdown("""
        <div class="ref-box-oliveyoung">
            <h5 style="color: #0284C7; margin-top:0;">💡 올리브영 1위 바솔 소구 기법 분석:</h5>
            <ul>
                <li><strong>첫 3초 1등 엠블럼 선점:</strong> '올리브영 W케어 1등' 뱃지를 최상단에 배치하여 대세감 부여.</li>
                <li><strong>[본품 + 리필 파우치] 더블 세트:</strong> 플라스틱 절감 친환경 메시지와 함께 단품 대비 높은 가성비로 락인.</li>
            </ul>
            <h5 style="color: #0F766E;">🎯 라엘 상세페이지 적용 방안:</h5>
            <ul>
                <li><strong>3대 골드 엠블럼 상단 배치:</strong> <code>[미국 아마존 1위]</code> + <code>[COSMOS NATURAL 인증]</code> + <code>[칸디다균 99.9% 항균]</code>.</li>
                <li><strong>올리브영 단독 기획 출시:</strong> <strong>[본품 150ml + 친환경 리필 파우치 150ml (19,900원)]</strong> 런칭.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 레퍼런스 2: 직관적 고민 후킹 (클리티 레퍼런스)
    st.markdown("#### ② [직관적 고민 후킹] — 문제 제기 & 자가진단 체크리스트")
    col_ref1_img, col_ref1_text = st.columns([1.2, 1.8])
    
    with col_ref1_img:
        p_ref1 = get_safe_image_path("images/cleety/cleety_detail_02.jpg")
        if p_ref1:
            st.image(p_ref1, caption="[타사 레퍼런스: 클리티] 7대 Y존 자가진단 체크리스트 컷", use_container_width=True)
            
    with col_ref1_text:
        st.markdown("""
        <div class="ref-box-solution">
            <h5 style="margin-top:0;">💡 타사 소구 기법 분석:</h5>
            <ul>
                <li><strong>고객 결핍 정밀 타깃팅:</strong> "분비물, 불쾌한 냄새, 가려움, 속당김" 등 일상 속 7대 불편 증상을 체크박스로 제시하여 고객의 즉각적 공감(Aha-moment) 유도.</li>
                <li><strong>문제 원인 규명:</strong> "단순히 물로만 씻거나 알칼리 비누를 쓸 때 무너지는 약산성 환경"을 시각 자료로 고발.</li>
            </ul>
            <h5 style="color: #0F766E;">🎯 라엘 상세페이지 적용 방안:</h5>
            <ul>
                <li><strong>도입부 2섹션에 배치:</strong> <em>"열심히 씻는데도 왜 찝찝함과 냄새는 반복될까요?"</em> 질문형 헤드카피 삽입.</li>
                <li><strong>3대 원인 기전 시각화:</strong> ① 높은 경피 흡수율, ② 알칼리 세정으로 인한 밸런스 붕괴, ③ 유해균 점막 부착을 인포그래픽으로 설명.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 레퍼런스 3: 임상 수치 시각화 (뷰티레시피 레퍼런스)
    st.markdown("#### ③ [임상 수치 시각화] — 99.9% 항균 & 공인 시험 성적서 원본 노출")
    col_ref2_img, col_ref2_text = st.columns([1.2, 1.8])
    
    with col_ref2_img:
        p_ref2 = get_safe_image_path("images/beautyrecipe/brecipe_img_03.jpg")
        if p_ref2:
            st.image(p_ref2, caption="[타사 레퍼런스: 뷰티레시피] 2대 질염균 99.9% 성적서 원본 컷", use_container_width=True)
            
    with col_ref2_text:
        st.markdown("""
        <div class="ref-box-solution">
            <h5 style="margin-top:0;">💡 타사 소구 기법 분석:</h5>
            <ul>
                <li><strong>구체적 원인균 실명 명시:</strong> 단순 '유해균'이 아닌 <strong>'칸디다균 99.99%', '가드넬라균 99.84%'</strong>를 정확한 숫자로 표기.</li>
                <li><strong>공인 시험기관 실명 성적서:</strong> 한국피부과학연구원 및 KOTITI 시험연구원의 직인이 찍힌 성적서 원본을 클로즈업하여 의학적 신뢰 구축.</li>
            </ul>
            <h5 style="color: #0F766E;">🎯 라엘 상세페이지 적용 방안:</h5>
            <ul>
                <li><strong>정량 수치 성적서 3종 실물 컷 삽입:</strong> ① 칸디다균 99.9% 항균 성적서, ② 암모니아/트리메틸아민 99% 소취 성적서, ③ 24시간 장벽 수분 개선 그래프.</li>
                <li><strong>COSMOS 천연 인증과 결합:</strong> <em>"순수한 천연 유기농 성분으로 입증한 놀라운 99.9% 항균력"</em>으로 반전 소구 완성.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 레퍼런스 4: 텍스처 및 7초 퀵린스 (아토팜 레퍼런스)
    st.markdown("#### ④ [텍스처 & 퀵 린스] — 산부인과 테스트 & 7초 잔여물 제로 (아토팜 벤치마킹)")
    col_ref3_img, col_ref3_text = st.columns([1.2, 1.8])
    
    with col_ref3_img:
        p_ref3 = get_safe_image_path("images/atopalm/atopalm_detail_02.png")
        if p_ref3:
            st.image(p_ref3, caption="[올리브영 더마 레퍼런스: 아토팜] 7초 퀵 린스 잔여물 0% 실증 컷", use_container_width=True)
            
    with col_ref3_text:
        st.markdown("""
        <div class="ref-box-solution">
            <h5 style="margin-top:0;">💡 아토팜 소구 기법 분석:</h5>
            <ul>
                <li><strong>7초 퀵 린스(Quick Rinse) 인체적용시험:</strong> 잔여물로 인한 가려움과 2차 자극을 우려하는 고객에게 <em>"7초 만에 잔여물 0% 완벽 세정"</em> 수치 제시.</li>
                <li><strong>산부인과 전문의 테스트 '아주 좋음':</strong> 의학적 공신력으로 극민감성 여성 락인.</li>
            </ul>
            <h5 style="color: #0F766E;">🎯 라엘 상세페이지 적용 방안:</h5>
            <ul>
                <li><strong>투명 비커 5초 용해 실험 컷:</strong> 코코넛 식물 유래 계면활성제가 잔여물 없이 물에 완전히 풀리는 비교 영상/컷 삽입.</li>
                <li><strong>헤드카피:</strong> <em>"손 마찰 제로, 5초 만에 잔여물 없이 씻겨 내려가는 퀵 린스 폼"</em>.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("---")
    
    # 4. 7개 섹션 풀 와이어프레임 스토리보드
    st.markdown("### 4️⃣ 라엘 상세페이지 7개 섹션 리뉴얼 마스터 와이어프레임")
    
    with st.expander("Section 1. 도입부 / 3초 Hero 존 (COSMOS + 99.9% 항균 + 아마존 1위)", expanded=True):
        st.markdown("""
        - **비주얼**: 맑은 물방울과 몽글몽글한 미세 거품 위에 본품 용기 클로즈업
        - **3대 신뢰 엠블럼**: `[COSMOS NATURAL 인증]` + `[칸디다균 99.9% 항균]` + `[미국 아마존 1위 라엘]`
        - **헤드카피**: **"COSMOS 천연 인증에 칸디다균 99.9% 항균을 더하다"**
        """)
        
    with st.expander("Section 2. 문제 제기 & 원인 규명 (Problem & Agitation)"):
        st.markdown("""
        - **헤드카피**: **"열심히 씻는데도 왜 찝찝함과 냄새는 반복될까요?"**
        - **원인 기전 3종**: ① 점막의 높은 화학물질 흡수율, ② 알칼리화로 인한 약산성 파괴, ③ 유해균의 점막 섬모 고착화
        """)
        
    with st.expander("Section 3. 독자 솔루션 & 바이오 메커니즘 (Solution & Technology)"):
        st.markdown("""
        - **헤드카피**: **"단 8가지 전성분, 그리고 유해균 부착을 막는 D-만노스 바이오 테크"**
        - **시각화**: 8개 성분 원형 인포그래픽 + D-만노스 유해균 분리 배출 3D 일러스트
        """)
        
    with st.expander("Section 4. 압도적 임상 데이터 실증 (Clinical Proof)"):
        st.markdown("""
        - **헤드카피**: **"숫자로 증명된 압도적인 항균력과 소취력"**
        - **성적서 3종 실물 노출**: ① 칸디다균 99.9% 항균 성적서, ② 트리메틸아민 99% 소취 성적서, ③ 24시간 장벽 보습 그래프
        """)
        
    with st.expander("Section 5. 텍스처 & 5초 퀵 린스 증명 (Texture & Quick Rinse)"):
        st.markdown("""
        - **헤드카피**: **"손 마찰 제로, 5초 만에 잔여물 없이 씻겨 내려가는 퀵 린스 폼"**
        - **시각화**: 투명 비커 세정 실험 컷 (점막 잔여물 0% 실증) + 초미세 마이크로 버블 클로즈업
        """)
        
    with st.expander("Section 6. 무결점 클린 안전성 인증 (Clean & Safe Certification)"):
        st.markdown("""
        - **인증 마크 4종**: COSMOS NATURAL 인증서 원본 + 피부 저자극 0.00 + 24종 알러젠 0% + 100% 무향
        """)
        
    with st.expander("Section 7. 번들 오퍼 & 이탈 방지 장치 (Offer & Trust Conversion)"):
        st.markdown("""
        - **메인 기획 오퍼**: **[올리브영 단독] 본품 150ml + 친환경 리필 150ml 더블 기획 (19,900원)**
        - **안심 전환 장치**: **7일 무료체험 & 100% 안심 환불 보장제** 배너 + 고민별 실구매자 포토 리뷰 큐레이션
        """)

# 푸터
st.markdown("---")
st.caption("© 2026 Feminine Wash Market Intelligence & Conversion Strategy Dashboard | Built with Streamlit & Plotly")
