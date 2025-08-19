##created and tested by ER. Ajay Bhattarai
'''This code converts the decimal degree latitude and longitude into the UTM coordinates EASTING AND NORTHING'''

import pandas as pd
import utm
import os

# Set file paths
input_path = r"C:\Users\ajayb\OneDrive - Tribhuvan University\Desktop\degree.csv"
output_path = r"C:\Users\ajayb\OneDrive - Tribhuvan University\Desktop\utm.csv"

# Load the CSV file
df = pd.read_csv(input_path)

# Check required columns
if 'latitude' not in df.columns or 'longitude' not in df.columns:
    raise ValueError("CSV must have 'latitude' and 'longitude' columns")

# Convert each latitude & longitude to UTM (Zone 44R)
df[['Easting', 'Northing', 'Zone Number', 'Zone Letter']] = df.apply(
    lambda row: pd.Series(utm.from_latlon(row['latitude'], row['longitude'])),
    axis=1
)

# Save to new CSV
df.to_csv(output_path, index=False)

print("Conversion complete. Saved to:", output_path)
