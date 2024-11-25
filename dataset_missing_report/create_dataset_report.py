import pandas as pd
import os
import geopandas as gpd
from shapely.geometry import Point
import json

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet


def export_to_pdf(data_list, sections):
    # Define data
    title = "Missing Values Report"

    # Create the PDF file
    file_path = "report/condominiums_report.pdf"
    doc = SimpleDocTemplate(file_path, pagesize=letter)

    # Create styles
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    subtitle_style = styles['Heading2']

    # Add title and subtitle as Paragraphs
    title_paragraph = Paragraph(title, title_style)
    
    elements = [title_paragraph, Spacer(1, 12)]
    
    n = 0
    for st in sections:
        subtitle_paragraph = Paragraph(st, subtitle_style)
        elements.append(subtitle_paragraph)
        elements.append(Spacer(1, 12))

        # Create the table
        table = Table(data_list[n], colWidths=[150, 200, 80])  # Adjust column widths as needed
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 12))
        n += 1

    doc.build(elements)
    print(f"PDF saved to {file_path}")


def create_gpkg(df: pd.DataFrame, dataset: str, name:str) -> None:
    os.makedirs('report/shapefiles', exist_ok=True) 
    
    #flatten lat and lng into tuple list
    lat_lngs = list(zip(df['latitude'], df['longitude']))
    gdf = gpd.GeoDataFrame(
        geometry=[Point(lon, lat) for lat, lon in lat_lngs]
    )

    #set CRS
    gdf.set_crs('EPSG:4326', allow_override=True, inplace=True)
    gdf.to_file(f"report/shapefiles/{dataset}.gpkg", layer=name, driver="GPKG")


#takes dataset df and dataset name
#returns dictionary of missing features by percentage
#and creates shapefiles of the missing parcels
def process_missing(df: pd.DataFrame, dataset: str, high_threshold: int, low_threshold: int, create_shp: bool) -> dict:
    perc_missing_dict = {}
    total_count = len(df)

    for feature in df.columns:
        missing_df = df[df[feature].isna()]
        missing_count = len(missing_df)
        percent_missing = round((missing_count/total_count) * 100, 2)
        if missing_count > low_threshold:
            perc_missing_dict[feature] = percent_missing
        
        #create shape
        if low_threshold < percent_missing < high_threshold and create_shp:
            create_gpkg(df, dataset, feature)
            print(f"GPKG created for {dataset} - {feature}")

    sorted_features = sorted(perc_missing_dict.items(), key=lambda x: x[1], reverse=True)
    return sorted_features

#reverses rename and some math transforms in the config to get the original client names
def create_reverse_name_dict(file_path: str) -> dict:
    with open(file_path, "r") as json_file:
        config = json.load(json_file)
    
    rename_dict = {}
    data = config['data']

    for d in data:
        if not 'transform' in data[d]:
            continue
        transform = data[d]['transform'] 
        if 'rename' in transform:
            rename = transform['rename']
            for r in rename:
                rename_dict[rename[r]] = [r, d]
                
        if 'math' in transform:
            maths = transform['math']
            for m in maths:
                if 'values' in maths[m]:
                    values = maths[m]['values']
                    if len(values) == 1 and isinstance(values[0], str):
                        rename_dict[values[0]] = rename_dict.get(values[0], [m, d])
    
    return rename_dict


#run this with the intermediate file as input
def create_missing_features_report(file_path: str, config: str, high_threshold: int, low_threshold: int, create_shp: bool = False) -> None:
    
    os.makedirs('report', exist_ok=True)
    pdf_data_list = []
    
    revserse_name_dict = create_reverse_name_dict(config)
    
    df = pd.read_parquet(file_path)
    dfs = {key: group for key, group in df.groupby('dataset')}

    #adding rows outside of datasets too
    no_dataset = df[df['dataset'].isna()]
    dfs['none'] = no_dataset

    for dataset in dfs.keys():
        print(dataset)
        dataset_specific_list = [["Feature", "Table Name", "Missing"]]
        
        data_list_dict = {}
        
        
        
        print("\nFeatures missing by percent:")
        not_included = []
        perc_missing_dict = process_missing(dfs[dataset], dataset, high_threshold, low_threshold, create_shp) 
        
        for feature, percent in perc_missing_dict:
            if percent >= high_threshold:
                not_included.append(feature)
                continue
            print(f"{feature}: {percent}")
             
            #------------CHANGE THIS BACK TO INCLUDE OUR INERNAL STUFF
            #convert feature name back to client name system if applicable and add to data list
            #feature_name_in_list = revserse_name_dict.get(feature, f"{feature} [X]")
            if feature in revserse_name_dict.keys():
                dataset_specific_list.append([revserse_name_dict[feature][0], revserse_name_dict[feature][1], f"{percent}%"])
        
        pdf_data_list.append(dataset_specific_list)
            
        print("\nFeatures not included in this dataset:")
        for i in not_included:
            print(i)
        print("\n")
    
    #export info to pdf
    export_to_pdf(pdf_data_list, dfs.keys())