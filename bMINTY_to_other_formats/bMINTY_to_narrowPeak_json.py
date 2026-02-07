import argparse
import json

import pandas as pd

######################################### Program argument parser##################################################
program_description = "Transform ATAC-seq data from bMINTY format to narrowPeak format."

parser = argparse.ArgumentParser(prog="bMINTY_to_narrowPeak.py",
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
output_dir = bminty_input_dict["output_dir"]

print("\nLoad required files")

signal_df = pd.read_csv(bminty_signal_file)
interval_df = pd.read_csv(bminty_interval_file)

print("\nGenerate the narroePeak file")


final_df = signal_df.merge(right=interval_df,
                           left_on="interval_id",
                           right_on="id")

final_df = final_df[["chromosome","start","end","name","strand","signal","p_value","summit"]]

final_df.insert(4,"score",0)
final_df.insert(8,"q_value",-1)

print("\nExport the final narrowPeak file")

final_df.to_csv(f"{output_dir}/output.narrowPeak.gz", sep="\t", header=False, index=False,compression="gzip")

print("\nProcess finished")