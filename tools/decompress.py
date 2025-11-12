import gzip
import struct
from datetime import datetime
import sys
import os
import csv

# --- Parameters ---
# Updated to match new compress.py format
PRICE_SCALE = 100_000  # 5 decimal places precision (updated from 10_000)
SIZE_SCALE = 100  # 2 decimal places precision (updated from 10)
TIME_UNIT = 1_000_000  # µs

# Parse command line arguments
if len(sys.argv) < 3:
    print("Usage: python decompress_test.py <input_file> <output_folder>")
    print("Example: python decompress_test.py ../sessions/CMBM-20251029.bin.gz ../decompressed")
    sys.exit(1)

COMPRESSED_PATH = sys.argv[1]
OUTPUT_FOLDER = sys.argv[2]

# Create output folder if it doesn't exist
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Generate output filename based on input filename
input_filename = os.path.basename(COMPRESSED_PATH)
output_filename = input_filename.replace('.bin.gz', '.csv').replace('.gz', '.csv')
output_path = os.path.join(OUTPUT_FOLDER, output_filename)

print(f"Decompressing: {COMPRESSED_PATH}")
print(f"Output folder: {OUTPUT_FOLDER}")
print(f"Output file: {output_path}\n")

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

# --- Write decompressed data to CSV ---
print("Writing decompressed data to CSV...")

with open(output_path, 'w', newline='') as csvfile:
    csv_writer = csv.writer(csvfile)

    # Write header
    csv_writer.writerow(['Timestamp_us', 'DateTime', 'PriceBid', 'PriceAsk', 'SizeBid', 'SizeAsk'])

    # Write all rows
    for i in range(num_rows):
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

        # Write row to CSV
        csv_writer.writerow([
            absolute_timestamp_us,
            dt.isoformat(),
            f"{price_bid:.5f}",
            f"{price_ask:.5f}",
            f"{size_bid_val:.2f}",
            f"{size_ask_val:.2f}"
        ])

        # Print first 5 rows as preview
        if i < 5:
            if i == 0:
                print("\nFirst 5 rows preview:")
                print(f"{'Timestamp (µs)':<25} {'DateTime':<30} {'PriceBid':<12} {'PriceAsk':<12} {'SizeBid':<10} {'SizeAsk':<10}")
                print("-" * 110)
            print(
                f"{absolute_timestamp_us:<25} {str(dt):<30} {price_bid:<12.5f} {price_ask:<12.5f} {size_bid_val:<10.2f} {size_ask_val:<10.2f}")

print(f"\n✅ Decompression complete!")
print(f"Output saved to: {output_path}")

# --- Stats ---
expected_size = 17 + (num_rows * row_size)
actual_size = len(binary_with_header)
output_file_size = os.path.getsize(output_path)

print(f"\n--- Statistics ---")
print(f"Total rows: {num_rows:,}")
print(f"Expected binary size: {expected_size / 1e6:.2f} MB (decompressed)")
print(f"Actual binary size: {actual_size / 1e6:.2f} MB (decompressed)")
print(f"CSV output size: {output_file_size / 1e6:.2f} MB")
if expected_size == actual_size:
    print("✅ File size matches expected size")
else:
    print(f"⚠️ Size mismatch: {actual_size - expected_size} bytes")