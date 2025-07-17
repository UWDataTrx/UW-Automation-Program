#!/usr/bin/env python3
"""
Test script to verify all imports are working correctly across the project.
This script should be run from the project root directory.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def test_imports():
    """Test all module imports to ensure they work correctly."""

    print("Testing imports...")

    modules_to_test = [
        # Core modules
        ("app", "Main application"),
        ("modules.merge", "Merge functionality"),
        ("modules.bg_disruption", "Background disruption processing"),
        ("modules.tier_disruption", "Tier disruption processing"),
        ("modules.audit_helper", "Audit helper functions"),
        ("modules.template_processor", "Template processing"),
        ("modules.data_processor", "Data processing"),
        ("modules.file_processor", "File processing"),
        ("modules.process_manager", "Process management"),
        ("modules.log_manager", "Log management"),
        ("modules.sharx_lbl", "SHARx line by line processing"),
        ("modules.epls_lbl", "EPLS line by line processing"),
        ("modules.openmdf_bg", "OpenMDF background processing"),
        ("modules.openmdf_tier", "OpenMDF tier processing"),
        # Utility modules
        ("utils.utils", "Core utilities"),
        ("utils.excel_utils", "Excel utilities"),
        ("utils.logic_processor", "Logic processor"),
        ("utils.utils_functions", "Utility functions"),
        # Config modules
        ("config.app_config", "Application configuration"),
        ("config.config_loader", "Configuration loader"),
        ("config.improved_config_manager", "Improved config manager"),
    ]

    results = []

    for module_name, description in modules_to_test:
        try:
            __import__(module_name)
            results.append((module_name, description, "✓ PASS"))
            print(f"✓ {module_name}: {description}")
        except ImportError as e:
            results.append((module_name, description, f"✗ FAIL: {e}"))
            print(f"✗ {module_name}: {description} - FAILED: {e}")
        except Exception as e:
            results.append((module_name, description, f"✗ ERROR: {e}"))
            print(f"✗ {module_name}: {description} - ERROR: {e}")

    print("\n" + "=" * 80)
    print("IMPORT TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, _, result in results if result.startswith("✓"))
    failed = len(results) - passed

    print(f"Total modules tested: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed == 0:
        print("\n🎉 All imports are working correctly!")
    else:
        print(f"\n⚠️  {failed} modules have import issues.")
        print("\nFailed modules:")
        for module_name, description, result in results:
            if not result.startswith("✓"):
                print(f"  - {module_name}: {result}")

    return failed == 0


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
