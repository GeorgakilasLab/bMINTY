"""
Stress Test Script for Sequential Folder Imports
Tracks: import time, CPU usage, RAM usage, database size, and other metrics
"""

import os
import sys
import time
import psutil
import sqlite3
import shutil
import json
from datetime import datetime
from pathlib import Path
import threading
from django.db import IntegrityError

# Django setup
sys.path.insert(0, '/bmintyApi')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bmintyApi.settings')

import django
django.setup()

from django.db import connection
from django.core.management import call_command


class MetricsMonitor:
    """Monitor system metrics during import operations"""
    
    def __init__(self):
        self.cpu_samples = []
        self.ram_samples = []
        self.monitoring = False
        self.monitor_thread = None
        self.process = psutil.Process()
        
    def start_monitoring(self, interval=0.5):
        """Start monitoring CPU and RAM usage"""
        self.monitoring = True
        self.cpu_samples = []
        self.ram_samples = []
        self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        """Stop monitoring and return statistics"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
            
        return {
            'cpu_avg': sum(self.cpu_samples) / len(self.cpu_samples) if self.cpu_samples else 0,
            'cpu_max': max(self.cpu_samples) if self.cpu_samples else 0,
            'cpu_min': min(self.cpu_samples) if self.cpu_samples else 0,
            'cpu_samples_count': len(self.cpu_samples),
            'ram_avg_mb': sum(self.ram_samples) / len(self.ram_samples) if self.ram_samples else 0,
            'ram_max_mb': max(self.ram_samples) if self.ram_samples else 0,
            'ram_min_mb': min(self.ram_samples) if self.ram_samples else 0,
            'ram_samples_count': len(self.ram_samples)
        }
        
    def _monitor_loop(self, interval):
        """Internal monitoring loop"""
        while self.monitoring:
            try:
                cpu_percent = self.process.cpu_percent(interval=None)
                self.cpu_samples.append(cpu_percent)
                ram_mb = self.process.memory_info().rss / (1024 * 1024)
                self.ram_samples.append(ram_mb)
                time.sleep(interval)
            except Exception as e:
                print(f"Monitoring error: {e}")
                break


class DatabaseMetrics:
    """Track database-related metrics"""
    
    @staticmethod
    def get_db_size(db_path):
        try:
            return os.path.getsize(db_path)
        except FileNotFoundError:
            return 0
            
    @staticmethod
    def get_db_size_mb(db_path):
        return DatabaseMetrics.get_db_size(db_path) / (1024 * 1024)
        
    @staticmethod
    def get_table_counts():
        from django.apps import apps
        counts = {}
        for model in apps.get_models():
            table_name = model._meta.db_table
            try:
                count = model.objects.count()
                counts[table_name] = count
            except Exception as e:
                counts[table_name] = f"Error: {e}"
        return counts
        
    @staticmethod
    def get_db_stats(db_path):
        """Get basic database statistics (file size only - avoids lock issues)"""
        if not os.path.exists(db_path):
            return {}
        
        try:
            # Only get file size - doesn't require a live connection
            size_mb = DatabaseMetrics.get_db_size_mb(db_path)
            return {'size_mb': size_mb}
        except Exception as e:
            print(f"  ⚠ Error getting db stats: {e}")
            return {}


class StressTestRunner:
    """Main stress test runner"""
    
    def __init__(self, db_path='/bmintyApi/db.sqlite3'):
        self.db_path = db_path
        self.results = {
            'test_start': datetime.now().isoformat(),
            'test_end': None,
            'total_duration_seconds': 0,
            'imports': []
        }
        
    def backup_database(self):
        if os.path.exists(self.db_path):
            backup_path = f"{self.db_path}.stress_test_backup_{int(time.time())}"
            shutil.copy2(self.db_path, backup_path)
            print(f"✓ Database backed up to: {backup_path}")
            return backup_path
        return None
        
    def create_fresh_database(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            print(f"✓ Removed existing database")
            
        print("✓ Creating fresh database schema...")
        call_command('migrate', verbosity=0)
        print(f"✓ Fresh database created at: {self.db_path}")
        
    def import_folder(self, folder_path, folder_name, import_function):
        print(f"\n{'='*80}")
        print(f"Starting import: {folder_name}")
        print(f"Folder: {folder_path}")
        print(f"{'='*80}")
        
        if not os.path.exists(folder_path):
            print(f"⚠ WARNING: Folder not found: {folder_path}")
            print(f"⚠ Skipping this import")
            return None
        
        db_size_before = DatabaseMetrics.get_db_size_mb(self.db_path)
        table_counts_before = DatabaseMetrics.get_table_counts()
        db_stats_before = DatabaseMetrics.get_db_stats(self.db_path)
        
        monitor = MetricsMonitor()
        monitor.start_monitoring(interval=0.5)
        
        start_time = time.time()
        import_success = False
        import_error = None
        
        try:
            import_function(folder_path)
            import_success = True
            print(f"✓ Import completed successfully")
        except Exception as e:
            import_error = str(e)
            print(f"✗ Import failed: {e}")
            import logging
            logging.exception("Import error details:")
            
        end_time = time.time()
        duration = end_time - start_time
        
        # Safeguard: if duration is negative, clamp to 0 (indicates system clock adjustment)
        if duration < 0:
            print(f"⚠ WARNING: Negative duration detected ({duration:.2f}s). System clock may have been adjusted backwards.")
            print(f"  start_time={start_time}, end_time={end_time}")
            duration = 0.01  # Minimum floor to indicate instantaneous operation
        
        system_metrics = monitor.stop_monitoring()
        
        db_size_after = DatabaseMetrics.get_db_size_mb(self.db_path)
        table_counts_after = DatabaseMetrics.get_table_counts()
        db_stats_after = DatabaseMetrics.get_db_stats(self.db_path)
        
        db_size_increase = db_size_after - db_size_before
        
        table_count_changes = {}
        for table_name in set(list(table_counts_before.keys()) + list(table_counts_after.keys())):
            before = table_counts_before.get(table_name, 0)
            after = table_counts_after.get(table_name, 0)
            if isinstance(before, int) and isinstance(after, int):
                change = after - before
                if change != 0:
                    table_count_changes[table_name] = {
                        'before': before,
                        'after': after,
                        'added': change
                    }
        
        result = {
            'folder_name': folder_name,
            'folder_path': folder_path,
            'success': import_success,
            'error': import_error,
            'timestamp_start': datetime.fromtimestamp(start_time).isoformat(),
            'timestamp_end': datetime.fromtimestamp(end_time).isoformat(),
            'duration_seconds': round(duration, 2),
            'duration_formatted': self._format_duration(duration),
            'system_metrics': {
                'cpu_average_percent': round(system_metrics['cpu_avg'], 2),
                'cpu_max_percent': round(system_metrics['cpu_max'], 2),
                'cpu_min_percent': round(system_metrics['cpu_min'], 2),
                'ram_average_mb': round(system_metrics['ram_avg_mb'], 2),
                'ram_max_mb': round(system_metrics['ram_max_mb'], 2),
                'ram_min_mb': round(system_metrics['ram_min_mb'], 2),
                'samples_collected': system_metrics['cpu_samples_count']
            },
            'database_metrics': {
                'size_before_mb': round(db_size_before, 2),
                'size_after_mb': round(db_size_after, 2),
                'size_increase_mb': round(db_size_increase, 2),
                'size_increase_percent': round((db_size_increase / db_size_before * 100) if db_size_before > 0 else 0, 2),
                'stats_before': db_stats_before,
                'stats_after': db_stats_after,
                'fragmentation_change': round(
                    db_stats_after.get('fragmentation_pct', 0) - db_stats_before.get('fragmentation_pct', 0), 2
                ) if db_stats_after and db_stats_before else 0
            },
            'table_changes': table_count_changes,
            'total_rows_added': sum(
                change['added'] for change in table_count_changes.values()
            )
        }
        
        self.results['imports'].append(result)
        self._print_import_summary(result)
        return result
        
    def _format_duration(self, seconds):
        if seconds < 60:
            return f"{seconds:.2f}s"
        elif seconds < 3600:
            mins = int(seconds // 60)
            secs = seconds % 60
            return f"{mins}m {secs:.2f}s"
        else:
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            secs = seconds % 60
            return f"{hours}h {mins}m {secs:.2f}s"
            
    def _print_import_summary(self, result):
        print(f"\n{'─'*80}")
        print(f"Import Summary: {result['folder_name']}")
        print(f"{'─'*80}")
        print(f"Status:           {'✓ SUCCESS' if result['success'] else '✗ FAILED'}")
        if result['error']:
            print(f"Error:            {result['error']}")
        print(f"Duration:         {result['duration_formatted']}")
        print(f"Rows Added:       {result['total_rows_added']:,}")
        print(f"DB Size Increase: {result['database_metrics']['size_increase_mb']:.2f} MB")
        print(f"Avg CPU Usage:    {result['system_metrics']['cpu_average_percent']:.1f}%")
        print(f"Avg RAM Usage:    {result['system_metrics']['ram_average_mb']:.1f} MB")
        print(f"Peak RAM Usage:   {result['system_metrics']['ram_max_mb']:.1f} MB")
        
        if result['table_changes']:
            print(f"\nTable Changes:")
            for table_name, changes in sorted(result['table_changes'].items()):
                print(f"  • {table_name}: +{changes['added']:,} rows ({changes['before']:,} → {changes['after']:,})")
        
        print(f"{'─'*80}\n")
        
    def finalize_results(self):
        self.results['test_end'] = datetime.now().isoformat()
        
        if self.results['imports']:
            total_duration = sum(imp['duration_seconds'] for imp in self.results['imports'])
            self.results['total_duration_seconds'] = total_duration
            self.results['total_duration_formatted'] = self._format_duration(total_duration)
            self.results['cumulative_metrics'] = {
                'total_imports': len(self.results['imports']),
                'successful_imports': sum(1 for imp in self.results['imports'] if imp['success']),
                'failed_imports': sum(1 for imp in self.results['imports'] if not imp['success']),
                'total_rows_added': sum(imp['total_rows_added'] for imp in self.results['imports']),
                'total_db_size_increase_mb': sum(imp['database_metrics']['size_increase_mb'] for imp in self.results['imports']),
                'average_import_time_seconds': total_duration / len(self.results['imports']),
                'average_cpu_percent': sum(imp['system_metrics']['cpu_average_percent'] for imp in self.results['imports']) / len(self.results['imports']),
                'peak_ram_mb': max(imp['system_metrics']['ram_max_mb'] for imp in self.results['imports']),
            }
            
        output_dir = os.environ.get("STRESS_TEST_OUTPUT_DIR", "/test-results")
        os.makedirs(output_dir, exist_ok=True)

        output_file = os.path.join(
            output_dir,
            f"stress_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
            
        print(f"\n{'='*80}")
        print(f"Results saved to: {output_file}")
        print(f"{'='*80}")
        
        return output_file
        
    def print_final_report(self):
        print(f"\n\n{'#'*80}")
        print(f"# STRESS TEST FINAL REPORT")
        print(f"{'#'*80}\n")
        
        if 'cumulative_metrics' in self.results:
            cm = self.results['cumulative_metrics']
            
            print(f"Test Duration:      {self.results['total_duration_formatted']}")
            print(f"Total Imports:      {cm['total_imports']}")
            print(f"Successful:         {cm['successful_imports']}")
            print(f"Failed:             {cm['failed_imports']}")
            print(f"Total Rows Added:   {cm['total_rows_added']:,}")
            print(f"DB Size Increase:   {cm['total_db_size_increase_mb']:.2f} MB")
            print(f"Avg Import Time:    {self._format_duration(cm['average_import_time_seconds'])}")
            print(f"Avg CPU Usage:      {cm['average_cpu_percent']:.1f}%")
            print(f"Peak RAM Usage:     {cm['peak_ram_mb']:.1f} MB")
            
            print(f"\n{'─'*80}")
            print(f"Individual Import Performance:")
            print(f"{'─'*80}")
            
            for idx, imp in enumerate(self.results['imports'], 1):
                status_icon = "✓" if imp['success'] else "✗"
                print(f"\n{idx}. {status_icon} {imp['folder_name']}")
                print(f"   Duration: {imp['duration_formatted']} | "
                      f"Rows: {imp['total_rows_added']:,} | "
                      f"Size: +{imp['database_metrics']['size_increase_mb']:.1f} MB | "
                      f"CPU: {imp['system_metrics']['cpu_average_percent']:.1f}% | "
                      f"RAM: {imp['system_metrics']['ram_average_mb']:.1f} MB")
                      
        print(f"\n{'#'*80}\n")


class IntervalDeduplicator:
    """Handles interval deduplication by matching against existing database entries"""
    
    @staticmethod
    def get_existing_intervals(assembly_id):
        """
        Get all intervals from database for a given assembly.
        Returns a dict mapping external_id -> interval object for fast lookup.
        """
        from interval.models import Interval
        
        intervals = Interval.objects.filter(assembly_id=assembly_id).values(
            'id', 'external_id'
        )
        
        mapping = {}
        for interval in intervals:
            mapping[interval['external_id']] = interval['id']
        
        return mapping
    
    @staticmethod
    def get_max_interval_id():
        """Get the maximum interval ID in the database"""
        from interval.models import Interval
        from django.db.models import Max
        
        max_id = Interval.objects.aggregate(Max('id'))['id__max']
        return max_id if max_id else 0
    
    @staticmethod
    def deduplicate_intervals_csv(intervals_df, existing_mapping, max_interval_id):
        """
        Process intervals DataFrame to deduplicate against existing database entries.
        Returns:
            - modified_df: DataFrame with updated interval IDs
            - csv_to_new_id_mapping: Dict mapping original CSV row indices to final internal IDs
        """
        csv_to_new_id_mapping = {}
        next_id = max_interval_id + 1
        
        # Create a copy to modify
        modified_df = intervals_df.copy()
        
        for idx, row in modified_df.iterrows():
            external_id = row.get('external_id')
            
            if external_id in existing_mapping:
                # Use existing interval ID
                internal_id = existing_mapping[external_id]
                csv_to_new_id_mapping[idx] = internal_id
                print(f"    → Interval {external_id}: using existing ID {internal_id}")
            else:
                # Assign new ID
                csv_to_new_id_mapping[idx] = next_id
                next_id += 1
                print(f"    → Interval {external_id}: assigning new ID {csv_to_new_id_mapping[idx]}")
        
        return csv_to_new_id_mapping
    
    @staticmethod
    def remap_signals_interval_ids_chunked(input_signal_path, output_signal_path, csv_to_new_id_mapping, chunksize=100000):
        """
        Process signals CSV in chunks to remap interval IDs memory-efficiently.
        Handles large CSV files (millions/billions of rows) without loading entire file.
        
        Args:
            input_signal_path: Path to original signals CSV
            output_signal_path: Path to write remapped signals CSV
            csv_to_new_id_mapping: Dict mapping original interval IDs to new IDs
            chunksize: Rows to process per chunk (default 100k)
        """
        import pandas as pd
        
        rows_processed = 0
        chunks_written = 0
        
        # Open output file once and write all chunks to it
        with open(output_signal_path, 'w') as f:
            for chunk_num, chunk in enumerate(pd.read_csv(input_signal_path, chunksize=chunksize)):
                # Remap the interval_id column using the mapping
                chunk['interval_id'] = chunk['interval_id'].map(
                    lambda original_id: csv_to_new_id_mapping.get(original_id - 1, original_id)
                )
                
                # Write chunk to output file (header only on first chunk)
                chunk.to_csv(
                    f,
                    header=(chunk_num == 0),
                    index=False
                )
                
                rows_processed += len(chunk)
                chunks_written += 1
                
                if chunks_written % 10 == 0:
                    print(f"      Processed {rows_processed:,} signal rows ({chunks_written} chunks)")
        
        print(f"      Total: {rows_processed:,} signal rows remapped across {chunks_written} chunks")
        return rows_processed


def import_folder_custom(folder_path, omit_zero_signals=False, validate_signal_refs=False, deduplicate_intervals=False):
    """
    Import folder using the pandas bulk import
    """
    import os
    import glob
    import pandas as pd
    from studies.models import Study
    from assay.models import Assay
    from pipelines.models import Pipeline
    from assembly.models import Assembly
    from databasemanager.pandas_bulk_import import bulk_import_with_pandas
    
    print(f"  → Processing folder: {folder_path}")
    folder_name = os.path.basename(folder_path)
    
    signal_files = glob.glob(os.path.join(folder_path, '*signal*.csv'))
    interval_files = glob.glob(os.path.join(folder_path, '*interval*.csv'))
    cell_files = glob.glob(os.path.join(folder_path, '*cell*.csv'))
    assay_files = glob.glob(os.path.join(folder_path, '*assay*.csv'))
    pipeline_files = glob.glob(os.path.join(folder_path, '*pipeline*.csv'))
    assembly_files = glob.glob(os.path.join(folder_path, '*assembly*.csv'))
    
    if not signal_files or not interval_files:
        print(f"  ⚠ Skipping - missing required files (signal/interval)")
        return
    
    # Load study data from CSV if available
    study_files = glob.glob(os.path.join(folder_path, '*study*.csv'))
    study_data = {}
    if study_files:
        df_study = pd.read_csv(study_files[0])
        if len(df_study) > 0:
            study_data = df_study.iloc[0].to_dict()
    
    # Create or get study with all available fields
    study_external_id = study_data.get('external_id', folder_name)
    study_defaults = {
        'name': study_data.get('name', folder_name),
        'description': study_data.get('description'),
        'external_repo': study_data.get('external_repo'),
        'availability': bool(study_data.get('availability', True)) if study_data.get('availability') is not None else True,
        'note': study_data.get('note', f'Imported from {folder_path}')
    }
    
    try:
        study, created = Study.objects.get_or_create(
            external_id=study_external_id,
            defaults=study_defaults
        )
        # Update fields if study already exists but data changed
        if not created:
            updates = {}
            for field in ['name', 'description', 'external_repo', 'availability', 'note']:
                new_val = study_defaults.get(field)
                if new_val is not None and getattr(study, field) != new_val:
                    updates[field] = new_val
            if updates:
                for k, v in updates.items():
                    setattr(study, k, v)
                study.save(update_fields=list(updates.keys()))
    except IntegrityError:
        # External ID already exists; reuse the existing study to avoid UNIQUE conflicts
        study = Study.objects.get(external_id=study_external_id)
    print(f"  → Study: {study.name} (ID: {study.id})")
    
    # Create or reuse pipeline (only import FIRST pipeline from CSV per dataset)
    pipeline_data = {}
    if pipeline_files:
        df_pipeline = pd.read_csv(pipeline_files[0])
        if len(df_pipeline) > 0:
            pipeline_data = df_pipeline.iloc[0].to_dict()

    # Use external_url (previously external_id) for pipeline lookup
    pipeline_external_url = pipeline_data.get('external_url') or pipeline_data.get('external_id', folder_name)
    pipeline_defaults = {
        'name': pipeline_data.get('name', folder_name),
        'description': pipeline_data.get('description', f'Pipeline for {folder_name}')
    }
    pipeline, created_pipeline = Pipeline.objects.get_or_create(
        external_url=pipeline_external_url,
        defaults=pipeline_defaults
    )
    # Update name/description if provided and different
    updates = {}
    for field in ['name', 'description']:
        if pipeline_defaults.get(field) and getattr(pipeline, field) != pipeline_defaults.get(field):
            updates[field] = pipeline_defaults[field]
    if updates:
        for k, v in updates.items():
            setattr(pipeline, k, v)
        pipeline.save(update_fields=list(updates.keys()))
    print(f"  → Pipeline: {pipeline.name} (ID: {pipeline.id})")

    # Then create assay attached to pipeline (required non-null fields filled with safe defaults)
    assay_data = {}
    if assay_files:
        df_assay = pd.read_csv(assay_files[0])
        if len(df_assay) > 0:
            assay_data = df_assay.iloc[0].to_dict()

    def _default(val, fallback):
        """Return fallback if val is None or NaN, otherwise return val"""
        if val is None:
            return fallback
        if isinstance(val, float) and pd.isna(val):
            return fallback
        # Convert empty strings to fallback for non-nullable fields
        if isinstance(val, str) and val.strip() == '':
            return fallback
        return val
    
    def _optional(val):
        """Return None for NaN/empty values, otherwise return val"""
        if val is None:
            return None
        if isinstance(val, float) and pd.isna(val):
            return None
        if isinstance(val, str) and val.strip() == '':
            return None
        return val

    # Create assay using the pipeline we just created/retrieved
    # (Only import FIRST assay from CSV per dataset)
    assay = Assay.objects.create(
        study=study,
        pipeline=pipeline,  # Use the pipeline we just created/retrieved
        external_id=_default(assay_data.get('external_id'), f"{folder_name}_assay"),
        name=_default(assay_data.get('name'), folder_name),
        type=_default(assay_data.get('type'), 'unspecified'),
        treatment=_default(assay_data.get('treatment'), 'unspecified'),
        platform=_default(assay_data.get('platform'), 'unspecified'),
        target=_optional(assay_data.get('target')),
        tissue=_optional(assay_data.get('tissue')),
        cell_type=_optional(assay_data.get('cell_type')),
        description=_optional(assay_data.get('description')),
        availability=bool(_default(assay_data.get('availability'), True)),
        note=_optional(assay_data.get('note')),
        kit=_optional(assay_data.get('kit')),
        date=_optional(assay_data.get('date')),
    )
    print(f"  → Assay: {assay.name} (ID: {assay.id}, pipeline_id: {assay.pipeline_id})")
    
    if assembly_files:
        df_assembly = pd.read_csv(assembly_files[0])
        if len(df_assembly) > 0:
            assembly_data = df_assembly.iloc[0].to_dict()
        else:
            assembly_data = {}
    else:
        assembly_data = {}

    assembly = Assembly.objects.create(
        name=assembly_data.get('name', folder_name),
        version=assembly_data.get('version', 'v1'),
        species=assembly_data.get('species')
    )
    print(f"  → Assembly: {assembly.name} (ID: {assembly.id})")
    
    # Handle interval deduplication if enabled
    interval_path_to_use = interval_files[0]
    signal_path_to_use = signal_files[0]
    
    if deduplicate_intervals:
        print(f"  → Deduplicating intervals against existing database...")
        
        # Load intervals CSV (usually small)
        df_intervals = pd.read_csv(interval_files[0])
        
        # Get existing intervals for this assembly
        existing_mapping = IntervalDeduplicator.get_existing_intervals(assembly.id)
        max_interval_id = IntervalDeduplicator.get_max_interval_id()
        
        print(f"    • Found {len(existing_mapping)} existing intervals in assembly")
        print(f"    • Current max interval ID: {max_interval_id}")
        print(f"    • Processing {len(df_intervals)} intervals from CSV...")
        
        # Deduplicate intervals and get mapping
        csv_to_new_id_mapping = IntervalDeduplicator.deduplicate_intervals_csv(
            df_intervals, existing_mapping, max_interval_id
        )
        
        # Process signals CSV in chunks (memory-efficient for large files)
        print(f"    • Remapping signals CSV in chunks...")
        import tempfile
        temp_dir = tempfile.gettempdir()
        interval_path_to_use = os.path.join(temp_dir, f'intervals_dedup_{int(time.time())}.csv')
        signal_path_to_use = os.path.join(temp_dir, f'signals_dedup_{int(time.time())}.csv')
        
        # Write deduplicated intervals CSV
        df_intervals.to_csv(interval_path_to_use, index=False)
        
        # Process signals CSV in chunks for memory efficiency
        IntervalDeduplicator.remap_signals_interval_ids_chunked(
            signal_files[0],
            signal_path_to_use,
            csv_to_new_id_mapping,
            chunksize=500000  # Process 500k rows at a time
        )
        
        print(f"    ✓ Deduplication complete")
    
    print(f"  → Importing intervals, cells, signals...")
    result = bulk_import_with_pandas(
        interval_path=interval_path_to_use,
        cell_path=cell_files[0] if cell_files else None,
        signal_path=signal_path_to_use,
        assembly_id=assembly.id,
        assay_id=assay.id,
        omit_zero_signals=omit_zero_signals,
        validate_signal_refs=validate_signal_refs,
        deduplicate_intervals=False,  # Already done by stress test script above
        ignore_optional_type_errors=True,
        ignore_conflicts=True,
        ignore_row_errors=False,
    )
    
    if not result.get('success'):
        raise Exception(f"Import failed: {result.get('error')}")
    
    # Display import summary with deduplication info
    counts = result['counts']
    if counts.get('original_interval_count', 0) > 0:
        dedup_info = f" ({counts.get('deduplicated_intervals', 0)} deduplicated from {counts.get('original_interval_count', 0)} original)"
        print(f"  ✓ Imported {counts['intervals']} intervals{dedup_info}, "
              f"{counts['cells']} cells, {counts['signals']} signals")
    else:
        print(f"  ✓ Imported {counts['intervals']} intervals, "
              f"{counts['cells']} cells, {counts['signals']} signals")


def main():
    """Main stress test execution"""
    import argparse
    parser = argparse.ArgumentParser(description="Stress test importer")
    parser.add_argument(
        "--omit-zero-signals",
        action="store_true",
        help="Omit zero-valued signals (faster, smaller DB)",
    )
    parser.add_argument(
        "--include-zero-signals",
        action="store_false",
        dest="omit_zero_signals",
        help="Include zero-valued signals (default)",
    )
    parser.add_argument(
        "--validate-signal-refs",
        action="store_true",
        dest="validate_signal_refs",
        help="Validate that interval_id and cell_id referenced in signals CSV exist in imported intervals/cells (default off)",
    )
    parser.add_argument(
        "--deduplicate-intervals",
        action="store_true",
        dest="deduplicate_intervals",
        help="Deduplicate intervals by checking against existing database entries (default off)",
    )
    # removed signals-import-mode option; sqlite single-file is enforced in importer
    parser.set_defaults(omit_zero_signals=False, validate_signal_refs=False, deduplicate_intervals=False)
    args = parser.parse_args()

    omit_zero_signals = args.omit_zero_signals
    validate_signal_refs = args.validate_signal_refs
    deduplicate_intervals = args.deduplicate_intervals

    data_root = '/data'
    test_folders = []

    if os.path.exists(data_root) and os.path.isdir(data_root):
        folder_names = sorted([
            d for d in os.listdir(data_root)
            if os.path.isdir(os.path.join(data_root, d))
        ])
        
        for folder_name in folder_names:
            folder_path = os.path.join(data_root, folder_name)
            test_folders.append({
                'name': f'Dataset: {folder_name}',
                'path': folder_path,
                'description': f'Auto-discovered folder: {folder_name}'
            })
        
        print(f"\n{'─'*80}")
        print(f"Discovered {len(test_folders)} folders in {data_root}:")
        for tf in test_folders:
            print(f"  • {tf['name']}")
        print(f"{'─'*80}\n")
    else:
        print(f"\n⚠ WARNING: Data directory not found: {data_root}")
        print(f"No folders to import.\n")
        return

    runner = StressTestRunner()

    print(f"\n{'#'*80}")
    print(f"# bMINTY STRESS TEST")
    print(f"# Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*80}\n")
    
    runner.create_fresh_database()

    for folder_config in test_folders:
        folder_path = folder_config['path']
        runner.import_folder(
            folder_path,
            folder_config['name'],
            lambda p, oz=omit_zero_signals, vsr=validate_signal_refs, di=deduplicate_intervals: import_folder_custom(p, omit_zero_signals=oz, validate_signal_refs=vsr, deduplicate_intervals=di)
        )
    
    results_file = runner.finalize_results()
    runner.print_final_report()
    
    print(f"\nStress test completed!")
    print(f"Results saved to: {results_file}")


if __name__ == '__main__':
    main()
