import pandas as pd
import os

# Define sample data with mandatory fields + Outstanding (as requested)
data = [
    {"Customer Name": "Amit Electronics", "Outstanding": 15000, "Phone": "9876543210", "Email": "amit@example.com"},
    {"Customer Name": "Balaji Hardwares", "Outstanding": 2500.50, "Phone": "9876543211", "Email": "balaji@example.com"},
    {"Customer Name": "Chandra Enterprises", "Outstanding": 0, "Phone": "9876543212", "Email": "chandra@example.com"},
    {"Customer Name": "Delta Solutions", "Outstanding": 50000, "Phone": "9876543213", "Email": "delta@example.com"},
]

# Create DataFrame
df = pd.DataFrame(data)

# Define output path (Desktop for easy access or Project Root)
# Let's put it in the project root so it's easy to find but not cluttering Desktop
file_path = r"C:\Users\aswin\AvrinaCRM\customer_sample_upload.xlsx"

try:
    df.to_excel(file_path, index=False)
    print(f"SUCCESS: Sample file created at: {file_path}")
except Exception as e:
    print(f"ERROR: Failed to create file: {e}")
