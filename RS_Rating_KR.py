import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from pykrx import stock
from tqdm import tqdm
import time
import warnings
warnings.filterwarnings('ignore')

LOOKBACK_DAYS = 400
MIN_DAYS = 252
OUTPUT_FILE = "kr_result.json"

print("한국 종목 리스트를 가져오는 중...")

today = datetime.today().strftime('%Y%m%d')
kospi = stock.get_market_ticker_list(today, market="KOSPI")
kosdaq = stock.get_market_ticker_list(today, market="KOSDAQ")

kr_codes = kospi + kosdaq
kr_list = []
for code in kr_codes:
    name = stock.get_market_ticker_name(code)
    kr_list.append({'Symbol': code, 'Name': name})

kr_list = pd.DataFrame(kr_list)
print(f"총 한국 종목 수: {len(kr_list)}개")

def calculate_rs_raw(symbol):
    try:
        end_date = datetime.today()
        start_date = end_date - timedelta(days=LOOKBACK_DAYS)
        
        df = stock.get_market_ohlcv_by_date(
            start_date.strftime('%Y%m%d'),
            end_date.strftime('%Y%m%d'),
            symbol
        )
        
        if df is None or len(df) < MIN_DAYS:
            return None
        
        close = df['종가']
        
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
    
    time.sleep(0.05)

if len(results) == 0:
    print("계산된 종목이 없습니다.")
else:
    df_result = pd.DataFrame(results)
    
    df_result['RS_Rating'] = df_result['RS_Raw'].rank(pct=True) * 98 + 1
    df_result['RS_Rating'] = df_result['RS_Rating'].round().astype(int)
    df_result['RS_Rating'] = df_result['RS_Rating'].clip(1, 99)
    
    df_result = df_result.sort_values('RS_Raw', ascending=False)
    df_result = df_result[df_result['RS_Rating'] >= 80]
    
    KST = timezone(timedelta(hours=9))
    update_time = datetime.now(KST).strftime('%Y-%m-%d %H:%M')
    df_result['UpdateTime'] = update_time
    
    df_result.to_json(OUTPUT_FILE, orient='records', force_ascii=False)
    
    print(f"\n완료! 80점 이상 {len(df_result)}개 종목 저장됨")
    print(f"결과 파일: {OUTPUT_FILE}")
    print("\n상위 10개:")
    print(df_result.head(10).to_string(index=False))