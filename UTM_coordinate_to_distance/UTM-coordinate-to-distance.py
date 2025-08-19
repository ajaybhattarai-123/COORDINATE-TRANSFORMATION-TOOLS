### CREATED AND TESTED BY : ER. AJAY BHATTARAI ###
'''
THIS CODE IS USED TO CALCULATE THE DISTANCE USING THE UTM COORDINATES (EASTING, NORTHING in meters)
'''

'''Recheck the code, and verify using the testing data and then only use it'''

import pandas as pd
import numpy as np
import os

# Source file path
source_path = r"C:\Users\ajayb\OneDrive - Tribhuvan University\Desktop\utm.csv"

# Read the CSV file (assumes columns: Easting, Northing in meters)
df = pd.read_csv(source_path)

# Calculate Euclidean distances between consecutive points
distances = [0]  # First point = 0
for i in range(1, len(df)):
    dx = df.loc[i, 'Easting'] - df.loc[i-1, 'Easting']
    dy = df.loc[i, 'Northing'] - df.loc[i-1, 'Northing']
    distance = np.sqrt(dx**2 + dy**2)
    distances.append(distance)

# Add Distance column
df['Distance_m'] = distances

# Create destination folder path
dest_folder = os.path.join(os.path.dirname(source_path), 'd')
os.makedirs(dest_folder, exist_ok=True)

# Destination file path
dest_file = os.path.join(dest_folder, 'output.csv')

# Save to CSV
df.to_csv(dest_file, index=False)

print(f"File saved to: {dest_file}")
