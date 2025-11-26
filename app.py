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

# 스타일: 뉴스 카드 및 레이아웃
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
st.markdown("데이터 오류 없는 **안전한 모드**로 동작합니다.")

# -----------------------------------------------------------------------------
# 2. 핵심 함수 (데이터 로드 & 뉴스)
# -----------------------------------------------------------------------------

@st.cache_data(ttl=600)
def get_real_news(keyword):
    """네이버 뉴스 제목 크롤링"""
    try:
        # 정확도순 정렬
        url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sm=tab_opt&sort=1"
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = requests.get(url, headers=headers, timeout=3)
        soup = BeautifulSoup(req.text, 'html.parser')
        
        news_list = []
        items = soup.select('div.news_wrap.api_ani_send')
        for item in items[:5]: # 최대 5개
            title = item.select_one('a.news_tit').get_text()
            link = item.select_one('a.news_tit')['href']
            desc_el = item.select_one('div.news_dsc')
            desc = desc_el.get_text() if desc_el else ""
            news_list.append({'title': title, 'link': link, 'desc': desc})
        return news_list
    except:
        return []

def find_sheet_name(xls, keyword):
    """유연한 시트 이름 찾기"""
    # 1. '매매' + '종합' 포함
    for name in xls.sheet_names:
        if keyword in name and "종합" in name:
            return name
    # 2. '매매'만 포함
    for name in xls.sheet_names:
        if keyword in name:
            return name
    return None

def load_data_safe(file, sheet_keyword):
    """에러 없이 데이터를 읽어오는 함수"""
    xls = pd.ExcelFile(file)
    target_sheet = find_sheet_name(xls, sheet_keyword)
    
    if not target_sheet:
        return None, None
    
    # 헤더 10행 기준 읽기
    df = pd.read_excel(file, sheet_name=target_sheet, header=10)
    
    # [핵심] 컬럼명 정리 (공백 제거, 문자열 변환)
    df.columns = df.columns.astype(str).str.strip().str.replace('\n', '')
    
    # 날짜 컬럼 찾기 (보통 첫번째 컬럼)
    date_col = df.columns[0]
    df.rename(columns={date_col: '날짜'}, inplace=True)
    
    # 유효한 데이터만 남기기 (날짜가 있는 행만)
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
    df = df.dropna(subset=['날짜'])
    
    # 이상한 더미 컬럼(숫자로 된 컬럼 등) 제거
    valid_cols = ['날짜']
    for col in df.columns:
        if col == '날짜': continue
        # 컬럼명이 숫자로만 되어있으면 제외 (엑셀 서식 찌꺼기)
        try:
            float(col)
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
    # 데이터 로드
    df_sale, sale_sheet = load_data_safe(uploaded_file, "매매")
    df_jeonse, jeonse_sheet = load_data_safe(uploaded_file, "전세")
    
    if df_sale is None:
        st.error("🚨 엑셀 파일에서 '매매' 시트를 찾을 수 없습니다.")
        st.info("올바른 KB 주간 시계열 파일을 업로드해주세요.")
    else:
        # --- 지역 선택 로직 (KeyError 방지) ---
        with st.sidebar:
            st.header("📍 2. 지역 선택")
            
            # 엑셀에 있는 진짜 컬럼 리스트 (날짜 제외)
            real_columns = [c for c in df_sale.columns if c != '날짜']
            
            # 사용 편의를 위해 그룹핑 (가상 그룹)
            # 엑셀 컬럼명에 해당 단어가 포함되어 있으면 그 그룹으로 묶음
            region_groups = {
                '전국/광역시도': ['전국', '서울', '경기', '인천', '부산', '대구', '대전', '광주', '울산', '세종', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주'],
                '서울 (구 단위)': ['종로', '중구', '용산', '성동', '광진', '동대문', '중랑', '성북', '강북', '도봉', '노원', '은평', '서대문', '마포', '양천', '강서', '구로', '금천', '영등포', '동작', '관악', '서초', '강남', '송파', '강동'],
                '경기 (시/구 단위)': ['수원', '성남', '고양', '용인', '부천', '안산', '남양주', '안양', '화성', '평택', '의정부', '시흥', '파주', '광명', '김포', '군포', '광주', '이천', '양주', '오산', '구리', '안성', '포천', '의왕', '하남', '과천', '분당', '일산', '평촌', '산본', '중동'],
                '부산/대구/인천 (구 단위)': ['해운대', '수영', '동래', '연제', '수성', '달서', '연수', '남동', '부평']
            }
            
            # 대분류 선택
            category = st.selectbox("어떤 지역을 보시겠습니까?", list(region_groups.keys()) + ["전체 목록에서 찾기"])
            
            # 상세 지역 리스트 만들기 (교집합)
            if category == "전체 목록에서 찾기":
                # 모든 컬럼 다 보여줌
                available_sub_regions = real_columns
            else:
                # 그룹에 정의된 이름이 실제 컬럼명에 '포함'되어 있거나 '일치'하는지 확인
                target_keywords = region_groups[category]
                available_sub_regions = []
                for col in real_columns:
                    # 정확히 일치하거나 (예: 서울)
                    if col in target_keywords:
                        available_sub_regions.append(col)
                        continue
                    # 혹은 포함되거나 (예: 서울 강북구 -> 강북이 포함됨)
                    for key in target_keywords:
                        if key == col: # 완전 일치 우선
                            available_sub_regions.append(col)
                            break
                
                # 중복 제거 및 정렬
                available_sub_regions = sorted(list(set(available_sub_regions)))
                
                # 만약 그룹핑 결과가 없으면(엑셀 양식이 달라서), 그냥 전체 다 보여줌 (안전장치)
                if not available_sub_regions:
                    available_sub_regions = real_columns

            # 최종 선택 (여기 있는 건 무조건 df 컬럼에 있음)
            selected_region = st.selectbox("상세 지역 선택", available_sub_regions)

        # --- 메인 화면 ---
        if selected_region:
            # 데이터 추출 (에러 날 수 없음)
            sale_data = df_sale.set_index('날짜')[selected_region]
            
            # 전세 데이터 확인
            jeonse_data = None
            if df_jeonse is not None and selected_region in df_jeonse.columns:
                jeonse_data = df_jeonse.set_index('날짜')[selected_region]

            col1, col2 = st.columns([2, 1])

            # [왼쪽] 차트 & 지표
            with col1:
                st.subheader(f"📈 {selected_region} 시세 흐름")
                
                # 지표 (Metric)
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
                    st.warning("데이터가 부족하여 증감률을 계산할 수 없습니다.")

                # Plotly 차트
                fig = go.Figure()
                # 매매
                fig.add_trace(go.Scatter(
                    x=sale_data.index, y=sale_data.values,
                    mode='lines', name='매매',
                    line=dict(color='#EF4444', width=2.5)
                ))
                # 전세
                if jeonse_data is not None:
                    fig.add_trace(go.Scatter(
                        x=jeonse_data.index, y=jeonse_data.values,
                        mode='lines', name='전세',
                        line=dict(color='#3B82F6', width=2.5)
                    ))
                
                fig.update_layout(
                    height=450,
                    margin=dict(l=20, r=20, t=30, b=20),
                    hovermode="x unified",
                    legend=dict(orientation="h", y=1.1),
                    xaxis=dict(showgrid=False), # 슬라이더 제거 완료
                    yaxis=dict(showgrid=True, gridcolor='#f1f3f5'),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig, use_container_width=True)

            # [오른쪽] 뉴스
            with col2:
                st.subheader("📰 관련 뉴스")
                st.caption(f"'{selected_region} 부동산' 키워드 검색 결과")
                
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
                    st.info("관련된 최신 뉴스가 없습니다.")

            # [하단] 상세 데이터
            with st.expander("📊 상세 데이터 표 (클릭해서 펼치기)"):
                merged = pd.DataFrame({'매매': sale_data})
                if jeonse_data is not None:
                    merged['전세'] = jeonse_data
                st.dataframe(merged.sort_index(ascending=False), use_container_width=True)

else:
    st.info("👈 왼쪽 사이드바에서 KB 시계열 엑셀 파일을 업로드해주세요.")
