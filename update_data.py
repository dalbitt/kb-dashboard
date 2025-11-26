import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
import requests
import io

# 1. 구글 시트 인증 및 연결
def connect_to_google_sheet():
    # 깃허브 Secrets에서 키 가져오기
    json_key = os.environ.get('GOOGLE_JSON_KEY')
    if not json_key:
        raise ValueError("GOOGLE_JSON_KEY 환경변수가 없습니다.")
    
    creds_dict = json.loads(json_key)
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

# 2. KB 데이터 가공 (여기가 핵심!)
def process_kb_data():
    # KB 부동산 주간 시계열 엑셀 다운로드 URL
    # 주의: KB는 URL이 종종 바뀝니다. 자동화가 실패하면 이 URL이 최신인지 확인해야 합니다.
    # 현재 시점 기준 예시 URL입니다. (실제 운영 시에는 최신 게시글을 크롤링하는 로직이 추가되면 더 좋습니다)
    url = "https://kbland.kr/file/stat/weekly_table.xlsx" # KB 고정 다운로드 링크 시도
    
    response = requests.get(url)
    if response.status_code != 200:
        print("엑셀 다운로드 실패! URL을 확인해주세요.")
        return None

    # 엑셀 읽기 (매매종합 시트)
    # KB 엑셀은 상단에 헤더가 복잡하므로 header=10 정도로 잡습니다 (파일마다 다를 수 있음 확인 필요)
    try:
        # sheet_name='매매종합'은 KB 엑셀의 탭 이름입니다.
        df = pd.read_excel(io.BytesIO(response.content), sheet_name='매매종합', header=10)
    except Exception as e:
        print(f"엑셀 읽기 오류: {e}")
        return None

    # 데이터 전처리: 날짜와 서울/경기 등 주요 지역만 추출하는 로직
    # KB 엑셀 구조: 첫 번째 컬럼이 날짜인 경우가 많음 (구조 확인 후 인덱싱 조정 필요)
    # 여기서는 예시로 가장 최근 데이터 1줄만 가져오는 것으로 가정합니다.
    
    # 실제로는 엑셀 구조를 뜯어보고 '날짜' 컬럼과 '지역' 컬럼을 매칭해야 합니다.
    # 일단 빈 데이터프레임이 아니라 엑셀 그대로를 가져오는지 테스트
    
    # 간단하게: 날짜 컬럼과 전국의 값만 가져와 봅니다. (열 위치는 엑셀 열어보고 수정 필요)
    # 예: 날짜는 A열(index 0), 전국은 B열(index 1), 서울은 C열... 이런 식일 것입니다.
    
    # 데이터가 너무 많으므로 최근 5주치만 잘라서 리턴해보겠습니다.
    df_recent = df.iloc[-5:, :10] # 최근 5행, 앞쪽 10개 열만
    
    # 구글 시트에 넣기 위해 문자열로 변환 (날짜 포맷 등 문제 방지)
    df_recent = df_recent.astype(str)
    
    return df_recent

# 3. 메인 실행 함수
def main():
    print("KB 데이터 업데이트 시작...")
    
    # 데이터 가져오기
    df = process_kb_data()
    if df is None:
        return

    # 구글 시트 연결
    client = connect_to_google_sheet()
    sh = client.open("kb_data") # 구글 시트 이름
    worksheet = sh.sheet1
    
    # 기존 내용 지우고 새로 쓰기 (또는 append)
    # 여기서는 '최신 현황판' 느낌으로 덮어쓰기를 하겠습니다.
    worksheet.clear()
    
    # 헤더 넣기
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())
    
    print("구글 시트 업데이트 완료!")

if __name__ == "__main__":
    main()
