import pandas as pd
import requests
import yfinance as yf
from io import StringIO
from datetime import datetime, timedelta

def fetch_nse_data():
    headers = {"User-Agent": "Mozilla/5.0"}
    date = datetime.now()
    
    # Check up to 7 days back to find the latest valid trading day
    for _ in range(7):
        date_str = date.strftime("%d%m%Y")
        url = f"https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{date_str}.csv"
        print(f"Trying date {date_str}...")
        
        response = requests.get(url, headers=headers, timeout=10)
        
        # If successful and file has data, return it
        if response.status_code == 200 and len(response.text) > 1000:
            print(f"✅ Success! Fetched latest data for {date.strftime('%Y-%m-%d')}")
            return pd.read_csv(StringIO(response.text))
            
        date -= timedelta(days=1)
        
    raise Exception("Could not find a valid NSE bhavcopy in the last 7 days.")

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
    
    print("Downloading historical data for top 250 volume leaders...")
    data = yf.download(yf_symbols, period="1y", group_by="ticker", progress=False)
    
    breakout_list = []
    
    for sym in symbols:
        ticker = f"{sym}.NS"
        if ticker not in data.columns.levels[0]:
            continue
            
        df_stock = data[ticker].dropna()
        if len(df_stock) < 200:
            continue
            
        current_price = float(df_stock['Close'].iloc[-1])
        
        dma_50 = float(df_stock['Close'].rolling(window=50).mean().iloc[-1])
        dma_100 = float(df_stock['Close'].rolling(window=100).mean().iloc[-1])
        dma_200 = float(df_stock['Close'].rolling(window=200).mean().iloc[-1])
        
        is_bull_run = current_price > dma_50 and current_price > dma_100 and current_price > dma_200
        pct_above_200_dma = ((current_price - dma_200) / dma_200) * 100
        is_fresh_breakout = pct_above_200_dma <= 10.0
        
        if is_bull_run and is_fresh_breakout:
            breakout_list.append({
                'Symbol': sym,
                'Price (₹)': round(current_price, 2),
                '50 DMA': round(dma_50, 2),
                '100 DMA': round(dma_100, 2),
                '200 DMA': round(dma_200, 2),
                'Distance from 200 DMA': f"{round(pct_above_200_dma, 2)}%"
            })
            
    return pd.DataFrame(breakout_list)

def create_html(df):
    if df.empty:
        html_table = "<p style='text-align:center; color:#666;'>No stocks currently match the breakout criteria today.</p>"
    else:
        html_table = df.to_html(index=False, classes='stock-table')
        
    last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Curated Breakout Stocks</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f9; }}
            .container {{ max-width: 900px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
            h2 {{ text-align: center; color: #2c3e50; margin-bottom: 5px; }}
            .subtitle {{ text-align: center; color: #7f8c8d; font-size: 14px; margin-bottom: 20px; }}
            .stock-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            .stock-table th, .stock-table td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
            .stock-table th {{ background-color: #27ae60; color: white; }}
            .stock-table tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .stock-table tr:hover {{ background-color: #f1f1f1; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🎯 Curated High-Volume Breakout Stocks</h2>
            <div class="subtitle">Criteria: Top 250 Vol | Price > 50, 100, 200 DMA | Within 10% of 200 DMA <br> Last updated: {last_update}</div>
            {html_table}
        </div>
    </body>
    </html>
    """
    
    with open("index.html", "w") as f:
        f.write(html_template)

if __name__ == "__main__":
    raw_df = fetch_nse_data()
    top_symbols = get_top_volume_symbols(raw_df)
    final_df = scan_breakout_stocks(top_symbols)
    create_html(final_df)
    print("Website updated successfully.")