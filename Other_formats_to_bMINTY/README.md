# Count matrix to bMINTY format conversion

This readme file lists and explains the usage of the conversion scripts from the original data file format το *bMINTY* format. Currently three main protocols are supported:

* scRNA-seq:
    
    Transform the scRNA-seq count matrix format to bMINTY format.
    
    Script: [`sc_count_matrix_to_bMINTY.py`](#sc_count_matrix_to_bmintypy)


* spatial RNA-seq:
    
    Transform the spatial count matrix format to bMINTY format.

    Script: [`spatial_count_matrix_to_bMINTY.py`](#spatial_count_matrix_to_bmintypy)

* ATAC-seq:

    Transform the narrowPeak format to bMINTY format.
    
    Script: [`narrowPeak_to_bMINTY.py`](#narrowpeak_to_bmintypy)

## Scripts  

### sc_count_matrix_to_bMINTY.py

The `sc_count_matrix_to_bMINTY.py` converts the original count matrix format to the bMINTY format. This script processes the count matrix of a single-cell RNA-sequencing (scRNA-seq) study and, when available, integrates cell annotations, gene annotations, and biotype information. All inputs are transformed into the bMINTY format.

The script usage is:

>python sc_count_matrix_to_bMINTY.py config_file
>
>positional arguments:
>
>    config_file: Path to the configuration json file

The script requires the json `config_file` file that acts as a configuration file for the script to run successfully. The format of the json should be the following:

```json
{
  "count_matrix":
  {
    "count_matrix_file": "/path/count_matrix.csv.gz",
    "cell_id_source": "columns"
  },
  "metadata":
  {
    "metadata_file": "/path/metadata.csv",
    "biotype_file": "/path/.gtf",
    "gene_mapping_file": "/path/gene_mapping.csv" 
  },
  "output_directory": "/path/results",
  "assay_id": 1 
}
```
The `config_file` json file consists of four main entries.

1. **count_matrix** dictionary (**mandatory**). The dictionary entries are:
    - **count_matrix_file**: Path to the count matrix file (gzip compressed csv file)
    - **cell_id_source**: The value of this flag informs about the orientation of the count matrix. 
      - `columns`: Genes across the rows and cells across the columns. 
      - `rows`: Cells across the rows and genes across the columns. 

2. **metadata** dictionary (**optional**). The dictionary entries are:
  
    -**metadata_file**: Path to the metadata file. If provided, the metadata file contains cell-level annotations through a csv file with columns `cell_label` and `cell_type`. In the first column there should be the label of each cell, while in the second column the type annotation.
    
    -**biotype_file**: An [Ensembl gtf file](https://www.ensembl.org/info/website/upload/gff.html) that contains information about the type of each gene. 
    
    -**gene_mapping**: A gene mapping file can be provided with the exact mapping between ensembl ids and gene symbols. This must be a csv file with columns `ensembl_id` and `gene_symbol` that associate each Ensembl gene id to its respective gene symbol.

3. **output_directory** (**mandatory**): The output directory in which the resulting scripts files are stored in. The resulting  *bMINTY* files are:
    - cell.csv
    - interval.csv
    - signal.csv

4. **assay** (**mandatory**): An assay identifier must be provided in the configuration file.

#### Required packages:
- `numpy`
- `pandas`

<br>

### spatial_count_matrix_to_bMINTY.py

The `spatial_count_matrix_to_bMINTY.py` converts the original spatial count matrix to the bMINTY format. The supported format for conversion are ***CosMx Nanostring - Bruker Spatial Biology*** format. The conversion script processes the count matrix and the cell cooridinates of a ***CosMx*** study and, when available, integrates cell annotations, gene annotations, and biotype information.

The script usage is:

>python sc_count_matrix_to_bMINTY.py config_file
>
>positional arguments:
>
>    config_file: Path to the configuration json file

The format of the json should be the following:

```json
{
    "count_matrix_file": "/path/exprMat_file.csv",
    "metadata_file": "/path/annotation.csv",
    "coordinates_file": "/path/metadata_file.csv",
    "gene_annotation_file": "/path/.gtf",
    "gene_mapping_file": "/path/mapping.csv",
    "output_directory": "/path/results",
    "assay_id": 1
}
```

The `config_file` json file consists of seven entries.

1. **count_matrix_file** (**mandatory**): Path to the count matrix file (gzip compressed csv file). The first two columns are essentially the indexes of the matrix, as they contain the field-of-view (fov) and the cell (or spot) label. The rest of the columns are the genes that have been identified during the sequencing process.

    **IMPORTANT NOTE**: In the count matrix the two first columns must be labeled and ordered as:
        
        - The fov column: `fov` (1st column)
        - The cell (or spot) column: `cell_ID` (2nd column)


    The `cell_ID` and `fov` columns will be updated to cell_ID_fov column in the **bMINTY** *cells.csv* output file. `cell_ID`s that do not exist in the coordinates files will be ommited.

2. **metadata_file** (**optional**): Path to the metadata file. If provided, the metadata file contains cell-level annotations through a csv file with index `cell_ID_fov` and a `cell_type` column. Thus, the identified cell (or spot) at a specific fov is annotated with the cell type of the corresponding entry in the `cell_type` column.

3. **coordinates_file** (**mandatory**):This csv file contains x,y global cell/spot coordinates. This file must contain (among others) the following columns with these exact labels:
    - fov
    - cell_ID
    - CenterY_global_px
    - CenterX_global_px

4. **gene_mapping_file** (**optional**):A gene mapping file can be provided with the exact mapping between ensembl ids and gene symbols. This must be a csv file with columns ensembl_id and gene_symbol that associate each Ensembl gene id to its respective gene symbol.

5. **gene_annotation** (**optional**): A GTF file can be provided to extract gene annotation and biotype information (e.g., biotype, chromosome, strand). If a GTF file is provided and no gene mapping file is supplied, the script will extract Ensembl IDs or gene symbols from the GTF as needed, depending on what is missing from the count matrix. For gene annotation however priority is given to the gene_mapping file if exists.

6. **output_directory** (**mandatory**): The output directory in which the resulting scripts files are stored in. The resulting  *bMINTY* files are:
    - cell.csv
    - interval.csv
    - signal.csv

7. **assay** (**mandatory**): An assay identifier must be provided in the configuration file.

#### Required packages:
- numpy
- pandas


### narrowPeak_to_bMINTY.py

The `narrowPeak_to_bMINTY.py` converts narrowPeak or IDR files format to the bMINTY format.

The script usage is:


>python narrowPeak_to_bMINTY.py config.json
>
>positional arguments:
>
>    config_file: Path to the configuration json file

The format of the json should be the following:

```json
{
    "input_file": "/path/input_file",
    "interval_type": "/path/interval_file",
    "output_dir": "/path/output_dir"
}
```

The `config_file` json file consists of three entries.

1. **input_file** (**mandatory**): Path to the [narrowPeak](https://genome.ucsc.edu/FAQ/FAQformat.html#format12) or IDR file.

2. **type** (**mandatory**): The type of interval. The available options can either be `narrowpeak` or `idr`.

3. **output_dir** (**mandatory**): The output directory in which the resulting scripts files are stored in. The resulting  *bMINTY* files are:
    - cell.csv
    - interval.csv
    - signal.csv

#### Required packages
- `pandas`

## Helper Scripts

### extract_annotations_from_giotto.R

This repository also includes extract_annotations_from_giotto.R to extract cell type annotation from a [Giotto (R) object](https://giottosuite.com/). The annotation was required as input for the `spatial_count_matrix_to_bMINTY.py`. This script is optional and is not required for executing the main utility scripts or for the bMINTY format.

#### Required packages:
- `Giotto`