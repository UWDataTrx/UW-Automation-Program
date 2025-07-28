import sys
from pathlib import Path

# Add the project root directory to the Python path using pathlib
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

import pandas as pd  # noqa: E402
import numpy as np  # noqa: E402
import logging  # noqa: E402
import multiprocessing  # noqa: E402
import re  # noqa: E402
import os  # noqa: E402


try:
    from config.app_config import ProcessingConfig
    from utils.utils import write_audit_log
except ImportError:
    # Fallback if imports are not available
    def write_audit_log(script_name, message, status="INFO"):
        """Fallback logging function when utils.utils is not available"""
        print(f"[{status}] {script_name}: {message}")

    # You must ensure config.app_config.ProcessingConfig is available for correct typing.
    raise ImportError(
        "config.app_config.ProcessingConfig must be available for DataProcessor to work correctly."
    )


class DataProcessor:
    """Handles data processing and validation operations."""

    def __init__(self, app_instance):
        self.app = app_instance
        try:
            self.username = os.getlogin()
        except Exception:
            self.username = (
                os.environ.get("USERNAME") or os.environ.get("USER") or "UnknownUser"
            )

    def _read_file_flexible(self, file_path):
        """Read file supporting both CSV and Excel formats."""
        try:
            file_path_obj = Path(file_path)
            if file_path_obj.suffix.lower() in (".xlsx", ".xls"):
                return pd.read_excel(file_path_obj), "Excel"
            else:
                return pd.read_csv(file_path_obj), "CSV"
        except Exception as e:
            raise Exception(f"Could not read file {file_path}: {str(e)}")

    def load_and_validate_data(self, file_path):
        """Load and validate the merged file data with enhanced error handling."""
        try:
            file_path_obj = Path(file_path)
            # Load the Excel file
            df = pd.read_excel(file_path_obj)
            logging.info(
                f"Loaded {len(df)} records from {file_path_obj} by user: {self.username}"
            )
            write_audit_log(
                "data_processor.py",
                f"User {self.username} loaded file: {file_path_obj}",
                "INFO",
            )

            # Validate that we have data
            if df.empty:
                write_audit_log(
                    "data_processor.py",
                    f"User {self.username} attempted to load empty file: {file_path_obj}",
                    "WARNING",
                )
                raise ValueError(
                    f"The file {file_path_obj} is empty or contains no data"
                )

            # Validate required columns using configuration with fallback
            write_audit_log(
                "data_processor.py",
                f"Validated columns for file: {file_path_obj} by user: {self.username}",
                "INFO",
            )
            logging.info(
                f"Validated columns for file: {file_path_obj} by user: {self.username}"
            )
            try:
                ProcessingConfig.validate_required_columns(df)
            except Exception as config_error:
                logging.warning(f"Configuration validation failed: {config_error}")
                # Fallback validation for essential columns
                essential_columns = ["DATEFILLED", "SOURCERECORDID"]
                missing_essential = [
                    col for col in essential_columns if col not in df.columns
                ]
                if missing_essential:
                    raise ValueError(f"Missing essential columns: {missing_essential}")

            # Prepare data for processing with enhanced error handling
            df = self._safe_prepare_data_for_processing(df)

            return df

        except Exception as e:
            write_audit_log(
                "data_processor.py",
                f"Processing failed for user: {self.username}: {e}",
                "ERROR",
            )
            error_msg = f"Error loading data from {file_path}: {str(e)}"
            logging.error(error_msg)
            write_audit_log("DataProcessor", error_msg, "ERROR")
            raise

    def _safe_prepare_data_for_processing(self, df):
        """Safely prepare data for processing with comprehensive error handling."""
        try:
            # Create a copy to avoid modifying the original
            df_processed = df.copy()

            # Remove existing RowID column if present
            if "RowID" in df_processed.columns:
                df_processed = df_processed.drop(columns=["RowID"])
                logging.info("Removed existing RowID column")

            # Add Logic column if missing
            if "Logic" not in df_processed.columns:
                df_processed["Logic"] = ""
                logging.info("Added missing Logic column")

            # Safe sorting with validation
            df_processed = self._safe_sort_dataframe(df_processed)

            # Safe RowID creation
            df_processed = self._safe_create_rowid(df_processed)

            return df_processed

        except Exception as e:
            logging.error(f"Error in data preparation: {e}")
            # Return original DataFrame with minimal processing as fallback
            if "Logic" not in df.columns:
                df["Logic"] = ""
            if "RowID" not in df.columns:
                df["RowID"] = df.index
            return df

    def _safe_sort_dataframe(self, df):
        """Safely sort the DataFrame with error handling."""
        sort_columns = ["DATEFILLED", "SOURCERECORDID"]

        try:
            # Check which sort columns are available
            available_sort_cols = [col for col in sort_columns if col in df.columns]

            if not available_sort_cols:
                logging.warning("No sort columns available. Using original order.")
                return df

            # Check for null values in sort columns and handle them
            for col in available_sort_cols:
                null_count = df[col].isnull().sum()
                if null_count > 0:
                    logging.warning(
                        f"Found {null_count} null values in sort column '{col}'. Filling with default values."
                    )

                    if col == "DATEFILLED":
                        # Fill null dates with a default date
                        df[col] = df[col].fillna(pd.Timestamp("1900-01-01"))
                    elif col == "SOURCERECORDID":
                        # Fill null IDs with a default pattern
                        df[col] = df[col].fillna("UNKNOWN_ID")

            # Perform the sort
            df_sorted = df.sort_values(by=available_sort_cols, ascending=True)
            logging.info(f"Successfully sorted by: {available_sort_cols}")

            return df_sorted

        except Exception as e:
            logging.warning(f"Sorting failed: {e}. Using original order.")
            return df

    def _safe_create_rowid(self, df):
        """Safely create RowID column with multiple fallback methods."""
        try:
            # Method 1: Standard numpy arange
            df["RowID"] = np.arange(len(df))
            logging.info("Successfully created RowID using np.arange")
            return df

        except Exception as e1:
            logging.warning(
                f"Standard RowID creation failed: {e1}. Trying alternative methods."
            )

            try:
                # Method 2: Use DataFrame index
                df["RowID"] = df.index.values
                logging.info("Created RowID using DataFrame index")
                return df

            except Exception as e2:
                logging.warning(
                    f"Index-based RowID creation failed: {e2}. Trying manual creation."
                )

                try:
                    # Method 3: Manual creation with list comprehension
                    df["RowID"] = [i for i in range(len(df))]
                    logging.info("Created RowID using manual list creation")
                    return df

                except Exception as e3:
                    logging.error(
                        f"All RowID creation methods failed: {e1}, {e2}, {e3}"
                    )
                    # Final fallback: create a simple series
                    df["RowID"] = pd.Series(range(len(df)), index=df.index)
                    logging.info("Created RowID using pandas Series (final fallback)")
                    return df

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
            logging.info(
                f"Processed {len(processed_df)} records using {num_workers} workers"
            )
            return processed_df

        except Exception as e:
            error_msg = f"Error processing data with multiprocessing: {str(e)}"
            logging.error(error_msg)
            write_audit_log("DataProcessor", error_msg, "ERROR")
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
            # Safe RowID removal with enhanced error handling
            try:
                if "RowID" in df_sorted.columns:
                    df_sorted.drop(columns=["RowID"], inplace=True)
                    logging.info("Successfully removed RowID column before saving")
            except Exception as e:
                logging.warning(f"Could not remove RowID column: {e}")
                # Continue without removing RowID - it's not critical for output
            output_file = output_dir / "merged_file_with_OR.xlsx"

            # Save to multiple formats
            self._save_to_parquet(df_sorted, output_dir)
            write_audit_log(
                "DataProcessor",
                f"Saved Parquet file: {output_dir / 'merged_file_with_OR.parquet'}",
                "INFO",
            )
            self._save_to_excel(df_sorted, output_file)
            write_audit_log("DataProcessor", f"Saved Excel file: {output_file}", "INFO")
            self._save_to_csv(df_sorted, output_dir)
            self._save_unmatched_reversals(excel_rows_to_highlight, output_dir)

            return output_file

        except Exception as e:
            error_msg = f"Error saving processed outputs: {str(e)}"
            logging.error(error_msg)
            write_audit_log("DataProcessor", error_msg, "ERROR")
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
            # Validate opportunity_name
            if not opportunity_name or not opportunity_name.strip():
                opportunity_name = "Unknown_Opportunity"
                logging.warning(
                    "Opportunity name was empty or invalid. Defaulting to 'Unknown_Opportunity'."
                )
                write_audit_log(
                    "DataProcessor",
                    "Opportunity name was empty or invalid. Defaulting to 'Unknown_Opportunity'.",
                    "WARNING",
                )
            csv_path = output_dir / f"{opportunity_name} Claim Detail.csv"
            df.drop_duplicates().to_csv(csv_path, index=False)
            logging.info(f"Saved CSV file: {csv_path}")
            write_audit_log("DataProcessor", f"Saved CSV file: {csv_path}", "INFO")
        except Exception as e:
            logging.warning(f"Could not save CSV: {e}")
            write_audit_log("DataProcessor", f"Could not save CSV: {e}", "ERROR")

    def _save_unmatched_reversals(self, excel_rows_to_highlight, output_dir):
        """Save unmatched reversals information."""
        try:
            unmatched_path = output_dir / "unmatched_reversals.txt"
            with open(unmatched_path, "w") as f:
                f.write(",".join(map(str, excel_rows_to_highlight)))
            logging.info(f"Saved unmatched reversals info: {unmatched_path}")
            write_audit_log(
                "DataProcessor",
                f"Saved unmatched reversals info: {unmatched_path}",
                "INFO",
            )
        except Exception as e:
            logging.warning(f"Could not save unmatched reversals: {e}")
            write_audit_log(
                "DataProcessor", f"Could not save unmatched reversals: {e}", "ERROR"
            )

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

        if not Path(file1_path).is_file():
            return False, f"File not found: {file1_path}"

        if not Path(file2_path).is_file():
            return False, f"File not found: {file2_path}"

        return True, "Inputs are valid"

    def validate_gross_cost_template(self, file_path):
        """Validate GrossCost column and suggest template type for both CSV and Excel files."""
        try:
            # Use the flexible file reader
            df, file_type = self._read_file_flexible(file_path)

            logging.info(
                f"Reading {file_type} file for template validation: {file_path}"
            )

            # Guard clause: no GrossCost column
            if "GrossCost" not in df.columns:
                return f"File Analysis Complete ({file_type}):\n\nNo 'GrossCost' column found in the data.\n\nTemplate Recommendation:\nUse the BLANK template since there's no cost data to analyze."

            return self._determine_template_type(df["GrossCost"], file_type)

        except Exception as e:
            logging.warning(f"Could not validate GrossCost column: {e}")
            return f"File Analysis Warning:\n\nCould not analyze the file: {str(e)}\n\nDefault Recommendation:\nIf your data contains cost information, use the STANDARD template.\nIf your data has no costs or only $0 values, use the BLANK template."

    def _determine_template_type(self, gross_cost_series, file_type=""):
        """Determine template type based on GrossCost data analysis."""
        # Check for null/empty values
        null_count = gross_cost_series.isnull().sum()
        total_count = len(gross_cost_series)

        # Convert to numeric, handling errors
        numeric_costs = pd.to_numeric(gross_cost_series, errors="coerce")
        zero_count = (numeric_costs == 0).sum()

        # Calculate percentages
        null_percent = (null_count / total_count) * 100 if total_count > 0 else 0
        zero_percent = (zero_count / total_count) * 100 if total_count > 0 else 0
        blank_or_zero_percent = (
            ((null_count + zero_count) / total_count) * 100 if total_count > 0 else 0
        )

        file_info = f" ({file_type})" if file_type else ""

        # Determine template recommendation
        if blank_or_zero_percent >= 80:
            return (
                f"File Analysis Complete{file_info}:\n\n"
                f"GrossCost Analysis:\n"
                f"• Total records: {total_count:,}\n"
                f"• Blank/null values: {null_count:,} ({null_percent:.1f}%)\n"
                f"• Zero values: {zero_count:,} ({zero_percent:.1f}%)\n"
                f"• Combined blank/zero: {blank_or_zero_percent:.1f}%\n\n"
                f"🎯 TEMPLATE RECOMMENDATION: BLANK TEMPLATE\n"
                f"Most of your cost data is blank or zero - use the Blind template for this type of data."
            )
        else:
            has_costs_count = total_count - null_count - zero_count
            return (
                f"File Analysis Complete{file_info}:\n\n"
                f"GrossCost Analysis:\n"
                f"• Total records: {total_count:,}\n"
                f"• Records with cost data: {has_costs_count:,} ({100 - blank_or_zero_percent:.1f}%)\n"
                f"• Blank/zero values: {null_count + zero_count:,} ({blank_or_zero_percent:.1f}%)\n\n"
                f"🎯 TEMPLATE RECOMMENDATION: STANDARD TEMPLATE\n"
                f"Your data contains significant cost information - use the Standard template to properly process this data."
            )
