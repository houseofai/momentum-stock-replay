#!/usr/bin/env python3
"""
Download historical market data from Interactive Brokers via IB Gateway
Designed to run in GitHub Actions with Docker IB Gateway service
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from ib_async import IB, Stock, util

# Configuration
IB_HOST = os.getenv('IB_HOST', 'localhost')
IB_PORT = int(os.getenv('IB_PORT', 4002))
IB_CLIENT_ID = int(os.getenv('IB_CLIENT_ID', 1))

# Symbols to download (can be expanded)
SYMBOLS = ['AAPL']

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / 'sessions'
OUTPUT_DIR.mkdir(exist_ok=True)


def connect_ib():
    """Connect to IB Gateway with retries"""
    ib = IB()
    max_retries = 5

    for attempt in range(max_retries):
        try:
            ib.connect(IB_HOST, IB_PORT, clientId=IB_CLIENT_ID, timeout=20)
            print(f"✓ Connected to IB Gateway at {IB_HOST}:{IB_PORT}")
            return ib
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 10
                print(f"Connection attempt {attempt + 1} failed: {e}")
                print(f"Retrying in {wait_time} seconds...")
                util.sleep(wait_time)
            else:
                print(f"✗ Failed to connect after {max_retries} attempts")
                raise

    return None


def download_symbol_data(ib, symbol, end_date=None):
    """Download historical data for a single symbol"""
    if end_date is None:
        # Use previous trading day
        end_date = datetime.now()
        # If it's weekend, go back to Friday
        if end_date.weekday() == 5:  # Saturday
            end_date -= timedelta(days=1)
        elif end_date.weekday() == 6:  # Sunday
            end_date -= timedelta(days=2)

    # Create contract
    contract = Stock(symbol, 'SMART', 'USD')
    ib.qualifyContracts(contract)

    print(f"\nDownloading {symbol} for {end_date.strftime('%Y-%m-%d')}...")

    try:
        # Request historical data - 1 day of 1-minute bars
        bars = ib.reqHistoricalData(
            contract,
            endDateTime=end_date,
            durationStr='1 D',  # Last trading day
            barSizeSetting='1 min',
            whatToShow='TRADES',
            useRTH=True,  # Regular trading hours only
            formatDate=1
        )

        if not bars:
            print(f"  ✗ No data received for {symbol}")
            return None

        # Convert to DataFrame
        df = util.df(bars)

        # Format timestamp
        df['ts_event'] = pd.to_datetime(df['date']).astype('int64') // 10**9

        # Map to MBP-1 format structure (simplified)
        # Note: IB provides OHLCV, not actual bid/ask levels
        # For demonstration, we'll use close price for both bid and ask
        df['bid_px_00'] = df['close']
        df['ask_px_00'] = df['close']
        df['bid_sz_00'] = df['volume']
        df['ask_sz_00'] = df['volume']
        df['symbol'] = symbol
        df['exchange'] = 'SMART'

        # Select columns in order
        output_df = df[['ts_event', 'bid_px_00', 'ask_px_00', 'bid_sz_00', 'ask_sz_00', 'symbol', 'exchange']]

        # Save to CSV (compatible with your compress.py format)
        date_str = end_date.strftime('%Y%m%d')
        filename = f"{symbol}-{date_str}.csv"
        filepath = OUTPUT_DIR / filename

        output_df.to_csv(filepath, index=False)

        print(f"  ✓ Downloaded {len(bars)} bars → {filename}")
        print(f"  ✓ Time range: {df['date'].min()} to {df['date'].max()}")

        return output_df

    except Exception as e:
        print(f"  ✗ Error downloading {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main download workflow"""
    print("=" * 70)
    print("IB Historical Data Downloader")
    print("=" * 70)
    print(f"Host: {IB_HOST}:{IB_PORT}")
    print(f"Symbols: {', '.join(SYMBOLS)}")
    print(f"Output directory: {OUTPUT_DIR}")
    print("=" * 70)

    # Connect to IB Gateway
    try:
        ib = connect_ib()
    except Exception as e:
        print(f"\n✗ Connection failed: {e}")
        sys.exit(1)

    if not ib:
        print("\n✗ Could not establish connection to IB Gateway")
        sys.exit(1)

    try:
        # Download data for each symbol
        results = {}
        for symbol in SYMBOLS:
            try:
                df = download_symbol_data(ib, symbol)
                if df is not None:
                    results[symbol] = len(df)
            except Exception as e:
                print(f"  ✗ Error processing {symbol}: {e}")

        # Summary
        print("\n" + "=" * 70)
        print("Download Summary")
        print("=" * 70)
        if results:
            for symbol, count in results.items():
                print(f"  ✓ {symbol}: {count:,} bars")
            print(f"\nTotal symbols downloaded: {len(results)}/{len(SYMBOLS)}")
        else:
            print("  ✗ No data downloaded")
            sys.exit(1)

    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        ib.disconnect()
        print("\n✓ Disconnected from IB Gateway")


if __name__ == '__main__':
    main()
