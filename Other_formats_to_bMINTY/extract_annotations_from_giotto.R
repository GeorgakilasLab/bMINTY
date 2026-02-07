library(Giotto)
file_path = "/SMI_Giotto_Object.RData"
load(file_path)
annotations <- gem@cell_metadata
n=unique(annotations$rna$Run_Tissue_name)

for (k in n) {
  lung_cells <- annotations$rna[annotations$rna$Run_Tissue_name %in% k, ]
  specific_columns <- lung_cells[, c("cell_ID", "cell_type", "niche")]
  cell_IDs <- specific_columns$cell_ID
  specific_columns <- as.data.frame(specific_columns)
  rownames(specific_columns) <- cell_IDs
  transformed_cell_IDs <- sub("^c_\\d+_(\\d+)_(\\d+)$", "\\2_\\1", cell_IDs)
  rownames(specific_columns) <- transformed_cell_IDs
  write.csv(specific_columns[, -1], file = paste0("/annotation_",k, ".csv"), row.names = TRUE)
}
