import streamlit as st
import pandas as pd
import plotly.graph_objects as go # 세밀한 차트 제어를 위해 변경
import requests
from bs4 import BeautifulSoup

# -----------------------------------------------------------------------------
# 1. 페이지 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="KB 부동산 인사이트 Pro",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 스타일 적용 (깔끔한 카드 디자인)
st.markdown("""
<style>
    .news-card {
        background-color: #f9f9f9;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
        border-left: 5px solid #03C75A;
    }
    .news-title {
        font-weight: bold;
        font-size: 1.1em;
        text-decoration: none;
        color: #333;
    }
    .news-title:hover {
        color: #03C75A;
        text-decoration: underline;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏢 KB 부동산 인사이트 Pro")
st.markdown("매매와 전세 흐름을 한눈에 비교하고, 해당 지역의 최신 뉴스까지 확인하세요.")

# -----------------------------------------------------------------------------
# 2. 함수 정의 (뉴스 크롤링 & 데이터 로드)
# -----------------------------------------------------------------------------

# (1) 네이버 뉴스 제목 가져오기 (캐싱 적용으로 속도 향상)
@st.cache_data(ttl=600) # 10분마다 갱신
def get_real_news(keyword):
    try:
        url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sm=tab_opt&sort=1&photo=0&field=0&pd=0&ds=&de=&docid=&related=0&mynews=0&office_type=0&office_section_code=0&news_office_checked=&nso=so%3Add%2Cp%3Aall&is_sug_officeid=0"
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = requests.get(url, headers=headers)
        soup = BeautifulSoup(req.text, 'html.parser')
        
        news_list = []
        # 네이버 뉴스 구조에 따른 클래스명 (변경될 수 있음)
        items = soup.select('div.news_wrap.api_ani_send')
        
        for item in items[:5]: # 상위 5개만
            title = item.select_one('a.news_tit').get_text()
            link = item.select_one('a.news_tit')['href']
            desc = item.select_one('div.news_dsc').get_text()
            news_list.append({'title': title, 'link': link, 'desc': desc})
            
        return news_list
    except Exception:
        return []

# (2) 데이터 전처리 함수 (매매/전세 공통)
def load_and_clean_data(file, sheet_keyword):
    xls = pd.ExcelFile(file)
    target_sheet = None
    for name in xls.sheet_names:
        if sheet_keyword in name and "종합" in name:
            target_sheet = name
            break
    
    if not target_sheet:
        return None
    
    # 데이터 읽기
    df = pd.read_excel(file, sheet_name=target_sheet, header=10)
    
    # 컬럼명 문자열 변환 및 이상한 컬럼 제거
    df.columns = df.columns.astype(str)
    
    # "50.83..." 같은 숫자형 컬럼 이름 제거 로직
    # 보통 지역명은 한글이므로, 한글이 포함되지 않고 숫자만 있는 컬럼을 날림
    clean_cols = []
    for c in df.columns:
        # 날짜 컬럼은 살림
        if c == df.columns[0]: 
            clean_cols.append(c)
            continue
            
        # 컬럼 이름이 실수(float)처럼 보이면 스킵
        try:
            float(c)
            continue # 숫자면 추가 안 함
        except:
            clean_cols.append(c) # 문자면 추가
            
    df = df[clean_cols]

    # 날짜 정리
    df.rename(columns={df.columns[0]: '날짜'}, inplace=True)
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
    df = df.dropna(subset=['날짜'])
    
    return df

# -----------------------------------------------------------------------------
# 3. 메인 로직
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("📂 설정")
    uploaded_file = st.file_uploader("KB 엑셀 파일 업로드", type=['xlsx', 'xls'])
    
    # 지역 매핑 (주요 지역 바로가기)
    REGIONS = ['전국', '서울', '경기', '인천', '부산', '대구', '대전', '광주', '울산', '세종']

if uploaded_file:
    # 1. 매매 & 전세 데이터 동시 로드
    df_sale = load_and_clean_data(uploaded_file, "매매")
    df_jeonse = load_and_clean_data(uploaded_file, "전세")

    if df_sale is None or df_jeonse is None:
        st.error("엑셀 파일에서 '매매종합' 또는 '전세종합' 시트를 찾을 수 없습니다.")
    else:
        # 2. 지역 선택 (사이드바)
        with st.sidebar:
            st.markdown("---")
            st.subheader("📍 지역 선택")
            main_region = st.selectbox("대분류", REGIONS)
            
            # 선택한 대분류에 포함된 상세 지역 추출
            # (매매 데이터 기준 컬럼리스트 사용)
            all_cols = [c for c in df_sale.columns if c != '날짜']
            
            if main_region == '전국':
                sub_candidates = REGIONS # 전국일 땐 광역시도만
            else:
                # 해당 지역명이 포함된 컬럼만 필터링
                sub_candidates = [c for c in all_cols if main_region in c]
            
            # 중복 제거 및 정렬
            sub_candidates = sorted(list(set(sub_candidates)))
            
            selected_sub = st.selectbox("상세 지역 (하나만 선택)", sub_candidates)

        # 3. 데이터 시각화 및 분석
        if selected_sub:
            col1, col2 = st.columns([2, 1])
            
            # [차트 데이터 준비]
            # 해당 지역의 매매/전세 데이터 추출
            sale_series = df_sale[['날짜', selected_sub]].set_index('날짜')[selected_sub]
            
            # 전세 데이터가 없는 지역이 있을 수 있으므로 체크
            if selected_sub in df_jeonse.columns:
                jeonse_series = df_jeonse[['날짜', selected_sub]].set_index('날짜')[selected_sub]
            else:
                jeonse_series = None

            # ---------------------------
            # 왼쪽: 차트 및 지표
            # ---------------------------
            with col1:
                st.subheader(f"📈 {selected_sub} 시세 흐름")
                
                # 최신 지표 카드 (Metric)
                last_date = sale_series.index[-1].strftime('%Y.%m.%d')
                
                cur_sale = sale_series.iloc[-1]
                prev_sale = sale_series.iloc[-2]
                diff_sale = cur_sale - prev_sale
                
                m_col1, m_col2 = st.columns(2)
                with m_col1:
                    st.metric("매매 지수", f"{cur_sale:.1f}", f"{diff_sale:.2f}")
                
                if jeonse_series is not None:
                    cur_jeonse = jeonse_series.iloc[-1]
                    prev_jeonse = jeonse_series.iloc[-2]
                    diff_jeonse = cur_jeonse - prev_jeonse
                    with m_col2:
                        st.metric("전세 지수", f"{cur_jeonse:.1f}", f"{diff_jeonse:.2f}")

                # Plotly 차트 그리기 (커스텀)
                fig = go.Figure()
                
                # 매매 (빨강)
                fig.add_trace(go.Scatter(
                    x=sale_series.index, 
                    y=sale_series.values,
                    mode='lines',
                    name='매매',
                    line=dict(color='#EF4444', width=2) # 붉은색
                ))
                
                # 전세 (파랑)
                if jeonse_series is not None:
                    fig.add_trace(go.Scatter(
                        x=jeonse_series.index, 
                        y=jeonse_series.values,
                        mode='lines',
                        name='전세',
                        line=dict(color='#3B82F6', width=2) # 파란색
                    ))

                # 차트 레이아웃 설정 (슬라이더 제거, 깔끔하게)
                fig.update_layout(
                    height=500,
                    hovermode="x unified",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    xaxis=dict(
                        rangeslider=dict(visible=False), # ★ 슬라이더 제거 요청 반영
                        showgrid=False
                    ),
                    yaxis=dict(showgrid=True, gridcolor='#eee'),
                    template='plotly_white'
                )
                st.plotly_chart(fig, use_container_width=True)

            # ---------------------------
            # 오른쪽: 실시간 뉴스
            # ---------------------------
            with col2:
                st.subheader("📰 실시간 부동산 뉴스")
                st.write(f"**'{selected_sub} 부동산'** 검색 결과")
                
                # 뉴스 크롤링 호출
                news_items = get_real_news(f"{selected_sub} 부동산")
                
                if news_items:
                    for news in news_items:
                        st.markdown(f"""
                        <div class="news-card">
                            <a href="{news['link']}" target="_blank" class="news-title">{news['title']}</a>
                            <p style="font-size:0.9em; color:#666; margin-top:5px;">{news['desc'][:60]}...</p>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("관련 뉴스를 찾을 수 없습니다.")

            # 하단: 상세 데이터 표 (접기/펼치기)
            with st.expander("📄 상세 데이터 표 보기"):
                # 매매/전세 합치기
                merged_df = pd.DataFrame({'매매': sale_series})
                if jeonse_series is not None:
                    merged_df['전세'] = jeonse_series
                
                st.dataframe(merged_df.sort_index(ascending=False))

else:
    # 파일 업로드 전 안내
    st.info("👈 왼쪽 사이드바에서 KB 시계열 엑셀 파일을 업로드해주세요.")
