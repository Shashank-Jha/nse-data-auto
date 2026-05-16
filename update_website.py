import json
import pandas as pd
import requests
import yfinance as yf
from io import StringIO
from datetime import datetime, timedelta

def fetch_nse_data():
    headers = {"User-Agent": "Mozilla/5.0"}
    date = datetime.now()
    
    for _ in range(7):
        date_str = date.strftime("%d%m%Y")
        url = f"https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{date_str}.csv"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200 and len(response.text) > 1000:
            return pd.read_csv(StringIO(response.text))
        date -= timedelta(days=1)
        
    raise Exception("Could not find a valid NSE bhavcopy.")

def get_top_volume_symbols(df):
    df.columns = df.columns.str.strip()
    df['SERIES'] = df['SERIES'].astype(str).str.strip()
    df = df[df['SERIES'] == 'EQ']
    
    exclude_keywords = ['BEES', 'ETF', 'LIQUID', 'GOLD', 'SILVER', 'CASH']
    pattern = '|'.join(exclude_keywords)
    df = df[~df['SYMBOL'].str.contains(pattern, case=False, na=False)]
    
    df = df.sort_values(by='TTL_TRD_QNTY', ascending=False).head(250)
    return df['SYMBOL'].tolist()

def scan_breakout_stocks(symbols):
    yf_symbols = [f"{sym}.NS" for sym in symbols]
    print("Downloading historical data...")
    data = yf.download(yf_symbols, period="1y", group_by="ticker", progress=False)
    
    breakout_list = []
    for sym in symbols:
        ticker = f"{sym}.NS"
        if ticker not in data.columns.levels[0]: continue
            
        df_stock = data[ticker].dropna()
        if len(df_stock) < 200: continue
            
        current_price = float(df_stock['Close'].iloc[-1])
        dma_50 = float(df_stock['Close'].rolling(window=50).mean().iloc[-1])
        dma_100 = float(df_stock['Close'].rolling(window=100).mean().iloc[-1])
        dma_200 = float(df_stock['Close'].rolling(window=200).mean().iloc[-1])
        pct_above_200_dma = ((current_price - dma_200) / dma_200) * 100
        
        high_idx = df_stock['Close'].idxmax()
        df_post_high = df_stock.loc[high_idx:]
        car_status = "Short History"
        
        if len(df_post_high) >= 10:
            car_series = df_post_high['Close'].expanding().mean()
            last_10_car = car_series.tail(10).tolist()
            if last_10_car[-1] > last_10_car[0] and last_10_car[-1] > last_10_car[-2]:
                car_status = "BUY (CAR Rising)"
            else:
                car_status = "AVOID (CAR Falling)"
        
        # We removed the 'if' statement here so ALL 250 stocks get added to the list
        breakout_list.append({
            'Symbol': sym,
            'Price (₹)': round(current_price, 2),
            '50 DMA': round(dma_50, 2),
            '100 DMA': round(dma_100, 2),
            '200 DMA': round(dma_200, 2),
            'Dist from 200 DMA': f"{round(pct_above_200_dma, 2)}%",
            'CAR Signal': car_status
        })
            
    return pd.DataFrame(breakout_list)

def save_to_json(df):
    last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stocks_list = df.to_dict(orient='records')
    output_data = { "last_updated": last_update, "stocks": stocks_list }
    with open("data.json", "w") as f:
        json.dump(output_data, f, indent=4)

if __name__ == "__main__":
    raw_df = fetch_nse_data()
    top_symbols = get_top_volume_symbols(raw_df)
    final_df = scan_breakout_stocks(top_symbols)
    save_to_json(final_df)
    print("Market data successfully saved to data.json")