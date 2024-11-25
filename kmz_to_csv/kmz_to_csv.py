from zipfile import ZipFile
from bs4 import BeautifulSoup
import pandas as pd
from pykml import parser
import shutil
import os

# Step 1: Extract KMZ file
def extract_kmz(kmz_path, output_folder='extracted_kml'):
    with ZipFile(kmz_path, 'r') as kmz:
        kmz.extractall(output_folder)
    for file in kmz.namelist():
        if file.endswith('.kml'):
            return f"{output_folder}/{file}"
    raise FileNotFoundError("No KML file found in the KMZ.")


# Step 2: get HTML descriptions from KML
def parse_kml(kml_file_path):
    with open(kml_file_path, 'r') as kml_file:
        k = parser.parse(kml_file).getroot()

    # Look for documents, folders and placeholders
    if hasattr(k, 'Document'):
        document = k.Document
        print("Debug: Found Document tag.")
        
        folders = document.Folder
        print(f"Debug: Found {len(folders)} folder(s)")

        placemarks = []
        for folder in folders:
            for placemark in folder.Placemark:
                placemarks.append(placemark)

        # process placemarks
        if placemarks:
            print(f"Debug: Found {len(placemarks)} placemark(s).")
            return placemarks
        else:
            print("Debug: No placemarks found in folder.")
    else:
        print("Debug: No Document tag found.")
        
    return placemarks

# Step 3.2: create a dictionary form the html 
def parse_html_table(description):
    # Parse the description using BeautifulSoup
    soup = BeautifulSoup(description, 'html.parser')

    table = soup.find('table')
    data = {}
    
    # Iterate over all rows in the table (excluding the header row)
    rows = table.find_all('tr')[1:]
    for row in rows:
        cols = row.find_all('td')
        if len(cols) == 2:  # Ensure the row has key-value pair
            key = cols[0].text.strip()
            value = cols[1].text.strip()
            data[key] = value
    return data


# Step 3.1: go through each description, convert to dict, collect all and change to a pd.df then to csv
def descriptions_to_csv(placemarks):
    all_data = []

    for placemark in placemarks:
        description = placemark.description.text
        data = parse_html_table(description)
        all_data.append(data)
    
    # Convert the list of dictionaries to a pandas DataFrame
    df = pd.DataFrame(all_data)
    df.to_csv('Parcels.csv', index=False)
    print("Descriptions moved to csv")

def kmz_to_csv(kmz_path):
    kml_path = extract_kmz(kmz_path)
    placemarks = parse_kml(kml_path)
    descriptions_to_csv(placemarks)
    temp_dir_name = os.path.dirname(kml_path)
    shutil.rmtree(temp_dir_name)