import os
import zipfile
import xml.etree.ElementTree as ET
import struct
import tempfile
import shutil

class SimpleKMLToShapefile:
    def __init__(self):
        self.shapes = []
        self.records = []
    
    def extract_kmz(self, kmz_path):
        """Extract KMZ and return KML content"""
        temp_dir = tempfile.mkdtemp()
        try:
            with zipfile.ZipFile(kmz_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Find KML file
            for file in os.listdir(temp_dir):
                if file.endswith('.kml'):
                    with open(os.path.join(temp_dir, file), 'r', encoding='utf-8') as f:
                        return f.read()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
        return None
    
    def parse_coordinates(self, coord_text):
        """Parse Google Earth polygon coordinates"""
        if not coord_text:
            return []
        
        coords = []
        coord_text = coord_text.strip()
        
        # Handle different coordinate formats
        # Split by newlines first, then by spaces
        lines = coord_text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Split by spaces or tabs
            parts = line.replace('\t', ' ').split(' ')
            
            for part in parts:
                part = part.strip()
                if not part or ',' not in part:
                    continue
                    
                try:
                    # Split longitude,latitude,altitude
                    coord_parts = part.split(',')
                    if len(coord_parts) >= 2:
                        lon = float(coord_parts[0])
                        lat = float(coord_parts[1])
                        # Basic validation for reasonable coordinates
                        if -180 <= lon <= 180 and -90 <= lat <= 90:
                            coords.append([lon, lat])
                except (ValueError, IndexError):
                    continue
        
        return coords
    
    def parse_kml(self, kml_content):
        """Parse KML content for polygons"""
        try:
            root = ET.fromstring(kml_content)
        except Exception as e:
            print(f"XML parsing error: {e}")
            return False
        
        # Find all Placemarks with Polygons - using simple iteration
        for elem in root.iter():
            if 'Placemark' in elem.tag:
                name = ""
                description = ""
                coordinates = []
                
                # Get name - search within this placemark
                for child in elem.iter():
                    if 'name' in child.tag and child.text:
                        name = child.text[:50]
                        break
                
                # Get description - search within this placemark  
                for child in elem.iter():
                    if 'description' in child.tag and child.text:
                        description = child.text[:100]
                        break
                
                # Get polygon coordinates - look for coordinates tag
                for child in elem.iter():
                    if 'coordinates' in child.tag and child.text:
                        # Check if this is within a Polygon
                        parent = child
                        is_polygon = False
                        for _ in range(5):  # Check up to 5 levels up
                            if parent is None:
                                break
                            if 'Polygon' in parent.tag:
                                is_polygon = True
                                break
                            parent = elem.find('.//' + parent.tag + '/..')
                            if parent is None:
                                # Alternative check - look for polygon-related tags
                                coord_text = child.text.strip()
                                if '\n' in coord_text or len(coord_text.split()) > 10:
                                    is_polygon = True
                                break
                        
                        if is_polygon:
                            coordinates = self.parse_coordinates(child.text)
                            break
                
                if coordinates and len(coordinates) >= 3:
                    # Ensure polygon is closed
                    if coordinates[0] != coordinates[-1]:
                        coordinates.append(coordinates[0])
                    
                    self.shapes.append(coordinates)
                    self.records.append({
                        'name': name or f'Polygon_{len(self.shapes) + 1}',
                        'description': description
                    })
        
        return len(self.shapes) > 0
    
    def write_shp(self, filename):
        """Write SHP file"""
        with open(filename, 'wb') as f:
            # File header
            f.write(struct.pack('>I', 9994))  # File code
            f.write(b'\x00' * 20)  # Unused
            
            file_length = 50  # Header length
            for shape in self.shapes:
                file_length += 4 + 44 + len(shape) * 16  # Record header + shape
            
            f.write(struct.pack('>I', file_length))  # File length
            f.write(struct.pack('<I', 1000))  # Version
            f.write(struct.pack('<I', 5))  # Shape type (Polygon)
            
            # Bounding box
            if self.shapes:
                all_coords = [coord for shape in self.shapes for coord in shape]
                min_x = min(coord[0] for coord in all_coords)
                min_y = min(coord[1] for coord in all_coords)
                max_x = max(coord[0] for coord in all_coords)
                max_y = max(coord[1] for coord in all_coords)
            else:
                min_x = min_y = max_x = max_y = 0
            
            f.write(struct.pack('<d', min_x))
            f.write(struct.pack('<d', min_y))
            f.write(struct.pack('<d', max_x))
            f.write(struct.pack('<d', max_y))
            f.write(struct.pack('<d', 0))  # Z min
            f.write(struct.pack('<d', 0))  # Z max
            f.write(struct.pack('<d', 0))  # M min
            f.write(struct.pack('<d', 0))  # M max
            
            # Records
            for i, shape in enumerate(self.shapes):
                record_length = 44 + len(shape) * 16
                f.write(struct.pack('>I', i + 1))  # Record number
                f.write(struct.pack('>I', record_length // 2))  # Content length
                
                # Shape
                f.write(struct.pack('<I', 5))  # Shape type (Polygon)
                
                # Bounding box
                min_x = min(coord[0] for coord in shape)
                min_y = min(coord[1] for coord in shape)
                max_x = max(coord[0] for coord in shape)
                max_y = max(coord[1] for coord in shape)
                
                f.write(struct.pack('<d', min_x))
                f.write(struct.pack('<d', min_y))
                f.write(struct.pack('<d', max_x))
                f.write(struct.pack('<d', max_y))
                
                f.write(struct.pack('<I', 1))  # Number of parts
                f.write(struct.pack('<I', len(shape)))  # Number of points
                f.write(struct.pack('<I', 0))  # Part start index
                
                # Points
                for coord in shape:
                    f.write(struct.pack('<d', coord[0]))
                    f.write(struct.pack('<d', coord[1]))
    
    def write_shx(self, filename):
        """Write SHX index file"""
        with open(filename, 'wb') as f:
            # Header (same as SHP)
            f.write(struct.pack('>I', 9994))
            f.write(b'\x00' * 20)
            
            file_length = 50 + len(self.shapes) * 4
            f.write(struct.pack('>I', file_length))
            f.write(struct.pack('<I', 1000))
            f.write(struct.pack('<I', 5))
            
            # Bounding box (same as SHP)
            if self.shapes:
                all_coords = [coord for shape in self.shapes for coord in shape]
                min_x = min(coord[0] for coord in all_coords)
                min_y = min(coord[1] for coord in all_coords)
                max_x = max(coord[0] for coord in all_coords)
                max_y = max(coord[1] for coord in all_coords)
            else:
                min_x = min_y = max_x = max_y = 0
            
            f.write(struct.pack('<d', min_x))
            f.write(struct.pack('<d', min_y))
            f.write(struct.pack('<d', max_x))
            f.write(struct.pack('<d', max_y))
            f.write(b'\x00' * 32)  # Z and M ranges
            
            # Index records
            offset = 50
            for shape in self.shapes:
                f.write(struct.pack('>I', offset))
                content_length = 44 + len(shape) * 16
                f.write(struct.pack('>I', content_length // 2))
                offset += 4 + content_length
    
    def write_dbf(self, filename):
        """Write DBF attribute file"""
        with open(filename, 'wb') as f:
            # Header
            f.write(struct.pack('<B', 3))  # dBASE III
            f.write(struct.pack('<BBB', 24, 1, 1))  # Date
            f.write(struct.pack('<I', len(self.records)))  # Number of records
            f.write(struct.pack('<H', 193))  # Header length (32 + 2*80 + 1)
            f.write(struct.pack('<H', 151))  # Record length (1 + 50 + 100)
            f.write(b'\x00' * 20)  # Reserved
            
            # Field descriptors
            # Name field
            f.write(b'NAME'.ljust(11, b'\x00'))
            f.write(struct.pack('<c', b'C'))  # Type
            f.write(b'\x00' * 4)  # Address
            f.write(struct.pack('<BB', 50, 0))  # Length, decimals
            f.write(b'\x00' * 14)  # Reserved
            
            # Description field
            f.write(b'DESC'.ljust(11, b'\x00'))
            f.write(struct.pack('<c', b'C'))  # Type
            f.write(b'\x00' * 4)  # Address
            f.write(struct.pack('<BB', 100, 0))  # Length, decimals
            f.write(b'\x00' * 14)  # Reserved
            
            f.write(b'\x0D')  # Header terminator
            
            # Records
            for record in self.records:
                f.write(b' ')  # Deletion flag
                f.write(record['name'][:50].ljust(50, ' ').encode('utf-8', errors='ignore'))
                f.write(record['description'][:100].ljust(100, ' ').encode('utf-8', errors='ignore'))
    
    def write_prj(self, filename):
        """Write PRJ projection file (WGS84)"""
        wgs84 = 'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]]'
        with open(filename, 'w') as f:
            f.write(wgs84)
    
    def convert(self, input_file, output_file):
        """Convert KML/KMZ to Shapefile"""
        # Read input file
        if input_file.lower().endswith('.kmz'):
            kml_content = self.extract_kmz(input_file)
            if not kml_content:
                raise Exception("Could not extract KML from KMZ file")
        else:
            with open(input_file, 'r', encoding='utf-8') as f:
                kml_content = f.read()
        
        # Parse KML
        if not self.parse_kml(kml_content):
            raise Exception("No polygons found in KML file")
        
        # Create output directory
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Remove extension from output file
        base_name = os.path.splitext(output_file)[0]
        
        # Write shapefile components
        self.write_shp(base_name + '.shp')
        self.write_shx(base_name + '.shx')
        self.write_dbf(base_name + '.dbf')
        self.write_prj(base_name + '.prj')
        
        print(f"Successfully converted {len(self.shapes)} polygons")
        print(f"Created: {base_name}.shp")
        
        return base_name + '.shp'

def convert_kml_to_shapefile(input_file, output_file):
    """Simple function to convert KML/KMZ to Shapefile"""
    converter = SimpleKMLToShapefile()
    return converter.convert(input_file, output_file)

# Example usage
if __name__ == "__main__":
    input_file = input("Enter KML/KMZ file path: ").strip()
    
    # Remove quotes if present
    if input_file.startswith('"') and input_file.endswith('"'):
        input_file = input_file[1:-1]
    elif input_file.startswith("'") and input_file.endswith("'"):
        input_file = input_file[1:-1]
    
    if not input_file:
        print("Please provide a file path")
        exit()
    
    if not os.path.exists(input_file):
        print(f"File not found: {input_file}")
        print("Please check the path and try again.")
        exit()
    
    # Generate output filename
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    output_file = f"{base_name}_converted.shp"
    
    try:
        result = convert_kml_to_shapefile(input_file, output_file)
        print(f"Conversion completed successfully!")
        print(f"Output: {result}")
    except Exception as e:
        print(f"Error: {e}")