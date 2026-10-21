import FinanceDataReader as fdr
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from tqdm import tqdm
import time
import warnings
warnings.filterwarnings('ignore')

# ==================== 설정 ====================
LOOKBACK_DAYS = 400
MIN_DAYS = 252
OUTPUT_FILE = "kr_result.json"

# ==================== 한국 종목 리스트 ====================
print("한국 종목 리스트를 가져오는 중...")

kospi = fdr.StockListing('KOSPI')[['Code', 'Name']]
kosdaq = fdr.StockListing('KOSDAQ')[['Code', 'Name']]
kr_list = pd.concat([kospi, kosdaq], ignore_index=True)
kr_list = kr_list.rename(columns={'Code': 'Symbol'})

print(f"총 한국 종목 수: {len(kr_list)}개")

# ==================== RS Raw 계산 함수 ====================
def calculate_rs_raw(symbol):
    try:
        end_date = datetime.today()
        start_date = end_date - timedelta(days=LOOKBACK_DAYS)
        
        df = fdr.DataReader(symbol, start_date, end_date)
        
        if df is None or len(df) < MIN_DAYS:
            return None
        
        close = df['Close']
        
        def roc(days):
            if len(close) > days:
                return (close.iloc[-1] / close.iloc[-days-1] - 1) * 100
            return np.nan
        
        p3  = roc(63)
        p6  = roc(126)
        p9  = roc(189)
        p12 = roc(252)
        
        if any(pd.isna([p3, p6, p9, p12])):
            return None
        
        rs_raw = 0.4 * p3 + 0.2 * p6 + 0.2 * p9 + 0.2 * p12
        return rs_raw
    
    except Exception:
        return None

# ==================== 계산 시작 ====================
print("\nRS 점수를 계산하는 중...")
results = []

for idx, row in tqdm(kr_list.iterrows(), total=len(kr_list)):
    symbol = row['Symbol']
    name = row['Name']
    
    rs_raw = calculate_rs_raw(symbol)
    
    if rs_raw is not None:
        results.append({
            'Symbol': symbol,
            'Name': name,
            'RS_Raw': rs_raw
        })
    
    time.sleep(0.03)

# ==================== 결과 정리 ====================
if len(results) == 0:
    print("계산된 종목이 없습니다.")
else:
    df_result = pd.DataFrame(results)
    
    df_result['RS_Rating'] = df_result['RS_Raw'].rank(pct=True) * 98 + 1
    df_result['RS_Rating'] = df_result['RS_Rating'].round().astype(int)
    df_result['RS_Rating'] = df_result['RS_Rating'].clip(1, 99)
    
    df_result = df_result.sort_values('RS_Raw', ascending=False)
    df_result = df_result[df_result['RS_Rating'] >= 80]
    
    # 업데이트 시간 추가
    update_time = datetime.now().strftime('%Y-%m-%d %H:%M')
    df_result['UpdateTime'] = update_time
    
    df_result.to_json(OUTPUT_FILE, orient='records', force_ascii=False)
    
    print(f"\n완료! 80점 이상 {len(df_result)}개 종목 저장됨")
    print(f"결과 파일: {OUTPUT_FILE}")
    print("\n상위 10개:")
    print(df_result.head(10).to_string(index=False))
