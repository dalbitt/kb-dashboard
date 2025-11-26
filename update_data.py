import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
from datetime import datetime
from PublicDataReader import KB

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
        
        # 시트 열기 (이름 확인 필수!)
        target_sheet_name = "kb_data" 
        sh = client.open(target_sheet_name)
        worksheet = sh.get_worksheet(0)
        print(f"✅ 구글 시트 '{target_sheet_name}' 접속 성공!")
        
    except Exception as e:
        print(f"❌ 구글 시트 연결 실패: {e}")
        return

    print("🚀 [2단계] KB 부동산 데이터 가져오기 (PublicDataReader)...")
    
    try:
        # 라이브러리를 사용해 데이터 조회
        kb = KB()
        
        # '주간' 아파트 '매매' 가격지수 가져오기
        # 이 라이브러리는 엑셀을 다운받는 게 아니라 데이터를 직접 가져옵니다.
        df = kb.get_price_index("아파트", "매매", "주간")
        
        if df is None or df.empty:
            raise Exception("데이터를 가져왔으나 비어있습니다.")
            
        print(f"✅ 데이터 수집 성공! (총 {len(df)}행)")
        
        # 데이터가 너무 많으므로(전체 역사), 최근 날짜 기준 일부만 잘라서 저장하거나
        # 전체를 저장하려면 구글 시트 용량을 고려해야 합니다.
        # 여기서는 '최근 10주' 데이터만 깔끔하게 저장하겠습니다.
        
        # 데이터 정리: 행(날짜)과 열(지역) 구조 확인
        # 라이브러리 결과는 보통 인덱스가 날짜로 되어 있습니다.
        df = df.sort_index(ascending=False) # 최신 날짜가 위로 오게 정렬
        df_recent = df.head(10) # 최근 10주치만
        
        # 인덱스(날짜)를 컬럼으로 뺍니다
        df_recent = df_recent.reset_index()
        df_recent.columns = df_recent.columns.astype(str) # 컬럼명을 문자열로 통일
        df_recent = df_recent.fillna("") # 빈칸 처리
        
        print(f"📊 저장할 데이터: {df_recent.shape[0]}주 분량")

        print("🚀 [3단계] 구글 시트에 업데이트...")
        worksheet.clear() # 기존 내용 삭제
        worksheet.update([df_recent.columns.values.tolist()] + df_recent.values.tolist())
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"🎉 업데이트 완료! ({now})")

    except Exception as e:
        print(f"❌ KB 데이터 수집 실패: {e}")
        print("💡 힌트: PublicDataReader가 KB 사이트 변경으로 막혔을 수도 있습니다.")
        raise e

if __name__ == "__main__":
    main()
