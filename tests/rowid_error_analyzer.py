"""
RowID Error Analyzer and Fixer
Diagnoses and fixes the 'RowID' column error in merged_file.xlsx processing.
"""

import pandas as pd
import numpy as np
import os
import sys
import traceback
import logging
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from config.app_config import ProcessingConfig as AppProcessingConfig

    REQUIRED_COLUMNS = getattr(
        AppProcessingConfig,
        "REQUIRED_COLUMNS",
        ["DATEFILLED", "SOURCERECORDID", "NDC", "MemberID"],
    )
except ImportError:
    # Fallback if config not available
    REQUIRED_COLUMNS = ["DATEFILLED", "SOURCERECORDID", "NDC", "MemberID"]


class RowIDErrorAnalyzer:
    """Analyzes and fixes RowID-related errors in data processing."""

    def __init__(self):
        self.setup_logging()

    def setup_logging(self):
        """Setup logging for the analyzer."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler("rowid_error_analysis.log"),
                logging.StreamHandler(sys.stdout),
            ],
        )
        self.logger = logging.getLogger(__name__)

    def analyze_merged_file_error(self, file_path="merged_file.xlsx"):
        """Analyze the merged file for RowID-related issues."""
        self.logger.info("=== RowID Error Analysis Started ===")
        self.logger.info(f"Analyzing file: {file_path}")

        # Check if file exists
        if not os.path.exists(file_path):
            self.logger.error(f"File not found: {file_path}")
            return self.create_error_report(
                "FILE_NOT_FOUND", f"File {file_path} does not exist"
            )

        try:
            # Load the file
            self.logger.info("Loading Excel file...")
            df = pd.read_excel(file_path)
            self.logger.info(
                f"Successfully loaded {len(df)} rows, {len(df.columns)} columns"
            )

            # Analyze the data structure
            analysis_results = self.analyze_dataframe_structure(df)

            # Test RowID creation
            rowid_test_results = self.test_rowid_creation(df)

            # Generate comprehensive report
            report = self.generate_analysis_report(
                analysis_results, rowid_test_results, file_path
            )

            return report

        except Exception as e:
            error_details = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc(),
            }
            self.logger.error(f"Error during analysis: {error_details}")
            return self.create_error_report("ANALYSIS_ERROR", error_details)

    def analyze_dataframe_structure(self, df):
        """Analyze the DataFrame structure for potential issues."""
        results = {}

        # Basic info
        results["shape"] = df.shape
        results["columns"] = list(df.columns)
        results["dtypes"] = df.dtypes.to_dict()
        results["memory_usage_mb"] = df.memory_usage(deep=True).sum() / 1024 / 1024

        # Check for existing RowID column
        results["has_existing_rowid"] = "RowID" in df.columns
        if results["has_existing_rowid"]:
            results["existing_rowid_info"] = {
                "dtype": str(df["RowID"].dtype),
                "unique_count": df["RowID"].nunique(),
                "has_nulls": df["RowID"].isnull().any(),
                "sample_values": df["RowID"].head(10).tolist(),
            }

        # Check required columns from config/app_config or fallback
        required_cols = REQUIRED_COLUMNS
        results["missing_required_columns"] = [
            col for col in required_cols if col not in df.columns
        ]
        results["has_all_required"] = len(results["missing_required_columns"]) == 0

        # Check for data quality issues
        results["data_quality"] = {
            "total_nulls": df.isnull().sum().sum(),
            "duplicate_rows": df.duplicated().sum(),
            "empty_columns": [col for col in df.columns if df[col].isnull().all()],
        }

        # Check key columns for sorting
        sort_columns = ["DATEFILLED", "SOURCERECORDID"]
        results["sort_column_issues"] = {}
        for col in sort_columns:
            if col in df.columns:
                results["sort_column_issues"][col] = {
                    "has_nulls": df[col].isnull().any(),
                    "null_count": df[col].isnull().sum(),
                    "dtype": str(df[col].dtype),
                }
            else:
                results["sort_column_issues"][col] = {"missing": True}

        return results

    def test_rowid_creation(self, df):
        """Test the RowID creation process to identify where it fails."""
        results = {}

        try:
            # Test 1: Basic RowID creation
            self.logger.info("Testing basic RowID creation...")
            test_df = df.copy()
            test_df["RowID"] = np.arange(len(test_df))
            results["basic_creation"] = {"success": True, "length": len(test_df)}
            self.logger.info("✓ Basic RowID creation successful")

        except Exception as e:
            results["basic_creation"] = {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
            self.logger.error(f"✗ Basic RowID creation failed: {e}")

        try:
            # Test 2: Sorting before RowID creation
            self.logger.info("Testing sorting before RowID creation...")
            test_df = df.copy()

            # Check if sort columns exist
            sort_cols = ["DATEFILLED", "SOURCERECORDID"]
            available_sort_cols = [col for col in sort_cols if col in test_df.columns]

            if available_sort_cols:
                test_df = test_df.sort_values(by=available_sort_cols, ascending=True)
                test_df["Logic"] = ""
                test_df["RowID"] = np.arange(len(test_df))
                results["sort_and_create"] = {
                    "success": True,
                    "sorted_by": available_sort_cols,
                    "length": len(test_df),
                }
                self.logger.info(
                    f"✓ Sort and RowID creation successful (sorted by: {available_sort_cols})"
                )
            else:
                results["sort_and_create"] = {
                    "success": False,
                    "error": f"Required sort columns not found: {sort_cols}",
                    "available_columns": list(test_df.columns),
                }
                self.logger.error(f"✗ Sort columns not available: {sort_cols}")

        except Exception as e:
            results["sort_and_create"] = {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
            self.logger.error(f"✗ Sort and RowID creation failed: {e}")

        try:
            # Test 3: Multiprocessing compatibility
            self.logger.info("Testing multiprocessing compatibility...")

            # Split dataframe (simulating multiprocessing)
            num_splits = 4
            df_splits = np.array_split(df, num_splits)

            processed_splits = []
            for i, split_df in enumerate(df_splits):
                # Simulate the processing that would happen in multiprocessing
                split_copy = split_df.copy()
                split_copy["RowID"] = np.arange(len(split_copy))
                processed_splits.append(split_copy)

            # Recombine
            combined_df = pd.concat(processed_splits, ignore_index=True)

            results["multiprocessing_test"] = {
                "success": True,
                "splits_count": len(df_splits),
                "combined_length": len(combined_df),
                "original_length": len(df),
            }
            self.logger.info("✓ Multiprocessing compatibility test successful")

        except Exception as e:
            results["multiprocessing_test"] = {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
            self.logger.error(f"✗ Multiprocessing compatibility test failed: {e}")

        return results

    def generate_analysis_report(self, structure_analysis, rowid_tests, file_path):
        """Generate a comprehensive analysis report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "file_analyzed": file_path,
            "structure_analysis": structure_analysis,
            "rowid_tests": rowid_tests,
            "recommendations": self.generate_recommendations(
                structure_analysis, rowid_tests
            ),
            "fix_suggestions": self.generate_fix_suggestions(
                structure_analysis, rowid_tests
            ),
        }

        # Save detailed report
        self.save_report_to_file(report)

        # Print summary
        self.print_summary_report(report)

        return report

    def generate_recommendations(self, structure_analysis, rowid_tests):
        """Generate recommendations based on analysis."""
        recommendations = []

        # Check basic issues
        if not rowid_tests.get("basic_creation", {}).get("success", False):
            recommendations.append(
                {
                    "priority": "HIGH",
                    "issue": "Basic RowID creation fails",
                    "recommendation": "Check DataFrame integrity and numpy installation",
                }
            )

        if not structure_analysis.get("has_all_required", True):
            missing = structure_analysis.get("missing_required_columns", [])
            recommendations.append(
                {
                    "priority": "HIGH",
                    "issue": f"Missing required columns: {missing}",
                    "recommendation": "Ensure merged file contains all required columns",
                }
            )

        # Check sort column issues
        sort_issues = structure_analysis.get("sort_column_issues", {})
        for col, issue_info in sort_issues.items():
            if issue_info.get("missing"):
                recommendations.append(
                    {
                        "priority": "HIGH",
                        "issue": f"Missing sort column: {col}",
                        "recommendation": f"Add {col} column to the merged file",
                    }
                )
            elif issue_info.get("has_nulls"):
                recommendations.append(
                    {
                        "priority": "MEDIUM",
                        "issue": f"Null values in sort column: {col}",
                        "recommendation": f"Clean null values in {col} before processing",
                    }
                )

        # Memory usage check
        memory_mb = structure_analysis.get("memory_usage_mb", 0)
        if memory_mb > 500:  # More than 500MB
            recommendations.append(
                {
                    "priority": "MEDIUM",
                    "issue": f"Large memory usage: {memory_mb:.1f}MB",
                    "recommendation": "Consider processing in smaller chunks",
                }
            )

        # Data quality issues
        data_quality = structure_analysis.get("data_quality", {})
        if data_quality.get("duplicate_rows", 0) > 0:
            recommendations.append(
                {
                    "priority": "LOW",
                    "issue": f"Duplicate rows found: {data_quality['duplicate_rows']}",
                    "recommendation": "Consider removing duplicates before processing",
                }
            )

        return recommendations

    def generate_fix_suggestions(self, structure_analysis, rowid_tests):
        """Generate specific fix suggestions."""
        fixes = []

        # If basic RowID creation fails
        if not rowid_tests.get("basic_creation", {}).get("success", False):
            fixes.append(
                {
                    "fix_type": "CODE_FIX",
                    "description": "Add error handling for RowID creation",
                    "code_example": """
try:
    df["RowID"] = np.arange(len(df))
except Exception as e:
    logging.error(f"RowID creation failed: {e}")
    # Fallback: use index
    df["RowID"] = df.index
""",
                }
            )

        # If sorting fails
        if not rowid_tests.get("sort_and_create", {}).get("success", False):
            fixes.append(
                {
                    "fix_type": "DATA_VALIDATION",
                    "description": "Add validation for sort columns",
                    "code_example": """
# Validate sort columns before sorting
required_sort_cols = ["DATEFILLED", "SOURCERECORDID"]
available_cols = [col for col in required_sort_cols if col in df.columns]

if len(available_cols) < len(required_sort_cols):
    missing_cols = set(required_sort_cols) - set(available_cols)
    raise ValueError(f"Missing required columns for sorting: {missing_cols}")

# Safe sorting with error handling
try:
    df = df.sort_values(by=available_cols, ascending=True)
except Exception as e:
    logging.warning(f"Sorting failed: {e}. Using original order.")
""",
                }
            )

        # If multiprocessing has issues
        if not rowid_tests.get("multiprocessing_test", {}).get("success", False):
            fixes.append(
                {
                    "fix_type": "MULTIPROCESSING_FIX",
                    "description": "Fix multiprocessing data handling",
                    "code_example": """
# Ensure proper data copying for multiprocessing
def safe_multiprocessing_split(df, num_workers):
    try:
        # Create deep copies to avoid multiprocessing issues
        df_blocks = [block.copy() for block in np.array_split(df, num_workers)]
        return df_blocks
    except Exception as e:
        logging.error(f"Multiprocessing split failed: {e}")
        return [df]  # Fallback to single process
""",
                }
            )

        return fixes

    def save_report_to_file(self, report):
        """Save the detailed report to a file."""
        import json

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"rowid_error_analysis_{timestamp}.json"

        try:
            with open(filename, "w") as f:
                json.dump(report, f, indent=2, default=str)
            self.logger.info(f"Detailed report saved to: {filename}")
        except Exception as e:
            self.logger.error(f"Failed to save report: {e}")

    def print_summary_report(self, report):
        """Print a summary of the analysis."""
        print("\n" + "=" * 60)
        print("ROWID ERROR ANALYSIS SUMMARY")
        print("=" * 60)

        structure = report["structure_analysis"]
        tests = report["rowid_tests"]

        print(f"File: {report['file_analyzed']}")
        print(f"Shape: {structure['shape'][0]} rows, {structure['shape'][1]} columns")
        print(f"Memory Usage: {structure['memory_usage_mb']:.1f} MB")

        print("\nTest Results:")
        for test_name, test_result in tests.items():
            status = "✓ PASS" if test_result.get("success", False) else "✗ FAIL"
            print(f"  {test_name}: {status}")
            if not test_result.get("success", False) and "error" in test_result:
                print(f"    Error: {test_result['error']}")

        print(f"\nRecommendations: {len(report['recommendations'])}")
        for i, rec in enumerate(report["recommendations"][:3], 1):  # Show top 3
            print(f"  {i}. [{rec['priority']}] {rec['issue']}")
            print(f"     → {rec['recommendation']}")

        if len(report["recommendations"]) > 3:
            print(f"  ... and {len(report['recommendations']) - 3} more")

        print(f"\nFix Suggestions: {len(report['fix_suggestions'])}")
        for i, fix in enumerate(report["fix_suggestions"], 1):
            print(f"  {i}. {fix['description']}")

        print("\n" + "=" * 60)

    def create_error_report(self, error_type, error_details):
        """Create an error report when analysis fails."""
        return {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_details": error_details,
            "status": "ANALYSIS_FAILED",
        }

    def fix_common_rowid_issues(self, file_path="merged_file.xlsx"):
        """Attempt to fix common RowID issues in the file."""
        self.logger.info("=== Attempting to Fix RowID Issues ===")

        if not os.path.exists(file_path):
            self.logger.error(f"File not found: {file_path}")
            return False

        try:
            # Load and analyze
            df = pd.read_excel(file_path)
            self.logger.info(f"Loaded file with {len(df)} rows")

            # Create backup
            backup_path = file_path.replace(".xlsx", "_backup.xlsx")
            df.to_excel(backup_path, index=False)
            self.logger.info(f"Backup created: {backup_path}")

            # Apply fixes
            fixed_df = self.apply_rowid_fixes(df)

            # Save fixed file
            fixed_path = file_path.replace(".xlsx", "_fixed.xlsx")
            fixed_df.to_excel(fixed_path, index=False)
            self.logger.info(f"Fixed file saved: {fixed_path}")

            return True

        except Exception as e:
            self.logger.error(f"Fix attempt failed: {e}")
            return False

    def apply_rowid_fixes(self, df):
        """Apply common fixes to the DataFrame."""
        self.logger.info("Applying RowID fixes...")

        # Remove existing RowID if present
        if "RowID" in df.columns:
            df = df.drop(columns=["RowID"])
            self.logger.info("Removed existing RowID column")

        # Ensure required columns exist
        if "Logic" not in df.columns:
            df["Logic"] = ""
            self.logger.info("Added missing Logic column")

        # Safe sorting
        sort_columns = ["DATEFILLED", "SOURCERECORDID"]
        available_sort_cols = [col for col in sort_columns if col in df.columns]

        if available_sort_cols:
            try:
                df = df.sort_values(by=available_sort_cols, ascending=True)
                self.logger.info(f"Sorted by: {available_sort_cols}")
            except Exception as e:
                self.logger.warning(f"Sorting failed: {e}. Using original order.")

        # Safe RowID creation
        try:
            df["RowID"] = np.arange(len(df))
            self.logger.info("Successfully created RowID column")
        except Exception as e:
            self.logger.warning(f"Standard RowID creation failed: {e}. Using index.")
            df["RowID"] = df.index

        return df


def main():
    """Main function to run the RowID error analysis."""
    analyzer = RowIDErrorAnalyzer()

    # Check for command line arguments
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = "merged_file.xlsx"

    print(f"Analyzing RowID errors for: {file_path}")

    # Run analysis
    report = analyzer.analyze_merged_file_error(file_path)

    # Offer to fix issues if analysis succeeds
    if report.get("status") != "ANALYSIS_FAILED":
        response = input("\nWould you like to attempt automatic fixes? (y/n): ")
        if response.lower() == "y":
            success = analyzer.fix_common_rowid_issues(file_path)
            if success:
                print("✓ Fixes applied successfully")
            else:
                print("✗ Fix attempt failed")


if __name__ == "__main__":
    main()
