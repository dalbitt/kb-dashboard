import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="KB 부동산 시세 대시보드", layout="wide")

st.title("🏠 KB 부동산 시세 분석기 (Pro 버전)")
st.markdown("KB 시계열 엑셀 파일을 업로드하면 **지역별 상세 분석**과 **뉴스**를 제공합니다.")

# --- 사이드바: 파일 및 옵션 ---
st.sidebar.header("📂 데이터 설정")
uploaded_file = st.sidebar.file_uploader("KB 엑셀 파일을 올려주세요", type=['xlsx', 'xls'])

# 주요 광역시/도 리스트 (KB 데이터 기준)
MAIN_REGIONS = [
    '서울', '경기', '인천', '부산', '대구', '광주', '대전', '울산', 
    '세종', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주'
]

if uploaded_file:
    try:
        # 1. 엑셀 로드 및 시트 선택
        xls = pd.ExcelFile(uploaded_file)
        sheet_names = xls.sheet_names
        
        # '매매'가 들어간 시트 자동 찾기
        default_index = 0
        for i, name in enumerate(sheet_names):
            if "매매" in name and "종합" in name:
                default_index = i
                break
        
        selected_sheet = st.sidebar.selectbox("📊 분석할 데이터(시트)", sheet_names, index=default_index)
        
        # 데이터 읽기 (헤더 10행 가정)
        df = pd.read_excel(uploaded_file, sheet_name=selected_sheet, header=10)
        
        # 2. 데이터 전처리
        # 날짜 컬럼 정리
        df.rename(columns={df.columns[0]: '날짜'}, inplace=True)
        df['날짜_변환'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.dropna(subset=['날짜_변환'])
        df['날짜'] = df['날짜_변환']
        df = df.drop(columns=['날짜_변환'])
        
        # 3. [기능 추가] 계층형 지역 선택
        st.sidebar.header("📍 지역 선택")
        
        # (1) 대분류 선택 (서울, 경기...)
        selected_main_region = st.sidebar.selectbox("대분류 선택", ["전국"] + MAIN_REGIONS)
        
        # (2) 상세 지역 필터링 로직
        all_columns = [col for col in df.columns if col != '날짜']
        
        if selected_main_region == "전국":
            # 전국일 때는 주요 광역시만 보여주기
            sub_regions = [r for r in all_columns if r in MAIN_REGIONS or r == '전국']
        else:
            # 선택한 지역(예: 서울)이 포함된 컬럼만 찾기 (예: 서울 강남구, 서울 도봉구...)
            # KB 데이터는 보통 "서울 강남구" 처럼 되어 있거나, 그냥 "강남구"로 되어있는데
            # 엑셀 구조상 상위 컬럼 병합이 되어있어 실제 컬럼명은 확인이 필요함.
            # 여기서는 단순하게 이름에 지역명이 포함된 것을 찾습니다.
            sub_regions = [col for col in all_columns if selected_main_region in col]
            
            # 만약 못 찾았으면(컬럼명이 그냥 '강남구' 식이라서), 전체 리스트를 보여줌
            if not sub_regions:
                sub_regions = all_columns

        # (3) 상세 지역 다중 선택
        selected_sub_regions = st.sidebar.multiselect(
            f"{selected_main_region} 상세 지역 선택", 
            sub_regions,
            default=sub_regions[:1] if sub_regions else None
        )

        # 4. 차트 그리기
        if selected_sub_regions:
            # 데이터 필터링
            filtered_df = df[['날짜'] + selected_sub_regions]
            
            # [기능 추가] 기간 선택 (슬라이더 대체 기능 - Date Input)
            st.sidebar.markdown("---")
            min_date = filtered_df['날짜'].min().date()
            max_date = filtered_df['날짜'].max().date()
            
            start_date, end_date = st.sidebar.date_input(
                "📅 조회 기간 선택",
                [min_date, max_date],
                min_value=min_date,
                max_value=max_date
            )
            
            # 날짜로 데이터 자르기
            mask = (filtered_df['날짜'].dt.date >= start_date) & (filtered_df['날짜'].dt.date <= end_date)
            filtered_df = filtered_df.loc[mask]

            # 시각화용 데이터 변환
            melted_df = filtered_df.melt(id_vars=['날짜'], var_name='지역', value_name='지수')

            # 메인 화면 구성
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.subheader(f"📈 {selected_main_region} 부동산 지수 추이")
                # [기능 추가] 슬라이더가 달린 차트
                fig = px.line(melted_df, x='날짜', y='지수', color='지역', markers=True)
                
                # 줌 & 슬라이더 설정
                fig.update_layout(
                    xaxis=dict(
                        rangeslider=dict(visible=True), # 하단 슬라이더 추가
                        type="date"
                    ),
                    hovermode="x unified" # 마우스 올리면 싹 다 보여주기
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.subheader("📰 지역 뉴스")
                target_region = selected_sub_regions[0] if selected_sub_regions else selected_main_region
                st.info(f"'{target_region}' 부동산 소식")
                
                # [기능 추가] 네이버 뉴스 바로가기 링크 생성
                search_query = f"{target_region} 부동산 전망 호재"
                naver_url = f"https://search.naver.com/search.naver?where=news&query={search_query}"
                
                st.markdown(f"""
                    <a href="{naver_url}" target="_blank">
                        <button style="
                            width: 100%; 
                            background-color: #03C75A; 
                            color: white; 
                            padding: 10px; 
                            border: none; 
                            border-radius: 5px; 
                            cursor: pointer;
                            font-weight: bold;">
                            N 네이버 뉴스 확인하기
                        </button>
                    </a>
                """, unsafe_allow_html=True)
                
                st.write("---")
                st.write("**최신 데이터 기준:**")
                last_row = filtered_df.iloc[-1]
                st.write(f"📅 {last_row['날짜'].strftime('%Y-%m-%d')}")
                for region in selected_sub_regions:
                    st.write(f"- {region}: **{last_row[region]}**")

            # 상세 데이터 표 (아래쪽 배치)
            with st.expander("📄 상세 데이터 표 보기"):
                st.dataframe(filtered_df.sort_values(by='날짜', ascending=False))
                
        else:
            st.warning("왼쪽 사이드바에서 상세 지역을 선택해주세요.")

    except Exception as e:
        st.error("오류가 발생했습니다.")
        st.write(e)
        st.warning("파일이 올바른 KB 엑셀 형식이 아니거나, 시트 이름이 다를 수 있습니다.")

else:
    st.info("👈 왼쪽 사이드바에서 KB 시계열 엑셀 파일을 업로드해주세요.")
    st.markdown("### 💡 팁")
    st.markdown("- **차트 확대:** 차트 위에서 마우스로 드래그하면 확대됩니다.")
    st.markdown("- **슬라이더:** 차트 밑에 있는 조절바를 움직여보세요.")
    st.markdown("- **뉴스:** 우측 버튼을 누르면 해당 지역 뉴스로 연결됩니다.")
