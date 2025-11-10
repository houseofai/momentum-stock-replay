import glob
import os
import pandas as pd
import numpy as np
import gzip
import struct

# --- Parameters ---
# Updated to handle consolidated ALL-EXCHANGES files
CSV_PATH = "C:/Users/otrem/PycharmProjects/momentum-finder/sessions/*_ALL-EXCHANGES_MBP-1.csv"
OUT_PATH = "../sessions/"

csv_files = glob.glob(CSV_PATH)
print(f"Found {len(csv_files)} CSV files to process.")
# Use higher precision to avoid data loss
PRICE_SCALE = 100_000  # 5 decimal places precision
SIZE_SCALE = 100  # 2 decimal places precision
TIME_UNIT = 1_000_000  # µs

for csv_file in csv_files:
    # --- Read CSV ---
    # New format has: ts_event, bid_px_00, ask_px_00, bid_sz_00, ask_sz_00, symbol, exchange
    df = pd.read_csv(csv_file)

    # Convert ts_event to datetime (handle mixed formats with ISO8601)
    df['time'] = pd.to_datetime(df['ts_event'], format='ISO8601', utc=True)
    df.sort_values('time', inplace=True)
    df.reset_index(drop=True, inplace=True)

    # --- Initial timestamp (in microseconds) ---
    t0 = df['time'].iloc[0]
    initial_timestamp_us = int(t0.timestamp() * TIME_UNIT)

    # --- Encode time deltas ---
    deltas = (df['time'] - t0).dt.total_seconds().fillna(0).to_numpy()
    deltas_us = (deltas * TIME_UNIT).astype(np.int64)  # Use int64 for larger range

    # --- Convert prices and sizes without delta encoding ---
    # Delta encoding can cause precision issues, store absolute values instead
    # Use new column names: bid_px_00, ask_px_00, bid_sz_00, ask_sz_00
    # Handle NaN values by filling with forward fill, then backward fill
    df['bid_px_00'] = df['bid_px_00'].ffill().bfill()
    df['ask_px_00'] = df['ask_px_00'].ffill().bfill()
    df['bid_sz_00'] = df['bid_sz_00'].ffill().bfill().fillna(0)
    df['ask_sz_00'] = df['ask_sz_00'].ffill().bfill().fillna(0)

    price_bid = (df['bid_px_00'] * PRICE_SCALE).round().astype(np.int32)
    price_ask = (df['ask_px_00'] * PRICE_SCALE).round().astype(np.int32)
    size_bid = (df['bid_sz_00'] * SIZE_SCALE).round().astype(np.int32)
    size_ask = (df['ask_sz_00'] * SIZE_SCALE).round().astype(np.int32)

    # --- Create binary buffer ---
    # Format: int64 timestamp_us, int32 priceBid, int32 priceAsk, int32 sizeBid, int32 sizeAsk
    # Total: 8 + 4 + 4 + 4 + 4 = 24 bytes per row

    num_rows = len(df)
    buffer = bytearray()

    # Write header
    # Magic number (4 bytes) + version (1 byte) + num_rows (4 bytes) + initial_timestamp (8 bytes)
    header = struct.pack('<4sBIQ',
                         b'TICK',  # Magic number
                         1,  # Version
                         num_rows,
                         initial_timestamp_us
                         )
    buffer.extend(header)

    # Write data rows
    for i in range(num_rows):
        row_data = struct.pack('<qiiii',
                               deltas_us[i],
                               price_bid[i],
                               price_ask[i],
                               size_bid[i],
                               size_ask[i]
                               )
        buffer.extend(row_data)

    # --- Compress with Gzip ---
    compressed = gzip.compress(bytes(buffer), compresslevel=9)

    # Extract filename: CMBM_2025-10-29_ALL-EXCHANGES_MBP-1.csv -> CMBM-20251029.bin.gz
    filename = os.path.basename(csv_file)
    parts = filename.split('_')
    symbol = parts[0]  # CMBM
    date_str = parts[1].replace('-', '')  # 2025-10-29 -> 20251029
    dest_file = os.path.join(OUT_PATH, f"{symbol}-{date_str}.bin.gz")

    with open(dest_file, 'wb') as f:
        f.write(compressed)

    # --- Verification: decompress and check ---
    print(f"\n✅ Compressed file written: {dest_file}")
    print(f"Symbol: {symbol}, Date: {date_str}")
    print(f"Initial timestamp: {initial_timestamp_us} µs ({t0})")
    print(f"Number of rows: {num_rows}")
    print(f"Original size: {len(buffer) / 1e6:.2f} MB")
    print(f"Compressed size: {len(compressed) / 1e6:.2f} MB")
    print(f"Compression ratio: {len(buffer) / len(compressed):.2f}x")
    print(f"Percentage: {len(compressed) / len(buffer) * 100:.1f}%")

    # --- Verify data integrity ---
    print("\n--- Data Integrity Check ---")
    decompressed = gzip.decompress(compressed)

    # Read header
    magic, version, num_rows_read, timestamp_read = struct.unpack('<4sBIQ', decompressed[:17])
    print(f"Magic: {magic}, Version: {version}, Rows: {num_rows_read}, Timestamp: {timestamp_read}")

    # Read first few rows and verify
    offset = 17
    print("\nFirst 3 rows verification:")
    for i in range(min(3, num_rows)):
        row_bytes = decompressed[offset:offset + 24]
        delta_t, p_bid, p_ask, s_bid, s_ask = struct.unpack('<qiiii', row_bytes)

        original_time = df['time'].iloc[i]
        original_price_bid = df['bid_px_00'].iloc[i]
        original_price_ask = df['ask_px_00'].iloc[i]
        original_size_bid = df['bid_sz_00'].iloc[i]
        original_size_ask = df['ask_sz_00'].iloc[i]

        decoded_price_bid = p_bid / PRICE_SCALE
        decoded_price_ask = p_ask / PRICE_SCALE
        decoded_size_bid = s_bid / SIZE_SCALE
        decoded_size_ask = s_ask / SIZE_SCALE

        print(f"\nRow {i}:")
        print(f"  Time: {original_time}")
        print(f"  Price Bid: {original_price_bid:.2f} -> {decoded_price_bid:.2f} ✓" if abs(
            original_price_bid - decoded_price_bid) < 0.01 else f"  Price Bid: {original_price_bid:.2f} -> {decoded_price_bid:.2f} ✗")
        print(f"  Price Ask: {original_price_ask:.2f} -> {decoded_price_ask:.2f} ✓" if abs(
            original_price_ask - decoded_price_ask) < 0.01 else f"  Price Ask: {original_price_ask:.2f} -> {decoded_price_ask:.2f} ✗")
        print(f"  Size Bid: {original_size_bid:.1f} -> {decoded_size_bid:.1f} ✓" if abs(
            original_size_bid - decoded_size_bid) < 0.1 else f"  Size Bid: {original_size_bid:.1f} -> {decoded_size_bid:.1f} ✗")
        print(f"  Size Ask: {original_size_ask:.1f} -> {decoded_size_ask:.1f} ✓" if abs(
            original_size_ask - decoded_size_ask) < 0.1 else f"  Size Ask: {original_size_ask:.1f} -> {decoded_size_ask:.1f} ✗")

        offset += 24