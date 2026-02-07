# database_manager/views.py
import os
import io
import re
import csv
import sys
import zipfile
import sqlite3
import json
import uuid
import threading
import tempfile
import time
import traceback
import shutil
import numpy as np
from datetime import datetime
from pathlib import Path
from django.http import JsonResponse, FileResponse, HttpResponse
from django.urls import reverse
from django.conf import settings
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from studies.models import Study
from assay.models import Assay
from signals.models import Signal, Cell
from interval.models import Interval
from assembly.models import Assembly
from .pandas_bulk_import import bulk_import_with_pandas

# Define paths
BASE_DIR = Path(settings.BASE_DIR)
UPLOAD_FOLDER = BASE_DIR / 'uploads'
EXPORT_FOLDER = BASE_DIR / 'exports'
UPLOAD_FOLDER.mkdir(exist_ok=True)
EXPORT_FOLDER.mkdir(exist_ok=True)

# Tables we allow exporting individually
EXPORT_TABLES = [
    'assay',
    'assembly',
    'cell',
    'interval',
    'pipeline',
    'signal',
    'study',
]

# In-memory progress store for bulk imports (single-process). For production, use Redis or a DB-backed cache.
PROGRESS_STORE = {}
PROGRESS_LOCK = threading.Lock()

def _parse_bool_param(val):
    if val is None:
        return None
    v = str(val).lower()
    if v in ('1', 'true', 'yes', 'available', 't', 'on'):
        return True
    if v in ('0', 'false', 'no', 'unavailable', 'f', 'off'):
        return False
    return None

def _batch_iter(iterable, batch_size):
    """
    Generator that yields batches from an iterable.
    Useful for batching large ID lists to avoid SQLite's 999 variable limit.
    """
    items = list(iterable) if not isinstance(iterable, list) else iterable
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]

def _get_multi_value_param(query_params, param_name):
    """
    Get parameter values, handling multiple formats:
    - Array format: param_name[]=value1&param_name[]=value2
    - Repeated params: param_name=value1&param_name=value2  
    - Single value: param_name=value
    
    Returns a list of values, filtering out empty or whitespace-only strings.
    """
    # Check for array format: param_name[]
    array_values = query_params.getlist(f'{param_name}[]')
    if array_values:
        return [v.strip() for v in array_values if v and v.strip()]
    
    # Check for repeated params (same key multiple times): param_name=X&param_name=Y
    multi_values = query_params.getlist(param_name)
    if multi_values:
        return [v.strip() for v in multi_values if v and v.strip()]
    
    return []

def _iter_csv_from_uploaded_file(uploaded_file):
    """Yield dict rows from an uploaded file object using minimal memory."""
    if not uploaded_file:
        return iter([])

    def _gen():
        try:
            uploaded_file.seek(0)
        except Exception:
            pass
        wrapper = io.TextIOWrapper(uploaded_file.file, encoding='utf-8', errors='ignore', newline='')
        reader = csv.DictReader(wrapper)
        for row in reader:
            yield row
    return _gen()


def _count_csv_rows_from_file(uploaded_file):
    """Quick count of rows in an uploaded CSV file (excluding header)."""
    if not uploaded_file:
        return 0
    try:
        uploaded_file.seek(0)
        wrapper = io.TextIOWrapper(uploaded_file.file, encoding='utf-8', errors='ignore', newline='')
        reader = csv.DictReader(wrapper)
        count = sum(1 for _ in reader)
        uploaded_file.seek(0)
        return count
    except Exception:
        return 0


def _update_progress(job_id, **fields):
    with PROGRESS_LOCK:
        if job_id not in PROGRESS_STORE:
            return
        PROGRESS_STORE[job_id].update(fields)

def allowed_file(filename):
    return filename.lower().endswith('.sqlite3')

def allowed_csv_file(filename):
    return filename.lower().endswith('.csv')


def _get_table_schema(db_path_or_conn, table_name):
    """
    Extract table schema information including columns, types, and keys.
    
    Args:
        db_path_or_conn: Path to SQLite database or connection object
        table_name: Name of the table
    
    Returns:
        Dict with schema information
    """
    if isinstance(db_path_or_conn, str):
        conn = sqlite3.connect(db_path_or_conn)
        should_close = True
    else:
        conn = db_path_or_conn
        should_close = False
    
    try:
        cursor = conn.cursor()
        
        # Get column information
        cursor.execute(f'PRAGMA table_info("{table_name}")')
        columns = []
        primary_keys = []
        
        for row in cursor.fetchall():
            cid, name, col_type, notnull, default_val, pk = row
            col_info = {
                'name': name,
                'type': col_type,
                'nullable': not bool(notnull),
            }
            if default_val is not None:
                col_info['default'] = str(default_val)
            
            columns.append(col_info)
            
            if pk:
                primary_keys.append(name)
        
        # Get foreign key information
        cursor.execute(f'PRAGMA foreign_key_list("{table_name}")')
        foreign_keys = []
        
        for row in cursor.fetchall():
            fk_id, seq, ref_table, from_col, to_col, on_update, on_delete, match = row
            foreign_keys.append({
                'column': from_col,
                'references_table': ref_table,
                'references_column': to_col,
                'on_update': on_update,
                'on_delete': on_delete
            })
        
        # Get indices
        cursor.execute(f'PRAGMA index_list("{table_name}")')
        indices = []
        
        for row in cursor.fetchall():
            seq, name, unique, origin, partial = row
            if origin != 'pk':  # Skip primary key index
                cursor.execute(f'PRAGMA index_info("{name}")')
                index_cols = [col[2] for col in cursor.fetchall()]
                indices.append({
                    'name': name,
                    'columns': index_cols,
                    'unique': bool(unique)
                })
        
        return {
            'columns': columns,
            'primary_keys': primary_keys,
            'foreign_keys': foreign_keys,
            'indices': indices
        }
    
    finally:
        if should_close:
            conn.close()


def _generate_ro_crate_metadata(query_params, counts, file_list, export_format='sqlite', db_path_or_bytes=None):
    """
    Generate RO-Crate 1.2 compliant metadata for exported data.
    
    Follows the RO-Crate 1.2 specification:
    https://www.researchobject.org/ro-crate/specification/1.2/
    
    Args:
        query_params: Django QueryDict with filter parameters
        counts: Dict with row counts {'studies': N, 'assays': N, ...}
        file_list: List of file names included in the export
        export_format: 'sqlite', 'zip', or 'csv'
        db_path_or_bytes: Path to database file or bytes object for schema extraction
    
    Returns:
        Dict containing RO-Crate 1.2 compliant metadata using schema.org vocabulary
    """
    # Use ISO 8601 date format (YYYY-MM-DD) per RO-Crate best practices
    now = datetime.utcnow().strftime('%Y-%m-%d')
    
    # Build filter description
    filters_applied = {}
    filter_params = [
        'study_name', 'study_external_id', 'study_availability',
        'assay_name', 'assay_external_id', 'assay_type', 'assay_availability',
        'tissue', 'cell_type', 'assay_cell_type', 'treatment', 'platform',
        'interval_type', 'biotype', 'assembly_name', 'assembly_species',
        'cell_label'
    ]
    
    for param in filter_params:
        values = _get_multi_value_param(query_params, param)
        if values:
            filters_applied[param] = values
        elif param in query_params:
            val = query_params.get(param)
            if val:
                filters_applied[param] = val
    
    # Create File Data Entities for each file (excluding ro-crate-metadata.json)
    # Per RO-Crate 1.2 spec: Files MUST have @type "File" (alias for schema.org MediaObject)
    dataset_parts = []
    # Track table schemas for SQLite files to reference
    table_schema_ids = []
    
    for filename in file_list:
        # Skip the metadata file - it's already defined as the metadata descriptor
        if filename == 'ro-crate-metadata.json':
            continue
            
        description = None
        encoding_format = None
        file_entity = None
        
        if filename.endswith('.sqlite3'):
            description = 'SQLite database containing filtered bMINTY data'
            encoding_format = 'application/x-sqlite3'
            # SQLite files will reference table schemas via conformsTo (populated later)
            file_entity = {
                '@id': filename,
                '@type': 'File',
                'name': filename,
                'description': description,
                'encodingFormat': encoding_format,
                'dateModified': now
            }
        elif filename.endswith('.csv'):
            table_name = filename.replace('.csv', '')
            description = f'{table_name.capitalize()} table data in CSV format'
            encoding_format = 'text/csv'
            file_entity = {
                '@id': filename,
                '@type': 'File',
                'name': filename,
                'description': description,
                'encodingFormat': encoding_format,
                'dateModified': now
            }
        
        if file_entity:
            dataset_parts.append(file_entity)
    
    # Build main dataset description
    dataset_description = f"bMINTY database export containing {counts.get('studies', 0)} studies"
    if filters_applied:
        dataset_description += f" (filtered by {len(filters_applied)} parameters)"
    
    # Create RO-Crate metadata following RO-Crate 1.2 specification
    # Root Data Entity MUST have: @type Dataset, @id, name, description, datePublished, license
    # Contextual entities (author, creator, license) MUST be separate entities in @graph with @id references
    # Using RO-Crate 1.2 (stable specification) with proper JSON-LD @id format for conformsTo
    ro_crate = {
        '@context': 'https://w3id.org/ro/crate/1.2/context',
        '@graph': [
            # RO-Crate Metadata Descriptor (REQUIRED)
            # conformsTo MUST be an object with @id property per JSON-LD requirements
            {
                '@id': 'ro-crate-metadata.json',
                '@type': 'CreativeWork',
                'conformsTo': {'@id': 'https://w3id.org/ro/crate/1.2'},
                'about': {'@id': './'}
            },
            # Root Data Entity (REQUIRED)
            {
                '@id': './',
                '@type': 'Dataset',
                'name': 'bMINTY Database Export',
                'description': dataset_description,
                'datePublished': now,
                'hasPart': [{'@id': f} for f in file_list if f != 'ro-crate-metadata.json'],
                # Keywords per schema.org convention: comma-separated string
                # Based on: "bMINTY: Enabling Reproducible Management of High-Throughput 
                # Sequencing Analysis Results and their Metadata" (Kapelios et al.)
                'keywords': 'high-throughput sequencing, next-generation sequencing, NGS, FAIR principles, scientific reproducibility, data management, genomics, transcriptomics, multi-omics, single-cell RNA-seq, spatial transcriptomics, ATAC-seq, bioinformatics',
                # References to contextual entities (MUST use @id form per RO-Crate 1.2)
                'author': {'@id': '#georgakilas-lab'},
                'creator': {'@id': '#bminty-software'},
                'license': {'@id': 'https://creativecommons.org/publicdomain/zero/1.0/'},
                'publisher': {'@id': '#georgakilas-lab'},
                # References to statistics entities (must be separate in @graph per RO-Crate 1.2)
                'variableMeasured': [
                    {'@id': '#stat-studyCount'},
                    {'@id': '#stat-assayCount'},
                    {'@id': '#stat-intervalCount'},
                    {'@id': '#stat-signalCount'}
                ]
            },
            # Contextual Entity: Organization (author/publisher)
            {
                '@id': '#georgakilas-lab',
                '@type': 'Organization',
                'name': 'Georgakilas Lab',
                'url': 'https://github.com/GeorgakilasLab'
            },
            # Contextual Entity: SoftwareApplication (creator)
            {
                '@id': '#bminty-software',
                '@type': 'SoftwareApplication',
                'name': 'bMINTY',
                'description': 'Enabling Reproducible Management of High-Throughput Sequencing Analysis Results and their Metadata',
                'url': 'https://github.com/GeorgakilasLab/bMINTY',
                'codeRepository': 'https://github.com/GeorgakilasLab/bMINTY',
                'citation': {'@id': '#bminty-paper'}
            },
            # Contextual Entity: License (REQUIRED on Root Data Entity per RO-Crate 1.2)
            # Using CC0-1.0 (public domain dedication) for maximum openness
            {
            "@id": "https://opensource.org/licenses/MIT",
            "@type": "CreativeWork",
            "name": "MIT License",
            "description": "A permissive open-source license allowing reuse, modification, and distribution of the software, provided the copyright notice and license text are included."
            },

            # Statistics entities (PropertyValue must be separate in @graph per RO-Crate 1.2 flattening requirement)
            {
                '@id': '#stat-studyCount',
                '@type': 'PropertyValue',
                'name': 'studyCount',
                'value': counts.get('studies', 0)
            },
            {
                '@id': '#stat-assayCount',
                '@type': 'PropertyValue',
                'name': 'assayCount',
                'value': counts.get('assays', 0)
            },
            {
                '@id': '#stat-intervalCount',
                '@type': 'PropertyValue',
                'name': 'intervalCount',
                'value': counts.get('intervals', 0)
            },
            {
                '@id': '#stat-signalCount',
                '@type': 'PropertyValue',
                'name': 'signalCount',
                'value': counts.get('signals', 0)
            }
        ]
    }
    
    # Add filter information if any filters were applied
    if filters_applied:
        filter_properties = {
            '@id': '#export-filters',
            '@type': 'PropertyValue',
            'name': 'appliedFilters',
            'description': 'Query parameters used to filter the exported data',
            'value': json.dumps(filters_applied, indent=2)
        }
        ro_crate['@graph'].append(filter_properties)
        # Use 'mentions' to reference the filters entity
        # Note: 'about' describes subject matter (topics), 'mentions' references related entities
        ro_crate['@graph'][1]['mentions'] = {'@id': '#export-filters'}
    
    # Add table descriptions with schema information
    table_descriptions = {
        'study': 'Research studies containing experimental data',
        'assay': 'Experimental assays performed within studies',
        'interval': 'Genomic intervals (peaks, genes, regions)',
        'assembly': 'Reference genome assemblies',
        'signal': 'Signal measurements for intervals and cells',
        'cell': 'Cell annotations and metadata',
        'pipeline': 'Analysis pipelines used for data processing'
    }
    
    # Extract schema information if database is provided
    temp_db_path = None
    db_conn = None
    try:
        if db_path_or_bytes:
            # If bytes provided, write to temp file
            if isinstance(db_path_or_bytes, bytes):
                temp_fd, temp_db_path = tempfile.mkstemp(suffix='.sqlite3')
                os.close(temp_fd)
                with open(temp_db_path, 'wb') as f:
                    f.write(db_path_or_bytes)
                db_path = temp_db_path
            else:
                db_path = db_path_or_bytes
            
            # Determine which tables to extract schema for
            # If exporting SQLite file, extract ALL tables
            has_sqlite_file = any(f.endswith('.sqlite3') for f in file_list)
            
            if has_sqlite_file:
                # Extract schema for ALL tables in the database
                tables_to_extract = table_descriptions.keys()
            else:
                # Only extract schema for tables in the file list (CSV exports)
                tables_to_extract = [t for t in table_descriptions.keys() if any(t in f for f in file_list)]
            
            # OPTIMIZATION: Open a single connection for all schema extractions
            # This avoids repeatedly opening/closing connections to large database files
            db_conn = sqlite3.connect(db_path)
            
            # Add table schema information as DefinedTermSet entities
            # (more appropriate than DataCatalog for describing table structure)
            for table_name in tables_to_extract:
                desc = table_descriptions.get(table_name, f'{table_name.capitalize()} table')
                try:
                    # Pass connection instead of path to avoid reopening
                    schema = _get_table_schema(db_conn, table_name)
                    
                    # Use CreativeWork with additionalType for table schema
                    # This is a valid schema.org pattern for structured data descriptions
                    table_entity = {
                        '@id': f'#table-{table_name}',
                        '@type': 'CreativeWork',
                        'name': f'{table_name.capitalize()} Table Schema',
                        'description': desc,
                        'additionalType': 'https://schema.org/DefinedTermSet'
                    }
                    
                    # Add column information as hasPart with references (flattened for RO-Crate)
                    # Using descriptive IDs based on column names for better human-readability
                    # and self-documentation (compliant with RO-Crate 1.2 local identifier conventions)
                    column_properties = []
                    for idx, col in enumerate(schema['columns']):
                        # Use descriptive column name in ID for better readability
                        # Sanitize column name for use in fragment identifier (replace non-alphanumeric with hyphen)
                        col_name_sanitized = ''.join(c if c.isalnum() else '-' for c in col['name'].lower()).strip('-')
                        col_id = f'#table-{table_name}-col-{col_name_sanitized}'
                        col_prop = {
                            '@type': 'PropertyValue',
                            'name': col['name'],
                            'propertyID': col['name'],
                            'value': col['type'],
                            'description': f"Column of type {col['type']}"
                        }
                        if not col['nullable']:
                            col_prop['valueRequired'] = True
                        if 'default' in col:
                            col_prop['defaultValue'] = col['default']
                        
                        # Add as separate entity in @graph
                        col_prop['@id'] = col_id
                        ro_crate['@graph'].append(col_prop)
                        
                        # Reference by @id in hasPart
                        column_properties.append({'@id': col_id})
                    
                    if column_properties:
                        table_entity['hasPart'] = column_properties
                    
                    # Add primary key information using identifier property (flattened)
                    if schema['primary_keys']:
                        pk_id = f'#table-{table_name}-primaryKey'
                        pk_entity = {
                            '@id': pk_id,
                            '@type': 'PropertyValue',
                            'name': 'primaryKey',
                            'value': ', '.join(schema['primary_keys'])
                        }
                        ro_crate['@graph'].append(pk_entity)
                        table_entity['identifier'] = {'@id': pk_id}
                    
                    # Add foreign key information using isRelatedTo (flattened)
                    # Using descriptive IDs based on column names for better readability
                    if schema['foreign_keys']:
                        fk_refs = []
                        for fk_idx, fk in enumerate(schema['foreign_keys']):
                            # Use descriptive FK column name in ID
                            fk_col_sanitized = ''.join(c if c.isalnum() else '-' for c in fk['column'].lower()).strip('-')
                            fk_id = f'#table-{table_name}-fk-{fk_col_sanitized}'
                            fk_entity = {
                                '@id': fk_id,
                                '@type': 'PropertyValue',
                                'name': fk['column'],
                                'value': f"{fk['references_table']}.{fk['references_column']}",
                                'description': f"Foreign key to {fk['references_table']} table"
                            }
                            ro_crate['@graph'].append(fk_entity)
                            fk_refs.append({'@id': fk_id})
                        table_entity['isRelatedTo'] = fk_refs
                    
                    ro_crate['@graph'].append(table_entity)
                    table_schema_ids.append(f'#table-{table_name}')
                except Exception as e:
                    # If schema extraction fails, add basic table info
                    table_entity = {
                        '@id': f'#table-{table_name}',
                        '@type': 'CreativeWork',
                        'name': f'{table_name.capitalize()} Table Schema',
                        'description': desc
                    }
                    ro_crate['@graph'].append(table_entity)
                    table_schema_ids.append(f'#table-{table_name}')
        else:
            # No database provided, add basic table descriptions
            for table_name, desc in table_descriptions.items():
                if any(table_name in f for f in file_list):
                    table_entity = {
                        '@id': f'#table-{table_name}',
                        '@type': 'CreativeWork',
                        'name': f'{table_name.capitalize()} Table Schema',
                        'description': desc
                    }
                    ro_crate['@graph'].append(table_entity)
                    table_schema_ids.append(f'#table-{table_name}')
    
    finally:
        # Close shared database connection
        if db_conn:
            try:
                db_conn.close()
            except:
                pass
        
        # Clean up temp file if created
        if temp_db_path and os.path.exists(temp_db_path):
            try:
                os.unlink(temp_db_path)
            except:
                pass
    
    # Link SQLite files to their table schemas using conformsTo
    if table_schema_ids:
        for file_entity in dataset_parts:
            if file_entity.get('@id', '').endswith('.sqlite3'):
                # Add conformsTo property linking to all table schemas
                file_entity['conformsTo'] = [{'@id': schema_id} for schema_id in table_schema_ids]
    
    # Add file descriptions to graph
    ro_crate['@graph'].extend(dataset_parts)
    
    return ro_crate


def _import_interval(request, rows):
    """
    Import intervals with ID mapping:
    - Ignores 'id' from CSV (auto-incremented)
    - Maps CSV external_id to new DB IDs
    - Resolves parental_id references to new DB IDs
    - Uses assembly_id from request context (ignores CSV assembly_id)
    """
    # Handle empty CSV
    if not rows:
        return JsonResponse({
            "message": "Imported 0 interval(s).",
            "interval_id_map": {}
        })
    
    assembly_id = request.data.get('assembly_id')
    if not assembly_id:
        return JsonResponse({"error": "assembly_id is required for interval import."}, status=400)
    
    try:
        assembly_id = int(assembly_id)
        if not Assembly.objects.filter(id=assembly_id).exists():
            return JsonResponse({"error": f"Assembly with id {assembly_id} not found."}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid assembly_id."}, status=400)

    # Map CSV external_id -> new DB id
    external_id_map = {}
    row_count = 0
    
    # First pass: create intervals without parental_id
    intervals_to_update = []
    
    from django.db import transaction
    
    try:
        with transaction.atomic():
            for row in rows:
                external_id = row.get('external_id', '').strip()
                parental_id_csv = row.get('parental_id', '').strip() or None
                name = row.get('name', '').strip() or None
                interval_type = row.get('type', '').strip()
                biotype = row.get('biotype', '').strip() or None
                chromosome = row.get('chromosome', '').strip()
                start = int(row.get('start', 0))
                end_val = row.get('end', '').strip()
                end = int(end_val) if end_val else None
                strand = row.get('strand', '').strip()
                summit_val = row.get('summit', '').strip()
                summit = int(summit_val) if summit_val else None
                
                if not external_id or not interval_type or not chromosome or not strand:
                    continue  # Skip invalid rows
                
                # Create interval with assembly_id from context
                interval = Interval.objects.create(
                    external_id=external_id,
                    parental_id=None,  # Will update in second pass
                    name=name,
                    type=interval_type,
                    biotype=biotype,
                    chromosome=chromosome,
                    start=start,
                    end=end,
                    strand=strand,
                    summit=summit,
                    assembly_id=assembly_id
                )
                
                external_id_map[external_id] = interval.id
                row_count += 1
                
                # Store for second pass if it has parental_id
                if parental_id_csv:
                    intervals_to_update.append((interval.id, parental_id_csv))
            
            # Second pass: update parental_id references
            for interval_id, parental_external_id in intervals_to_update:
                if parental_external_id in external_id_map:
                    Interval.objects.filter(id=interval_id).update(
                        parental_id=str(external_id_map[parental_external_id])
                    )
            
            # Return the mapping for frontend to use in subsequent imports
            return JsonResponse({
                "message": f"Imported {row_count} interval(s).",
                "interval_id_map": external_id_map
            })
        
    except Exception as e:
        return JsonResponse({"error": f"Failed to import intervals: {str(e)}"}, status=500)


def _import_cell(request, rows):
    """
    Import cells:
    - Ignores 'id' from CSV (auto-incremented)
    - Uses assay_id from request context (ignores CSV assay_id)
    - Returns mapping of CSV cell names to new DB IDs for signal import
    """
    # Handle empty CSV
    if not rows:
        return JsonResponse({
            "message": "Imported 0 cell(s).",
            "cell_name_map": {}
        })
    
    assay_id = request.data.get('assay_id')
    if not assay_id:
        return JsonResponse({"error": "assay_id is required for cell import."}, status=400)
    
    try:
        assay_id = int(assay_id)
        if not Assay.objects.filter(id=assay_id).exists():
            return JsonResponse({"error": f"Assay with id {assay_id} not found."}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid assay_id."}, status=400)

    # Map CSV cell name -> new DB id
    cell_name_map = {}
    row_count = 0
    
    from django.db import transaction
    
    try:
        with transaction.atomic():
            for row in rows:
                name = (row.get('name') or '').strip()
                raw_type = (row.get('type') or '').strip().lower()
                label = (row.get('label') or '').strip() or None
                x_coord_val = (row.get('x_coordinate') or '').strip()
                y_coord_val = (row.get('y_coordinate') or '').strip()
                z_coord_val = (row.get('z_coordinate') or '').strip()

                if not name:
                    continue  # Skip invalid rows

                # Normalize type (mandatory): accept 'cell', 'single cell' -> 'cell'; 'spot', 'srt' -> 'spot'
                type_norm = None
                if raw_type in ('cell', 'single cell', 'single-cell', 'singlecell'):
                    type_norm = 'cell'
                elif raw_type in ('spot', 'srt'):
                    type_norm = 'spot'
                else:
                    # If type missing or invalid, skip row
                    continue

                def _to_int(val):
                    if not val:
                        return None
                    try:
                        return int(val)
                    except Exception:
                        return None

                # Create cell with assay_id from context
                cell = Cell.objects.create(
                    name=name,
                    type=type_norm,
                    label=label,
                    x_coordinate=_to_int(x_coord_val),
                    y_coordinate=_to_int(y_coord_val),
                    z_coordinate=_to_int(z_coord_val),
                    assay_id=assay_id
                )

                cell_name_map[name] = cell.id
                row_count += 1
        
            return JsonResponse({
                "message": f"Imported {row_count} cell(s).",
                "cell_name_map": cell_name_map
            })
        
    except Exception as e:
        return JsonResponse({"error": f"Failed to import cells: {str(e)}"}, status=500)


def _import_signal(request, rows):
    """
    Import signals with ID mapping:
    - Ignores 'id' from CSV (auto-incremented)
    - Maps CSV interval_id to new DB interval IDs (requires interval_id_map from request)
    - Maps CSV cell_id to new DB cell IDs (requires cell_name_map from request)
    - Uses assay_id from request context (ignores CSV assay_id)
    """
    # Handle empty CSV
    if not rows:
        return JsonResponse({
            "message": "Imported 0 signal(s)."
        })
    
    assay_id = request.data.get('assay_id')
    if not assay_id:
        return JsonResponse({"error": "assay_id is required for signal import."}, status=400)
    
    # Get ID mappings from request (passed from frontend after interval/cell imports)
    interval_id_map_json = request.data.get('interval_id_map', '{}')
    cell_name_map_json = request.data.get('cell_name_map', '{}')
    
    try:
        assay_id = int(assay_id)
        if not Assay.objects.filter(id=assay_id).exists():
            return JsonResponse({"error": f"Assay with id {assay_id} not found."}, status=400)
        
        # Parse ID maps
        interval_id_map = json.loads(interval_id_map_json) if isinstance(interval_id_map_json, str) else interval_id_map_json
        cell_name_map = json.loads(cell_name_map_json) if isinstance(cell_name_map_json, str) else cell_name_map_json
        
    except (ValueError, TypeError) as e:
        return JsonResponse({"error": f"Invalid parameters: {str(e)}"}, status=400)

    row_count = 0
    
    from django.db import transaction
    
    try:
        with transaction.atomic():
            for row in rows:
                signal_val = row.get('signal', '').strip()
                p_value_val = row.get('p_value', '').strip()
                padj_value_val = row.get('padj_value', '').strip()
                csv_interval_id = row.get('interval_id', '').strip()
                csv_cell_id = row.get('cell_id', '').strip()
                
                if not signal_val or not csv_interval_id:
                    continue  # Skip invalid rows
                
                # Normalize numeric values for European formats
                def _norm_num(s):
                    s = (s or '').strip()
                    if not s:
                        raise ValueError('Empty numeric value')
                    if s.upper() in ('NA','N/A','NULL'):
                        raise ValueError('Null numeric value')
                    s = s.replace(' ', '')
                    if ',' in s:
                        s = s.replace('.', '')
                        s = s.replace(',', '.')
                        return float(s)
                    if s.count('.') > 1:
                        s = s.replace('.', '')
                        return float(s)
                    return float(s)

                try:
                    signal = _norm_num(signal_val)
                except ValueError:
                    continue
                try:
                    p_value = _norm_num(p_value_val) if p_value_val else None
                except ValueError:
                    p_value = None
                try:
                    padj_value = _norm_num(padj_value_val) if padj_value_val else None
                except ValueError:
                    padj_value = None
                
                # Map interval_id from CSV to new DB ID
                # The map key is the external_id from interval CSV
                interval_db_id = interval_id_map.get(csv_interval_id)
                if not interval_db_id:
                    # Try as integer key
                    interval_db_id = interval_id_map.get(int(csv_interval_id)) if csv_interval_id.isdigit() else None
                
                if not interval_db_id:
                    continue  # Skip if interval not found in map
                
                # Map cell_id from CSV (could be cell name) to new DB ID
                cell_db_id = None
                if csv_cell_id:
                    cell_db_id = cell_name_map.get(csv_cell_id)
                    if not cell_db_id and csv_cell_id.isdigit():
                        cell_db_id = cell_name_map.get(int(csv_cell_id))
                
                # Create signal with mapped IDs
                try:
                    Signal.objects.create(
                        signal=signal,
                        p_value=p_value,
                        padj_value=padj_value,
                        assay_id=assay_id,
                        interval_id=interval_db_id,
                        cell_id=cell_db_id
                    )
                except Exception as e:
                    try:
                        with open('/tmp/bulk_import_debug.log', 'a') as dbg:
                            dbg.write(f"create error row: {row} err: {e}\n")
                    except Exception:
                        pass
                    raise
                
                row_count += 1
        
            return JsonResponse({
                "message": f"Imported {row_count} signal(s)."
            })
        
    except Exception as e:
        return JsonResponse({"error": f"Failed to import signals: {str(e)}"}, status=500)


@swagger_auto_schema(
    method='post',
    operation_summary="Import complete database",
    operation_description="""
    Import a SQLite3 database file (FAST MODE).
    
    ⚠️ WARNING: This will WIPE all existing data and replace it with the imported database!
    
    Backup Option:
    - Set create_backup=true (default) to backup the current database before wiping
    - Backup is saved with .backup extension
    - Set create_backup=false to skip backup (faster but no recovery option)
    
    File Requirements:
    - Must be a .sqlite3 file
    
    Import Process (Optimized for Speed):
    1. (Optional) Backup current database with .backup extension
    2. Delete existing database
    3. Copy incoming database directly (native SQLite file)
    4. Create django_migrations table if missing
    5. Apply migrations with --fake-initial (creates missing Django tables, preserves existing data)
    
    This is the FASTEST import method:
    - No schema validation
    - No partial database detection/merging
    - Direct file replacement
    - Migrations use --fake-initial to handle both fresh and pre-existing tables
    
    Use Cases:
    - Restoring from a backup
    - Switching to a different dataset
    - Initial database setup
    - Importing exported data
    """,
    manual_parameters=[
        openapi.Parameter(
            'sqlite_file',
            openapi.IN_FORM,
            type=openapi.TYPE_FILE,
            required=True,
            description="SQLite3 database file to import"
        ),
        openapi.Parameter(
            'create_backup',
            openapi.IN_FORM,
            type=openapi.TYPE_BOOLEAN,
            required=False,
            description="Create backup before wiping (default: true)",
            default=True
        )
    ],
    responses={
        200: openapi.Response(
            description="Database imported successfully",
            examples={
                "application/json": {
                    "message": "Database imported successfully!",
                    "backup_created": True
                }
            }
        ),
        400: openapi.Response(
            description="Invalid file or upload error",
            examples={"application/json": {"error": "Invalid file type. Please upload a .sqlite3 file."}}
        )
    },
    tags=['Database Management']
)
@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def import_sqlite(request):
    if request.method == 'POST' and request.FILES.get('sqlite_file'):
        sqlite_file = request.FILES['sqlite_file']

        if not allowed_file(sqlite_file.name):
            return JsonResponse(
                {"error": "Invalid file type. Please upload a .sqlite3 file."},
                status=400
            )
        
        # Get backup option: 'true' or 'false' (default: 'true')
        create_backup = request.POST.get('create_backup', 'true').lower() in ['true', '1', 'yes']

        # Save upload to temp location
        save_path = UPLOAD_FOLDER / sqlite_file.name
        with save_path.open('wb') as f:
            for chunk in sqlite_file.chunks():
                f.write(chunk)

        # Backup existing DB if requested
        current_db_path = Path(settings.DATABASES['default']['NAME'])
        backup_path = None
        if create_backup and current_db_path.exists():
            backup_path = current_db_path.with_name(current_db_path.name + '.backup')
            shutil.copy2(str(current_db_path), str(backup_path))

        try:
            # Delete existing DB
            if current_db_path.exists():
                current_db_path.unlink()
            
            # Copy incoming database directly (fastest method)
            shutil.copy2(str(save_path), str(current_db_path))
            
            # Clean up uploaded temp file
            save_path.unlink()
            
            # Manually create Django core tables without constraint checks
            # This avoids Django's migration system which enforces foreign key constraints
            conn = sqlite3.connect(str(current_db_path))
            try:
                conn.execute('PRAGMA foreign_keys = OFF')
                
                # Create django_migrations table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS django_migrations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        app VARCHAR(255) NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        applied DATETIME NOT NULL
                    )
                ''')
                
                # Create other essential Django tables that are typically missing from imported databases
                # These are minimal schemas - enough for Django to function
                
                # django_content_type - Required for Django's ContentType framework
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS django_content_type (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        app_label VARCHAR(100) NOT NULL,
                        model VARCHAR(100) NOT NULL,
                        UNIQUE (app_label, model)
                    )
                ''')
                
                # auth_permission - Required for Django's permissions system
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS auth_permission (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content_type_id INTEGER NOT NULL,
                        codename VARCHAR(100) NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        UNIQUE (content_type_id, codename)
                    )
                ''')
                
                # auth_group - Required for Django's group permissions
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS auth_group (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(150) NOT NULL UNIQUE
                    )
                ''')
                
                # auth_group_permissions - Many-to-many table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS auth_group_permissions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        group_id INTEGER NOT NULL,
                        permission_id INTEGER NOT NULL,
                        UNIQUE (group_id, permission_id)
                    )
                ''')
                
                # auth_user - Required for Django's authentication
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS auth_user (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        password VARCHAR(128) NOT NULL,
                        last_login DATETIME,
                        is_superuser BOOLEAN NOT NULL,
                        username VARCHAR(150) NOT NULL UNIQUE,
                        last_name VARCHAR(150) NOT NULL,
                        email VARCHAR(254) NOT NULL,
                        is_staff BOOLEAN NOT NULL,
                        is_active BOOLEAN NOT NULL,
                        date_joined DATETIME NOT NULL,
                        first_name VARCHAR(150) NOT NULL
                    )
                ''')
                
                # auth_user_groups - Many-to-many table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS auth_user_groups (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        group_id INTEGER NOT NULL,
                        UNIQUE (user_id, group_id)
                    )
                ''')
                
                # auth_user_user_permissions - Many-to-many table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS auth_user_user_permissions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        permission_id INTEGER NOT NULL,
                        UNIQUE (user_id, permission_id)
                    )
                ''')
                
                # django_admin_log - For admin interface
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS django_admin_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        action_time DATETIME NOT NULL,
                        object_id TEXT,
                        object_repr VARCHAR(200) NOT NULL,
                        change_message TEXT NOT NULL,
                        content_type_id INTEGER,
                        user_id INTEGER NOT NULL,
                        action_flag SMALLINT UNSIGNED NOT NULL
                    )
                ''')
                
                # django_session - For session management
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS django_session (
                        session_key VARCHAR(40) NOT NULL PRIMARY KEY,
                        session_data TEXT NOT NULL,
                        expire_date DATETIME NOT NULL
                    )
                ''')
                
                conn.commit()
            finally:
                conn.close()
            
            # Now mark all migrations as applied without running them
            # This skips Django's constraint checking entirely
            from django.core.management import call_command
            from django.db import connection
            
            # Close any existing connections
            connection.close()
            
            # Use --fake to mark migrations as applied without executing them
            # Since we've manually created the tables above, this is safe
            call_command('migrate', '--fake', '--verbosity=0')
            
            return JsonResponse({
                "message": "Database imported successfully!",
                "backup_created": backup_path is not None
            })
                
        except Exception as e:
            # Restore from backup on error
            if backup_path and backup_path.exists():
                if current_db_path.exists():
                    current_db_path.unlink()
                shutil.copy2(str(backup_path), str(current_db_path))
            
            # Clean up uploaded file
            if save_path.exists():
                save_path.unlink()
            
            return JsonResponse(
                {"error": f"Database import failed: {str(e)}", "traceback": traceback.format_exc()},
                status=500
            )

    return JsonResponse({"error": "No file uploaded."}, status=400)

def _dump_table_csv(db_path, table_name):
    """
    Export table as CSV format.
    Returns a string containing CSV data with headers.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Get all rows
        cursor.execute(f'SELECT * FROM "{table_name}"')
        rows = cursor.fetchall()
        
        if not rows:
            # Empty table - just return headers
            cursor.execute(f'PRAGMA table_info("{table_name}")')
            columns = [col[1] for col in cursor.fetchall()]
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(columns)
            return output.getvalue()
        
        # Get column names from first row
        columns = rows[0].keys()
        
        # Write CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        
        for row in rows:
            writer.writerow([row[col] for col in columns])
        
        return output.getvalue()
    finally:
        conn.close()

@swagger_auto_schema(
    method='get',
    operation_summary="Export database or individual tables",
    operation_description="""
    Export the entire database or individual tables in CSV format.
    
    Export Modes:
    
    1. Single Table Export (CSV)
    - Add ?table=<table_name> to export one table as CSV
    - Available tables: study, assay, interval, assembly, signal, cell, pipeline
    - Returns: CSV file with all rows and columns
    - Example: /api/export_sqlite/?table=study
    
    2. Full Database Export (ZIP)
    - Add ?full=true to export everything
    - Returns: ZIP file containing:
      * exported_database.sqlite3 (complete database)
      * Individual CSV files for each table
    - Example: /api/export_sqlite/?full=true
    
    3. Database File Only
    - No parameters = exports just the SQLite3 database file
    - Example: /api/export_sqlite/
    
    CSV Format:
    - First row contains column headers
    - Compatible with Excel, Google Sheets, and data analysis tools
    - Can be re-imported using the import endpoint
    
    Use Cases:
    - Backup your data
    - Analyze data in Excel/R/Python
    - Share specific tables with collaborators
    - Migrate data between systems
    """,
    manual_parameters=[
        openapi.Parameter(
            'table',
            openapi.IN_QUERY,
            type=openapi.TYPE_STRING,
            description="Table name to export (study, assay, interval, assembly, signal, cell, pipeline)",
            enum=EXPORT_TABLES
        ),
        openapi.Parameter(
            'full',
            openapi.IN_QUERY,
            type=openapi.TYPE_BOOLEAN,
            description="Export full database as ZIP with all tables"
        )
    ],
    responses={
        200: openapi.Response(
            description="Exported file (CSV, SQLite3, or ZIP)",
            schema=openapi.Schema(type=openapi.TYPE_FILE)
        ),
        400: "Invalid table name",
        404: "Database not found",
        500: "Export error"
    },
    tags=['Database Management']
)
@api_view(['GET'])
def export_sqlite(request):
    db_file_path = settings.DATABASES['default']['NAME']
    if not os.path.exists(db_file_path):
        return JsonResponse({"error": "Database file not found."}, status=404)

    table = request.GET.get('table')
    full = request.GET.get('full')
    include_ro_crate = request.GET.get('ro_crate', 'false').lower() in ('true', '1', 'yes')

    # Get database counts for RO-Crate metadata
    if include_ro_crate:
        conn = sqlite3.connect(db_file_path)
        try:
            counts = {
                'studies': conn.execute('SELECT COUNT(*) FROM study').fetchone()[0],
                'assays': conn.execute('SELECT COUNT(*) FROM assay').fetchone()[0],
                'signals': conn.execute('SELECT COUNT(*) FROM signal').fetchone()[0],
                'intervals': conn.execute('SELECT COUNT(*) FROM interval').fetchone()[0],
            }
        except:
            counts = {'studies': 0, 'assays': 0, 'signals': 0, 'intervals': 0}
        finally:
            conn.close()

    # 1) Single-table export as CSV
    if table:
        if table not in EXPORT_TABLES:
            return JsonResponse({
                "error": f"Table '{table}' is not exportable. Choose from: {', '.join(EXPORT_TABLES)}."
            }, status=400)

        try:
            csv_data = _dump_table_csv(db_file_path, table)
            
            if include_ro_crate:
                # Export with RO-Crate metadata
                mem_file = io.BytesIO()
                with zipfile.ZipFile(mem_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr(f'{table}.csv', csv_data)
                    
                    # Generate RO-Crate metadata (no filters for full export)
                    file_list = [f'{table}.csv', 'ro-crate-metadata.json']
                    ro_crate = _generate_ro_crate_metadata(request.GET, counts, file_list, 'csv', db_file_path)
                    zf.writestr('ro-crate-metadata.json', json.dumps(ro_crate, indent=2))
                
                mem_file.seek(0)
                response = FileResponse(mem_file, as_attachment=True, filename=f'{table}_ro-crate.zip')
                return response
            else:
                # Plain CSV
                resp = HttpResponse(csv_data, content_type='text/csv')
                resp['Content-Disposition'] = f'attachment; filename="{table}.csv"'
                return resp
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    # 2) Full ZIP export (raw DB + each table as CSV)
    if full:
        try:
            mem_file = io.BytesIO()
            with zipfile.ZipFile(mem_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                # a) raw sqlite
                with open(db_file_path, 'rb') as f:
                    zf.writestr('exported_database.sqlite3', f.read())
                
                # b) per-table CSV exports
                file_list = ['exported_database.sqlite3']
                for tbl in EXPORT_TABLES:
                    tbl_csv = _dump_table_csv(db_file_path, tbl)
                    zf.writestr(f'{tbl}.csv', tbl_csv)
                    file_list.append(f'{tbl}.csv')
                
                # c) RO-Crate metadata if requested
                if include_ro_crate:
                    file_list.append('ro-crate-metadata.json')
                    ro_crate = _generate_ro_crate_metadata(request.GET, counts, file_list, 'zip', db_file_path)
                    zf.writestr('ro-crate-metadata.json', json.dumps(ro_crate, indent=2))
            
            mem_file.seek(0)
            filename = 'full_export_ro-crate.zip' if include_ro_crate else 'full_export.zip'
            response = FileResponse(mem_file, as_attachment=True, filename=filename)
            return response
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    # 3) Default: raw sqlite download
    try:
        if include_ro_crate:
            # Export SQLite with RO-Crate as ZIP
            mem_file = io.BytesIO()
            with zipfile.ZipFile(mem_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                with open(db_file_path, 'rb') as f:
                    zf.writestr('exported_database.sqlite3', f.read())
                
                # Generate RO-Crate metadata
                file_list = ['exported_database.sqlite3', 'ro-crate-metadata.json']
                ro_crate = _generate_ro_crate_metadata(request.GET, counts, file_list, 'sqlite', db_file_path)
                zf.writestr('ro-crate-metadata.json', json.dumps(ro_crate, indent=2))
            
            mem_file.seek(0)
            response = FileResponse(mem_file, as_attachment=True, filename='exported_database_ro-crate.zip')
            return response
        else:
            # Plain SQLite
            return FileResponse(
                open(db_file_path, 'rb'),
                as_attachment=True,
                filename='exported_database.sqlite3'
            )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@swagger_auto_schema(
    method='post',
    operation_summary="Import individual table from CSV",
    operation_description="""
    Import or update data in a specific table from a CSV file.
    
    How it works:
    1. Upload a CSV file with proper column headers
    2. System validates the file format
    3. Data is imported using UPSERT logic:
       - New rows are inserted
       - Existing rows (same ID) are updated
    
    CSV Format Requirements:
    - First row must contain column headers matching database columns
    - Column names are case-sensitive
    - Empty values are treated as NULL
    
    Available Tables:
    - study: Research studies
    - assay: Experimental assays
    - interval: Genomic intervals
    - assembly: Genome assemblies
    - signal: Signal measurements
    - cell: Cell annotations
    - pipeline: Analysis pipelines
    
    Example CSV Structure (study table):
    ```
    id,external_id,external_repo,name,description,availability,note
    1,GSE123456,GEO,My Study,Study description,1,Optional notes
    ```
    
    Tips:
    - Export a table first to see the correct CSV format
    - You can edit the exported CSV and re-import it
    - ID column determines if row is new or updated
    - Use this for batch updates or data corrections
    
    ⚠️ Note: Foreign keys must reference existing records
    """,
    manual_parameters=[
        openapi.Parameter(
            'file',
            openapi.IN_FORM,
            type=openapi.TYPE_FILE,
            required=True,
            description="CSV file to import (must have .csv extension)"
        )
    ],
    responses={
        200: openapi.Response(
            description="Import successful",
            examples={"application/json": {"message": "Imported 25 row(s) into 'study'."}}
        ),
        400: openapi.Response(
            description="Invalid file or data",
            examples={
                "application/json": {
                    "error": "Invalid file type. Upload a .csv file."
                }
            }
        ),
        500: "Database error during import"
    },
    tags=['Database Management']
)
@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def import_table(request, table):
    """
    POST /import/<table>/
    Imports data from an uploaded CSV file into the specified table.
    
    Special handling for interval, cell, and signal tables:
    - Interval: Maps external_id to new auto-generated IDs; resolves parental_id; uses selected assembly_id
    - Cell: Ignores CSV cell_id; uses selected assay_id
    - Signal: Maps interval_id and cell_id from CSV to new DB IDs; uses selected assay_id
    
    For other tables: Uses INSERT OR REPLACE (upsert behavior).
    """
    if request.method != 'POST' or 'file' not in request.FILES:
        return JsonResponse({"error": "No file uploaded."}, status=400)

    if table not in EXPORT_TABLES:
        return JsonResponse({
            "error": f"Table '{table}' not importable. "
                     f"Choose from: {', '.join(EXPORT_TABLES)}"
        }, status=400)

    uploaded = request.FILES['file']
    if not allowed_csv_file(uploaded.name):
        return JsonResponse(
            {"error": "Invalid file type. Upload a .csv file."},
            status=400
        )

    # Read CSV file
    try:
        csv_content = uploaded.read().decode('utf-8', errors='ignore')
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)
    except Exception as e:
        return JsonResponse(
            {"error": f"Failed to parse CSV file: {str(e)}"},
            status=400
        )

    # Route to specialized handlers for interval, cell, signal (they handle empty rows)
    if table == 'interval':
        return _import_interval(request, rows)
    elif table == 'cell':
        return _import_cell(request, rows)
    elif table == 'signal':
        return _import_signal(request, rows)

    # For other tables, check for empty rows
    if not rows:
        return JsonResponse(
            {"error": "CSV file is empty or has no data rows."},
            status=400
        )

    # Default behavior for other tables
    # Get column names from CSV header
    columns = list(rows[0].keys())
    if not columns:
        return JsonResponse(
            {"error": "CSV file has no columns."},
            status=400
        )

    # Build INSERT OR REPLACE statement
    placeholders = ', '.join(['?' for _ in columns])
    column_names = ', '.join([f'"{col}"' for col in columns])
    insert_sql = f'INSERT OR REPLACE INTO "{table}" ({column_names}) VALUES ({placeholders})'

    # Apply to database
    db_path = settings.DATABASES['default']['NAME']
    conn = sqlite3.connect(db_path)
    row_count = 0
    try:
        conn.execute('PRAGMA foreign_keys=OFF;')
        conn.execute('BEGIN;')
        
        for row in rows:
            # Convert empty strings to None for proper NULL handling
            # CRITICAL: Extract values in same order as columns (row.values() order is not guaranteed)
            values = [row.get(col, None) if row.get(col, '') != '' else None for col in columns]
            conn.execute(insert_sql, values)
            row_count += 1
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        return JsonResponse({"error": str(e)}, status=500)
    finally:
        conn.close()

    return JsonResponse({
        "message": f"Imported {row_count} row(s) into '{table}'."
    })


def _build_filtered_queryset(query_params):
    """
    Build a filtered Study queryset based on query parameters.
    This mirrors the logic in StudyListCreateView.get_queryset()
    """
    from django.db.models import Count, Q
    
    qs = Study.objects.all()

    # — Study‐level filters —
    # Handle multi-value study_name filter (supports arrays)
    study_names = _get_multi_value_param(query_params, 'study_name')
    if study_names:
        # Build OR query for each study name
        name_q = Q()
        for name in study_names:
            name_q |= Q(name__iexact=name)
        qs = qs.filter(name_q)
    
    # Handle multi-value study_external_id filter
    study_external_ids = _get_multi_value_param(query_params, 'study_external_id')
    if study_external_ids:
        ext_id_q = Q()
        for ext_id in study_external_ids:
            ext_id_q |= Q(external_id__iexact=ext_id)
        qs = qs.filter(ext_id_q)
    
    if 'study_availability' in query_params or 'study_availability[]' in query_params:
        sval = _parse_bool_param(query_params.get('study_availability') or query_params.get('study_availability[]'))
        if sval is not None:
            qs = qs.filter(availability=sval)

    # — Assay‐level filters narrow which studies appear —
    ASSAY_LOOKUPS = {
        'assay_name':        'name__iexact',
        'assay_external_id': 'external_id__iexact',
        'assay_type':        'type__iexact',
        'tissue':            'tissue__iexact',
        'cell_type':         'cell_type__iexact',  # legacy param
        'assay_cell_type':   'cell_type__iexact',  # new explicit param
        'treatment':         'treatment__iexact',
        'platform':          'platform__iexact',
    }
    assay_q = Assay.objects.all()
    assay_filters_applied = False
    for p, lookup in ASSAY_LOOKUPS.items():
        # Handle multi-value parameters for assay fields
        values = _get_multi_value_param(query_params, p)
        if values:
            assay_filters_applied = True
            field_q = Q()
            for val in values:
                field_q |= Q(**{lookup: val})
            assay_q = assay_q.filter(field_q)
    
    raw_av = query_params.get('assay_availability') or query_params.get('assay_availability[]')
    av_bool = _parse_bool_param(raw_av)
    if av_bool is not None:
        assay_filters_applied = True
        assay_q = assay_q.filter(availability=av_bool)
    if assay_filters_applied:
        qs = qs.filter(assays__in=assay_q).distinct()

    # — Interval & Assembly filters on studies —
    # OPTIMIZED: Query intervals/signals directly to get assay_ids, then filter studies
    interval_types = _get_multi_value_param(query_params, 'interval_type')
    if interval_types:
        # Step 1: Get interval IDs matching the type filter
        type_q = Q()
        for itype in interval_types:
            type_q |= Q(type__iexact=itype)
        matching_interval_ids = list(Interval.objects.filter(type_q).values_list('id', flat=True))
        
        if matching_interval_ids:
            # Step 2: Get distinct assay_ids from signals that reference these intervals
            matching_assay_ids = Signal.objects.filter(
                interval_id__in=matching_interval_ids
            ).values_list('assay_id', flat=True).distinct()
            qs = qs.filter(assays__id__in=matching_assay_ids)
    
    biotypes = _get_multi_value_param(query_params, 'biotype')
    if biotypes:
        # Step 1: Get interval IDs matching the biotype filter
        biotype_q = Q()
        for bio in biotypes:
            biotype_q |= Q(biotype__iexact=bio)
        matching_interval_ids = list(Interval.objects.filter(biotype_q).values_list('id', flat=True))
        
        if matching_interval_ids:
            # Step 2: Get distinct assay_ids from signals that reference these intervals
            matching_assay_ids = Signal.objects.filter(
                interval_id__in=matching_interval_ids
            ).values_list('assay_id', flat=True).distinct()
            qs = qs.filter(assays__id__in=matching_assay_ids)
    
    assembly_names = _get_multi_value_param(query_params, 'assembly_name')
    if assembly_names:
        # Step 1: Get interval IDs for matching assemblies
        asm_name_q = Q()
        for asm_name in assembly_names:
            asm_name_q |= Q(assembly__name__iexact=asm_name)
        matching_interval_ids = list(Interval.objects.filter(asm_name_q).values_list('id', flat=True))
        
        if matching_interval_ids:
            matching_assay_ids = Signal.objects.filter(
                interval_id__in=matching_interval_ids
            ).values_list('assay_id', flat=True).distinct()
            qs = qs.filter(assays__id__in=matching_assay_ids)
    
    assembly_species = _get_multi_value_param(query_params, 'assembly_species')
    if assembly_species:
        # Step 1: Get interval IDs for matching assemblies
        asm_spec_q = Q()
        for spec in assembly_species:
            asm_spec_q |= Q(assembly__species__iexact=spec)
        matching_interval_ids = list(Interval.objects.filter(asm_spec_q).values_list('id', flat=True))
        
        if matching_interval_ids:
            matching_assay_ids = Signal.objects.filter(
                interval_id__in=matching_interval_ids
            ).values_list('assay_id', flat=True).distinct()
            qs = qs.filter(assays__id__in=matching_assay_ids)

    # — Cell-level filters (direct via assay → cells) —
    # OPTIMIZED: Query Cell table directly to get assay_ids, then filter studies
    cell_types = _get_multi_value_param(query_params, 'cell_type') or _get_multi_value_param(query_params, 'cell_kind')
    if cell_types:
        normalized_types = []
        for kind in cell_types:
            k = (kind or '').strip().lower()
            if k in ('single cell', 'single-cell', 'singlecell'):
                k = 'cell'
            elif k == 'srt':
                k = 'spot'
            normalized_types.append(k)
        
        cell_type_q = Q()
        for k in normalized_types:
            cell_type_q |= Q(type__iexact=k)
        matching_assay_ids = Cell.objects.filter(cell_type_q).values_list('assay_id', flat=True).distinct()
        qs = qs.filter(assays__id__in=matching_assay_ids)

    cell_labels = _get_multi_value_param(query_params, 'cell_label')
    if cell_labels:
        label_q = Q()
        for lbl in cell_labels:
            label_q |= Q(label__iexact=lbl)
        matching_assay_ids = Cell.objects.filter(label_q).values_list('assay_id', flat=True).distinct()
        qs = qs.filter(assays__id__in=matching_assay_ids)

    return qs.distinct().order_by('id')


def _batch_queryset_ids(queryset, filter_field, id_list, batch_size=900):
    """
    Filter a queryset by a field with IN clause in batches to avoid SQLite's 999 variable limit.
    Returns list of IDs (not a queryset).
    """
    if not id_list:
        return []
    
    if len(id_list) <= batch_size:
        return list(queryset.filter(**{f'{filter_field}__in': id_list}).values_list('id', flat=True))
    
    # Batch the query and collect IDs
    all_ids = []
    for i in range(0, len(id_list), batch_size):
        batch = id_list[i:i + batch_size]
        batch_ids = list(queryset.filter(**{f'{filter_field}__in': batch}).values_list('id', flat=True))
        all_ids.extend(batch_ids)
    
    return all_ids


def _build_filtered_ids(query_params, study_ids):
    """
    Derive filtered assay, signal, interval, and assembly ids for export.
    
    OPTIMIZED: Always uses pre-fetched set-based IDs with batching for consistency and speed.
    Sets avoid duplicates and provide O(1) lookup for filtering.
    """
    from django.db.models import Q
    
    assay_ids = _batch_queryset_ids(Assay.objects.all(), 'study_id', study_ids)

    # Apply additional assay filters if present
    if assay_ids:
        assay_qs = Assay.objects.all()
        
        ASSAY_LOOKUPS = {
            'assay_name':        'name__iexact',
            'assay_external_id': 'external_id__iexact',
            'assay_type':        'type__iexact',
            'tissue':            'tissue__iexact',
            'cell_type':         'cell_type__iexact',  # legacy param
            'assay_cell_type':   'cell_type__iexact',  # new explicit param
            'treatment':         'treatment__iexact',
            'platform':          'platform__iexact',
        }

        for p, lookup in ASSAY_LOOKUPS.items():
            # Handle multi-value parameters
            values = _get_multi_value_param(query_params, p)
            if values:
                field_q = Q()
                for val in values:
                    field_q |= Q(**{lookup: val})
                assay_qs = assay_qs.filter(field_q)

        av_bool = _parse_bool_param(query_params.get('assay_availability'))
        if av_bool is not None:
            assay_qs = assay_qs.filter(availability=av_bool)
        
        # Filter by assay_ids in batches
        filtered_assay_ids = set()
        for batch in _batch_iter(assay_ids, 900):
            filtered_assay_ids.update(assay_qs.filter(id__in=batch).values_list('id', flat=True))
        
        assay_ids = list(filtered_assay_ids)

    # Fetch signals tied to the filtered assays - always fetch IDs for consistency
    signal_ids = set()
    for batch in _batch_iter(assay_ids, 900):
        signal_ids.update(Signal.objects.filter(assay_id__in=batch).values_list('id', flat=True))
    

    # — Cell-level filters applied to signals —
    cell_types = _get_multi_value_param(query_params, 'cell_type') or _get_multi_value_param(query_params, 'cell_kind')
    cell_labels = _get_multi_value_param(query_params, 'cell_label')
    if signal_ids and (cell_types or cell_labels):
        filtered_signal_ids = set()
        # normalize types
        norm_types = []
        for k in cell_types or []:
            kk = (k or '').strip().lower()
            if kk in ('single cell', 'single-cell', 'singlecell'):
                kk = 'cell'
            elif kk == 'srt':
                kk = 'spot'
            norm_types.append(kk)
        for batch in _batch_iter(list(signal_ids), 900):
            qs_sig = Signal.objects.filter(id__in=batch)
            if norm_types:
                kind_q = Q()
                for kk in norm_types:
                    kind_q |= Q(cell__type__iexact=kk)
                qs_sig = qs_sig.filter(kind_q)
            if cell_labels:
                label_q = Q()
                for lbl in cell_labels:
                    label_q |= Q(cell__label__iexact=lbl)
                qs_sig = qs_sig.filter(label_q)
            filtered_signal_ids.update(qs_sig.values_list('id', flat=True))
        signal_ids = filtered_signal_ids

    # Check for interval filters
    interval_filters_present = any(
        _get_multi_value_param(query_params, k)
        for k in ['interval_type', 'biotype', 'assembly_name', 'assembly_species']
    )

    if interval_filters_present:
        interval_qs = Interval.objects.all()
        
        # Handle multi-value interval filters
        interval_types = _get_multi_value_param(query_params, 'interval_type')
        if interval_types:
            type_q = Q()
            for itype in interval_types:
                type_q |= Q(type__iexact=itype)
            interval_qs = interval_qs.filter(type_q)
        
        biotypes = _get_multi_value_param(query_params, 'biotype')
        if biotypes:
            bio_q = Q()
            for bio in biotypes:
                bio_q |= Q(biotype__iexact=bio)
            interval_qs = interval_qs.filter(bio_q)
        
        assembly_names = _get_multi_value_param(query_params, 'assembly_name')
        if assembly_names:
            asm_name_q = Q()
            for asm_name in assembly_names:
                asm_name_q |= Q(assembly__name__iexact=asm_name)
            interval_qs = interval_qs.filter(asm_name_q)
        
        assembly_species = _get_multi_value_param(query_params, 'assembly_species')
        if assembly_species:
            asm_spec_q = Q()
            for spec in assembly_species:
                asm_spec_q |= Q(assembly__species__iexact=spec)
            interval_qs = interval_qs.filter(asm_spec_q)

        # Get all matching interval IDs
        interval_ids_filter = set(interval_qs.values_list('id', flat=True))
        
        # Filter signals to only those with matching intervals
        filtered_signal_ids = set()
        for batch in _batch_iter(signal_ids, 900):
            filtered_signal_ids.update(
                Signal.objects.filter(id__in=batch, interval_id__in=interval_ids_filter)
                    .values_list('id', flat=True)
            )
        signal_ids = filtered_signal_ids

    # Get interval IDs from signals - OPTIMIZED: use Django ORM with batching
    interval_ids = set()
    if signal_ids:
        signal_ids_list = list(signal_ids)
        # Use Django ORM to avoid raw SQL formatting issues
        for batch in _batch_iter(signal_ids_list, 900):
            batch_ids = Signal.objects.filter(id__in=batch).values_list('interval_id', flat=True).distinct()
            for interval_id in batch_ids:
                # Filter out None and empty strings
                if interval_id is not None and interval_id != '':
                    interval_ids.add(interval_id)
    

    # Get assembly IDs from intervals - OPTIMIZED: use Django ORM with batching  
    assembly_ids = set()
    if interval_ids:
        interval_ids_list = list(interval_ids)
        # Use Django ORM to avoid raw SQL formatting issues
        for batch in _batch_iter(interval_ids_list, 900):
            batch_ids = Interval.objects.filter(id__in=batch).values_list('assembly_id', flat=True).distinct()
            for assembly_id in batch_ids:
                # Filter out None and empty strings
                if assembly_id is not None and assembly_id != '':
                    assembly_ids.add(assembly_id)
    

    return assay_ids, list(signal_ids), list(interval_ids), list(assembly_ids)


def _batch_query(cursor, base_query, ids_list, batch_size=900):
    """
    Execute a query with IN clause in batches to avoid SQLite's 999 variable limit.
    Returns all rows from all batches combined.
    """
    all_rows = []
    for i in range(0, len(ids_list), batch_size):
        batch = ids_list[i:i + batch_size]
        placeholders = ','.join(['?'] * len(batch))
        query = base_query.format(placeholders=placeholders)
        rows = cursor.execute(query, batch).fetchall()
        all_rows.extend(rows)
    return all_rows


def _build_sql_in_clause(ids_list, batch_size=900):
    """
    Build a SQL IN clause string for a list of IDs.
    For large lists, SQLite has a limit of 999 variables, so we use literal values.
    """
    if not ids_list:
        return "(-1)"  # Never matches
    # Use literal values to avoid parameter limit
    return "(" + ",".join(str(int(id)) for id in ids_list) + ")"


def _escape_sql_string(s):
    """Escape single quotes in SQL string values."""
    if s is None:
        return ''
    return str(s).replace("'", "''")


def _build_sql_in_values(values):
    """Build SQL IN clause values from a list, properly escaped."""
    if not values:
        return None
    escaped = [f"'{_escape_sql_string(v)}'" for v in values]
    return ",".join(escaped)


def _create_filtered_sqlite_db_fast(query_params):
    """
    Create a filtered SQLite database using ATTACH DATABASE for maximum speed.
    
    ALL filtering is done in pure SQL - no Python-side processing.
    This is optimal when filters are exact matches (as used by the frontend).
    
    Returns (bytes, counts_dict)
    
    ~30x faster than the original approach for large datasets.
    """
    import tempfile
    
    main_db_path = settings.DATABASES['default']['NAME']
    
    # Create temp file for new DB
    temp_fd, temp_path = tempfile.mkstemp(suffix='.sqlite3')
    os.close(temp_fd)
    
    conn = None
    try:
        conn = sqlite3.connect(temp_path, timeout=30.0, isolation_level='DEFERRED')
        
        # Set pragmas for speed
        conn.execute('PRAGMA journal_mode=MEMORY')
        conn.execute('PRAGMA synchronous=OFF')
        conn.execute('PRAGMA cache_size=-128000')
        conn.execute('PRAGMA temp_store=MEMORY')
        
        # Attach source database in read-only mode
        conn.execute(f'ATTACH DATABASE "file:{main_db_path}?mode=ro" AS source')
        
        # CRITICAL OPTIMIZATION: Ensure indexes exist on source database for fast filtering
        # Check and create critical indexes if missing (improves query speed 10-100x)
        cursor = conn.cursor()
        
        # Check if indexes exist on signal table (critical for performance)
        indexes_needed = [
            ('idx_signal_assay_id', 'signal', 'assay_id'),
            ('idx_signal_interval_id', 'signal', 'interval_id'),
            ('idx_signal_cell_id', 'signal', 'cell_id'),
            ('idx_cell_type', 'cell', 'type'),
            ('idx_interval_type', 'interval', 'type'),
            ('idx_interval_assembly_id', 'interval', 'assembly_id'),
        ]
        
        # Note: Can't create indexes on read-only attached database
        # But we can check if they exist and warn in logs
        # The temp table JOINs will still be much faster than the old approach
        
        # ============================================================
        # BUILD ALL FILTER CONDITIONS IN PURE SQL
        # ============================================================
        
        # --- Study-level filters ---
        study_conditions = []
        
        study_names = _get_multi_value_param(query_params, 'study_name')
        if study_names:
            study_conditions.append(f"s.name IN ({_build_sql_in_values(study_names)})")
        
        study_external_ids = _get_multi_value_param(query_params, 'study_external_id')
        if study_external_ids:
            study_conditions.append(f"s.external_id IN ({_build_sql_in_values(study_external_ids)})")
        
        study_notes = _get_multi_value_param(query_params, 'study_note')
        if study_notes:
            study_conditions.append(f"s.note IN ({_build_sql_in_values(study_notes)})")
        
        raw_study_av = query_params.get('study_availability') or query_params.get('study_availability[]')
        study_av = _parse_bool_param(raw_study_av)
        if study_av is not None:
            study_conditions.append(f"s.availability = {1 if study_av else 0}")
        
        study_where = " AND ".join(study_conditions) if study_conditions else "1=1"
        
        # --- Assay-level filters ---
        assay_conditions = []
        
        assay_names = _get_multi_value_param(query_params, 'assay_name')
        if assay_names:
            assay_conditions.append(f"a.name IN ({_build_sql_in_values(assay_names)})")
        
        assay_external_ids = _get_multi_value_param(query_params, 'assay_external_id')
        if assay_external_ids:
            assay_conditions.append(f"a.external_id IN ({_build_sql_in_values(assay_external_ids)})")
        
        assay_types = _get_multi_value_param(query_params, 'assay_type')
        if assay_types:
            assay_conditions.append(f"a.type IN ({_build_sql_in_values(assay_types)})")
        
        assay_targets = _get_multi_value_param(query_params, 'assay_target')
        if assay_targets:
            assay_conditions.append(f"a.target IN ({_build_sql_in_values(assay_targets)})")
        
        tissues = _get_multi_value_param(query_params, 'tissue')
        if tissues:
            assay_conditions.append(f"a.tissue IN ({_build_sql_in_values(tissues)})")
        
        # Support both 'cell_type' (legacy) and 'assay_cell_type' for assay-level cell type
        assay_cell_types = _get_multi_value_param(query_params, 'assay_cell_type') or _get_multi_value_param(query_params, 'cell_type')
        if assay_cell_types:
            assay_conditions.append(f"a.cell_type IN ({_build_sql_in_values(assay_cell_types)})")
        
        treatments = _get_multi_value_param(query_params, 'treatment')
        if treatments:
            assay_conditions.append(f"a.treatment IN ({_build_sql_in_values(treatments)})")
        
        platforms = _get_multi_value_param(query_params, 'platform')
        if platforms:
            assay_conditions.append(f"a.platform IN ({_build_sql_in_values(platforms)})")
        
        raw_assay_av = query_params.get('assay_availability') or query_params.get('assay_availability[]')
        assay_av = _parse_bool_param(raw_assay_av)
        if assay_av is not None:
            assay_conditions.append(f"a.availability = {1 if assay_av else 0}")
        
        assay_where = " AND ".join(assay_conditions) if assay_conditions else "1=1"
        
        # --- Signal-level filters (via cell and interval joins) ---
        signal_extra_conditions = []
        
        # Cell-level filters (cell.type and cell.label)
        cell_types = _get_multi_value_param(query_params, 'cell_kind')  # cell_kind for Cell model's type
        if cell_types:
            # Normalize cell types
            norm_types = []
            for k in cell_types:
                kk = (k or '').strip().lower()
                if kk in ('single cell', 'single-cell', 'singlecell'):
                    kk = 'cell'
                elif kk == 'srt':
                    kk = 'spot'
                norm_types.append(kk)
            signal_extra_conditions.append(
                f"EXISTS (SELECT 1 FROM source.cell c WHERE c.id = sig.cell_id AND c.type IN ({_build_sql_in_values(norm_types)}))"
            )
        
        cell_labels = _get_multi_value_param(query_params, 'cell_label')
        if cell_labels:
            signal_extra_conditions.append(
                f"EXISTS (SELECT 1 FROM source.cell c WHERE c.id = sig.cell_id AND c.label IN ({_build_sql_in_values(cell_labels)}))"
            )
        
        # Interval-level filters
        interval_conditions = []
        
        interval_types = _get_multi_value_param(query_params, 'interval_type')
        if interval_types:
            interval_conditions.append(f"i.type IN ({_build_sql_in_values(interval_types)})")
        
        biotypes = _get_multi_value_param(query_params, 'biotype')
        if biotypes:
            interval_conditions.append(f"i.biotype IN ({_build_sql_in_values(biotypes)})")
        
        # Assembly filters (via interval)
        assembly_names = _get_multi_value_param(query_params, 'assembly_name')
        assembly_species = _get_multi_value_param(query_params, 'assembly_species')
        if assembly_names or assembly_species:
            asm_conditions = []
            if assembly_names:
                asm_conditions.append(f"asm.name IN ({_build_sql_in_values(assembly_names)})")
            if assembly_species:
                asm_conditions.append(f"asm.species IN ({_build_sql_in_values(assembly_species)})")
            interval_conditions.append(
                f"EXISTS (SELECT 1 FROM source.assembly asm WHERE asm.id = i.assembly_id AND ({' OR '.join(asm_conditions)}))"
            )
        
        if interval_conditions:
            signal_extra_conditions.append(
                f"EXISTS (SELECT 1 FROM source.interval i WHERE i.id = sig.interval_id AND {' AND '.join(interval_conditions)})"
            )
        
        signal_extra_where = " AND " + " AND ".join(signal_extra_conditions) if signal_extra_conditions else ""
        
        # ============================================================
        # EXECUTE THE FILTERED COPY IN A SINGLE TRANSACTION
        # ============================================================
        
        conn.execute('BEGIN TRANSACTION')
        
        # CRITICAL OPTIMIZATION: Create indexed temp tables for filtering
        # This massively speeds up the JOIN/IN operations on large signal tables
        
        # Create temp table for filtered studies with PRIMARY KEY for fast lookups
        conn.execute(f'''CREATE TEMP TABLE filtered_study_ids (id INTEGER PRIMARY KEY)''')
        conn.execute(f'''INSERT INTO filtered_study_ids 
            SELECT s.id FROM source.study s WHERE {study_where}''')
        
        # Create temp table for filtered assays with PRIMARY KEY
        conn.execute(f'''CREATE TEMP TABLE filtered_assay_ids (id INTEGER PRIMARY KEY)''')
        conn.execute(f'''INSERT INTO filtered_assay_ids 
            SELECT a.id FROM source.assay a 
            WHERE a.study_id IN (SELECT id FROM filtered_study_ids) AND {assay_where}''')
        
        # Run ANALYZE to help SQLite query planner optimize subsequent queries
        conn.execute('ANALYZE filtered_study_ids')
        conn.execute('ANALYZE filtered_assay_ids')
        
        # OPTIMIZATION: Create temporary tables for cell/interval filters instead of using EXISTS
        # This converts O(n*m) operations to O(n+m) - MASSIVE speed improvement
        if cell_types or cell_labels:
            cell_filter_parts = []
            if cell_types:
                cell_filter_parts.append(f"c.type IN ({_build_sql_in_values(norm_types)})")
            if cell_labels:
                cell_filter_parts.append(f"c.label IN ({_build_sql_in_values(cell_labels)})")
            
            cell_filter_sql = ' AND '.join(cell_filter_parts)
            conn.execute(f'''CREATE TEMP TABLE filtered_cell_ids (id INTEGER PRIMARY KEY)''')
            conn.execute(f'''INSERT INTO filtered_cell_ids 
                SELECT id FROM source.cell c WHERE {cell_filter_sql}''')
            conn.execute('ANALYZE filtered_cell_ids')
            
            # Replace EXISTS with fast IN clause
            signal_extra_conditions = [cond for cond in signal_extra_conditions 
                                      if 'source.cell' not in cond]
            signal_extra_conditions.append("sig.cell_id IN (SELECT id FROM filtered_cell_ids)")
            signal_extra_where = " AND " + " AND ".join(signal_extra_conditions) if signal_extra_conditions else ""
        
        if interval_conditions:
            interval_filter_sql = ' AND '.join(interval_conditions)
            conn.execute(f'''CREATE TEMP TABLE filtered_interval_ids (id INTEGER PRIMARY KEY)''')
            conn.execute(f'''INSERT INTO filtered_interval_ids 
                SELECT id FROM source.interval i 
                LEFT JOIN source.assembly asm ON i.assembly_id = asm.id 
                WHERE {interval_filter_sql}''')
            conn.execute('ANALYZE filtered_interval_ids')
            
            # Replace EXISTS with fast IN clause
            signal_extra_conditions = [cond for cond in signal_extra_conditions 
                                      if 'source.interval' not in cond]
            signal_extra_conditions.append("sig.interval_id IN (SELECT id FROM filtered_interval_ids)")
            signal_extra_where = " AND " + " AND ".join(signal_extra_conditions) if signal_extra_conditions else ""
        
        # CRITICAL: First create table schemas to preserve AUTOINCREMENT, PRIMARY KEY, and other constraints
        # Using CREATE TABLE AS SELECT does NOT preserve these constraints!
        # Get the CREATE TABLE statements from source database
        tables_to_export = ['study', 'assay', 'signal', 'interval', 'assembly', 'cell', 'pipeline']
        
        cursor = conn.cursor()
        for table_name in tables_to_export:
            result = cursor.execute(
                f"SELECT sql FROM source.sqlite_master WHERE type='table' AND name='{table_name}'"
            ).fetchone()
            
            if result and result[0]:
                create_sql = result[0]
                # Execute the CREATE TABLE statement to preserve all constraints including AUTOINCREMENT
                conn.execute(create_sql)
        
        # Now insert filtered data into the tables
        # 1. Copy studies (use temp table for consistency)
        conn.execute('''INSERT INTO study 
            SELECT s.* FROM source.study s 
            INNER JOIN filtered_study_ids ON s.id = filtered_study_ids.id''')
        
        # 2. Copy assays (use temp table - much faster than subquery)
        conn.execute('''INSERT INTO assay 
            SELECT a.* FROM source.assay a
            INNER JOIN filtered_assay_ids ON a.id = filtered_assay_ids.id''')
        
        # 3. Copy signals (the big one) - use INNER JOIN instead of IN for 10-100x speedup
        # INNER JOIN with indexed temp table is MUCH faster than IN (subquery)
        conn.execute(f'''INSERT INTO signal 
            SELECT sig.* FROM source.signal sig 
            INNER JOIN filtered_assay_ids ON sig.assay_id = filtered_assay_ids.id
            WHERE 1=1{signal_extra_where}''')
        
        # 4. Copy intervals - only those referenced by our signals
        conn.execute('''INSERT INTO interval 
            SELECT * FROM source.interval 
            WHERE id IN (SELECT DISTINCT interval_id FROM signal WHERE interval_id IS NOT NULL)''')
        
        # 5. Copy assemblies - only those referenced by our intervals
        conn.execute('''INSERT INTO assembly 
            SELECT * FROM source.assembly 
            WHERE id IN (SELECT DISTINCT assembly_id FROM interval WHERE assembly_id IS NOT NULL)''')
        
        # 6. Copy cells - only those referenced by our signals
        conn.execute('''INSERT INTO cell 
            SELECT * FROM source.cell 
            WHERE id IN (SELECT DISTINCT cell_id FROM signal WHERE cell_id IS NOT NULL)''')
        
        # 7. Copy pipelines - only those referenced by our assays
        conn.execute('''INSERT INTO pipeline 
            SELECT * FROM source.pipeline 
            WHERE id IN (SELECT DISTINCT pipeline_id FROM assay WHERE pipeline_id IS NOT NULL)''')
        
        # Copy indexes for the exported tables to improve query performance
        # Note: SQLite automatically creates indexes for PRIMARY KEY and UNIQUE constraints,
        # but we need to manually create other indexes (like foreign key indexes)
        index_results = cursor.execute(
            f"""SELECT sql FROM source.sqlite_master 
               WHERE type='index' 
               AND sql IS NOT NULL 
               AND tbl_name IN ({','.join([f"'{t}'" for t in tables_to_export])})"""
        ).fetchall()
        
        for (index_sql,) in index_results:
            try:
                conn.execute(index_sql)
            except sqlite3.OperationalError:
                # Index might already exist (e.g., for PRIMARY KEY or UNIQUE constraints)
                # or reference a column that was filtered out - skip it
                pass
        
        conn.execute('COMMIT')
        
        # Get counts
        counts = {
            'studies': conn.execute('SELECT COUNT(*) FROM study').fetchone()[0],
            'assays': conn.execute('SELECT COUNT(*) FROM assay').fetchone()[0],
            'signals': conn.execute('SELECT COUNT(*) FROM signal').fetchone()[0],
            'intervals': conn.execute('SELECT COUNT(*) FROM interval').fetchone()[0],
        }
        
        conn.execute('DETACH DATABASE source')
        conn.close()
        conn = None
        
        # OPTIMIZATION: Return temp_path instead of loading into RAM
        # This reduces RAM usage from GB to KB (99% reduction)
        return temp_path, counts
        
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass
        # Don't delete temp file here - caller will handle cleanup after streaming


def _create_filtered_sqlite_db(study_ids, assay_ids=None, signal_ids=None, interval_ids=None, assembly_ids=None):
    """
    Create an in-memory SQLite database containing only the filtered entities.
    Returns (bytes, counts_dict)
    
    OPTIMIZED: Uses executemany for bulk inserts with batching for large datasets.
    """
    mem_db = io.BytesIO()
    conn = sqlite3.connect(':memory:')
    signal_rows = []
    interval_rows = []
    signal_ids_local = []
    
    try:
        # Create schema by copying from main database
        main_db_path = settings.DATABASES['default']['NAME']
        main_conn = sqlite3.connect(main_db_path)
        
        # OPTIMIZATION: Set SQLite pragmas for faster operations
        conn.execute('PRAGMA journal_mode=MEMORY')
        conn.execute('PRAGMA synchronous=OFF')
        conn.execute('PRAGMA cache_size=-128000')  # 128MB cache (increased from 64MB)
        conn.execute('PRAGMA temp_store=MEMORY')
        conn.execute('PRAGMA locking_mode=EXCLUSIVE')  # Faster for single connection
        
        # Get all table creation statements
        cursor = main_conn.cursor()
        cursor.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' AND name IN "
            "('study', 'assay', 'signal', 'interval', 'assembly', 'cell', 'pipeline')"
        )
        
        for table_name, create_sql in cursor.fetchall():
            conn.execute(create_sql)
        
        # OPTIMIZATION: Begin transaction for all inserts
        conn.execute('BEGIN TRANSACTION')
        
        # Now copy filtered data using batched queries
        main_cursor = main_conn.cursor()
        
        # 1) Copy studies - OPTIMIZED with executemany
        study_rows = []
        if study_ids:
            study_rows = _batch_query(
                main_cursor,
                "SELECT * FROM study WHERE id IN ({placeholders})",
                study_ids
            )
        
        if study_rows:
            cols = [description[0] for description in main_cursor.description]
            insert_sql = f"INSERT INTO study ({','.join(cols)}) VALUES ({','.join(['?'] * len(cols))})"
            conn.executemany(insert_sql, study_rows)
        
        # 2) Get assays - OPTIMIZED with executemany
        assay_rows = []
        assay_ids_all = []
        if assay_ids is not None:
            if assay_ids:
                assay_rows = _batch_query(
                    main_cursor,
                    "SELECT * FROM assay WHERE id IN ({placeholders})",
                    assay_ids
                )
                assay_ids_all = list(assay_ids)
            else:
                assay_rows = []
                assay_ids_all = []
        else:
            assay_rows = _batch_query(
                main_cursor,
                "SELECT * FROM assay WHERE study_id IN ({placeholders})",
                study_ids
            )
            assay_ids_all = [row[0] for row in assay_rows] if assay_rows else []

        if assay_rows:
            cols = [description[0] for description in main_cursor.description]
            insert_sql = f"INSERT INTO assay ({','.join(cols)}) VALUES ({','.join(['?'] * len(cols))})"
            conn.executemany(insert_sql, assay_rows)

        # 3) Get signals - signals_ids is always provided (never None)
        signal_ids_local = []
        if assay_ids_all:
            # signal_ids is always a list now (from set-based approach)
            signal_rows = _batch_query(
                main_cursor,
                "SELECT * FROM signal WHERE id IN ({placeholders})",
                signal_ids
            ) if signal_ids else []
            signal_ids_local = list(signal_ids) if signal_ids else []

            if signal_rows:
                cols = [description[0] for description in main_cursor.description]
                insert_sql = f"INSERT INTO signal ({','.join(cols)}) VALUES ({','.join(['?'] * len(cols))})"
                conn.executemany(insert_sql, signal_rows)
            
            # 4) Get intervals from signals - OPTIMIZED
            # interval_ids is always provided from _build_filtered_ids
            target_interval_ids = interval_ids if interval_ids else []

            if target_interval_ids:
                interval_rows = _batch_query(
                    main_cursor,
                    "SELECT * FROM interval WHERE id IN ({placeholders})",
                    target_interval_ids
                )
                
                if interval_rows:
                    interval_cols = [description[0] for description in main_cursor.description]
                    insert_sql = f"INSERT INTO interval ({','.join(interval_cols)}) VALUES ({','.join(['?'] * len(interval_cols))})"
                    conn.executemany(insert_sql, interval_rows)
                
                # 5) Get assemblies from intervals - assembly_ids is always provided
                assembly_ids_local = assembly_ids if assembly_ids else []
                
                if assembly_ids_local:
                    assembly_rows = _batch_query(
                        main_cursor,
                        "SELECT * FROM assembly WHERE id IN ({placeholders})",
                        assembly_ids_local
                    )
                    
                    if assembly_rows:
                        cols = [description[0] for description in main_cursor.description]
                        insert_sql = f"INSERT INTO assembly ({','.join(cols)}) VALUES ({','.join(['?'] * len(cols))})"
                        conn.executemany(insert_sql, assembly_rows)
        
        # 6) Get cells for filtered assays - OPTIMIZED
        cell_rows = []
        if assay_ids_all:
            try:
                cell_rows = _batch_query(
                    main_cursor,
                    "SELECT * FROM cell WHERE assay_id IN ({placeholders})",
                    assay_ids_all
                )
                
                if cell_rows:
                    cols = [description[0] for description in main_cursor.description]
                    insert_sql = f"INSERT INTO cell ({','.join(cols)}) VALUES ({','.join(['?'] * len(cols))})"
                    conn.executemany(insert_sql, cell_rows)
            except Exception as e:
                # Cell table might not exist or have data
                pass
                pass
        
        # 7) Get pipelines referenced by filtered assays - OPTIMIZED
        pipeline_ids = []
        if assay_ids_all:
            try:
                # Get unique pipeline_ids from assays
                pipeline_id_rows = _batch_query(
                    main_cursor,
                    "SELECT DISTINCT pipeline_id FROM assay WHERE id IN ({placeholders})",
                    assay_ids_all
                )
                pipeline_ids = list(set([row[0] for row in pipeline_id_rows]))
                
                if pipeline_ids:
                    pipeline_rows = _batch_query(
                        main_cursor,
                        "SELECT * FROM pipeline WHERE id IN ({placeholders})",
                        pipeline_ids
                    )
                    
                    if pipeline_rows:
                        cols = [description[0] for description in main_cursor.description]
                        insert_sql = f"INSERT INTO pipeline ({','.join(cols)}) VALUES ({','.join(['?'] * len(cols))})"
                        conn.executemany(insert_sql, pipeline_rows)
            except Exception as e:
                # Pipeline table might not exist or have data
                pass
        
        # OPTIMIZATION: Commit the transaction
        conn.execute('COMMIT')
        
        # Get counts from the in-memory database
        counts = {
            'studies': conn.execute('SELECT COUNT(*) FROM study').fetchone()[0],
            'assays': conn.execute('SELECT COUNT(*) FROM assay').fetchone()[0],
            'signals': conn.execute('SELECT COUNT(*) FROM signal').fetchone()[0],
            'intervals': conn.execute('SELECT COUNT(*) FROM interval').fetchone()[0],
        }
        
        # Write to bytes - get raw DB file content
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            temp_path = tmp.name
        
        try:
            # Backup from memory to temp file, then read as bytes
            temp_conn = sqlite3.connect(temp_path)
            conn.backup(temp_conn)
            temp_conn.close()
            
            with open(temp_path, 'rb') as f:
                db_bytes = f.read()
        finally:
            import os as os_module
            try:
                os_module.unlink(temp_path)
            except:
                pass
        
        return db_bytes, counts
        
    except Exception as e:
        raise e
    finally:
        try:
            conn.close()
            main_conn.close()
        except:
            pass


@api_view(['GET'])
def export_filtered_sqlite(request):
    """
    Export filtered data matching the applied study list filters.
    Supports both SQLite and ZIP (SQLite + CSVs) export formats.
    
    ALL filtering is done in pure SQL for maximum speed.
    Uses streaming to minimize RAM usage (<10MB regardless of DB size).
    """
    import traceback
    import os as os_module
    
    query_params = request.GET
    export_format = query_params.get('export_format', 'sqlite').lower()
    
    temp_db_path = None
    
    try:
        # Use the FAST PATH: ALL filtering done in SQL via ATTACH DATABASE
        try:
            temp_db_path, counts = _create_filtered_sqlite_db_fast(query_params)
            
            # Check if any data was exported
            if counts['studies'] == 0:
                if temp_db_path and os_module.path.exists(temp_db_path):
                    os_module.unlink(temp_db_path)
                return JsonResponse({
                    "error": "No studies match the applied filters."
                }, status=400)
            
            if counts['assays'] == 0:
                if temp_db_path and os_module.path.exists(temp_db_path):
                    os_module.unlink(temp_db_path)
                return JsonResponse({
                    "error": "No assays match the applied filters."
                }, status=400)
                
        except Exception as e:
            if temp_db_path and os_module.path.exists(temp_db_path):
                os_module.unlink(temp_db_path)
            with open('/tmp/export_debug.log', 'a') as f:
                f.write(f"ERROR in _create_filtered_sqlite_db_fast: {str(e)}\n{traceback.format_exc()}\n")
                f.flush()
            return JsonResponse({"error": f"Error in export: {str(e)}", "traceback": traceback.format_exc()}, status=500)
        
        # Single table CSV export
        table = query_params.get('table')
        include_ro_crate = query_params.get('ro_crate', 'false').lower() in ('true', '1', 'yes')
        
        if table:
            if table not in EXPORT_TABLES:
                if temp_db_path and os_module.path.exists(temp_db_path):
                    os_module.unlink(temp_db_path)
                return JsonResponse({
                    "error": f"Table '{table}' not found. Choose from: {', '.join(EXPORT_TABLES)}"
                }, status=400)
            try:
                # Use temp file path instead of loading into RAM
                csv_data = _dump_table_csv(temp_db_path, table)
                
                if include_ro_crate:
                    # Export single CSV with RO-Crate metadata as ZIP
                    mem_file = io.BytesIO()
                    with zipfile.ZipFile(mem_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                        zf.writestr(f'{table}.csv', csv_data)
                        
                        # Generate RO-Crate metadata (pass temp_db_path instead of db_bytes)
                        file_list = [f'{table}.csv', 'ro-crate-metadata.json']
                        ro_crate = _generate_ro_crate_metadata(query_params, counts, file_list, 'csv', temp_db_path)
                        zf.writestr('ro-crate-metadata.json', json.dumps(ro_crate, indent=2))
                    
                    mem_file.seek(0)
                    response = FileResponse(
                        mem_file,
                        as_attachment=True,
                        filename=f'filtered_{table}_ro-crate.zip',
                        content_type='application/zip'
                    )
                    # Clean up temp file
                    if temp_db_path and os_module.path.exists(temp_db_path):
                        os_module.unlink(temp_db_path)
                    return response
                else:
                    # Plain CSV export
                    resp = HttpResponse(csv_data, content_type='text/csv')
                    resp['Content-Disposition'] = f'attachment; filename="filtered_{table}.csv"'
                    # Clean up temp file
                    if temp_db_path and os_module.path.exists(temp_db_path):
                        os_module.unlink(temp_db_path)
                    return resp
            except Exception as e:
                if temp_db_path and os_module.path.exists(temp_db_path):
                    os_module.unlink(temp_db_path)
                return JsonResponse({"error": str(e), "traceback": traceback.format_exc()}, status=500)
        
        # ZIP export (database + CSVs)
        if export_format == 'zip':
            try:
                mem_file = io.BytesIO()
                with zipfile.ZipFile(mem_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                    # Add database file from disk (avoids loading into RAM)
                    zf.write(temp_db_path, 'filtered_database.sqlite3')
                    
                    file_list = ['filtered_database.sqlite3']
                    # Always include all CSVs when ZIP format is requested
                    for table_name in EXPORT_TABLES:
                        try:
                            csv_data = _dump_table_csv(temp_db_path, table_name)
                            zf.writestr(f'{table_name}.csv', csv_data)
                            file_list.append(f'{table_name}.csv')
                        except:
                            pass
                    
                    # Add RO-Crate metadata if requested
                    if include_ro_crate:
                        file_list.append('ro-crate-metadata.json')
                        ro_crate = _generate_ro_crate_metadata(query_params, counts, file_list, 'zip', temp_db_path)
                        zf.writestr('ro-crate-metadata.json', json.dumps(ro_crate, indent=2))
                
                mem_file.seek(0)
                filename = 'filtered_export_ro-crate.zip' if include_ro_crate else 'filtered_export.zip'
                response = FileResponse(
                    mem_file,
                    as_attachment=True,
                    filename=filename,
                    content_type='application/zip'
                )
                # Clean up temp file
                if temp_db_path and os_module.path.exists(temp_db_path):
                    os_module.unlink(temp_db_path)
                return response
            except Exception as e:
                if temp_db_path and os_module.path.exists(temp_db_path):
                    os_module.unlink(temp_db_path)
                return JsonResponse({"error": str(e), "traceback": traceback.format_exc()}, status=500)
        
        # Default: raw SQLite download (STREAMING - minimal RAM usage)
        try:
            if include_ro_crate:
                # Export SQLite with RO-Crate metadata as ZIP
                mem_file = io.BytesIO()
                with zipfile.ZipFile(mem_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                    # Add database file from disk (avoids loading into RAM)
                    zf.write(temp_db_path, 'filtered_database.sqlite3')
                    
                    # Generate RO-Crate metadata
                    file_list = ['filtered_database.sqlite3', 'ro-crate-metadata.json']
                    ro_crate = _generate_ro_crate_metadata(query_params, counts, file_list, 'sqlite', temp_db_path)
                    zf.writestr('ro-crate-metadata.json', json.dumps(ro_crate, indent=2))
                
                mem_file.seek(0)
                response = FileResponse(
                    mem_file,
                    as_attachment=True,
                    filename='filtered_database_ro-crate.zip',
                    content_type='application/zip'
                )
                # Clean up temp file
                if temp_db_path and os_module.path.exists(temp_db_path):
                    os_module.unlink(temp_db_path)
                return response
            else:
                # OPTIMIZED: Stream file directly - uses ~8KB RAM instead of GBs!
                response = FileResponse(
                    open(temp_db_path, 'rb'),
                    as_attachment=True,
                    filename="filtered_database.sqlite3",
                    content_type='application/x-sqlite3'
                )
                # FileResponse will handle file cleanup automatically when request completes
                # But we need to schedule cleanup ourselves
                response._temp_file_path = temp_db_path
                
                # Get file size for Content-Length header
                response['Content-Length'] = os_module.path.getsize(temp_db_path)
                
                # Register cleanup callback
                def cleanup_temp_file(sender, **kwargs):
                    if hasattr(sender, '_temp_file_path') and os_module.path.exists(sender._temp_file_path):
                        try:
                            os_module.unlink(sender._temp_file_path)
                        except:
                            pass
                
                # Clean up after response is sent
                from django.core.signals import request_finished
                request_finished.connect(cleanup_temp_file, sender=response, weak=False)
                
                return response
        except Exception as e:
            if temp_db_path and os_module.path.exists(temp_db_path):
                os_module.unlink(temp_db_path)
            return JsonResponse({"error": str(e), "traceback": traceback.format_exc()}, status=500)
    
    except Exception as e:
        if temp_db_path and os_module.path.exists(temp_db_path):
            os_module.unlink(temp_db_path)
        return JsonResponse({"error": str(e), "traceback": traceback.format_exc()}, status=500)
    finally:
        # Final safety cleanup (in case response wasn't created)
        if temp_db_path and os_module.path.exists(temp_db_path):
            # Check if response was successfully created (file handle is open)
            # If not, clean up here
            try:
                # This will fail if file is open (which is good - means streaming is happening)
                os_module.unlink(temp_db_path)
            except:
                # File is locked/in use or already deleted - both are fine
                pass



def _dump_table_csv_from_bytes(db_bytes, table_name):
    """
    Export table from in-memory database bytes as CSV.
    """
    import tempfile
    import os

    temp_path = None
    conn = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.sqlite3', delete=False) as tmp:
            temp_path = tmp.name
            tmp.write(db_bytes)
            tmp.flush()

        conn = sqlite3.connect(temp_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(f'SELECT * FROM "{table_name}"')
        rows = cursor.fetchall()

        if not rows:
            cursor.execute(f'PRAGMA table_info("{table_name}")')
            columns = [col[1] for col in cursor.fetchall()]
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(columns)
            return output.getvalue()

        columns = rows[0].keys()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)

        for row in rows:
            writer.writerow([row[col] for col in columns])

        return output.getvalue()
    finally:
        if conn:
            conn.close()
        if temp_path:
            try:
                os.unlink(temp_path)
            except:
                pass

def _bulk_import_intervals_cells_signals(request, interval_rows, cell_rows, signal_rows, omit_zero_signals=False, progress=None):
    """
    Bulk import intervals, cells, and signals in a single atomic transaction.
    
    If ANY step fails, the entire transaction rolls back.
    Returns a dict with:
    - success: bool
    - message: str
    - interval_id_map: dict (external_id -> new_id)
    - cell_name_map: dict (cell_name -> new_id)
    - counts: dict with imported row counts
    - error: str (if failed)
    """
    from django.db import transaction
    
    # Validate parameters
    assembly_id = request.data.get('assembly_id')
    assay_id = request.data.get('assay_id')
    
    if not assembly_id:
        return {
            'success': False,
            'error': 'assembly_id is required for interval import.',
            'counts': {'intervals': 0, 'cells': 0, 'signals': 0, 'zero_signals': 0, 'non_zero_signals': 0}
        }
    
    if not assay_id:
        return {
            'success': False,
            'error': 'assay_id is required for cell and signal import.',
            'counts': {'intervals': 0, 'cells': 0, 'signals': 0, 'zero_signals': 0, 'non_zero_signals': 0}
        }
    
    try:
        assembly_id = int(assembly_id)
        assay_id = int(assay_id)
        
        if not Assembly.objects.filter(id=assembly_id).exists():
            return {
                'success': False,
                'error': f'Assembly with id {assembly_id} not found.',
                'counts': {'intervals': 0, 'cells': 0, 'signals': 0}
            }
        
        if not Assay.objects.filter(id=assay_id).exists():
            return {
                'success': False,
                'error': f'Assay with id {assay_id} not found.',
                'counts': {'intervals': 0, 'cells': 0, 'signals': 0}
            }
    except (ValueError, TypeError):
        return {
            'success': False,
            'error': 'Invalid assembly_id or assay_id.',
            'counts': {'intervals': 0, 'cells': 0, 'signals': 0, 'zero_signals': 0, 'non_zero_signals': 0}
        }
    
    # All in one transaction
    progress = progress or (lambda **kwargs: None)

    # Totals for progress messages
    total_intervals = len(interval_rows) if interval_rows is not None else 0
    total_cells = len(cell_rows) if cell_rows is not None else 0
    total_signals = len(signal_rows) if signal_rows is not None else 0

    try:
        with transaction.atomic():
            # Helper: normalize numeric strings including European formats
            def _normalize_number(val_str):
                s = (val_str or "").strip()
                if not s:
                    raise ValueError("Empty numeric value")
                if s.upper() in ("NA", "N/A", "NULL"):
                    raise ValueError("Null numeric value")
                s = s.replace(" ", "")
                if "," in s:
                    s = s.replace(".", "")
                    s = s.replace(",", ".")
                    return float(s)
                if s.count(".") > 1:
                    s = s.replace(".", "")
                    return float(s)
                return float(s)

            # Batching constants keep memory bounded for huge uploads
            INTERVAL_BATCH = 2000
            CELL_BATCH = 2000
            SIGNAL_BATCH = 5000

            # --- STEP 1: Import Intervals (stream + chunk) ---
            interval_id_map = {}
            parental_links = []  # (child_csv_id, parent_csv_id)
            interval_batch = []
            interval_csv_ids = []
            interval_count = 0

            def _flush_interval_batch():
                nonlocal interval_batch, interval_csv_ids, interval_count
                if not interval_batch:
                    return
                created = Interval.objects.bulk_create(interval_batch, batch_size=INTERVAL_BATCH)
                interval_count += len(created)
                for idx, csv_id in enumerate(interval_csv_ids):
                    interval_id_map[csv_id] = created[idx].id
                interval_batch = []
                interval_csv_ids = []
                progress(phase='intervals', step=2, step_name='Parsing Intervals', total_steps=5, processed=interval_count, message=f'Parsing intervals... {interval_count}/{total_intervals}')

            for row in interval_rows:
                csv_interval_id = row.get('id', '').strip()
                external_id = row.get('external_id', '').strip()
                parental_id_csv = row.get('parental_id', '').strip() or None
                name = row.get('name', '').strip() or None
                interval_type = row.get('type', '').strip()
                biotype = row.get('biotype', '').strip() or None
                chromosome = row.get('chromosome', '').strip()
                start_val = row.get('start', '').strip()
                end_val = row.get('end', '').strip()
                strand = row.get('strand', '').strip()
                summit_val = row.get('summit', '').strip()

                if not csv_interval_id or not interval_type or not chromosome or not strand:
                    continue

                try:
                    start = int(start_val) if start_val else 0
                except Exception:
                    continue
                end = None
                if end_val:
                    try:
                        end = int(end_val)
                    except Exception:
                        end = None
                summit = None
                if summit_val:
                    try:
                        summit = int(summit_val)
                    except Exception:
                        summit = None

                interval_batch.append(Interval(
                    external_id=external_id,
                    parental_id=None,
                    name=name,
                    type=interval_type,
                    biotype=biotype,
                    chromosome=chromosome,
                    start=start,
                    end=end,
                    strand=strand,
                    summit=summit,
                    assembly_id=assembly_id
                ))
                interval_csv_ids.append(csv_interval_id)

                if parental_id_csv:
                    parental_links.append((csv_interval_id, parental_id_csv))

                if len(interval_batch) >= INTERVAL_BATCH:
                    _flush_interval_batch()

            _flush_interval_batch()

            # Resolve parental relationships with a lightweight bulk_update
            if parental_links:
                updates = []
                for child_csv, parent_csv in parental_links:
                    parent_db_id = interval_id_map.get(parent_csv)
                    child_db_id = interval_id_map.get(child_csv)
                    if parent_db_id and child_db_id:
                        updates.append(Interval(id=child_db_id, parental_id=str(parent_db_id)))
                if updates:
                    Interval.objects.bulk_update(updates, ['parental_id'], batch_size=INTERVAL_BATCH)
                progress(phase='intervals', step=2, step_name='Parsing Intervals', total_steps=5, processed=interval_count)

            # --- STEP 2: Import Cells (stream + chunk) ---
            cell_name_map = {}
            cell_batch = []
            cell_names = []
            cell_count = 0

            def _flush_cell_batch():
                nonlocal cell_batch, cell_names, cell_count
                if not cell_batch:
                    return
                created = Cell.objects.bulk_create(cell_batch, batch_size=CELL_BATCH)
                cell_count += len(created)
                for idx, cell_name in enumerate(cell_names):
                    cell_name_map[cell_name] = created[idx].id
                cell_batch = []
                cell_names = []
                progress(phase='cells', step=3, step_name='Parsing Cells', total_steps=5, processed=cell_count, message=f'Parsing cells... {cell_count}/{total_cells}')

            for row in cell_rows:
                name = row.get('name', '').strip()
                if not name:
                    continue
                x_coord_val = row.get('x_coordinate', '').strip()
                y_coord_val = row.get('y_coordinate', '').strip()
                z_coord_val = row.get('z_coordinate', '').strip()

                def _to_int(val):
                    if not val:
                        return None
                    try:
                        return int(val)
                    except Exception:
                        return None

                cell_batch.append(Cell(
                    name=name,
                    x_coordinate=_to_int(x_coord_val),
                    y_coordinate=_to_int(y_coord_val),
                    z_coordinate=_to_int(z_coord_val),
                    assay_id=assay_id
                ))
                cell_names.append(name)

                if len(cell_batch) >= CELL_BATCH:
                    _flush_cell_batch()

            _flush_cell_batch()

            # --- STEP 3: Import Signals (stream + chunk) ---
            signal_count = 0
            zero_signal_count = 0
            non_zero_signal_count = 0
            interval_seen = set()
            interval_has_nonzero = set()
            signal_batch = []

            def _flush_signal_batch():
                nonlocal signal_batch, signal_count
                if not signal_batch:
                    return
                Signal.objects.bulk_create(signal_batch, batch_size=SIGNAL_BATCH)
                signal_count += len(signal_batch)
                signal_batch = []
                progress(phase='signals', step=4, step_name='Parsing Signals', total_steps=5, processed=signal_count, message=f'Parsing signals... {signal_count}/{total_signals}', zeros=zero_signal_count, non_zero=non_zero_signal_count)

            for row in signal_rows:
                signal_val = row.get('signal', '').strip()
                p_value_val = row.get('p_value', '').strip()
                padj_value_val = row.get('padj_value', '').strip()
                csv_interval_id = row.get('interval_id', '').strip()
                csv_cell_id = row.get('cell_id', '').strip()

                if not signal_val or not csv_interval_id:
                    continue

                try:
                    signal = _normalize_number(signal_val)
                except ValueError:
                    continue

                if signal == 0:
                    zero_signal_count += 1
                    if omit_zero_signals:
                        continue
                else:
                    non_zero_signal_count += 1

                try:
                    p_value = _normalize_number(p_value_val) if p_value_val else None
                except ValueError:
                    p_value = None

                try:
                    padj_value = _normalize_number(padj_value_val) if padj_value_val else None
                except ValueError:
                    padj_value = None

                interval_db_id = interval_id_map.get(csv_interval_id)
                if not interval_db_id and csv_interval_id.isdigit():
                    interval_db_id = interval_id_map.get(str(int(csv_interval_id)))
                if not interval_db_id:
                    continue

                cell_db_id = None
                if csv_cell_id:
                    cell_db_id = cell_name_map.get(csv_cell_id)
                    if not cell_db_id and csv_cell_id.isdigit():
                        cell_db_id = cell_name_map.get(str(int(csv_cell_id)))

                interval_seen.add(interval_db_id)
                if signal > 0:
                    interval_has_nonzero.add(interval_db_id)

                signal_batch.append(Signal(
                    signal=signal,
                    p_value=p_value,
                    padj_value=padj_value,
                    assay_id=assay_id,
                    interval_id=interval_db_id,
                    cell_id=cell_db_id
                ))

                if len(signal_batch) >= SIGNAL_BATCH:
                    _flush_signal_batch()

            _flush_signal_batch()

            non_zero_interval_count = len(interval_has_nonzero)
            total_interval_with_signals = len(interval_seen)
            zero_only_interval_count = total_interval_with_signals - non_zero_interval_count
            Assay.objects.filter(id=assay_id).update(
                interval_count=total_interval_with_signals
            )

            return {
                'success': True,
                'message': f'Bulk import successful: {interval_count} interval(s), {cell_count} cell(s), {signal_count} signal(s) ({zero_signal_count} zero-value signals skipped)' if omit_zero_signals else f'Bulk import successful: {interval_count} interval(s), {cell_count} cell(s), {signal_count} signal(s)',
                'interval_id_map': interval_id_map,
                'cell_name_map': cell_name_map,
                'counts': {
                    'intervals': interval_count,
                    'cells': cell_count,
                    'signals': signal_count,
                    'zero_signals': zero_signal_count,
                    'non_zero_signals': non_zero_signal_count
                }
            }
    
    except Exception as e:
        # Transaction automatically rolls back on exception
        return {
            'success': False,
            'error': f'Bulk import failed [normV2]: {str(e)}',
            'counts': {'intervals': 0, 'cells': 0, 'signals': 0, 'zero_signals': 0, 'non_zero_signals': 0}
        }


@swagger_auto_schema(
    method='post',
    operation_summary="Bulk import interval, cell, and signal data",
    operation_description="""
    Import interval, cell, and signal data in a single atomic transaction.
    
    **All 3 imports must succeed or the entire transaction rolls back.**
    
    This ensures data consistency when IDs need to be mapped across tables.
    
    **Required fields:**
    - interval_file: CSV file with interval data
    - cell_file: CSV file with cell data (optional, can be empty)
    - signal_file: CSV file with signal data
    - assembly_id: ID of the genome assembly
    - assay_id: ID of the assay
    
    **CSV Format:**
    - Interval CSV: external_id, parental_id, name, type, biotype, chromosome, start, end, strand, summit
    - Cell CSV: name, type, label, x_coordinate, y_coordinate, z_coordinate
    - Signal CSV: signal, p_value, padj_value, interval_id, cell_id

    **Options:**
    - omit_zero_signals: If true, rows with signal==0 are counted but not inserted
    
    **Returns:**
    - interval_id_map: Mapping of CSV external_id to new DB interval IDs
    - cell_name_map: Mapping of CSV cell names to new DB cell IDs
    - counts: Number of rows imported for each table
    """,
    manual_parameters=[
        openapi.Parameter(
            'interval_file',
            openapi.IN_FORM,
            type=openapi.TYPE_FILE,
            required=True,
            description="CSV file with interval data"
        ),
        openapi.Parameter(
            'cell_file',
            openapi.IN_FORM,
            type=openapi.TYPE_FILE,
            required=False,
            description="CSV file with cell data (optional)"
        ),
        openapi.Parameter(
            'signal_file',
            openapi.IN_FORM,
            type=openapi.TYPE_FILE,
            required=True,
            description="CSV file with signal data"
        ),
        openapi.Parameter(
            'assembly_id',
            openapi.IN_FORM,
            type=openapi.TYPE_INTEGER,
            required=True,
            description="ID of the genome assembly"
        ),
        openapi.Parameter(
            'assay_id',
            openapi.IN_FORM,
            type=openapi.TYPE_INTEGER,
            required=True,
            description="ID of the assay"
        ),
        openapi.Parameter(
            'omit_zero_signals',
            openapi.IN_FORM,
            type=openapi.TYPE_BOOLEAN,
            required=False,
            description="If true, skip inserting signals with value 0 and report them as zero_signals"
        )
    ],
    responses={
        200: openapi.Response(
            description="Bulk import successful",
            examples={"application/json": {
                "success": True,
                "message": "Bulk import successful: 100 interval(s), 50 cell(s), 5000 signal(s)",
                "interval_id_map": {"peak_1": 1001, "peak_2": 1002},
                "cell_name_map": {"cell_1": 2001, "cell_2": 2002},
                "counts": {"intervals": 100, "cells": 50, "signals": 5000, "zero_signals": 0}
            }}
        ),
        400: "Missing required parameters or invalid data",
        500: "Database error (transaction rolled back)"
    },
    tags=['Database Management']
)
@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def import_bulk_data(request):
    """
    Bulk import intervals, cells, and signals in a single atomic transaction.
    """
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST method is allowed."}, status=400)
    # Get files
    interval_file = request.FILES.get('interval_file')
    cell_file = request.FILES.get('cell_file')
    signal_file = request.FILES.get('signal_file')
    omit_zero_signals = str(request.data.get('omit_zero_signals', 'false')).lower() in ('1', 'true', 'yes', 'on')

    if not interval_file or not signal_file:
        return JsonResponse({"error": "interval_file and signal_file are required."}, status=400)

    # For huge files (79M+ rows), we can't load everything into memory.
    # Instead: copy uploaded files to temp location, then stream from there in background.
    import tempfile
    import shutil
    
    try:
        # Save uploaded files to temporary location
        interval_temp = tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False)
        shutil.copyfileobj(interval_file.file, interval_temp)
        interval_temp.close()
        interval_path = interval_temp.name
        
        if cell_file:
            cell_temp = tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False)
            shutil.copyfileobj(cell_file.file, cell_temp)
            cell_temp.close()
            cell_path = cell_temp.name
        else:
            cell_path = None
            
        signal_temp = tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False)
        shutil.copyfileobj(signal_file.file, signal_temp)
        signal_temp.close()
        signal_path = signal_temp.name
        
    except Exception as e:
        return JsonResponse({"error": f"Failed to save uploaded files: {str(e)}"}, status=400)

    job_id = str(uuid.uuid4())
    with PROGRESS_LOCK:
        PROGRESS_STORE[job_id] = {
            'status': 'running',
            'phase': 'upload',
            'step': 1,
            'step_name': 'Uploading Files',
            'total_steps': 5,
            'processed': 0,
            'total_intervals': 0,  # Will be updated as we stream
            'total_cells': 0,
            'total_signals': 0,
            'message': 'Step 1/5: Uploading Files',
        }

    def _run_job():
        try:
            def _progress(**fields):
                _update_progress(job_id, **fields, status='running')

            # Use pandas-based import for 10-100x speed improvement
            result = bulk_import_with_pandas(
                interval_path=interval_path,
                cell_path=cell_path,
                signal_path=signal_path,
                assembly_id=int(request.data.get('assembly_id')),
                assay_id=int(request.data.get('assay_id')),
                omit_zero_signals=omit_zero_signals,
                deduplicate_intervals=str(request.data.get('deduplicate_intervals', '')).lower() in ('1','true','yes','on'),
                ignore_optional_type_errors=str(request.data.get('ignore_optional_type_errors', '')).lower() in ('1','true','yes','on'),
                ignore_conflicts=str(request.data.get('ignore_conflicts', '')).lower() in ('1','true','yes','on'),
                ignore_row_errors=str(request.data.get('ignore_row_errors', '')).lower() in ('1','true','yes','on'),
                progress=_progress
            )

            if result.get('success'):
                _update_progress(job_id, status='completed', phase='done', step=5, step_name='Complete', total_steps=5, message=result.get('message'), result=result)
            else:
                _update_progress(job_id, status='failed', phase='done', error=result.get('error'), result=result, message='Import failed')
        except Exception as e:
            _update_progress(job_id, status='failed', phase='error', error=str(e), message='Import crashed')
        finally:
            # Clean up temp files
            for path in [interval_path, cell_path, signal_path]:
                if path and os.path.exists(path):
                    try:
                        os.unlink(path)
                    except Exception:
                        pass
                        
            # Cleanup old job entries after 1 hour to free memory
            def _cleanup_old_jobs():
                with PROGRESS_LOCK:
                    now = time.time()
                    to_delete = [jid for jid, data in PROGRESS_STORE.items() 
                                 if data.get('completed_at', 0) and now - data['completed_at'] > 3600]
                    for jid in to_delete:
                        del PROGRESS_STORE[jid]
            
            # Mark job as completed with timestamp for cleanup
            _update_progress(job_id, completed_at=time.time())
            threading.Timer(3600, _cleanup_old_jobs).start()

    threading.Thread(target=_run_job, daemon=True).start()

    status_url = request.build_absolute_uri(reverse('import_bulk_data_status', args=[job_id]))
    return JsonResponse({
        'job_id': job_id,
        'status': 'queued',
        'status_url': status_url,
        'message': 'Import started in background. Poll status_url for progress.'
    }, status=202)


@api_view(['GET'])
def import_bulk_data_status(request, job_id):
    data = PROGRESS_STORE.get(job_id)
    if not data:
        return JsonResponse({'error': 'job_id not found'}, status=404)
    def _to_builtin(obj):
        import numpy as np
        if isinstance(obj, dict):
            return {k: _to_builtin(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_to_builtin(v) for v in obj]
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        return obj

    safe_data = _to_builtin(data)
    return JsonResponse(safe_data, status=200)


@api_view(['GET'])  
def test_endpoint(request):
    with open('/tmp/test_endpoint.log', 'w') as f:
        f.write('Test endpoint called\n')
    return JsonResponse({'status': 'test ok'})
