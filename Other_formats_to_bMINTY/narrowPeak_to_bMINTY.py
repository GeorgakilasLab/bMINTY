import sys
import os
import argparse
import json

import pandas as pd

def parse_args():
    parser = argparse.ArgumentParser(description="Convert narrowPeak/IDR files to bMINTY")
    parser.add_argument("config_file", help="Path to the json config file.")
    return parser.parse_args()

def main():
    args = parse_args()
    input_json_file = args.config_file

    with open(input_json_file,"r") as IN:
        input_dict = json.load(IN)

    input_file = input_dict["input_file"]
    interval_type = input_dict["type"]
    output_dir = input_dict["output_dir"]

    try:
        df = pd.read_csv(input_file, sep='\t', header=None, comment='#', usecols=range(10), names=[
            'chrom', 'start', 'end', 'name', 'score', 'strand', 
            'signal', 'p_val', 'q_val', 'summit_offset'
        ])
    except Exception as e:
        sys.exit(f"Error reading file (Ensure it is a valid tab-separated narrowPeak/IDR file): {e}")
    total_rows = len(df)
    row_ids = range(1, total_rows + 1)
    intervals = pd.DataFrame()
    intervals['id'] = row_ids
    is_dot_name = (df['name'] == '.')
    intervals['name'] = df['name']
    intervals.loc[is_dot_name, 'name'] = "peak_" + pd.Series(row_ids).astype(str)
    intervals['external_id'] = intervals['name']
    intervals['parental_id'] = "" 
    intervals['type'] = interval_type
    intervals['biotype'] = "N/A"
    intervals['chromosome'] = df['chrom']
    intervals['start'] = df['start']
    intervals['end'] = df['end']
    intervals['strand'] = df['strand']
    intervals['summit'] = df['summit_offset']
    intervals['assembly_id'] = "N/A"
    intervals_out = intervals[[
        'id', 'external_id', 'parental_id', 'name', 'type', 
        'biotype', 'chromosome', 'start', 'end', 'strand', 
        'summit', 'assembly_id'
    ]]
    signals = pd.DataFrame()
    signals['id'] = row_ids
    signals['signal'] = df['signal']
    signals['p_value'] = df['p_val']
    signals['padj_value'] = df['q_val']
    
    signals['assay_id'] = "N/A"
    signals['interval_id'] = row_ids
    signals['cell_id'] = "N/A"
    signals_out = signals[[
        'id', 'signal', 'p_value', 'padj_value', 
        'assay_id', 'interval_id', 'cell_id'
    ]]
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    path_intervals = os.path.join(output_dir, f"{base_name}_intervals.csv")
    path_signals = os.path.join(output_dir, f"{base_name}_signals.csv")
    intervals_out.to_csv(path_intervals, index=False)
    signals_out.to_csv(path_signals, index=False)

if __name__ == "__main__":
    main()