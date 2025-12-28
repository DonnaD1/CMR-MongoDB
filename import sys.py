import sys
from asammdf import MDF
import pandas as pd
import numpy as np

#MDF to CSV 

if len(sys.argv) < 2:
    print("Usage: python export_channels.py <mdf_file>")
    sys.exit(1)

mdf_file = sys.argv[1]

try:
    mdf = MDF(mdf_file)
except Exception as e:
    print(f"[ERROR] Failed to open MDF file '{mdf_file}': {e}")
    sys.exit(1)

channels_to_export = [
    'Movella_AccY', 'Movella_AccX', 'Movella_VelX',
    'RR_Calibrated_Output', 'RL_Calibrated_Output',
    'FR_Calibrated_Output', 'FL_Calibrated_Output'
]

try:
    ref_signal = mdf.get('Movella_VelX')
except KeyError:
    print("[ERROR] Reference channel 'Movella_VelX' not found in MDF file.")
    sys.exit(1)

ref_time = ref_signal.timestamps
data = {'Time': ref_time, 'Movella_VelX': ref_signal.samples}

for ch in channels_to_export:
    if ch == 'Movella_VelX': 
        continue
    try:
        sig = mdf.get(ch)
        if len(sig.samples) == 0 or len(sig.timestamps) == 0:
            print(f"[WARNING] Channel '{ch}' has no data. Skipping.")
            continue
        interp_vals = np.interp(ref_time, sig.timestamps, sig.samples)
        data[ch] = interp_vals
    except KeyError:
        print(f"[WARNING] Channel '{ch}' not found in MDF file. Skipping.")

# Create DataFrame and export to CSV
output_file = "output_filtered_hybrid1.csv"
df = pd.DataFrame(data)
df.to_csv(output_file, index=False)
print(f"[INFO] Export complete. Saved to '{output_file}'")

import os 
from pymongo import MongoClient 
from datetime import datetime

#Load to MongoDB + organize by year, month, and date 
if len(df)!=len(ref_time):
    sys.exit(1)

if not np.allclose(df["Time"].values, ref_time):
    sys.exit(1)

mdf_name=os.path.basename(mdf_file)

dt=None
pattern=[
    "%y-%m-%d_%H-%M-%S"
]

for fmt in pattern:
    try:
        dt=datetime.strptime(
            mdf_name.replace("logfile_", "").replace(".mdf", ""),
            fmt
        )
        break
    except ValueError:
        pass

if dt is None:
    sys.exit(1)

year=dt.year
month=dt.month
day=dt.day

#Need to add MongoDB server (is local use "mongodb://localhost:27017/")
client=MongoClient()
db=client["car_data"]
collection=db["mdf_files"]

records=df.to_dict(orient="records")

existing=collection.find_one({
    "file_name": mdf_name,
    "year": year,
    "month": month,
    "day": day
})

if existing:
    print("[INFO] This file already exists in MongoDB. Skipping load")
    sys.exit(0)

document={
    "file_name": mdf_name,
    "year": year,
    "month": month,
    "day": day,
    "signals": records
}

collection.insert_one(document)
print("File successfully loaded into MongoDB")

collection.create_index([("year", 1), ("month", 1), ("day", 1)])
collection.create_index("file_name")