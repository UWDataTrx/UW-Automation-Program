import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
import importlib.util  # noqa: E402
import json  # noqa: E402
import platform  # noqa: E402
import traceback  # noqa: E402
from datetime import datetime  # noqa: E402


class DiagnosticTool:
    def __init__(self):
        self.report_lines = []
        self.issues_found = []
        self.recommendations = []

    def add_section(self, title):
        """Add a section header to the report."""
        self.report_lines.append(f"\n{'=' * 60}")
        self.report_lines.append(f"{title}")
        self.report_lines.append(f"{'=' * 60}")

    def add_line(self, line):
        """Add a line to the report."""
        self.report_lines.append(line)

    def add_issue(self, issue, recommendation=None):
        """Add an issue and optional recommendation."""
        self.issues_found.append(issue)
        if recommendation:
            self.recommendations.append(recommendation)

    def check_python_environment(self):
        """Check Python installation and environment."""
        self.add_section("PYTHON ENVIRONMENT")

        # Python version
        python_version = sys.version
        self.add_line(f"Python Version: {python_version}")

        # Python executable path
        python_exe = sys.executable
        self.add_line(f"Python Executable: {python_exe}")

        # Check if running in virtual environment
        in_venv = hasattr(sys, "real_prefix") or (
            hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
        )
        self.add_line(f"Virtual Environment: {'Yes' if in_venv else 'No'}")

        if in_venv:
            self.add_line(f"Virtual Env Path: {sys.prefix}")

        # Check Python version compatibility
        version_info = sys.version_info
        if version_info.major < 3 or (
            version_info.major == 3 and version_info.minor < 8
        ):
            self.add_issue(
                f"Python version {version_info.major}.{version_info.minor} may be too old",
                "Consider upgrading to Python 3.8 or newer",
            )

    def check_required_packages(self):
        """Check if required packages are installed."""
        self.add_section("REQUIRED PACKAGES")

        required_packages = [
            "pandas",
            "numpy",
            "openpyxl",
            "xlwings",
            "customtkinter",
            "tkinter",
            "pathlib",
            "multiprocessing",
            "threading",
        ]

        missing_packages = []

        for package in required_packages:
            try:
                if package == "tkinter":
                    import tkinter

                    version = tkinter.TkVersion
                elif package == "pathlib":
                    # pathlib is built-in, just check if importable
                    importlib.util.find_spec("pathlib")
                    version = "Built-in"
                elif package == "multiprocessing":
                    # multiprocessing is built-in, just check if importable
                    importlib.util.find_spec("multiprocessing")
                    version = "Built-in"
                elif package == "threading":
                    # threading is built-in, just check if importable
                    importlib.util.find_spec("threading")
                    version = "Built-in"
                else:
                    module = importlib.import_module(package)
                    version = getattr(module, "__version__", "Unknown")

                self.add_line(f"✓ {package}: {version}")

            except ImportError:
                self.add_line(f"✗ {package}: NOT INSTALLED")
                missing_packages.append(package)

        if missing_packages:
            self.add_issue(
                f"Missing packages: {', '.join(missing_packages)}",
                f"Install missing packages: pip install {' '.join(missing_packages)}",
            )

    def check_excel_availability(self):
        """Check Excel COM interface availability."""
        self.add_section("EXCEL COM INTERFACE")

        try:
            import xlwings as xw

            # Try to create a temporary Excel application
            app = xw.App(visible=False, add_book=False)
            app.quit()
            self.add_line("✓ Excel COM interface is available")
            self.add_line("✓ xlwings can communicate with Excel")
        except ImportError:
            self.add_line("✗ xlwings not installed")
            self.add_issue(
                "xlwings package not found", "Install xlwings: pip install xlwings"
            )
        except Exception as e:
            self.add_line(f"✗ Excel COM interface error: {e}")
            self.add_issue(
                "Excel COM interface not working",
                "Ensure Microsoft Excel is installed and try: xlwings addin install",
            )

    def check_system_resources(self):
        """Check system resources."""
        self.add_section("SYSTEM RESOURCES")

        # Disk space
        try:
            import shutil

            total, used, free = shutil.disk_usage(".")
            free_gb = free / (1024**3)
            total_gb = total / (1024**3)
            used_percent = (used / total) * 100

            self.add_line(f"Disk Space - Total: {total_gb:.1f}GB")
            self.add_line(f"Disk Space - Free: {free_gb:.1f}GB")
            self.add_line(f"Disk Space - Used: {used_percent:.1f}%")

            if free_gb < 1.0:
                self.add_issue(
                    f"Low disk space: {free_gb:.1f}GB available",
                    "Free up disk space (minimum 1GB recommended)",
                )

        except Exception as e:
            self.add_line(f"Could not check disk space: {e}")

        # Memory
        try:
            import psutil

            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            total_gb = memory.total / (1024**3)
            used_percent = memory.percent

            self.add_line(f"Memory - Total: {total_gb:.1f}GB")
            self.add_line(f"Memory - Available: {available_gb:.1f}GB")
            self.add_line(f"Memory - Used: {used_percent:.1f}%")

            if available_gb < 2.0:
                self.add_issue(
                    f"Low available memory: {available_gb:.1f}GB",
                    "Close other applications to free memory (2GB+ recommended)",
                )

        except ImportError:
            self.add_line("psutil not available - cannot check memory")
        except Exception as e:
            self.add_line(f"Could not check memory: {e}")

    def check_file_permissions(self):
        """Check file permissions in current directory using pathlib."""
        self.add_section("FILE PERMISSIONS")

        current_dir = Path.cwd()
        self.add_line(f"Current Directory: {current_dir}")

        # Test write permissions
        test_file = current_dir / "permission_test.tmp"
        try:
            test_file.write_text("test", encoding="utf-8")
            test_file.unlink()
            self.add_line("✓ Write permissions: OK")
        except Exception as e:
            self.add_line(f"✗ Write permissions: FAILED - {e}")
            self.add_issue(
                "Cannot write files in current directory",
                "Run as administrator or change to a writable directory",
            )

        # Check for locked Excel files
        excel_patterns = ["*_Rx Repricing_wf.xlsx", "*.xlsx", "*.xls"]
        locked_files = []

        for pattern in excel_patterns:
            for file_path in current_dir.glob(pattern):
                try:
                    with file_path.open("r+b"):
                        pass
                except (PermissionError, IOError):
                    locked_files.append(str(file_path.name))

        if locked_files:
            self.add_line(f"✗ Locked Excel files found: {', '.join(locked_files)}")
            self.add_issue(
                f"Excel files are locked: {', '.join(locked_files)}",
                "Close Excel and any other programs using these files",
            )
        else:
            self.add_line("✓ No locked Excel files detected")

    def check_running_processes(self):
        """Check for conflicting running processes."""
        self.add_section("RUNNING PROCESSES")

        try:
            import psutil

            # Check for Excel processes
            excel_processes = []
            python_processes = []

            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    name = proc.info["name"].lower()
                    if "excel" in name:
                        excel_processes.append(
                            f"{proc.info['name']} (PID: {proc.info['pid']})"
                        )
                    elif "python" in name:
                        cmdline = proc.info.get("cmdline", [])
                        if cmdline and any(
                            "app.py" in arg or "merge.py" in arg for arg in cmdline
                        ):
                            python_processes.append(
                                f"Python script (PID: {proc.info['pid']})"
                            )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if excel_processes:
                self.add_line(f"Excel processes running: {len(excel_processes)}")
                for proc in excel_processes:
                    self.add_line(f"  - {proc}")
                if len(excel_processes) > 1:
                    self.add_issue(
                        f"Multiple Excel processes detected ({len(excel_processes)})",
                        "Close Excel completely before running the automation",
                    )
            else:
                self.add_line("✓ No Excel processes detected")

            if python_processes:
                self.add_line(f"Python automation processes: {len(python_processes)}")
                for proc in python_processes:
                    self.add_line(f"  - {proc}")
                if len(python_processes) > 1:
                    self.add_issue(
                        "Multiple automation processes detected",
                        "Only run one instance of the automation at a time",
                    )

        except ImportError:
            self.add_line("psutil not available - cannot check processes")
        except Exception as e:
            self.add_line(f"Error checking processes: {e}")

    def check_config_files(self):
        """Check configuration files using pathlib."""
        self.add_section("CONFIGURATION FILES")

        config_files = [
            "config.json",
            "config/config.json",
            "config/file_paths.json",
            "_Rx Repricing_wf.xlsx",
        ]

        for config_file in config_files:
            file_path = Path(config_file)
            if file_path.exists():
                try:
                    if file_path.suffix == ".json":
                        json.loads(
                            file_path.read_text(encoding="utf-8")
                        )  # Validate JSON
                        self.add_line(f"✓ {config_file}: Valid")
                    else:
                        self.add_line(f"✓ {config_file}: Found")
                except json.JSONDecodeError as e:
                    self.add_line(f"✗ {config_file}: Invalid JSON - {e}")
                    self.add_issue(
                        f"Invalid JSON in {config_file}",
                        f"Check and fix JSON syntax in {config_file}",
                    )
                except Exception as e:
                    self.add_line(f"? {config_file}: Error reading - {e}")
            else:
                self.add_line(f"✗ {config_file}: Not found")
                if config_file == "_Rx Repricing_wf.xlsx":
                    self.add_issue(
                        "Template file not found",
                        "Ensure _Rx Repricing_wf.xlsx is in the current directory",
                    )

    def check_recent_logs(self):
        """Check recent log files for errors using pathlib."""
        self.add_section("RECENT LOGS")

        log_files = ["repricing_log.log", "audit_log.csv"]

        for log_file in log_files:
            log_path = Path(log_file)
            if log_path.exists():
                try:
                    # Get file modification time
                    mod_time = datetime.fromtimestamp(log_path.stat().st_mtime)
                    self.add_line(f"✓ {log_file}: Last modified {mod_time}")

                    # Check for recent errors
                    lines = log_path.read_text(
                        encoding="utf-8", errors="ignore"
                    ).splitlines()

                    # Look for errors in last 50 lines
                    recent_lines = lines[-50:] if len(lines) > 50 else lines
                    error_count = sum(
                        1 for line in recent_lines if "ERROR" in line.upper()
                    )

                    if error_count > 0:
                        self.add_line(f"  ⚠ Found {error_count} recent errors")
                        # Show last few errors
                        errors = [
                            line.strip()
                            for line in recent_lines
                            if "ERROR" in line.upper()
                        ]
                        for error in errors[-3:]:  # Show last 3 errors
                            self.add_line(f"    {error}")

                except Exception as e:
                    self.add_line(f"? {log_file}: Error reading - {e}")
            else:
                self.add_line(f"- {log_file}: Not found (normal if no recent runs)")

    def run_diagnosis(self):
        """Run all diagnostic checks."""
        print("UW Automation Program - Diagnostic Tool")
        print("=" * 50)
        print("Collecting system information...")

        # Add timestamp
        self.add_section("DIAGNOSTIC REPORT")
        self.add_line(f"Generated: {datetime.now()}")
        self.add_line(f"Platform: {platform.platform()}")
        self.add_line(f"Machine: {platform.machine()}")
        self.add_line(f"Processor: {platform.processor()}")

        # Run all checks
        print("Checking Python environment...")
        self.check_python_environment()

        print("Checking required packages...")
        self.check_required_packages()

        print("Checking Excel COM interface...")
        self.check_excel_availability()

        print("Checking system resources...")
        self.check_system_resources()

        print("Checking file permissions...")
        self.check_file_permissions()

        print("Checking running processes...")
        self.check_running_processes()

        print("Checking configuration files...")
        self.check_config_files()

        print("Checking recent logs...")
        self.check_recent_logs()

        # Summary
        self.add_section("SUMMARY")

        if self.issues_found:
            self.add_line(f"Issues Found: {len(self.issues_found)}")
            self.add_line("")
            for i, issue in enumerate(self.issues_found, 1):
                self.add_line(f"{i}. {issue}")

            self.add_line("")
            self.add_line("RECOMMENDATIONS:")
            for i, rec in enumerate(self.recommendations, 1):
                self.add_line(f"{i}. {rec}")
        else:
            self.add_line("✓ No major issues detected!")

        # Save report locally using pathlib
        report_file = Path("diagnostic_report.txt")
        report_file.write_text("\n".join(self.report_lines), encoding="utf-8")

        print("\nDiagnostic complete!")
        print(f"Report saved to: {report_file.absolute()}")

        # Try to automatically upload report to support directory
        self._upload_report_to_support(report_file)

        # Print summary to console
        print("\n" + "=" * 50)
        print("SUMMARY")
        print("=" * 50)

        if self.issues_found:
            print(f"⚠ {len(self.issues_found)} issues found:")
            for issue in self.issues_found:
                print(f"  • {issue}")

            print("\nRecommendations:")
            for rec in self.recommendations:
                print(f"  • {rec}")
        else:
            print("✓ No major issues detected!")

        print(f"\nFull report available in: {report_file.absolute()}")

        return len(self.issues_found) == 0

    def _upload_report_to_support(self, report_file):
        """Automatically upload diagnostic report to support directory using pathlib."""
        try:
            # Get support directory path from configuration
            try:
                from config.app_config import ProcessingConfig

                support_dir = ProcessingConfig.get_diagnostic_reports_path()
            except ImportError:
                # Fallback to hardcoded path if config module is not available
                support_dir = Path(
                    r"C:\Users\DamionMorrison\OneDrive - True Rx Health Strategists\True Community - Data Analyst\UW Python Program\Diagnostic Reports"
                )

            # Create support directory if it doesn't exist
            support_dir = Path(support_dir)
            support_dir.mkdir(parents=True, exist_ok=True)

            # Get user information for unique filename
            import getpass
            import socket

            username = getpass.getuser()
            hostname = socket.gethostname()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Map usernames to folder names (handle common variations)
            user_folder_mapping = {
                "DamionMorrison": "Damion Morrison",
                "Damion Morrison": "Damion Morrison",
                "DannyBushnell": "Danny Bushnell",
                "Danny Bushnell": "Danny Bushnell",
                "BrettBauer": "Brett Bauer",
                "Brett Bauer": "Brett Bauer",
                "BrendanReamer": "Brendan Reamer",
                "Brendan Reamer": "Brendan Reamer",
                "MitchellFrederick": "Mitchell Frederick",
                "Mitchell Frederick": "Mitchell Frederick",
                # Add variations for different username formats
                "damion.morrison": "Damion Morrison",
                "danny.bushnell": "Danny Bushnell",
                "brett.bauer": "Brett Bauer",
                "brendan.reamer": "Brendan Reamer",
                "mitchell.frederick": "Mitchell Frederick",
            }

            # Get the correct folder name for this user
            user_folder = user_folder_mapping.get(username, "Other Users")
            user_specific_dir = support_dir / user_folder

            # Create user-specific directory if it doesn't exist
            user_specific_dir.mkdir(parents=True, exist_ok=True)

            # Create unique filename
            unique_filename = f"diagnostic_report_{username}_{hostname}_{timestamp}.txt"
            support_file_path = user_specific_dir / unique_filename

            # Copy report to support directory using pathlib
            report_file = Path(report_file)
            support_file_path.write_bytes(report_file.read_bytes())

            print("✓ Report automatically uploaded to support directory:")
            print(f"  Location: {support_file_path}")
            print(f"  Filename: {unique_filename}")

            # Also create a summary file for quick overview using pathlib
            summary_file = (
                user_specific_dir / f"summary_{username}_{hostname}_{timestamp}.txt"
            )
            summary_content = [
                "Diagnostic Report Summary",
                "========================",
                f"User: {username}",
                f"Computer: {hostname}",
                f"Generated: {datetime.now()}",
                f"Platform: {platform.platform()}",
                f"Python Version: {sys.version.split()[0]}",
                f"Issues Found: {len(self.issues_found)}",
                "",
                "Issues:",
            ]
            for i, issue in enumerate(self.issues_found, 1):
                summary_content.append(f"{i}. {issue}")
            summary_content.append(f"\nFull Report: {unique_filename}")
            summary_file.write_text("\n".join(summary_content), encoding="utf-8")

            print(
                f"✓ Summary also created in {user_folder}: summary_{username}_{hostname}_{timestamp}.txt"
            )

            return True

        except PermissionError:
            print("⚠ Could not upload report - permission denied to support directory")
            print("  Please manually send the diagnostic_report.txt file")
            return False
        except Exception as e:
            print(f"⚠ Could not upload report automatically: {e}")
            print("  Please manually send the diagnostic_report.txt file")
            return False


def main():
    """Main function to run diagnostics."""
    try:
        tool = DiagnosticTool()
        success = tool.run_diagnosis()

        print("\n" + "=" * 50)
        if success:
            print("System appears healthy for running the UW Automation Program!")
        else:
            print("Issues detected - please review recommendations above.")

        print("\nSupport Information:")
        # Note: The upload status is already printed by _upload_report_to_support method
        print("• If you need immediate assistance, describe:")
        print("  - What you were trying to do when the problem occurred")
        print("  - Any specific error messages you saw")
        print("  - When the problem started")

        return 0 if success else 1

    except Exception as e:
        print(f"Error running diagnostics: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()

    # Keep window open on Windows
    if platform.system() == "Windows":
        input("\nPress Enter to continue...")

    sys.exit(exit_code)
