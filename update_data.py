import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
import io
import cloudscraper # 이게 핵심 해결사입니다
from datetime import datetime

def main():
    print("🚀 [1단계] 구글 시트 연결 중...")
    
    try:
        json_key = os.environ.get('GOOGLE_JSON_KEY')
        if not json_key:
            raise ValueError("❌ GOOGLE_JSON_KEY 없습니다.")
        
        creds_dict = json.loads(json_key)
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        sh = client.open("kb_data")
        worksheet = sh.get_worksheet(0)
        print("✅ 구글 시트 접속 성공!")
        
    except Exception as e:
        print(f"❌ 구글 시트 에러: {e}")
        return

    print("🚀 [2단계] KB 보안벽 우회하여 다운로드 시도...")

    # cloudscraper: 봇 탐지를 뚫는 라이브러리
    scraper = cloudscraper.create_scraper()
    
    # KB 부동산 주간 시계열 공식 단축 URL (이게 제일 정확합니다)
    target_url = "https://kbland.kr/file/stat/weekly_table.xlsx"

    try:
        # 1. 파일 다운로드
        response = scraper.get(target_url)
        print(f"📡 응답 코드: {response.status_code}")
        
        if response.status_code != 200:
            raise Exception(f"차단당함. 상태코드: {response.status_code}")
            
        # 2. 엑셀 파싱
        print("📊 엑셀 파일 해독 중...")
        
        # 파일 내용 앞부분이 '<!DOCTYPE' (HTML)이면 여전히 차단된 것
        if response.content[:10].startswith(b'<!DOCTYPE') or response.content[:5].startswith(b'<html'):
            print(f"❌ 실패: 엑셀 대신 HTML(웹페이지)이 다운로드됨.\n내용: {response.text[:200]}")
            raise Exception("KB 서버가 여전히 차단 중입니다.")

        # 엑셀 읽기
        df = pd.read_excel(io.BytesIO(response.content), sheet_name='매매종합', header=10, engine='openpyxl')
        
        # 데이터 정제
        df = df.dropna(how='all') # 빈 줄 제거
        
        # 최근 데이터 추출 (상위 20개 행)
        df_recent = df.head(20).fillna("").astype(str)
        
        print(f"✅ 성공! 데이터 {len(df)}행 확보함.")

        # 3. 구글 시트 저장
        print("🚀 [3단계] 구글 시트 업데이트...")
        worksheet.clear()
        worksheet.update([df_recent.columns.values.tolist()] + df_recent.values.tolist())
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"🎉 작업 끝! ({now})")

    except Exception as e:
        print(f"❌ 작업 실패: {e}")
        # 실패 시 에러를 던져서 빨간불이 뜨게 함
        raise e

if __name__ == "__main__":
    main()
