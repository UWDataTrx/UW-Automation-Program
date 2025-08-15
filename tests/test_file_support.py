#!/usr/bin/env python3
"""
Test script to verify CSV and Excel file support for template validation.
"""

import os
import tempfile

import pandas as pd

from modules.data_processor import DataProcessor


class MockApp:
    """Mock app instance for testing."""

    pass


def test_csv_support():
    """Test CSV file template validation."""
    # Create test CSV data
    test_data = {
        "SOURCERECORDID": [1, 2, 3, 4, 5],
        "GrossCost": [0, 0, 10.50, 25.00, 0],
        "MemberID": ["M001", "M002", "M003", "M004", "M005"],
    }
    df = pd.DataFrame(test_data)

    # Create temporary CSV file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        csv_path = f.name
        df.to_csv(csv_path, index=False)

    try:
        # Test the data processor
        mock_app = MockApp()
        processor = DataProcessor(mock_app)

        result = processor.validate_gross_cost_template(csv_path)
        print("CSV Test Result:")
        print(result)
        print("-" * 50)

        return "CSV" in result and "TEMPLATE RECOMMENDATION" in result

    finally:
        # Clean up
        os.unlink(csv_path)


def test_excel_support():
    """Test Excel file template validation."""
    # Create test Excel data
    test_data = {
        "SOURCERECORDID": [1, 2, 3, 4, 5],
        "GrossCost": [15.50, 22.00, 8.75, 45.00, 12.25],
        "MemberID": ["M001", "M002", "M003", "M004", "M005"],
    }
    df = pd.DataFrame(test_data)

    # Create temporary Excel file
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        excel_path = f.name
        df.to_excel(excel_path, index=False)

    try:
        # Test the data processor
        mock_app = MockApp()
        processor = DataProcessor(mock_app)

        result = processor.validate_gross_cost_template(excel_path)
        print("Excel Test Result:")
        print(result)
        print("-" * 50)

        return "Excel" in result and "TEMPLATE RECOMMENDATION" in result

    finally:
        # Clean up
        os.unlink(excel_path)


def test_no_grosscost_column():
    """Test file without GrossCost column."""
    # Create test data without GrossCost
    test_data = {
        "SOURCERECORDID": [1, 2, 3, 4, 5],
        "Amount": [15.50, 22.00, 8.75, 45.00, 12.25],
        "MemberID": ["M001", "M002", "M003", "M004", "M005"],
    }
    df = pd.DataFrame(test_data)

    # Create temporary CSV file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        csv_path = f.name
        df.to_csv(csv_path, index=False)

    try:
        # Test the data processor
        mock_app = MockApp()
        processor = DataProcessor(mock_app)

        result = processor.validate_gross_cost_template(csv_path)
        print("No GrossCost Column Test Result:")
        print(result)
        print("-" * 50)

        return "No 'GrossCost' column found" in result and "BLANK template" in result

    finally:
        # Clean up
        os.unlink(csv_path)


if __name__ == "__main__":
    print("Testing CSV and Excel file support for template validation...")
    print("=" * 60)

    try:
        csv_success = test_csv_support()
        excel_success = test_excel_support()
        no_grosscost_success = test_no_grosscost_column()

        print("Test Results:")
        print(f"CSV Support: {'✅ PASS' if csv_success else '❌ FAIL'}")
        print(f"Excel Support: {'✅ PASS' if excel_success else '❌ FAIL'}")
        print(
            f"No GrossCost Column: {'✅ PASS' if no_grosscost_success else '❌ FAIL'}"
        )

        if all([csv_success, excel_success, no_grosscost_success]):
            print(
                "\n🎉 All tests passed! The application now supports both CSV and Excel files."
            )
        else:
            print("\n⚠️ Some tests failed. Please check the implementation.")

    except Exception as e:
        print(f"Test error: {e}")
        import traceback

        traceback.print_exc()
