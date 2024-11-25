import pandas as pd
import geopandas as gpd
import glob
import json
import os

from pdf_maker import make_report_pdf

class Create_Report():
    
    def __init__(self, high: int = 100, low: int = 0, additonal_primary: list = [], additional_secondary: list = [], gpkg_path: str = None, gpkg_id: str = None):

        primary_fields = [
            "key_primary",
            "area_land_sqft",
            "area_finished_sqft",
            "sale_date",
            "valid_sale",
            "sale_price",
            "model_customer_value",
            "model_customer_land_value",
            "model_customer_impr_value",
            "building_quality_score",
            "building_quality_desc",
            "building_condition_score",
            "building_condition_desc",
            "neighborhood",
            "school_district",
            "is_residential",
            "zip",
            "building_year_built",
            "building_effective_age_years",
            "city"
        ]

        secondary_fields = [
            "heat_type_desc",
            "area_garage_sqft",
            "garage_style_desc",
            "area_basement_sqft",
            "zoning",
            "district",
            "area_garage_sqft",
            "structure_type",
            "residence_type",
            "rooms_bed",
            "rooms_full_bath",
            "rooms_half_bath"
        ]
        
        self.high = high
        self.low = low
        
        self.primary_fields = primary_fields + additonal_primary
        self.secondary_fields = secondary_fields + additional_secondary
        
        self.gpkg_path = gpkg_path
        self.gpkg_id = gpkg_id
        
        self.config_path = 'config.json'
        
        self.missing_dict = {}
        self.missing_ids_by_feature = {}
        self.feature_hash = {}
        self.rename_dict = self.reverse_name()
        
        self.create_report()
    
    
    def reverse_name(self):

        with open(self.config_path, "r") as json_file:
            config = json.load(json_file)
        
        rename_dict = {}
        data = config['data']
        
        for d in data:
            if not 'transform' in data[d]:
                continue
            transform = data[d]['transform']
            if 'math' in transform:
                maths = transform['math']
                for m in maths:
                    if not 'values' in maths[m]:
                        continue
                    values = maths[m]['values']
                    if not isinstance(values, list):
                        continue
                    for value in values:
                        if not isinstance(value, str):
                            continue
                        rename_dict[value] = m
                        
            if 'rename' in data[d]['transform']:
                rename = data[d]['transform']['rename']
                for r in rename:
                    rename_dict[r] = rename[r]
            
        return rename_dict
            

    def create_gpkg(self) -> None:
        gdf = gpd.read_file(self.gpkg_path)

        #read in attributes at strings
        for col in gdf.columns:
            if col != 'geometry':
                gdf.loc[:, col] = gdf[col].astype(str)
        
        #compare against missing ids to form new gpkg
        for hash in self.missing_ids_by_feature:
            
            feature = self.feature_hash[hash]
            
            id_set = self.missing_ids_by_feature[hash]

            # Filter rows by ID
            filtered_gdf = gdf[gdf[self.gpkg_id].isin(id_set)].copy()
            
            layer_name = f"{feature[0]} - {feature[1]}"
            filtered_gdf.to_file(f"report/missing_values.gpkg", layer=layer_name, driver="GPKG")


    def process_missing(self, df: pd.DataFrame, file_name: str) -> None: 
        total_count = len(df)
        tracked = self.rename_dict.keys()

        for feature in df.columns:
            if feature not in tracked:
                continue
            
            hash = feature + file_name
            
            self.feature_hash[hash] = [feature, file_name]
            
            val = self.rename_dict[feature]
            group = 2
            
            if val in self.primary_fields:
                group = 0
            elif val in self.secondary_fields:
                group = 1
            
            self.missing_dict[hash] = [0, group]
            
            missing_df = df[df[feature].isna()]
            missing_count = len(missing_df)
            percent_missing = round((missing_count/total_count) * 100, 2)
            if self.low < percent_missing < self.high:
                self.missing_dict[hash][0] = percent_missing
                
                #steps to prep data for shapefile output
                if self.gpkg_path and self.gpkg_id:
                    csv_key_arr = []
                    for t in tracked:
                        if self.rename_dict[t] == 'key_primary':
                            csv_key_arr.append(t)
                    
                    if not csv_key_arr:
                        continue
                    
                    csv_key_name = None
                    for ck_name in csv_key_arr:
                        if ck_name in missing_df.columns:
                            csv_key_name = ck_name
                            break
                    
                    id_set = set(missing_df[csv_key_name])

                    if hash in self.missing_ids_by_feature:
                        self.missing_ids_by_feature[hash].update(id_set)
                    else:
                        self.missing_ids_by_feature[hash] = id_set


    def create_report(self) -> None:
        os.makedirs('report', exist_ok=True)
        
        csv_files = glob.glob("csv/*.csv")
        
        for csv in csv_files:
            file_name = csv.replace('csv/', '').replace('.csv', '')
            df = pd.read_csv(csv, dtype=str)
            self.process_missing(df, file_name)
        
        self.missing_dict = dict(sorted(self.missing_dict.items(), key=lambda item: (item[1][1], -item[1][0])))
        
        #get it ready to print and export to pdf
        pdf_ready_list = []
        for hash in self.missing_dict:
            print(self.feature_hash[hash][0], "-", self.feature_hash[hash][1], ":", f'{self.missing_dict[hash][0]}%')
            pdf_row = [self.feature_hash[hash][0], self.feature_hash[hash][1], self.missing_dict[hash][0], self.missing_dict[hash][1]]
            pdf_ready_list.append(pdf_row)
        
        r = make_report_pdf(pdf_ready_list)
        
        if self.gpkg_path and self.gpkg_id:
            self.create_gpkg()