import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
import requests
import io
from datetime import datetime

def main():
    print("🚀 [1단계] 구글 시트 연결 시작...")
    
    # 1. 구글 시트 인증
    try:
        json_key = os.environ.get('GOOGLE_JSON_KEY')
        if not json_key:
            raise ValueError("❌ GOOGLE_JSON_KEY 환경변수가 없습니다. Secrets 설정을 확인하세요.")
        
        creds_dict = json.loads(json_key)
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # 시트 열기 (첫 번째 시트 무조건 선택)
        sh = client.open("kb_data") 
        worksheet = sh.get_worksheet(0) # 이름이 sheet1이든 시트1이든 무조건 첫번째 것 선택
        print("✅ 구글 시트 접속 성공!")
        
        # 연결 테스트용 로그 남기기
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        worksheet.update_cell(1, 1, f"업데이트 확인: {now}")
        print(f"✅ 시트 쓰기 테스트 성공! (A1 셀을 확인해보세요: {now})")
        
    except Exception as e:
        print(f"❌ 구글 시트 연결 실패: {e}")
        print("💡 힌트: 구글 시트 이름이 'kb_data'가 맞나요? 서비스 계정 이메일을 '편집자'로 초대했나요?")
        raise e # 에러를 발생시켜 Actions를 실패로 만듦

    print("🚀 [2단계] KB 부동산 데이터 다운로드 시작...")
    
    # 2. KB 데이터 가져오기
    # KB 서버가 로봇을 막을 수 있으므로 헤더(신분증) 추가
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    # KB 통계 다운로드 링크 (링크가 변경될 수 있음)
    url = "https://kbland.kr/file/stat/weekly_table.xlsx" 

    try:
        response = requests.get(url, headers=headers, timeout=30)
        print(f"📡 서버 응답 코드: {response.status_code}")
        
        if response.status_code != 200:
            raise Exception(f"파일 다운로드 실패 (코드: {response.status_code})")
            
        # 엑셀 파일 읽기
        print("📊 엑셀 파일 파싱 중...")
        # KB 엑셀은 '매매종합' 시트가 핵심
        df = pd.read_excel(io.BytesIO(response.content), sheet_name='매매종합', header=10)
        
        # 데이터가 비었는지 확인
        if df.empty:
            raise Exception("엑셀 내용은 읽었으나 데이터가 비어있습니다.")
            
        print(f"✅ 데이터 추출 성공! (행 개수: {len(df)})")
        
        # 최신 데이터 5줄만 샘플로 추출 (전체 다 넣으면 너무 많음)
        # 실제로는 여기서 필요한 지역과 날짜를 정제하는 로직이 들어갑니다.
        # 테스트를 위해 상위 20행, 10열만 잘라서 저장합니다.
        df_sample = df.iloc[:20, :10].astype(str)
        
        # 3. 구글 시트에 데이터 업데이트
        print("🚀 [3단계] 구글 시트에 데이터 저장 중...")
        worksheet.clear() # 기존 데이터 삭제
        worksheet.update([df_sample.columns.values.tolist()] + df_sample.values.tolist())
        
        print("🎉 모든 작업 완료! 구글 시트를 확인하세요.")

    except Exception as e:
        print(f"❌ KB 데이터 처리 실패: {e}")
        # 여기서 에러가 나면 KB URL이 바뀌었거나 엑셀 구조가 바뀐 것입니다.
        raise e

if __name__ == "__main__":
    main()
