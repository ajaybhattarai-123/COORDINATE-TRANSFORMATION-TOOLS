import xml.etree.ElementTree as ET
import os

# List of input KML file paths
input_files = [
    r"C:\Users\ajayb\OneDrive - Tribhuvan University\Desktop\4-CSV\KML FOR GIS\D-    Tikapur UG41.csv.kml",
    r"C:\Users\ajayb\OneDrive - Tribhuvan University\Desktop\4-CSV\KML FOR GIS\C-    indicator Data_123.csv.kml",
    r"C:\Users\ajayb\OneDrive - Tribhuvan University\Desktop\4-CSV\KML FOR GIS\B-    GI Co-ordinate.csv.kml",
    r"C:\Users\ajayb\OneDrive - Tribhuvan University\Desktop\4-CSV\KML FOR GIS\A-    Chamber Co-ordinate.kml"
]

# Output path
output_file = r"C:\Users\ajayb\OneDrive - Tribhuvan University\Desktop\4-CSV\KML FOR GIS\mergedkml.kml"

# Define KML namespace
KML_NS = "http://www.opengis.net/kml/2.2"
ET.register_namespace("", KML_NS)

# Create root KML element
kml_root = ET.Element("{%s}kml" % KML_NS)
document = ET.SubElement(kml_root, "{%s}Document" % KML_NS)

# Loop through each file and append its Placemarks (or all contents) to the document
for file_path in input_files:
    tree = ET.parse(file_path)
    root = tree.getroot()

    # Usually <Document> or <Folder> is inside <kml>
    for child in root:
        if child.tag.endswith("Document") or child.tag.endswith("Folder"):
            for elem in child:
                document.append(elem)

# Write the merged KML file
tree = ET.ElementTree(kml_root)
tree.write(output_file, encoding="utf-8", xml_declaration=True)

print(f"Merged KML saved as: {output_file}")
