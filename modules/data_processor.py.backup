"""
Data processing module for handling CSV/Excel data operations.
Extracted from app.py to improve cohesion and reduce file size.
"""

import pandas as pd
import numpy as np
import logging
import multiprocessing
from pathlib import Path
import re
import os
import sys

from config.app_config import ProcessingConfig
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.utils import write_shared_log


class DataProcessor:
    """Handles data processing and validation operations."""
    
    def __init__(self, app_instance):
        self.app = app_instance
        
    def load_and_validate_data(self, file_path):
        """Load and validate the merged file data."""
        try:
            df = pd.read_excel(file_path)
            logging.info(f"Loaded {len(df)} records from {file_path}")
            
            # Validate required columns using configuration
            ProcessingConfig.validate_required_columns(df)
            
            # Prepare data for processing
            df = df.sort_values(by=["DATEFILLED", "SOURCERECORDID"], ascending=True)
            df["Logic"] = ""
            df["RowID"] = np.arange(len(df))
            
            return df
            
        except Exception as e:
            error_msg = f"Error loading data from {file_path}: {str(e)}"
            logging.error(error_msg)
            write_shared_log("DataProcessor", error_msg, "ERROR")
            raise
    
    def process_data_multiprocessing(self, df):
        """Process data using multiprocessing for improved performance."""
        try:
            # Import and use multiprocessing helpers
            from modules import mp_helpers
            
            num_workers = ProcessingConfig.get_multiprocessing_workers()
            df_blocks = np.array_split(df, num_workers)
            out_queue = multiprocessing.Queue()
            processes = []
            
            # Start worker processes
            for block in df_blocks:
                p = multiprocessing.Process(
                    target=mp_helpers.worker, args=(block, out_queue)
                )
                p.start()
                processes.append(p)
            
            # Collect results
            results = [out_queue.get() for _ in processes]
            for p in processes:
                p.join()
            
            processed_df = pd.concat(results)
            logging.info(f"Processed {len(processed_df)} records using {num_workers} workers")
            return processed_df
            
        except Exception as e:
            error_msg = f"Error processing data with multiprocessing: {str(e)}"
            logging.error(error_msg)
            write_shared_log("DataProcessor", error_msg, "ERROR")
            raise
    
    def save_processed_outputs(self, df, output_dir=None):
        """Save processed data to various output formats."""
        try:
            if output_dir is None:
                output_dir = Path.cwd()
            else:
                output_dir = Path(output_dir)
            
            # Sort and filter data
            df_sorted = pd.concat([df[df["Logic"] == ""], df[df["Logic"] == "OR"]])
            
            # Create row mapping for highlighting
            row_mapping = {
                row["RowID"]: i + 2 for i, (_, row) in enumerate(df_sorted.iterrows())
            }
            excel_rows_to_highlight = [
                row_mapping[rid] for rid in [] if rid in row_mapping
            ]  # Placeholder for unmatched reversals
            
            # Clean up data
            df_sorted.drop(columns=["RowID"], inplace=True, errors="ignore")
            output_file = output_dir / "merged_file_with_OR.xlsx"
            
            # Save to multiple formats
            self._save_to_parquet(df_sorted, output_dir)
            self._save_to_excel(df_sorted, output_file)
            self._save_to_csv(df_sorted, output_dir)
            self._save_unmatched_reversals(excel_rows_to_highlight, output_dir)
            
            return output_file
            
        except Exception as e:
            error_msg = f"Error saving processed outputs: {str(e)}"
            logging.error(error_msg)
            write_shared_log("DataProcessor", error_msg, "ERROR")
            raise
    
    def _save_to_parquet(self, df, output_dir):
        """Save data to Parquet format for large DataFrames."""
        try:
            parquet_path = output_dir / "merged_file_with_OR.parquet"
            df.drop_duplicates().to_parquet(parquet_path, index=False)
            logging.info(f"Saved intermediate Parquet file: {parquet_path}")
        except Exception as e:
            logging.warning(f"Could not save Parquet: {e}")
    
    def _save_to_excel(self, df, output_file):
        """Save data to Excel format."""
        df.drop_duplicates().to_excel(output_file, index=False)
        logging.info(f"Saved Excel file: {output_file}")
    
    def _save_to_csv(self, df, output_dir):
        """Save data to CSV format with opportunity name."""
        try:
            opportunity_name = self._extract_opportunity_name()
            csv_path = output_dir / f"{opportunity_name} Claim Detail.csv"
            df.drop_duplicates().to_csv(csv_path, index=False)
            logging.info(f"Saved CSV file: {csv_path}")
        except Exception as e:
            logging.warning(f"Could not save CSV: {e}")
    
    def _save_unmatched_reversals(self, excel_rows_to_highlight, output_dir):
        """Save unmatched reversals information."""
        try:
            unmatched_path = output_dir / "unmatched_reversals.txt"
            with open(unmatched_path, "w") as f:
                f.write(",".join(map(str, excel_rows_to_highlight)))
            logging.info(f"Saved unmatched reversals info: {unmatched_path}")
        except Exception as e:
            logging.warning(f"Could not save unmatched reversals: {e}")
    
    def _extract_opportunity_name(self):
        """Extract opportunity name from file1_path."""
        opportunity_name = ProcessingConfig.DEFAULT_OPPORTUNITY_NAME
        try:
            if self.app.file1_path:
                if self.app.file1_path.lower().endswith(".xlsx"):
                    df_file1 = pd.read_excel(self.app.file1_path)
                else:
                    df_file1 = pd.read_csv(self.app.file1_path)
                
                if df_file1.shape[1] >= 2:
                    # Get the value from the first row, second column
                    raw_name = str(df_file1.iloc[0, 1])
                    # Clean for filename
                    opportunity_name = re.sub(r'[\\/*?:"<>|]', "_", raw_name)
        except Exception as e:
            logging.warning(f"Could not extract opportunity name from file1: {e}")
        
        return opportunity_name
    
    def validate_merge_inputs(self, file1_path, file2_path):
        """Validate that merge inputs are valid."""
        # Check if both file paths are set and files exist
        if not file1_path or not file2_path:
            return False, "Both input files must be selected."
        
        if not os.path.isfile(file1_path):
            return False, f"File not found: {file1_path}"
        
        if not os.path.isfile(file2_path):
            return False, f"File not found: {file2_path}"
        
        return True, "Inputs are valid"
    
    def validate_gross_cost_template(self, file_path):
        """Validate GrossCost column and suggest template type."""
        try:
            df = pd.read_csv(file_path)
            
            # Guard clause: no GrossCost column
            if "GrossCost" not in df.columns:
                return None
            
            return self._determine_template_type(df["GrossCost"])
            
        except Exception as e:
            logging.warning(f"Could not validate GrossCost column: {e}")
            return None
    
    def _determine_template_type(self, gross_cost_series):
        """Determine which template type to recommend based on GrossCost data."""
        if gross_cost_series.isna().all() or (gross_cost_series == 0).all():
            return "The GrossCost column is blank or all zero. Please use the Blind template."
        else:
            return "The GrossCost column contains data. Please use the Standard template."
