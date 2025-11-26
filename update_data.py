import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
from datetime import datetime
from PublicDataReader import Kbland # 여기가 바뀌었습니다!

def main():
    print("🚀 [1단계] 구글 시트 연결 중...")
    
    try:
        # 구글 시트 인증
        json_key = os.environ.get('GOOGLE_JSON_KEY')
        if not json_key:
            raise ValueError("❌ GOOGLE_JSON_KEY 환경변수가 없습니다.")
        
        creds_dict = json.loads(json_key)
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # 시트 열기
        target_sheet_name = "kb_data" 
        sh = client.open(target_sheet_name)
        worksheet = sh.get_worksheet(0)
        print(f"✅ 구글 시트 '{target_sheet_name}' 접속 성공!")
        
    except Exception as e:
        print(f"❌ 구글 시트 연결 실패: {e}")
        return

    print("🚀 [2단계] KB 부동산 데이터 가져오기 (Kbland)...")
    
    try:
        # 라이브러리 초기화 (KB -> Kbland로 변경)
        kb = Kbland()
        
        # 매매가격지수 가져오기 (월간/주간 선택 가능)
        # params: '매매종합', '전세종합' 등
        print("📊 KB 주간 아파트 매매가격지수 다운로드 중...")
        
        # 이 함수가 내부적으로 KB 엑셀을 받아서 정리해줍니다.
        # (시간이 5~10초 정도 걸릴 수 있습니다)
        df = kb.get_weekly_price_index()

        if df is None or df.empty:
            raise Exception("데이터를 가져왔으나 비어있습니다.")
            
        print(f"✅ 데이터 수집 성공! (총 {len(df)}행)")
        
        # --- 데이터 다듬기 ---
        # 최신 날짜가 아래에 있을 수 있으므로 날짜 내림차순 정렬 (최신이 위로)
        df = df.sort_index(ascending=False)
        
        # 구글 시트에 넣기 좋게 가공 (최근 10주치만)
        df_recent = df.head(10)
        
        # 인덱스(날짜)를 컬럼으로 꺼내기
        df_recent = df_recent.reset_index()
        
        # 모든 데이터를 문자열로 변환 (오류 방지)
        df_recent = df_recent.fillna("").astype(str)
        
        print(f"💾 저장할 데이터: {df_recent.shape[0]}주 분량")

        print("🚀 [3단계] 구글 시트에 업데이트...")
        worksheet.clear() # 기존 내용 싹 지우기
        
        # 데이터프레임 헤더와 내용 업데이트
        worksheet.update([df_recent.columns.values.tolist()] + df_recent.values.tolist())
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"🎉 업데이트 완료! ({now})")

    except Exception as e:
        print(f"❌ KB 데이터 수집 실패: {e}")
        raise e

if __name__ == "__main__":
    main()
