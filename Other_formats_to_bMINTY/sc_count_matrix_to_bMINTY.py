
# %%
import argparse
import os
import sys
import numpy as np
import re
import pandas as pd
import json
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(
        prog="bMINTY format",
        description="Process the count matrix and optionally metadata and biotype information for scRNA-seq data to transform them to bMINTY format"
    )

    parser.add_argument(
        "path",
        help="Path to json file",
        type=str
    )

    args = parser.parse_args()

    with open(args.path) as f:
        config = json.load(f)


    out_dir = config["output_directory"]
    os.makedirs(out_dir, exist_ok=True)
    # assay_id = config.get("assay", {}).get("assay_id", 1)
    assay_id = config.get("assay_id",1)

    try:
        path_matrix = config["count_matrix"]["count_matrix_file"]
    except KeyError as e:
        raise KeyError(f"Something is wrong with your count matrix")
    
    print("Running...")
    matrix = pd.read_csv(path_matrix, compression="gzip", index_col=0)
    cell_id_source =config["count_matrix"]['cell_id_source']

    if cell_id_source == "columns":
        cell_names = matrix.columns.astype(str)
        gene_keys = matrix.index.astype(str)
    else:
        cell_names = matrix.index.astype(str)
        gene_keys = matrix.columns.astype(str)

    if gene_keys.str.startswith("ENSG").all():
        genes_in_matrix = "ensembl_id"
    else:
        genes_in_matrix = "gene_symbol"

    path_metadata = config["metadata"]["metadata_file"]
    labels = np.full(len(cell_names), np.nan)

    if path_metadata and os.path.exists(path_metadata):
        metadata = pd.read_csv(path_metadata, index_col=0 ,sep = ",")
        labels = metadata.reindex(cell_names)["cell_type"].values

    cell_df = pd.DataFrame({
        "id" :range(1, len(cell_names) + 1),
        "name": cell_names, 
        "type": 'cell',
        "label": labels,
        "x_coordinate": np.nan,
        "y_coordinate": np.nan,
        "z_coordinate":np.nan,
        "assay_id": 1
        })
    cell_df.to_csv(os.path.join(out_dir, "cell.csv"), index=False, sep=",")

    interval_df = pd.DataFrame({  
            "id": range(1, len(gene_keys) + 1),
            "external_id": gene_keys if genes_in_matrix == "ensembl_id" else np.nan,
            "parental_id": np.nan,
            "name": gene_keys if genes_in_matrix == "gene_symbol" else np.nan,
            "type": "gene" ,
            "biotype": np.nan,
            "chromosome": np.nan,
            "start": np.nan,
            "end": np.nan,
            "strand": np.nan,
            "summit": np.nan,
            "assembly_id": 1
        }) 

    meta_dict = config.get("metadata")
    # gm = config.get("gene_mapping")
    # if gm and gm.get("file") and Path(gm["file"]).exists():
    #     gene_annotation=pd.read_csv(gm["file"])
    #     if genes_in_matrix == "gene_symbol":
    #         interval_df["external_id"]=interval_df["name"].map(gene_annotation.set_index('gene_symbol')['ensembl_id'])
    #     else:
    #         interval_df["name"]=interval_df["external_id"].map(gene_annotation.set_index('ensembl_id')['gene_symbol'])

    
    if meta_dict.get("gene_mapping_file") and Path(meta_dict["gene_mapping_file"]).exists():
        gene_annotation=pd.read_csv(meta_dict["gene_mapping_file"])
        if genes_in_matrix == "gene_symbol":
            interval_df["external_id"]=interval_df["name"].map(gene_annotation.set_index('gene_symbol')['ensembl_id'])
        else:
            interval_df["name"]=interval_df["external_id"].map(gene_annotation.set_index('ensembl_id')['gene_symbol'])


    # ga = config.get("biotypes")
    # gtf_file = None
    # if ga and ga.get("file"):
    #     type_file = os.path.splitext(ga["file"])[1].lower().lstrip(".")
    #     if type_file == "gtf" and Path(ga["file"]).exists():
    #         gtf_file = ga["file"]

    gtf_file = None
    if meta_dict.get("biotype_file"):
        type_file = os.path.splitext(meta_dict["biotype_file"])[1].lower().lstrip(".")
        if type_file == "gtf" and Path(meta_dict["biotype_file"]).exists():
            gtf_file = meta_dict["biotype_file"]

    if gtf_file:
        records = []
        with open(gtf_file, "rt") as gtf:
            for line in gtf:
                if line.startswith("#"):
                    continue
                fields = line.strip().split("\t") 
                if len(fields) < 9:
                    continue
                if fields[2] != "gene":
                    continue
                chrom = fields[0]
                start = int(fields[3])
                end = int(fields[4])
                strand = fields[6]  
                attrs = fields[8]
                gene_id_match = re.search(r'gene_id "([^"]+)"', attrs) #ensembl id
                gene_name_match = re.search(r'gene_name "([^"]+)"', attrs) #gene symbol
                gene_type_match = re.search(r'gene_type "([^"]+)"', attrs) or re.search(r'gene_biotype "([^"]+)"', attrs) #gene_type
                gene_id = gene_id_match.group(1).split(".")[0] if gene_id_match else None
                gene_name = gene_name_match.group(1) if gene_name_match else None
                gene_type = gene_type_match.group(1) if gene_type_match else None
                records.append({"Gene": gene_name, "Ensembl_ID": gene_id, "Gene Type":gene_type,"chromosome": chrom,
                    "start": start,"end": end,"strand": strand})

        gtf_df = pd.DataFrame(records)
        if genes_in_matrix == "gene_symbol":
            gtf_by_name = gtf_df.drop_duplicates(subset=["Gene"]).set_index("Gene")
            gtf_by_name=gtf_by_name[gtf_by_name.index.isin(gene_keys)] 
            interval_df["biotype"] = interval_df["name"].map(gtf_by_name["Gene Type"])
            interval_df["chromosome"] = interval_df["name"].map(gtf_by_name["chromosome"])
            interval_df["start"] = interval_df["name"].map(gtf_by_name["start"])
            interval_df["end"] = interval_df["name"].map(gtf_by_name["end"])
            interval_df["strand"] = interval_df["name"].map(gtf_by_name["strand"])
            if (not meta_dict.get("gene_mapping_file")) or (not Path(meta_dict["gene_mapping_file"]).exists()):
                interval_df["external_id"] = interval_df["name"].map(gtf_by_name["Ensembl_ID"])
        else:
            gtf_by_id = gtf_df.drop_duplicates(subset=["Ensembl_ID"]).set_index("Ensembl_ID")
            gtf_by_id=gtf_by_id[gtf_by_id.index.isin(gene_keys)] 
            interval_df["biotype"] = interval_df["external_id"].map(gtf_by_id["Gene Type"])
            interval_df["chromosome"] = interval_df["external_id"].map(gtf_by_id["chromosome"])
            interval_df["start"] = interval_df["external_id"].map(gtf_by_id["start"])
            interval_df["end"] = interval_df["external_id"].map(gtf_by_id["end"]) 
            interval_df["strand"] = interval_df["external_id"].map(gtf_by_id["strand"]) 
            if (not meta_dict.get("gene_mapping_file")) or (not Path(meta_dict["gene_mapping_file"]).exists()):
                interval_df["name"] = interval_df["external_id"].map(gtf_by_id["Gene"])
                    
    else:
        print("no gtf file saving interval without biotypes info") 


    interval_df.to_csv(os.path.join(out_dir, "interval.csv"), sep=",", index=False)

    if cell_id_source == "columns":
        df_reset = matrix.reset_index().rename(columns={"index": "gene_key"})
    else:
        df_reset = matrix.T.reset_index().rename(columns={"index": "gene_key"})

    long_df = df_reset.melt(id_vars="gene_key", var_name="cell_ID", value_name="expression")

    interval_key_col = "external_id" if genes_in_matrix == "ensembl_id" else "name"
    gene_map = interval_df.set_index(interval_key_col)["id"]
    cell_map = cell_df.set_index("name")["id"]

    long_df["interval_id"] = long_df["gene_key"].map(gene_map)
    long_df["cell_id"] = long_df["cell_ID"].astype(str).map(cell_map)

    signal_df = pd.DataFrame({
        "id": range(1, len(long_df) + 1),
        "signal": long_df["expression"],
        "p_value": np.nan,
        "padj_value": np.nan,
        "assay_id": assay_id,
        "interval_id": long_df["interval_id"],
        "cell_id": long_df["cell_id"]
    })
    signal_df.to_csv(os.path.join(out_dir, "signal.csv"), sep=",", index=False)

if __name__ == "__main__":
    main()