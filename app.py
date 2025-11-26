import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# 페이지 설정
st.set_page_config(page_title="KB 부동산 시세", layout="wide")

st.title("🏠 KB 부동산 주간/월간 시세")

# 구글 시트 연결 (나중에 설정할 비밀키 사용)
# 주의: 로컬 테스트 시에는 secrets.toml 파일이 필요하지만, 
# 클라우드 배포 시에는 Streamlit Cloud의 Secrets 기능을 사용합니다.

try:
    # Streamlit Secrets에서 설정 정보 가져오기
    gcp_service_account = json.loads(st.secrets["gcp_service_account"]["json_key"])
    
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(gcp_service_account, scope)
    client = gspread.authorize(creds)
    
    # 구글 시트 열기 (시트 이름 정확해야 함)
    sh = client.open("kb_data") # 1단계에서 만든 시트 이름
    worksheet = sh.sheet1
    
    # 데이터 가져오기
    data = worksheet.get_all_records()
    
    if not data:
        st.warning("아직 데이터가 없습니다. 자동화가 실행될 때까지 기다려주세요!")
    else:
        df = pd.DataFrame(data)
        st.write("### 📊 최신 데이터 확인")
        st.dataframe(df)
        
        # 여기에 나중에 차트 그리는 코드가 들어갑니다.

except Exception as e:
    st.error(f"데이터를 불러오는데 실패했습니다: {e}")
    st.info("설정(Secrets)이 아직 완료되지 않았을 수 있습니다.")
