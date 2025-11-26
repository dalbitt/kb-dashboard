import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. 페이지 설정 (반드시 맨 윗줄에 있어야 함)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="KB 부동산 인사이트 Pro",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. 스타일 및 헤더 (앱 느낌 나게 꾸미기)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    .main-header {font-size: 2.5rem; font-weight: 700; color: #1E3A8A;}
    .sub-header {font-size: 1.2rem; color: #64748B;}
    .metric-card {background-color: #F8FAFC; padding: 20px; border-radius: 10px; border: 1px solid #E2E8F0;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🏢 KB 부동산 인사이트 Pro</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">빅데이터 기반 주간/월간 시세 흐름 분석 대시보드</div>', unsafe_allow_html=True)
st.markdown("---")

# -----------------------------------------------------------------------------
# 3. 사이드바: 데이터 업로드 및 설정
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("📂 데이터 센터")
    uploaded_file = st.file_uploader("KB 시계열 엑셀(.xlsx) 업로드", type=['xlsx', 'xls'])
    
    st.info("""
    **💡 사용 가이드**
    1. KB부동산(kbland.kr)에서 '주간 아파트 시세' 다운로드
    2. 파일 업로드
    3. 원하는 지역과 기간 선택
    """)
    st.markdown("---")

# 주요 지역 정의 (매핑을 위해)
REGIONS = {
    '서울': ['서울', '강북', '강남', '도봉', '노원', '성북', '은평', '서대문', '마포', '양천', '강서', '구로', '금천', '영등포', '동작', '관악', '서초', '송파', '강동', '종로', '중구', '용산', '성동', '광진', '동대문', '중랑'],
    '경기': ['경기', '수원', '성남', '고양', '용인', '부천', '안산', '남양주', '안양', '화성', '평택', '의정부', '시흥', '파주', '광명', '김포', '군포', '광주', '이천', '양주', '오산', '구리', '안성', '포천', '의왕', '하남', '과천', '여주', '동두천'],
    '인천': ['인천', '중구', '동구', '미추홀', '연수', '남동', '부평', '계양', '서구'],
    '부산': ['부산', '중구', '서구', '동구', '영도', '부산진', '동래', '남구', '북구', '해운대', '사하', '금정', '강서', '연제', '수영', '사상', '기장'],
    '대구': ['대구', '중구', '동구', '서구', '남구', '북구', '수성', '달서', '달성'],
    '대전': ['대전', '동구', '중구', '서구', '유성', '대덕'],
    '광주': ['광주', '동구', '서구', '남구', '북구', '광산'],
    '울산': ['울산', '중구', '남구', '동구', '북구', '울주'],
    '세종': ['세종'],
    '전국': ['전국']
}

# -----------------------------------------------------------------------------
# 4. 메인 로직
# -----------------------------------------------------------------------------
if uploaded_file:
    try:
        # (1) 엑셀 로드
        xls = pd.ExcelFile(uploaded_file)
        sheet_names = xls.sheet_names
        
        # '매매' 시트 자동 감지
        default_idx = 0
        for i, name in enumerate(sheet_names):
            if "매매" in name and "종합" in name:
                default_idx = i
                break
        
        with st.sidebar:
            st.header("⚙️ 분석 옵션")
            selected_sheet = st.selectbox("분석 시트 선택", sheet_names, index=default_idx)
        
        # 데이터 읽기 (헤더 10행 기준)
        df = pd.read_excel(uploaded_file, sheet_name=selected_sheet, header=10)
        
        # ★ [오류 수정 핵심] 모든 컬럼명을 문자열(String)로 강제 변환
        df.columns = df.columns.astype(str)
        
        # 날짜 컬럼 처리
        df.rename(columns={df.columns[0]: '날짜'}, inplace=True)
        df['날짜_변환'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.dropna(subset=['날짜_변환'])
        df['날짜'] = df['날짜_변환']
        df = df.drop(columns=['날짜_변환'])
        
        # (2) 지역 선택 로직
        all_cols = [c for c in df.columns if c != '날짜']
        
        with st.sidebar:
            main_region = st.selectbox("📍 대지역 선택", list(REGIONS.keys()))
            
            # 선택한 대지역에 해당하는 컬럼만 필터링 (스마트 검색)
            # 1. REGIONS 사전에 있는 키워드가 포함된 컬럼 찾기
            # 2. 혹은 KB 엑셀 특성상 '서울 강남구' 처럼 되어있을 수 있으므로 대지역명이 포함된 것도 찾기
            
            keywords = REGIONS[main_region]
            sub_regions = []
            
            if main_region == '전국':
                # 전국 선택 시 주요 광역시만 보여주기
                sub_regions = [c for c in all_cols if c in REGIONS.keys() or c == '전국']
            else:
                for col in all_cols:
                    # 컬럼명에 키워드가 포함되어 있는지 확인
                    for key in keywords:
                        if key in col:
                            sub_regions.append(col)
                            break
            
            # 중복 제거 및 정렬
            sub_regions = sorted(list(set(sub_regions)))
            
            # 만약 못 찾았으면 전체 보여주기 (안전장치)
            if not sub_regions:
                sub_regions = all_cols
            
            # 상세 지역 다중 선택
            selected_subs = st.multiselect(
                "상세 지역 선택 (복수 선택 가능)", 
                sub_regions, 
                default=sub_regions[:1] if sub_regions else None
            )

        # (3) 차트 및 대시보드 표출
        if selected_subs:
            # 기간 필터링
            filtered_df = df[['날짜'] + selected_subs].sort_values('날짜')
            
            # 최신 데이터 요약 카드 (Metrics)
            last_date = filtered_df['날짜'].iloc[-1].strftime('%Y.%m.%d')
            st.subheader(f"📊 {main_region} 시장 동향 ({last_date} 기준)")
            
            # 컬럼 3개로 나누어 최신 지수 보여주기
            cols = st.columns(min(len(selected_subs), 4))
            for idx, region in enumerate(selected_subs[:4]): # 최대 4개까지만 카드 보여줌
                latest_val = filtered_df[region].iloc[-1]
                prev_val = filtered_df[region].iloc[-2]
                diff = latest_val - prev_val
                
                with cols[idx]:
                    st.metric(
                        label=region, 
                        value=f"{latest_val:.1f}", 
                        delta=f"{diff:.2f}",
                        delta_color="normal" # 상승 빨강, 하락 파랑 자동
                    )

            # 차트 그리기 (기간 슬라이더 포함)
            st.markdown("### 📈 시계열 변동 차트")
            melted_df = filtered_df.melt(id_vars=['날짜'], var_name='지역', value_name='지수')
            
            fig = px.line(melted_df, x='날짜', y='지수', color='지역', markers=True)
            fig.update_layout(
                xaxis=dict(
                    rangeslider=dict(visible=True), # 하단 슬라이더
                    type="date"
                ),
                height=500,
                hovermode="x unified",
                template="plotly_white" # 깔끔한 흰색 배경
            )
            st.plotly_chart(fig, use_container_width=True)

            # (4) 뉴스 및 추가 정보
            st.markdown("### 📰 관련 뉴스 및 분석")
            
            # 탭으로 구분
            tab1, tab2 = st.tabs(["네이버 뉴스", "상세 데이터"])
            
            with tab1:
                target = selected_subs[0] if selected_subs else main_region
                query = f"{main_region} {target} 부동산 전망"
                url = f"https://search.naver.com/search.naver?where=news&query={query}"
                
                st.markdown(f"""
                <div style="background-color:#F0FDF4; padding:15px; border-radius:10px; border:1px solid #BBF7D0;">
                    <strong>🔍 '{target}' 관련 최신 뉴스를 확인해보세요.</strong><br><br>
                    <a href="{url}" target="_blank" style="text-decoration:none;">
                        <button style="background-color:#03C75A; color:white; border:none; padding:10px 20px; border-radius:5px; font-weight:bold; cursor:pointer;">
                            N 네이버 뉴스 검색 바로가기
                        </button>
                    </a>
                </div>
                """, unsafe_allow_html=True)
            
            with tab2:
                st.dataframe(filtered_df.sort_values('날짜', ascending=False), use_container_width=True)

        else:
            st.warning("👈 왼쪽 사이드바에서 상세 지역을 하나 이상 선택해주세요.")

    except Exception as e:
        st.error("🚨 데이터를 처리하는 중 문제가 발생했습니다.")
        st.code(f"에러 내용: {e}")
        st.info("💡 팁: 다운로드 받은 KB 엑셀 파일을 수정하지 말고 그대로 올려주세요.")

else:
    # 파일 업로드 전 초기 화면 (예쁘게)
    st.markdown("""
    <div style="text-align:center; padding: 50px;">
        <h2>👋 환영합니다!</h2>
        <p style="color:gray;">왼쪽 사이드바에서 <strong>KB 부동산 엑셀 파일</strong>을 업로드하면<br>
        전문가 수준의 차트와 분석을 바로 보실 수 있습니다.</p>
    </div>
    """, unsafe_allow_html=True)
