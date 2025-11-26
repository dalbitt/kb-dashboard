import streamlit as st
import pandas as pd
import plotly.express as px

# 페이지 기본 설정
st.set_page_config(page_title="KB 부동산 시세 분석기", layout="wide")

st.title("🏠 KB 부동산 주간/월간 시세 차트")
st.markdown("KB부동산 엑셀 파일을 업로드하면 즉시 차트를 그려줍니다.")

# 1. 사이드바: 파일 업로드 기능
st.sidebar.header("📂 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("KB 시계열 엑셀 파일(.xlsx)을 올려주세요", type=['xlsx'])

st.sidebar.markdown("---")
st.sidebar.info("💡 **사용법**\n1. [KB부동산](https://kbland.kr/) 접속\n2. 주간/월간 시계열 엑셀 다운로드\n3. 여기에 파일 드래그 & 드롭")

# 2. 데이터 처리 및 시각화
if uploaded_file:
    try:
        # 엑셀 읽기 (KB 엑셀 구조에 맞춰 헤더 자동 탐지 시도)
        # 보통 10~11행 쯤에 지역명이 있습니다.
        df = pd.read_excel(uploaded_file, sheet_name='매매종합', header=10)
        
        # 데이터 전처리
        # 첫 번째 컬럼(날짜) 이름이 없는 경우가 많아 '날짜'로 강제 지정
        df.rename(columns={df.columns[0]: '날짜'}, inplace=True)
        
        # 날짜 형식이 아닌 행(빈 칸, 설명 등) 제거
        df = df[pd.to_datetime(df['날짜'], errors='coerce').notna()]
        df['날짜'] = pd.to_datetime(df['날짜'])
        
        # 3. 사용자 입력 (지역 선택)
        # 컬럼 중에서 지역 이름만 추출 (날짜 컬럼 제외)
        region_list = [col for col in df.columns if col != '날짜']
        
        st.write("### 📈 지역별 매매지수 비교")
        selected_regions = st.multiselect(
            "확인하고 싶은 지역을 선택하세요 (여러 개 선택 가능)", 
            region_list, 
            default=['서울', '전국'] if '서울' in region_list else [region_list[0]]
        )
        
        if selected_regions:
            # 선택한 지역 데이터만 뽑아서 차트용으로 변환 (Melting)
            filtered_df = df[['날짜'] + selected_regions]
            melted_df = filtered_df.melt(id_vars=['날짜'], var_name='지역', value_name='매매지수')
            
            # 차트 그리기 (Plotly)
            fig = px.line(melted_df, x='날짜', y='매매지수', color='지역', 
                          title='주간 아파트 매매가격지수 추이',
                          hover_data={'날짜': '|%Y-%m-%d'})
            
            # 차트 보여주기
            st.plotly_chart(fig, use_container_width=True)
            
            # 상세 데이터 표
            with st.expander("📄 상세 데이터 보기"):
                st.dataframe(filtered_df.sort_values(by='날짜', ascending=False))
        else:
            st.warning("지역을 하나 이상 선택해주세요.")
            
    except Exception as e:
        st.error("엑셀 파일을 읽는 중 오류가 발생했습니다.")
        st.error(f"에러 내용: {e}")
        st.warning("올바른 KB 시계열 파일인지 확인해주세요.")

else:
    # 파일이 없을 때 보여줄 안내 문구
    st.info("👈 왼쪽 사이드바에서 엑셀 파일을 업로드하면 분석이 시작됩니다.")
