# bMINTY to other formats conversion

This readme file lists the conversion scripts from *bMINTY* format to the original data file format with respect to the data generation protocol. Currently three main protocols are supported:

* scRNA-seq:
    
    Transform from bMINTY format to count matrix format.
    
    Script: [`bMINTY_to_sc_count_matrix.py`](#bminty_to_sc_count_matrixpy)


* spatial RNA-seq:
    
    Transform from bMINTY format to spatial count matrix format.

    Script: [`bMINTY_to_spatial_count_matrix.py`](#bminty_to_spatial_count_matrixpy)

* ATAC-seq:

    Transform from bMINTY format to narrowPeak format file.
    
    Script: [`bMINTY_to_narrowPeak.py`](#bminty_to_narrowpeakpy)

## Scripts  

### bMINTY_to_sc_count_matrix.py

The `bMINTY_to_sc_count_matrix.py` converts the bMINTY formatted scRNA-seq stored data to the count matrix format. This format consists of a matrix that has the genes as row labels and the cells as column labels (or the transpose of this configuration). Thus, *(i,j)* element of the matrix is the expression level of the *i-th* gene in the *j-th* cell.

The script usage is:

>bMINTY_to_sc_count_matrix.py [-h] bminty_json_input_file
>
>Transform single cell RNA-seq data from bMINTY format to count matrix format.
>
>positional arguments:
>  
>   bminty_input_json_file:
        Path to the bminty input json file


The script requires the json file `bminty_json_input_file` that acts as a configuration file for the script to run successfully.

```json
{
    "bminty_signal_file": "/path/signal.csv",
    "bminty_interval_file": "/path/interval.csv",
    "bminty_cell_file": "/path/cell.csv",
    "gene_ident": "gene_ident_value",
    "output_dir": "/path/output_dir"
}
```

The json consists of five **mandatory** fields:

1. **"bminty_signal_file"**: Path to the bMINTY signal csv file

2. **"bminty_interval_file"**: Path to the bMINTY interval csv file

3. **"bminty_cell_file"**: Path to the bMINTY cell csv file

4. **"gene_ident"**: Flag that can take "ensgid" or "name" values. Defines whether the genes are labeled after the Ensembl gene ids ("ensgid") or gene names ("name") in the resulting count matrix respectively.

5. **"output_dir"**: Path where the resulting count matrix is stored in

#### Required packages:
- `pandas`

<br>

### bMINTY_to_spatial_count_matrix.py

The `bMINTY_to_spatial_count_matrix.py` converts the bMINTY formatted spatial RNA-seq stored data to the spatial count matrix format. This format consists of a matrix that has a two component index. The first element is the field of view (fov) and the second one is the cell or the spot for which the gene expression levels are observed. Then, for each fov and each cell/spot the gene expression levels are recorded.


The script usage is:

>bMINTY_to_spatial_count_matrix.py [-h] bminty_input_json_file
>
>Transform spatial RNA-seq data from bMINTY format to count matrix format.
>    
>positional arguments:
>  
>   bminty_input_json_file:
        Path to the bminty input json file


The script requires the json file `bminty_json_input_file` that acts as a config file for the script to run successfully. 

```json
{
    "bminty_signal_file": "/path/signal.csv",
    "bminty_interval_file": "/path/interval.csv",
    "bminty_cell_file": "/path/cell.csv",
    "gene_ident": "gene_ident_value",
    "output_dir": "/path/output_dir"
}
```

The json consists of five **mandatory** fields:

1. **"bminty_signal_file"**: Path to the bMINTY signal csv file

2. **"bminty_interval_file"**: Path to the bMINTY interval csv file

3. **"bminty_cell_file"**: Path to the bMINTY cell csv file

4. **"gene_ident"**: Flag that can take "ensgid" or "name" values. Defines whether the genes are labeled after the Ensembl gene ids ("ensgid") or gene names ("name") in the resulting count matrix respectively.

5. **"output_dir"**: Path where the resulting count matrix is stored in

#### Required packages:
- `pandas`

<br>

### bMINTY_to_narrowPeak.py

The `bMINTY_to_narrowPEAK.py` converts the bMINTY formatted ATAC-seq stored data to the [*narrowPeak*](https://genome.ucsc.edu/FAQ/FAQformat.html#format12) file format.

The script usage is:

> bMINTY_to_narrowPeak.py [-h] bminty_input_json_file
>
> Transform ATAC-seq data from bMINTY format to narrowPeak format.
>
>positional arguments:
>   
>   bminty_input_json_file:
>        Path to the bminty input json file

The script requires the json file `bminty_json_input_file` that acts as a config file for the script to run successfully.

```json
{
    "bminty_signal_file": "/path/signal.csv",
    "bminty_interval_file": "/path/interval.csv",
    "output_dir": "/path/output_dir"
}
```

The json file consists of three **mandatory** fields:

1. **"bminty_signal_file"**: Path to the bMINTY signal csv file

2. **"bminty_interval_file"**: Path to the bMINTY interval csv file

3. **"output_dir"**: Path where the resulting count matrix is stored in

#### Required packages:
- `pandas`