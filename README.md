# 📊 네이버 오픈API 기반 브랜드·경쟁사 종합 인텔리전스 대시보드

네이버 개발자 오픈API(검색 트렌드, 쇼핑, 블로그, 카페, 뉴스)와 **네이버 검색광고 API(절대 검색량, SOV, 기기별 쿼리수)**를 통합 연동하여, 자사 및 경쟁사 브랜드의 시장 점유율과 소비자 반응을 실시간으로 추적·시각화하는 Streamlit 대시보드입니다.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://icb10proj2-3bx4bjrbpn7susafuxhcvs.streamlit.app/)

---

## 🚀 서비스 바로가기
* **배포 URL**: [네이버 API 종합 분석 대시보드 바로가기](https://icb10proj2-3bx4bjrbpn7susafuxhcvs.streamlit.app/)

---

## 💡 핵심 기능 및 특장점

### 1. ⚔️ 브랜드 절대 검색량(쿼리수) & 점유율 (SOV) 분석
* **실제 검색 쿼리수 집계**: 네이버 검색광고 API(`keywordstool`)를 연동하여 최근 30일간의 PC/Mobile 실제 검색 횟수 추출
* **브랜드 SOV(Share of Voice)**: 경쟁사 대비 자사 검색 점유율 및 기기별(PC vs 모바일) 유입 비중 비교
* **연관 롱테일 키워드 발굴**: 브랜드 유입 시 함께 검색되는 상위 15개 연관 키워드 및 광고 경쟁도 제공

### 2. 📈 통합 검색어 트렌드 & 통계 검증
* **데이터랩(DataLab) 트렌드 오버레이**: 일자별 상대 검색 비율(0~100) 시각화
* **기술통계 및 이상치(Anomaly) 탐지**: IQR 기반의 검색 급증/급감 구간 탐지, 왜도(Skewness), 첨도(Kurtosis) 통계 리포트 자동 생성

### 3. 🛒 쇼핑 & 커머스 반응 분석
* **가격대 분포 및 점유율**: 키워드별 상위 브랜드 점유율 및 최저가 히스토그램/박스플롯 분석
* **쇼핑인사이트 카테고리 클릭 트렌드**: 주요 소비재 카테고리별 클릭 추이 분석

### 4. 📢 다채널 버즈 및 소셜 여론 모니터링
* **블로그 / 카페 / 뉴스 3채널 실시간 분석**: 일자별 게시글 발행 추이 및 활성 커뮤니티/언론사 점유율 파악

---

## 🛠️ 기술 스택 (Tech Stack)

* **Language**: Python 3.11
* **Framework & UI**: Streamlit
* **Data & Statistics**: Pandas, NumPy, SciPy (IQR 이상치 검증 및 분포 통계)
* **Visualization**: Plotly Express / Graph Objects
* **Authentication & Security**: HMAC-SHA256 암호화 서명, python-dotenv, Streamlit Secrets

---

## 🔑 환경 변수 설정 (Secrets)

로컬 실행 시 `.env` 파일에, Streamlit Cloud 배포 시 `Advanced settings > Secrets`에 아래 환경변수를 등록합니다.

```toml
# 네이버 개발자센터 API (OpenAPI)
NAVER_CLIENT_ID = "your_naver_client_id"
NAVER_CLIENT_SECRET = "your_naver_client_secret"

# 네이버 검색광고 API (SearchAd API)
NAVER_ADS_CUSTOMER_ID = "your_customer_id"
NAVER_ADS_API_KEY = "your_search_ad_api_key"
NAVER_ADS_SECRET_KEY = "your_search_ad_secret_key"
