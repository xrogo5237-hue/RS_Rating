import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from tqdm import tqdm
import time
import warnings
warnings.filterwarnings('ignore')

LOOKBACK_DAYS = 400
MIN_DAYS = 252
OUTPUT_FILE = "us_result.json"
MIN_PRICE = 5.0

print("미국 종목 리스트를 가져오는 중...")

import FinanceDataReader as fdr

nasdaq = fdr.StockListing('NASDAQ')
nyse = fdr.StockListing('NYSE')
us_list = pd.concat([nasdaq, nyse], ignore_index=True)

exclude_keywords = [
    'ETF', 'Fund', 'Trust', 'Index', 'Income', 'Bond', 'Preferred',
    'Warrant', 'Unit', 'Notes', 'Debenture', 'Senior', 'Subordinated',
    'Due 20', 'Due 19', 'Due 18', '%', 'Coupon', 'ADR', 'Depositary'
]
mask = \~us_list['Name'].str.contains('|'.join(exclude_keywords), case=False, na=False)
us_list = us_list[mask][['Symbol', 'Name']].reset_index(drop=True)

print(f"필터 후 미국 종목 수: {len(us_list)}개")

def calculate_rs_raw(symbol):
    try:
        end_date = datetime.today()
        start_date = end_date - timedelta(days=LOOKBACK_DAYS)
        
        df = yf.download(symbol, start=start_date, end=end_date, progress=False)
        
        if df is None or len(df) < MIN_DAYS:
            return None
        
        if df['Close'].iloc[-1] < MIN_PRICE:
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
        return float(rs_raw)
    
    except Exception:
        return None

print("\nRS 점수를 계산하는 중...")
results = []

for idx, row in tqdm(us_list.iterrows(), total=len(us_list)):
    symbol = row['Symbol']
    name = row['Name']
    
    rs_raw =