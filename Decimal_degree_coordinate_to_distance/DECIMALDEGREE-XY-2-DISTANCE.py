### CREATED AND TESTED BY : ER. AJAY BHATTARAI ###
'''
THIS CODE IS USED TO CALCULATE THE DISTANCE USING THE DECIMAL DEGREE LATITUDE AND LOGITUDE
'''
import pandas as pd
import numpy as np
import os

# Source file path
source_path = r"C:\Users\ajayb\OneDrive - Tribhuvan University\Desktop\degree.csv"

# Read the CSV file (assumes columns: Latitude, Longitude in decimal degrees)
df = pd.read_csv(source_path)

# Earth radius in meters
R = 6371000  

# Function to compute Haversine distance
def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2.0)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

# Calculate distances
distances = [0]  # First point = 0
for i in range(1, len(df)):
    distance = haversine(df.loc[i-1, 'Latitude'], df.loc[i-1, 'Longitude'],
                         df.loc[i, 'Latitude'], df.loc[i, 'Longitude'])
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
