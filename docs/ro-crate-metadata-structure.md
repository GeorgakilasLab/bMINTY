# RO-Crate 1.2 Metadata Structure — bMINTY Export

The metadata is written as `ro-crate-metadata.json` inside a ZIP export,, triggered when  ro_crate=true during export.

---

## Top-level structure

```json
{
  "@context": "https://w3id.org/ro/crate/1.2/context",
  "@graph": [ ... ]
}
```

---

## Entities in `@graph`

### 1. Metadata Descriptor (`ro-crate-metadata.json`)

| Field | Value |
|---|---|
| `@id` | `ro-crate-metadata.json` |
| `@type` | `CreativeWork` |
| `conformsTo` | `https://w3id.org/ro/crate/1.2` |
| `about` | reference to `./` |

### 2. Root Data Entity (`./`)

| Field | Value |
|---|---|
| `@id` | `./` |
| `@type` | `Dataset` |
| `name` | `bMINTY Database Export` |
| `description` | Dynamic: study count + active filter count |
| `datePublished` | ISO 8601 date of export (UTC) |
| `keywords` | Static comma-separated string (NGS, FAIR, genomics, etc.) |
| `hasPart` | References to each exported file |
| `author` | → `#georgakilas-lab` |
| `creator` | → `#bminty-software` |
| `publisher` | → `#georgakilas-lab` |
| `license` | → CC0 1.0 URL |
| `variableMeasured` | → `#stat-studyCount`, `#stat-assayCount`, `#stat-intervalCount`, `#stat-signalCount` |
| `mentions` *(if filters used)* | → `#export-filters` |

### 3. Contextual Entities (always present)

- **`#georgakilas-lab`** (`Organization`): name + GitHub URL
- **`#bminty-software`** (`SoftwareApplication`): name, description, GitHub URL, MIT license ref, citation ref
- **`#bminty-paper`** (`ScholarlyArticle`): paper name, author ref, GitHub URL
- **`https://opensource.org/licenses/MIT`** (`CreativeWork`): MIT License description

### 4. Statistics (PropertyValue — always present)

| ID | Name | Value |
|---|---|---|
| `#stat-studyCount` | `studyCount` | count of studies in export |
| `#stat-assayCount` | `assayCount` | count of assays in export |
| `#stat-intervalCount` | `intervalCount` | count of intervals in export |
| `#stat-signalCount` | `signalCount` | count of signals in export |

### 5. Applied Filters (`#export-filters`) — conditional

Only present if the export was filtered. A `PropertyValue` with `name: appliedFilters` and a JSON string `value` containing all non-empty filter params.

**Possible filter parameters:**

| Parameter | Description |
|---|---|
| `study_name` | Study name |
| `study_external_id` | Study external identifier |
| `study_availability` | Study availability status |
| `assay_name` | Assay name |
| `assay_external_id` | Assay external identifier |
| `assay_type` | Assay type |
| `assay_availability` | Assay availability status |
| `tissue` | Tissue type |
| `cell_type` | Cell type |
| `assay_cell_type` | Assay-level cell type |
| `treatment` | Treatment condition |
| `platform` | Sequencing platform |
| `interval_type` | Genomic interval type |
| `biotype` | Biotype |
| `assembly_name` | Reference genome assembly name |
| `assembly_species` | Species of the assembly |
| `cell_label` | Cell label/annotation |

### 6. File Entities — per exported file

One entity per file (SQLite or CSV), each with:

| Field | Value |
|---|---|
| `@type` | `File` |
| `name` | filename |
| `description` | human-readable description of the file |
| `encodingFormat` | `application/x-sqlite3` or `text/csv` |
| `dateModified` | ISO 8601 date of export |
| `conformsTo` *(SQLite only)* | references to all table schema entities |

### 7. Table Schema Entities — per table

For each of the 7 tables (`study`, `assay`, `interval`, `assembly`, `signal`, `cell`, `pipeline`), a `CreativeWork` entity is added with:

| Field | Value |
|---|---|
| `@id` | `#table-{name}` |
| `@type` | `CreativeWork` |
| `additionalType` | `https://schema.org/DefinedTermSet` |
| `hasPart` | list of column `PropertyValue` references |
| `identifier` | → primary key `PropertyValue` |
| `isRelatedTo` | → foreign key `PropertyValue` entries |

**Column entities** (`PropertyValue` per column):

| Field | Value |
|---|---|
| `@id` | `#table-{name}-col-{column_name}` |
| `name` | column name |
| `propertyID` | column name |
| `value` | SQLite column type |
| `description` | `Column of type {type}` |
| `valueRequired` | `true` if NOT NULL |
| `defaultValue` | default value if defined |

**Primary key entities** (`PropertyValue`):

| Field | Value |
|---|---|
| `@id` | `#table-{name}-primaryKey` |
| `name` | `primaryKey` |
| `value` | comma-separated primary key column names |

**Foreign key entities** (`PropertyValue`):

| Field | Value |
|---|---|
| `@id` | `#table-{name}-fk-{column_name}` |
| `name` | FK column name |
| `description` | `Foreign key to {referenced_table} table` |
| `valueReference` | → `#table-{referenced_table}-col-{referenced_column}` |

Schema data is extracted live from the SQLite database via `PRAGMA table_info`, `PRAGMA foreign_key_list`, and `PRAGMA index_list`.

---

## Export formats that trigger RO-Crate

| Format | Query Params | Files in ZIP |
|---|---|---|
| SQLite (default) | `?ro_crate=true` | `filtered_database.sqlite3` + `ro-crate-metadata.json` |
| Full ZIP | `?full=true&ro_crate=true` | all table CSVs + `filtered_database.sqlite3` + `ro-crate-metadata.json` |
| Single CSV | `?table=study&ro_crate=true` | `study.csv` + `ro-crate-metadata.json` |

---

## Table descriptions

| Table | Description |
|---|---|
| `study` | Research studies containing experimental data |
| `assay` | Experimental assays performed within studies |
| `interval` | Genomic intervals (peaks, genes, regions) |
| `assembly` | Reference genome assemblies |
| `signal` | Signal measurements for intervals and cells |
| `cell` | Cell annotations and metadata |
| `pipeline` | Analysis pipelines used for data processing |
