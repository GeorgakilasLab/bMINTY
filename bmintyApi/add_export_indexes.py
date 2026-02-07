#!/usr/bin/env python3
"""
Add critical indexes to bMINTY database for fast filtered exports.

This script creates indexes on foreign key columns that are used for filtering
during exports. Running this once will dramatically speed up all future exports
(10-100x faster for large databases).

Usage:
    python3 add_export_indexes.py

This is a one-time operation. Indexes will persist in the database.
"""

import sqlite3
import sys
import time
from pathlib import Path

# Get database path from Django settings
import os
import django

# Set up Django environment
sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bmintyApi.settings')
django.setup()

from django.conf import settings


def add_indexes():
    """Add performance-critical indexes to the database."""
    
    db_path = settings.DATABASES['default']['NAME']
    print(f"Database: {db_path}")
    
    # Get database size
    db_size_mb = Path(db_path).stat().st_size / (1024 * 1024)
    print(f"Database size: {db_size_mb:.1f} MB")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Critical indexes for export performance
    indexes_to_create = [
        {
            'name': 'idx_signal_assay_id',
            'table': 'signal',
            'column': 'assay_id',
            'description': 'Speeds up signal filtering by assay (most common operation)'
        },
        {
            'name': 'idx_signal_interval_id', 
            'table': 'signal',
            'column': 'interval_id',
            'description': 'Speeds up interval-based filtering (e.g., by gene type)'
        },
        {
            'name': 'idx_signal_cell_id',
            'table': 'signal',
            'column': 'cell_id',
            'description': 'Speeds up cell-based filtering (e.g., by cell type)'
        },
        {
            'name': 'idx_interval_assembly_id',
            'table': 'interval',
            'column': 'assembly_id',
            'description': 'Speeds up assembly-based interval lookups'
        },
        {
            'name': 'idx_interval_type',
            'table': 'interval',
            'column': 'type',
            'description': 'Speeds up filtering by interval type (gene, peak, etc.)'
        },
        {
            'name': 'idx_cell_assay_id',
            'table': 'cell',
            'column': 'assay_id',
            'description': 'Speeds up cell lookups by assay'
        },
        {
            'name': 'idx_cell_type',
            'table': 'cell',
            'column': 'type',
            'description': 'Speeds up filtering by cell type'
        },
        {
            'name': 'idx_assay_study_id',
            'table': 'assay',
            'column': 'study_id',
            'description': 'Speeds up assay lookups by study'
        },
    ]
    
    print("\n" + "="*70)
    print("CREATING PERFORMANCE INDEXES")
    print("="*70)
    
    created_count = 0
    skipped_count = 0
    
    for idx_info in indexes_to_create:
        idx_name = idx_info['name']
        table = idx_info['table']
        column = idx_info['column']
        description = idx_info['description']
        
        # Check if index already exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
            (idx_name,)
        )
        
        if cursor.fetchone():
            print(f"✓ {idx_name:30s} [EXISTS]")
            skipped_count += 1
            continue
        
        # Create the index
        print(f"⏳ Creating {idx_name:30s} on {table}.{column}...", end=' ', flush=True)
        start_time = time.time()
        
        try:
            cursor.execute(f'CREATE INDEX {idx_name} ON {table}({column})')
            conn.commit()
            elapsed = time.time() - start_time
            print(f"✓ ({elapsed:.1f}s)")
            print(f"   → {description}")
            created_count += 1
        except Exception as e:
            print(f"✗ FAILED: {e}")
    
    print("\n" + "="*70)
    print(f"SUMMARY: Created {created_count} indexes, {skipped_count} already existed")
    print("="*70)
    
    if created_count > 0:
        # Run ANALYZE to update query planner statistics
        print("\n⏳ Running ANALYZE to update query planner statistics...", end=' ', flush=True)
        start_time = time.time()
        cursor.execute('ANALYZE')
        conn.commit()
        elapsed = time.time() - start_time
        print(f"✓ ({elapsed:.1f}s)")
        
        # Show new database size
        conn.close()
        new_db_size_mb = Path(db_path).stat().st_size / (1024 * 1024)
        size_increase_mb = new_db_size_mb - db_size_mb
        print(f"\nDatabase size after indexing: {new_db_size_mb:.1f} MB (+{size_increase_mb:.1f} MB)")
        print(f"Index overhead: {(size_increase_mb / db_size_mb * 100):.1f}% of original size")
        
        print("\n" + "="*70)
        print("✓ ALL DONE! Your exports will now be MUCH faster!")
        print("="*70)
        print("\nExpected speedup for filtered exports: 10-100x faster")
        print("The indexes are permanent - you only need to run this once.")
    else:
        conn.close()
        print("\n✓ All indexes already exist. Database is already optimized!")
    

if __name__ == '__main__':
    try:
        add_indexes()
    except Exception as e:
        print(f"\n✗ ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
