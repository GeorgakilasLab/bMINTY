import json
import argparse

import pandas as pd

######################################### Program argument parser##################################################
program_description = "Transform single cell RNA-seq data from bMINTY format to count matrix format."

parser = argparse.ArgumentParser(prog="bMINTY_to_sc_count_matrix.py",
                                 description=program_description)

parser.add_argument("bminty_input_json_file",
                    help="Path to the bminty input json file",
                    type=str)

args = parser.parse_args()

bminty_input_json_file = args.bminty_input_json_file

#################################################### Generate the files #########################################
print("\nLoad input json file")

with open(bminty_input_json_file,"r") as IN:
    bminty_input_dict = json.load(IN)

bminty_signal_file = bminty_input_dict["bminty_signal_file"]
bminty_interval_file = bminty_input_dict["bminty_interval_file"]
bminty_cell_file = bminty_input_dict["bminty_cell_file"]
gene_ident = bminty_input_dict["gene_ident"]
output_dir = bminty_input_dict["output_dir"]

print("\nLoad required files")

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

aux_cell_df = cell_df[["id","name"]]
aux_cell_df.set_index("id",inplace=True)
aux_cell_df.index.name = None
cell_name_to_cell_id_dict = aux_cell_df.to_dict()
cell_name_to_cell_id_dict = cell_name_to_cell_id_dict["name"]

del(aux_cell_df)

signal_df["interval_id"] = signal_df["interval_id"].map(id_to_external_id_dict)
signal_df["cell_id"] = signal_df["cell_id"].map(cell_name_to_cell_id_dict)

sc_count_matrix_df = signal_df.pivot_table(index="interval_id",
                                           columns="cell_id",
                                           values="signal")

sc_count_matrix_df.columns.name=None
sc_count_matrix_df.index.name=None
sc_count_matrix_df.fillna(0,inplace=True)
sc_count_matrix_df = sc_count_matrix_df.astype(int)

print("\nExport the final count matrix.")
sc_count_matrix_df.to_csv(f"{output_dir}/sc_count_matrix.csv.gz",compression="gzip")

print("\nProcess finished")
