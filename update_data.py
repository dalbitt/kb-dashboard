import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
import requests
import io
from datetime import datetime

def main():
    print("🚀 [1단계] 구글 시트 연결 중...")
    
    # 1. 구글 시트 인증 (기존과 동일)
    try:
        json_key = os.environ.get('GOOGLE_JSON_KEY')
        if not json_key:
            raise ValueError("❌ GOOGLE_JSON_KEY 환경변수가 없습니다.")
        
        creds_dict = json.loads(json_key)
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        target_sheet_name = "kb_data"
        sh = client.open(target_sheet_name)
        worksheet = sh.get_worksheet(0)
        print(f"✅ 구글 시트 '{target_sheet_name}' 접속 성공!")
        
    except Exception as e:
        print(f"❌ 구글 시트 연결 실패: {e}")
        return

    print("🚀 [2단계] KB 부동산 데이터 직접 다운로드...")
    
    # ★ KB 서버 차단 우회 설정 (이게 핵심입니다)
    url = "https://kbland.kr/upload/stat/weekly_table.xlsx"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://kbland.kr/",  # 나 KB 사이트에서 왔어! 라고 속임
        "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        print(f"📡 서버 응답 코드: {response.status_code}")
        
        if response.status_code != 200:
            raise Exception(f"다운로드 실패. 코드: {response.status_code}")

        # 엑셀 파일 열기 (엔진 명시)
        print("📊 엑셀 파일 해독 중...")
        
        # KB 엑셀의 '매매종합' 시트 읽기. header=10은 KB 엑셀 구조상 제목줄 위치입니다.
        try:
            df = pd.read_excel(io.BytesIO(response.content), sheet_name='매매종합', header=10, engine='openpyxl')
        except Exception as excel_err:
            # 만약 엑셀이 아니라고 하면, 서버가 보낸 내용을 텍스트로 찍어서 확인
            print(f"❌ 엑셀 읽기 실패. 서버가 보낸 내용 앞부분: {response.text[:100]}")
            raise excel_err

        if df.empty:
            raise Exception("데이터가 비어있습니다.")
            
        print(f"✅ 엑셀 읽기 성공! (원본 {len(df)}행)")
        
        # --- 데이터 가공 ---
        # 1. 불필요한 상단/좌측 정보 제거하고 순수 데이터만 남기기
        # 보통 KB 엑셀은 날짜가 없는 행들이 상단에 좀 더 있을 수 있어서 정제 필요
        # '구분' 컬럼 같은게 있어서 날짜형식이 아닌 행들을 제거
        
        # 날짜 컬럼 찾기 (보통 첫번째 컬럼)
        # 엑셀 구조상 첫 컬럼이 날짜가 아닐 수도 있어, 안전하게 처리
        df = df.dropna(how='all') # 전체가 빈 행 삭제
        
        # 화면에 보여줄 요약본 만들기 (최근 15주, 주요 지역)
        # 너무 크면 구글 시트 터지므로 상위 15행만 자릅니다.
        df_recent = df.head(15)
        
        # 구글 시트 저장용 문자열 변환
        df_recent = df_recent.fillna("").astype(str)

        print("🚀 [3단계] 구글 시트에 덮어쓰기...")
        worksheet.clear()
        worksheet.update([df_recent.columns.values.tolist()] + df_recent.values.tolist())
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"🎉 진짜 완료! ({now}) - 구글 시트를 확인하세요.")

    except Exception as e:
        print(f"❌ 작업 실패: {e}")
        raise e

if __name__ == "__main__":
    main()
