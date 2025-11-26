import streamlit as st
import pandas as pd
import plotly.graph_objects as go
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

# 스타일 적용
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
# 2. 함수 정의
# -----------------------------------------------------------------------------

@st.cache_data(ttl=600)
def get_real_news(keyword):
    try:
        url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sm=tab_opt&sort=1&photo=0&field=0&pd=0&ds=&de=&docid=&related=0&mynews=0&office_type=0&office_section_code=0&news_office_checked=&nso=so%3Add%2Cp%3Aall&is_sug_officeid=0"
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = requests.get(url, headers=headers)
        soup = BeautifulSoup(req.text, 'html.parser')
        
        news_list = []
        items = soup.select('div.news_wrap.api_ani_send')
        for item in items[:5]:
            title = item.select_one('a.news_tit').get_text()
            link = item.select_one('a.news_tit')['href']
            desc = item.select_one('div.news_dsc').get_text()
            news_list.append({'title': title, 'link': link, 'desc': desc})
        return news_list
    except Exception:
        return []

# ★ [수정] 시트 찾기 로직 유연화
def find_sheet_name(xls, keyword):
    # 1순위: '매매' + '종합' 둘 다 있는거 (예: 매매종합)
    for name in xls.sheet_names:
        if keyword in name and "종합" in name:
            return name
    # 2순위: 그냥 키워드만 있는거 (예: 1.매매, 매매)
    for name in xls.sheet_names:
        if keyword in name:
            return name
    return None

def load_and_clean_data(file, sheet_keyword):
    xls = pd.ExcelFile(file)
    
    # 시트 찾기
    target_sheet = find_sheet_name(xls, sheet_keyword)
    
    if not target_sheet:
        return None, xls.sheet_names # 못 찾으면 현재 시트 목록 리턴
    
    # 데이터 읽기
    df = pd.read_excel(file, sheet_name=target_sheet, header=10)
    df.columns = df.columns.astype(str)
    
    # 이상한 컬럼 제거 (숫자만 있는 컬럼명 제거)
    clean_cols = []
    for c in df.columns:
        if c == df.columns[0]: 
            clean_cols.append(c)
            continue
        try:
            float(c) # 숫자로 변환되면 더미 데이터임
            continue
        except:
            clean_cols.append(c)
            
    df = df[clean_cols]

    # 날짜 정리
    df.rename(columns={df.columns[0]: '날짜'}, inplace=True)
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
    df = df.dropna(subset=['날짜'])
    
    return df, target_sheet

# -----------------------------------------------------------------------------
# 3. 메인 로직
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("📂 설정")
    uploaded_file = st.file_uploader("KB 엑셀 파일 업로드", type=['xlsx', 'xls'])
    REGIONS = ['전국', '서울', '경기', '인천', '부산', '대구', '대전', '광주', '울산', '세종']

if uploaded_file:
    # 1. 데이터 로드 시도
    # xls 객체를 한 번 만들기 위해 여기서 처리하지 않고 함수 내부에서 처리
    # 매매 데이터 로드
    df_sale, sale_sheet_name = load_and_clean_data(uploaded_file, "매매")
    
    # 전세 데이터 로드 (실패해도 괜찮음)
    df_jeonse, jeonse_sheet_name = load_and_clean_data(uploaded_file, "전세")

    # [디버깅용] 만약 매매 데이터가 없으면 사용자에게 시트 목록을 보여줌
    if df_sale is None:
        st.error("🚨 엑셀 파일에서 '매매' 관련 시트를 찾을 수 없습니다.")
        st.write("📂 파일에 포함된 시트 목록:", sale_sheet_name) # 여기엔 시트 목록이 들어있음
        st.warning("올바른 KB 시계열 파일을 업로드했는지 확인해주세요.")
    else:
        # 2. 지역 선택
        with st.sidebar:
            st.markdown("---")
            st.subheader("📍 지역 선택")
            main_region = st.selectbox("대분류", REGIONS)
            
            all_cols = [c for c in df_sale.columns if c != '날짜']
            if main_region == '전국':
                sub_candidates = REGIONS
            else:
                sub_candidates = [c for c in all_cols if main_region in c]
            
            sub_candidates = sorted(list(set(sub_candidates)))
            
            # 목록이 비었을 경우 대비
            if not sub_candidates:
                sub_candidates = [main_region]

            selected_sub = st.selectbox("상세 지역", sub_candidates)

        # 3. 화면 표시
        if selected_sub:
            col1, col2 = st.columns([2, 1])
            
            # 데이터 추출
            sale_series = df_sale[['날짜', selected_sub]].set_index('날짜')[selected_sub]
            
            # 전세 데이터가 있으면 가져오고, 없으면(None) 패스
            jeonse_series = None
            if df_jeonse is not None and selected_sub in df_jeonse.columns:
                jeonse_series = df_jeonse[['날짜', selected_sub]].set_index('날짜')[selected_sub]

            # --- 차트 영역 ---
            with col1:
                st.subheader(f"📈 {selected_sub} 시세 흐름")
                
                # Metric
                cur_sale = sale_series.iloc[-1]
                prev_sale = sale_series.iloc[-2]
                diff_sale = cur_sale - prev_sale
                
                m1, m2 = st.columns(2)
                m1.metric("매매 지수", f"{cur_sale:.1f}", f"{diff_sale:.2f}")
                
                if jeonse_series is not None:
                    cur_jeonse = jeonse_series.iloc[-1]
                    prev_jeonse = jeonse_series.iloc[-2]
                    diff_jeonse = cur_jeonse - prev_jeonse
                    m2.metric("전세 지수", f"{cur_jeonse:.1f}", f"{diff_jeonse:.2f}")

                # Plotly Chart
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=sale_series.index, y=sale_series.values, mode='lines', name='매매', line=dict(color='#EF4444', width=2)))
                
                if jeonse_series is not None:
                    fig.add_trace(go.Scatter(x=jeonse_series.index, y=jeonse_series.values, mode='lines', name='전세', line=dict(color='#3B82F6', width=2)))

                fig.update_layout(
                    height=500,
                    hovermode="x unified",
                    legend=dict(orientation="h", y=1.1),
                    xaxis=dict(rangeslider=dict(visible=False), showgrid=False), # 슬라이더 제거
                    yaxis=dict(showgrid=True, gridcolor='#eee'),
                    template='plotly_white'
                )
                st.plotly_chart(fig, use_container_width=True)

            # --- 뉴스 영역 ---
            with col2:
                st.subheader("📰 실시간 뉴스")
                st.write(f"**{selected_sub} 부동산** 최신 소식")
                
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

            # 상세 데이터
            with st.expander("📄 상세 데이터 표 보기"):
                merged_df = pd.DataFrame({'매매': sale_series})
                if jeonse_series is not None:
                    merged_df['전세'] = jeonse_series
                st.dataframe(merged_df.sort_index(ascending=False))

else:
    st.info("👈 왼쪽 사이드바에서 KB 시계열 엑셀 파일을 업로드해주세요.")
