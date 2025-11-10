import gzip
import struct
from datetime import datetime
import sys

# --- Parameters ---
# Updated to match new compress.py format
PRICE_SCALE = 100_000  # 5 decimal places precision (updated from 10_000)
SIZE_SCALE = 100  # 2 decimal places precision (updated from 10)
TIME_UNIT = 1_000_000  # µs

# Allow path as command line argument
if len(sys.argv) > 1:
    COMPRESSED_PATH = sys.argv[1]
else:
    # Default to sessions folder
    COMPRESSED_PATH = "../sessions/CMBM-20251029.bin.gz"

print(f"Decompressing: {COMPRESSED_PATH}\n")

# --- Decompression ---
with gzip.open(COMPRESSED_PATH, 'rb') as f:
    binary_with_header = f.read()

# --- Read header (17 bytes) ---
# Magic number (4 bytes) + Version (1 byte) + Num rows (4 bytes) + Initial timestamp (8 bytes)
offset = 0

# Read magic number
magic = binary_with_header[offset:offset + 4].decode('ascii')
offset += 4

# Read version
version = struct.unpack('<B', binary_with_header[offset:offset + 1])[0]
offset += 1

# Read number of rows
num_rows = struct.unpack('<I', binary_with_header[offset:offset + 4])[0]
offset += 4

# Read initial timestamp (8 bytes)
initial_timestamp_us = struct.unpack('<Q', binary_with_header[offset:offset + 8])[0]
offset += 8

print(f"Magic: {magic}")
print(f"Version: {version}")
print(f"Number of rows: {num_rows:,}")
print(f"Initial timestamp: {initial_timestamp_us} µs")
print(f"Initial datetime: {datetime.fromtimestamp(initial_timestamp_us / TIME_UNIT)}\n")

# --- Read data rows ---
# New format: int64 delta_time_us + int32 price_bid + int32 price_ask + int32 size_bid + int32 size_ask
# Total: 8 + 4 + 4 + 4 + 4 = 24 bytes per row
row_size = 24

print("First 5 rows:")
print(f"{'Timestamp (µs)':<25} {'DateTime':<30} {'PriceBid':<12} {'PriceAsk':<12} {'SizeBid':<10} {'SizeAsk':<10}")
print("-" * 110)

for i in range(min(5, num_rows)):
    row_offset = offset + (i * row_size)

    # Unpack: int64 delta_time_us + 4 × int32
    delta_time_us, price_bid_scaled, price_ask_scaled, size_bid_scaled, size_ask_scaled = struct.unpack(
        '<qiiii',
        binary_with_header[row_offset:row_offset + row_size]
    )

    # Calculate absolute timestamp
    absolute_timestamp_us = initial_timestamp_us + delta_time_us

    # Convert to original values (no cumulative encoding, just scaling)
    price_bid = price_bid_scaled / PRICE_SCALE
    price_ask = price_ask_scaled / PRICE_SCALE
    size_bid_val = size_bid_scaled / SIZE_SCALE
    size_ask_val = size_ask_scaled / SIZE_SCALE

    dt = datetime.fromtimestamp(absolute_timestamp_us / TIME_UNIT)

    print(
        f"{absolute_timestamp_us:<25} {str(dt):<30} {price_bid:<12.5f} {price_ask:<12.5f} {size_bid_val:<10.2f} {size_ask_val:<10.2f}")

# --- Stats ---
expected_size = 17 + (num_rows * row_size)
actual_size = len(binary_with_header)
print(f"\nTotal rows: {num_rows:,}")
print(f"Expected size: {expected_size / 1e6:.2f} MB (decompressed)")
print(f"Actual size: {actual_size / 1e6:.2f} MB (decompressed)")
if expected_size == actual_size:
    print("✅ File size matches expected size")
else:
    print(f"⚠️ Size mismatch: {actual_size - expected_size} bytes")