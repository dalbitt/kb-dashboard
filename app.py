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
    layout="wide"
)

st.markdown("""
<style>
    .news-card {
        background-color: #f8f9fa;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 8px;
        border-left: 4px solid #03C75A;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .news-title {
        font-weight: 700;
        font-size: 14px;
        color: #2d3436;
        text-decoration: none;
        display: block;
        margin-bottom: 4px;
    }
    .news-title:hover {
        color: #03C75A;
        text-decoration: underline;
    }
    .news-desc {
        font-size: 12px;
        color: #636e72;
        line-height: 1.4;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏢 KB 부동산 인사이트 Pro")
st.markdown("Unnamed 오류 수정 및 그래프 자동 확대 적용 버전")

# -----------------------------------------------------------------------------
# 2. 핵심 함수
# -----------------------------------------------------------------------------

@st.cache_data(ttl=600)
def get_real_news(keyword):
    try:
        url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sm=tab_opt&sort=1"
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = requests.get(url, headers=headers, timeout=3)
        soup = BeautifulSoup(req.text, 'html.parser')
        
        news_list = []
        items = soup.select('div.news_wrap.api_ani_send')
        for item in items[:5]: 
            title = item.select_one('a.news_tit').get_text()
            link = item.select_one('a.news_tit')['href']
            desc_el = item.select_one('div.news_dsc')
            desc = desc_el.get_text() if desc_el else ""
            news_list.append({'title': title, 'link': link, 'desc': desc})
        return news_list
    except:
        return []

def find_sheet_name(xls, keyword):
    for name in xls.sheet_names:
        if keyword in name and "종합" in name:
            return name
    for name in xls.sheet_names:
        if keyword in name:
            return name
    return None

def load_data_safe(file, sheet_keyword):
    xls = pd.ExcelFile(file)
    target_sheet = find_sheet_name(xls, sheet_keyword)
    
    if not target_sheet:
        return None, None
    
    df = pd.read_excel(file, sheet_name=target_sheet, header=10)
    
    # [핵심 수정 1] Unnamed 컬럼 및 빈 컬럼 제거
    # 컬럼을 문자열로 변환 후, 'Unnamed'가 포함된 컬럼은 삭제
    df.columns = df.columns.astype(str).str.strip().str.replace('\n', '')
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')] # Unnamed로 시작하는 컬럼 삭제
    
    date_col = df.columns[0]
    df.rename(columns={date_col: '날짜'}, inplace=True)
    
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
    df = df.dropna(subset=['날짜'])
    
    valid_cols = ['날짜']
    for col in df.columns:
        if col == '날짜': continue
        try:
            float(col) # 숫자로만 된 컬럼명(더미) 제거
        except ValueError:
            valid_cols.append(col)
            
    return df[valid_cols], target_sheet

# -----------------------------------------------------------------------------
# 3. 메인 로직
# -----------------------------------------------------------------------------

with st.sidebar:
    st.header("📂 1. 데이터 업로드")
    uploaded_file = st.file_uploader("KB 엑셀 파일(.xlsx)을 올려주세요", type=['xlsx', 'xls'])

if uploaded_file:
    df_sale, sale_sheet = load_data_safe(uploaded_file, "매매")
    df_jeonse, jeonse_sheet = load_data_safe(uploaded_file, "전세")
    
    if df_sale is None:
        st.error("🚨 '매매' 시트를 찾을 수 없습니다. KB 파일을 확인해주세요.")
    else:
        with st.sidebar:
            st.header("📍 2. 지역 선택")
            
            real_columns = [c for c in df_sale.columns if c != '날짜']
            
            # [핵심 수정 3] 지역 그룹 세분화 (광역시 분리)
            region_groups = {
                '전국/수도권': ['전국', '서울', '경기', '인천', '수도권'],
                '5대 광역시': ['부산', '대구', '광주', '대전', '울산'],
                '지방 도단위': ['강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주', '세종'],
                '서울 (구별)': ['종로', '중구', '용산', '성동', '광진', '동대문', '중랑', '성북', '강북', '도봉', '노원', '은평', '서대문', '마포', '양천', '강서', '구로', '금천', '영등포', '동작', '관악', '서초', '강남', '송파', '강동'],
                '경기 (시/구별)': ['수원', '성남', '고양', '용인', '부천', '안산', '남양주', '안양', '화성', '평택', '의정부', '시흥', '파주', '광명', '김포', '군포', '광주', '이천', '양주', '오산', '구리', '안성', '포천', '의왕', '하남', '과천', '분당', '일산', '평촌', '산본'],
                '부산 (구별)': ['해운대', '수영', '동래', '연제', '부산진', '금정', '남구', '북구', '강서', '사하', '사상', '기장', '영도', '중구', '서구', '동구'],
                '대구 (구별)': ['수성', '달서', '중구', '동구', '서구', '남구', '북구', '달성'],
                '인천 (구별)': ['연수', '남동', '부평', '계양', '서구', '미추홀', '중구', '동구'],
                '광주/대전/울산 (구별)': ['광산', '유성', '대덕', '울주']
            }
            
            category = st.selectbox("지역 그룹 선택", list(region_groups.keys()) + ["전체 목록(가나다순)"])
            
            if category == "전체 목록(가나다순)":
                available_sub_regions = real_columns
            else:
                target_keywords = region_groups[category]
                available_sub_regions = []
                for col in real_columns:
                    if col in target_keywords: # 정확히 일치
                        available_sub_regions.append(col)
                        continue
                    for key in target_keywords: # 포함 여부
                        if key == col: 
                            available_sub_regions.append(col)
                            break
                available_sub_regions = sorted(list(set(available_sub_regions)))
                
                if not available_sub_regions:
                    available_sub_regions = real_columns

            selected_region = st.selectbox("상세 지역", available_sub_regions)

        if selected_region:
            sale_data = df_sale.set_index('날짜')[selected_region]
            jeonse_data = None
            if df_jeonse is not None and selected_region in df_jeonse.columns:
                jeonse_data = df_jeonse.set_index('날짜')[selected_region]

            col1, col2 = st.columns([2, 1])

            with col1:
                st.subheader(f"📈 {selected_region} 시세 흐름")
                
                try:
                    curr = sale_data.iloc[-1]
                    prev = sale_data.iloc[-2]
                    diff = curr - prev
                    
                    m1, m2 = st.columns(2)
                    m1.metric("매매 지수", f"{curr:.1f}", f"{diff:.2f}")
                    if jeonse_data is not None:
                        j_curr = jeonse_data.iloc[-1]
                        j_prev = jeonse_data.iloc[-2]
                        j_diff = j_curr - j_prev
                        m2.metric("전세 지수", f"{j_curr:.1f}", f"{j_diff:.2f}")
                except:
                    pass

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=sale_data.index, y=sale_data.values,
                    mode='lines', name='매매',
                    line=dict(color='#EF4444', width=2.5)
                ))
                if jeonse_data is not None:
                    fig.add_trace(go.Scatter(
                        x=jeonse_data.index, y=jeonse_data.values,
                        mode='lines', name='전세',
                        line=dict(color='#3B82F6', width=2.5)
                    ))
                
                # [핵심 수정 2] 그래프 스케일 자동 조정 (autorange)
                fig.update_layout(
                    height=450,
                    margin=dict(l=20, r=20, t=30, b=20),
                    hovermode="x unified",
                    legend=dict(orientation="h", y=1.1),
                    xaxis=dict(showgrid=False),
                    # Y축을 데이터 범위에 맞게 자동 확대 (0부터 시작하지 않음)
                    yaxis=dict(showgrid=True, gridcolor='#f1f3f5', autorange=True, fixedrange=False), 
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.subheader("📰 관련 뉴스")
                st.caption(f"'{selected_region} 부동산' 검색 결과")
                
                news_items = get_real_news(f"{selected_region} 부동산")
                if news_items:
                    for news in news_items:
                        st.markdown(f"""
                        <div class="news-card">
                            <a href="{news['link']}" target="_blank" class="news-title">{news['title']}</a>
                            <div class="news-desc">{news['desc'][:50]}...</div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("뉴스가 없습니다.")

            with st.expander("📊 상세 데이터 표"):
                merged = pd.DataFrame({'매매': sale_data})
                if jeonse_data is not None:
                    merged['전세'] = jeonse_data
                st.dataframe(merged.sort_index(ascending=False), use_container_width=True)

else:
    st.info("👈 왼쪽 사이드바에서 KB 시계열 엑셀 파일을 업로드해주세요.")
