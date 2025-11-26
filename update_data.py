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
            raise ValueError("❌ GOOGLE_JSON_KEY 환경변수가 없습니다.")
        
        creds_dict = json.loads(json_key)
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # 시트 열기
        sh = client.open("kb_data") 
        worksheet = sh.get_worksheet(0)
        print("✅ 구글 시트 접속 성공!")
        
        # 연결 테스트
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        worksheet.update_cell(1, 1, f"연결 확인됨: {now}")
        
    except Exception as e:
        print(f"❌ 구글 시트 연결 실패: {e}")
        raise e

    print("🚀 [2단계] KB 부동산 데이터 다운로드 시작...")
    
    # KB 서버가 봇을 차단하지 않게 브라우저인 척 위장
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # ★ KB 주간 시계열 다운로드 주소 (가장 최신 링크로 추정)
    # 만약 여기서 에러가 나면 이 링크가 바뀐 것입니다.
    url = "https://kbland.kr/upload/stat/weekly_table.xlsx" # URL 수정됨

    try:
        response = requests.get(url, headers=headers, timeout=30)
        print(f"📡 서버 응답 코드: {response.status_code}")
        
        if response.status_code != 200:
            # 200(성공)이 아니면 KB 사이트 구조가 바뀐 것
            raise Exception(f"파일 다운로드 실패. 링크 확인 필요 (코드: {response.status_code})")
            
        # 엑셀 파일 읽기
        print("📊 엑셀 파일 파싱 중...")
        
        # 🚨 [수정한 부분] engine='openpyxl'을 추가해서 엑셀임을 명시!
        df = pd.read_excel(io.BytesIO(response.content), sheet_name='매매종합', header=10, engine='openpyxl')
        
        if df.empty:
            raise Exception("엑셀 데이터가 비어있습니다.")
            
        print(f"✅ 데이터 추출 성공! (행 개수: {len(df)})")
        
        # 3. 구글 시트에 데이터 업데이트 (테스트용으로 상위 20줄만)
        # 엑셀에 NaN(빈값)이 있으면 구글시트 오류가 나므로 빈 문자열로 변환
        df_sample = df.iloc[:20, :10].fillna("").astype(str)
        
        print("🚀 [3단계] 구글 시트에 데이터 저장 중...")
        worksheet.clear()
        worksheet.update([df_sample.columns.values.tolist()] + df_sample.values.tolist())
        
        print("🎉 모든 작업 완료! 구글 시트를 확인하세요.")

    except Exception as e:
        print(f"❌ KB 데이터 처리 실패: {e}")
        print("💡 힌트: 'Bad Zip File' 에러가 나면 KB 다운로드 주소(URL)가 바뀐 것입니다.")
        raise e

if __name__ == "__main__":
    main()
