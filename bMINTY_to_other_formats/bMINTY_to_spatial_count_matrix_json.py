import json
import argparse

import pandas  as pd

######################################### Program argument parser##################################################
program_description = "Transform spatial scRNA-seq data from bMINTY format to spatial count matrix format."

parser = argparse.ArgumentParser(prog="bMINTY_to_spatial_count_matrix.py",
                                 description=program_description)

parser.add_argument("bminty_input_json_file",
                    help="Path to the bminty input json file",
                    type=str)

args = parser.parse_args()

bminty_input_json_file = args.bminty_input_json_file

print("\nLoad required files")

print("\nLoad input json file")

with open(bminty_input_json_file,"r") as IN:
    bminty_input_dict = json.load(IN)

bminty_signal_file = bminty_input_dict["bminty_signal_file"]
bminty_interval_file = bminty_input_dict["bminty_interval_file"]
bminty_cell_file = bminty_input_dict["bminty_cell_file"]
gene_ident = bminty_input_dict["gene_ident"]
output_dir = bminty_input_dict["output_dir"]

signal_df = pd.read_csv(bminty_signal_file)
interval_df = pd.read_csv(bminty_interval_file)
cell_df = pd.read_csv(bminty_cell_file)

aux_interval_df = interval_df.loc[:,["id","external_id","name"]].set_index("id")
aux_interval_df.index.name = None

id_to_external_id_dict = dict()

for id,ser in aux_interval_df.iterrows():
    external_id = ser.external_id
    name = ser.loc["name"]

    if gene_ident == "ensgid" and external_id != "unknown":
        id_to_external_id_dict[id] = external_id
    elif gene_ident == "ensgid" and external_id == "unknown":
        id_to_external_id_dict[id] = name
    else:
        id_to_external_id_dict[id] = name

del(aux_interval_df)

print("\nGenerate the count matrix")

cell_meta = cell_df.loc[:,["id","name"]].copy()
cell_meta[["cell", "fov"]] = cell_df["name"].str.split("_", expand=True)
cell_meta.drop("name",inplace=True,axis=1)

external_signal_df = signal_df.copy()
external_signal_df["interval_id"] = external_signal_df["interval_id"].map(id_to_external_id_dict)
external_signal_df = external_signal_df.loc[:,["id","cell_id","interval_id","signal"]]

merged = external_signal_df.merge(cell_meta[["id", "cell", "fov"]],
                                  left_on="cell_id",
                                  right_on="id",
                                  how="left")

spatial_expression_df = merged.pivot_table(index=["cell", "fov"],
                                           columns="interval_id",
                                           values="signal").reset_index()

spatial_expression_df.fillna(0,inplace=True)
spatial_expression_df = spatial_expression_df.astype(int)
spatial_expression_df.sort_values(["fov","cell"],inplace=True)
spatial_expression_df.index.name = None
spatial_expression_df.reset_index(inplace=True)
spatial_expression_df.drop("index",axis=1,inplace=True)

print("\nExport the final count matrix.")
spatial_expression_df.to_csv(f"{output_dir}/spatial_count_matrix.csv.gz",compression="gzip")

print("\nProcess finished")
