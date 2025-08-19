'''In this Code, The Open Elevation API uses SRTM (Shuttle Radar Topography Mission) data, specifically:

SRTM 30m resolution for most of the world
SRTM 90m resolution in some areas

GPS Visualizer likely uses a different DEM source or combination of sources, which could include:

ASTER GDEM (30m resolution)
USGS NED (10m resolution for US)
EU-DEM (25m resolution for Europe)
Local high-resolution DEMs'''

import xml.etree.ElementTree as ET
import zipfile
import os
import csv
import math
import urllib.request
import json

def get_elevations_batch_fast(coordinates):
    """
    Get elevations for multiple coordinates using batch API (much faster)
    """
    if not coordinates:
        return coordinates
    
    updated_coordinates = []
    batch_size = 50  # Process 50 coordinates at once
    total = len(coordinates)
    
    print("Fetching elevation data (batch processing)...")
    
    for i in range(0, total, batch_size):
        batch = coordinates[i:i + batch_size]
        batch_coords = []
        
        # Prepare coordinates for batch API
        for name, lat, lon, elev in batch:
            batch_coords.append(f"{lat},{lon}")
        
        # Join coordinates with pipe separator
        locations = "|".join(batch_coords)
        
        try:
            # Use batch API endpoint
            url = f"https://api.open-elevation.com/api/v1/lookup?locations={locations}"
            
            with urllib.request.urlopen(url, timeout=30) as response:
                data = json.loads(response.read().decode())
                
                if 'results' in data and len(data['results']) > 0:
                    # Match elevations back to coordinates
                    for j, (name, lat, lon, elev) in enumerate(batch):
                        if j < len(data['results']):
                            api_elevation = data['results'][j]['elevation']
                            if api_elevation is not None:
                                elev = float(api_elevation)
                        updated_coordinates.append((name, lat, lon, elev))
                else:
                    # If batch fails, keep original coordinates
                    updated_coordinates.extend(batch)
        
        except Exception as e:
            print(f"Batch {i//batch_size + 1} failed, keeping original elevations: {str(e)}")
            # Keep original coordinates if API fails
            updated_coordinates.extend(batch)
        
        # Show progress
        processed = min(i + batch_size, total)
        print(f"Processed {processed}/{total} coordinates...")
    
    return updated_coordinates

def dd_to_utm(lat, lon):
    """
    Convert decimal degrees to UTM coordinates
    Returns UTM zone, easting, northing
    """
    # Calculate UTM zone
    zone = int((lon + 180) / 6) + 1
    
    # Convert to radians
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    
    # UTM parameters
    k0 = 0.9996  # scale factor
    E0 = 500000  # false easting
    N0 = 0 if lat >= 0 else 10000000  # false northing
    
    # WGS84 ellipsoid parameters
    a = 6378137.0  # semi-major axis
    f = 1/298.257223563  # flattening
    e2 = 2*f - f*f  # eccentricity squared
    
    # Central meridian
    lon0_rad = math.radians((zone - 1) * 6 - 180 + 3)
    
    # Calculate UTM coordinates
    N = a / math.sqrt(1 - e2 * math.sin(lat_rad)**2)
    T = math.tan(lat_rad)**2
    C = e2 * math.cos(lat_rad)**2 / (1 - e2)
    A = math.cos(lat_rad) * (lon_rad - lon0_rad)
    
    M = a * ((1 - e2/4 - 3*e2**2/64 - 5*e2**3/256) * lat_rad -
             (3*e2/8 + 3*e2**2/32 + 45*e2**3/1024) * math.sin(2*lat_rad) +
             (15*e2**2/256 + 45*e2**3/1024) * math.sin(4*lat_rad) -
             (35*e2**3/3072) * math.sin(6*lat_rad))
    
    easting = k0 * N * (A + (1-T+C)*A**3/6 + (5-18*T+T**2+72*C-58*e2)*A**5/120) + E0
    northing = k0 * (M + N*math.tan(lat_rad)*(A**2/2 + (5-T+9*C+4*C**2)*A**4/24 + (61-58*T+T**2+600*C-330*e2)*A**6/720)) + N0
    
    hemisphere = 'N' if lat >= 0 else 'S'
    
    return f"{zone}{hemisphere}", round(easting, 2), round(northing, 2)

def extract_coordinates_from_kml(kml_content):
    """
    Extract coordinates from KML content (Points, LineStrings, Polygons)
    """
    coordinates = []
    
    try:
        root = ET.fromstring(kml_content)
        
        # Handle KML namespaces
        namespaces = {'kml': 'http://www.opengis.net/kml/2.2'}
        
        # Find all Placemark elements
        for placemark in root.findall('.//kml:Placemark', namespaces):
            name = ""
            name_elem = placemark.find('.//kml:name', namespaces)
            if name_elem is not None and name_elem.text:
                name = name_elem.text.strip()
            
            # Find Point coordinates
            point = placemark.find('.//kml:Point', namespaces)
            if point is not None:
                coord_elem = point.find('.//kml:coordinates', namespaces)
                if coord_elem is not None and coord_elem.text:
                    coord_text = coord_elem.text.strip()
                    parts = coord_text.split(',')
                    if len(parts) >= 2:
                        try:
                            lon = float(parts[0])
                            lat = float(parts[1])
                            elev = float(parts[2]) if len(parts) > 2 else 0.0
                            coordinates.append((name, lat, lon, elev))
                        except ValueError:
                            continue
            
            # Find LineString coordinates (paths)
            linestring = placemark.find('.//kml:LineString', namespaces)
            if linestring is not None:
                coord_elem = linestring.find('.//kml:coordinates', namespaces)
                if coord_elem is not None and coord_elem.text:
                    coord_text = coord_elem.text.strip()
                    # Split by whitespace or newlines to get individual coordinate sets
                    coord_sets = coord_text.replace('\n', ' ').replace('\t', ' ').split()
                    for i, coord_set in enumerate(coord_sets):
                        if coord_set.strip():
                            parts = coord_set.strip().split(',')
                            if len(parts) >= 2:
                                try:
                                    lon = float(parts[0])
                                    lat = float(parts[1])
                                    elev = float(parts[2]) if len(parts) > 2 else 0.0
                                    point_name = f"{name}_Point_{i+1}" if name else f"LineString_Point_{i+1}"
                                    coordinates.append((point_name, lat, lon, elev))
                                except ValueError:
                                    continue
            
            # Find Polygon coordinates
            polygon = placemark.find('.//kml:Polygon', namespaces)
            if polygon is not None:
                # Check outer boundary
                outer_boundary = polygon.find('.//kml:outerBoundaryIs/kml:LinearRing', namespaces)
                if outer_boundary is not None:
                    coord_elem = outer_boundary.find('.//kml:coordinates', namespaces)
                    if coord_elem is not None and coord_elem.text:
                        coord_text = coord_elem.text.strip()
                        coord_sets = coord_text.replace('\n', ' ').replace('\t', ' ').split()
                        for i, coord_set in enumerate(coord_sets):
                            if coord_set.strip():
                                parts = coord_set.strip().split(',')
                                if len(parts) >= 2:
                                    try:
                                        lon = float(parts[0])
                                        lat = float(parts[1])
                                        elev = float(parts[2]) if len(parts) > 2 else 0.0
                                        point_name = f"{name}_Point_{i+1}" if name else f"Polygon_Point_{i+1}"
                                        coordinates.append((point_name, lat, lon, elev))
                                    except ValueError:
                                        continue
    
    except ET.ParseError as e:
        print(f"Error parsing KML: {e}")
    
    return coordinates

def process_file(file_path):
    """
    Process KML or KMZ file and extract coordinates
    """
    coordinates = []
    
    if file_path.lower().endswith('.kmz'):
        # Extract KML from KMZ (ZIP) file
        try:
            with zipfile.ZipFile(file_path, 'r') as kmz:
                for file_name in kmz.namelist():
                    if file_name.lower().endswith('.kml'):
                        with kmz.open(file_name) as kml_file:
                            kml_content = kml_file.read().decode('utf-8')
                            coordinates.extend(extract_coordinates_from_kml(kml_content))
                        break
        except zipfile.BadZipFile:
            print("Error: Invalid KMZ file")
            return []
    
    elif file_path.lower().endswith('.kml'):
        # Read KML file directly
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                kml_content = file.read()
                coordinates = extract_coordinates_from_kml(kml_content)
        except FileNotFoundError:
            print("Error: File not found")
            return []
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='latin-1') as file:
                    kml_content = file.read()
                    coordinates = extract_coordinates_from_kml(kml_content)
            except Exception as e:
                print(f"Error reading file: {e}")
                return []
    
    else:
        print("Error: File must be .kml or .kmz")
        return []
    
    return coordinates

def save_to_csv(coordinates, output_path):
    """
    Save coordinates to CSV file
    """
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow(['Name', 'Latitude', 'Longitude', 'Elevation', 'UTM_Zone', 'UTM_Easting', 'UTM_Northing'])
            
            # Write data
            for name, lat, lon, elev in coordinates:
                utm_zone, easting, northing = dd_to_utm(lat, lon)
                writer.writerow([name, lat, lon, elev, utm_zone, easting, northing])
        
        print(f"CSV file saved: {output_path}")
        
    except Exception as e:
        print(f"Error saving CSV: {e}")

def main():
    """
    Main function
    """
    print("KML/KMZ Coordinate Extractor (Fast Version)")
    print("=" * 50)
    
    # Get file path from user
    file_path = input("Enter the full path to your KML/KMZ file (in quotes): ").strip().strip('"\'')
    
    if not os.path.exists(file_path):
        print("Error: File does not exist")
        return
    
    # Process file
    print("Processing file...")
    coordinates = process_file(file_path)
    
    if not coordinates:
        print("No coordinates found in the file")
        return
    
    print(f"Found {len(coordinates)} coordinate points")
    
    # Ask user if they want elevation data
    get_elevation = input("Fetch elevation data from DEM? (y/n, default=y): ").strip().lower()
    if get_elevation != 'n':
        # Get elevations from DEM data (batch processing - much faster)
        coordinates = get_elevations_batch_fast(coordinates)
        print("Elevation data fetching completed!")
    else:
        print("Skipping elevation data fetching")
    
    # Create output CSV path in same directory
    file_dir = os.path.dirname(file_path)
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    output_path = os.path.join(file_dir, f"{file_name}_coordinates.csv")
    
    # Save to CSV
    save_to_csv(coordinates, output_path)
    
    print("Processing completed!")
    print(f"Results saved to: {output_path}")

if __name__ == "__main__":
    main()