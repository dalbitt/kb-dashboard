import streamlit as st
import pandas as pd
import plotly.express as px

# 페이지 설정
st.set_page_config(page_title="KB 부동산 시세 분석기", layout="wide")

st.title("🏠 KB 부동산 시세 차트 (만능 버전)")
st.markdown("엑셀 파일을 올리고, **분석하고 싶은 시트(Sheet)**를 직접 선택하세요.")

# 1. 파일 업로드
st.sidebar.header("📂 1단계: 파일 업로드")
uploaded_file = st.sidebar.file_uploader("KB 엑셀 파일을 올려주세요", type=['xlsx', 'xls'])

st.sidebar.markdown("---")
st.sidebar.info("💡 **팁**: 주간/월간 시계열 파일 모두 가능합니다.")

if uploaded_file:
    try:
        # 엑셀 파일 로드 (데이터를 읽기 전에 시트 목록부터 확인)
        xls = pd.ExcelFile(uploaded_file)
        sheet_names = xls.sheet_names
        
        # 2. 사용자에게 시트 선택하게 하기
        st.sidebar.header("📑 2단계: 시트 선택")
        # 보통 '매매'라는 글자가 들어간 시트를 기본으로 잡아줌 (없으면 첫번째꺼)
        default_index = 0
        for i, name in enumerate(sheet_names):
            if "매매" in name and "종합" in name:
                default_index = i
                break
        
        selected_sheet = st.sidebar.selectbox(
            "어떤 데이터를 보시겠습니까?", 
            sheet_names, 
            index=default_index
        )
        
        # 선택한 시트 읽기
        # header=10: KB 엑셀은 보통 11번째 줄부터 데이터가 시작됩니다.
        # 만약 데이터가 이상하게 보이면 이 숫자를 조정해야 합니다.
        df = pd.read_excel(uploaded_file, sheet_name=selected_sheet, header=10)
        
        # 3. 데이터 전처리 (여기가 제일 중요)
        # 첫 번째 열을 '날짜'로 가정하고 이름 변경
        df.rename(columns={df.columns[0]: '날짜'}, inplace=True)
        
        # 날짜가 아닌 찌꺼기 행(제목, 빈칸 등) 제거
        # '날짜' 열을 날짜형식으로 변환해보고, 실패하면(NaT) 그 행을 지움
        df['날짜_변환'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.dropna(subset=['날짜_변환']) # 날짜가 없는 행 삭제
        df['날짜'] = df['날짜_변환'] # 깨끗한 날짜로 덮어쓰기
        df = df.drop(columns=['날짜_변환']) # 임시 컬럼 삭제
        
        # 4. 지역 선택 및 차트 그리기
        # 날짜 컬럼을 뺀 나머지는 모두 '지역'으로 간주
        region_list = [col for col in df.columns if col != '날짜']
        
        if not region_list:
            st.error("데이터를 찾을 수 없습니다. 시트나 헤더 위치가 다른 것 같아요.")
        else:
            st.write(f"### 📈 {selected_sheet} 차트")
            
            # 기본적으로 '서울', '전국'이 있으면 그걸 먼저 보여줌
            default_regions = [r for r in region_list if r in ['서울', '서울 강북', '서울 강남', '전국']]
            if not default_regions:
                default_regions = [region_list[0]] # 없으면 맨 첫번째 지역
            
            selected_regions = st.multiselect(
                "확인할 지역을 선택하세요:", 
                region_list, 
                default=default_regions
            )
            
            if selected_regions:
                # 차트 데이터 만들기
                filtered_df = df[['날짜'] + selected_regions]
                melted_df = filtered_df.melt(id_vars=['날짜'], var_name='지역', value_name='지수')
                
                # 차트 그리기
                fig = px.line(melted_df, x='날짜', y='지수', color='지역',
                              title=f'{selected_sheet} 변동 추이',
                              markers=True)
                
                st.plotly_chart(fig, use_container_width=True)
                
                # 표 보여주기
                with st.expander("상세 데이터 표 보기"):
                    st.dataframe(filtered_df.sort_values(by='날짜', ascending=False))
            else:
                st.warning("지역을 선택해주세요.")

    except Exception as e:
        st.error("오류가 발생했습니다.")
        st.write("원인:", e)
        st.warning("혹시 '표지'나 '목차' 시트를 선택하셨나요? 데이터가 있는 시트(예: 매매종합)를 선택해주세요.")

else:
    st.info("👈 왼쪽에서 엑셀 파일을 업로드해주세요.")
