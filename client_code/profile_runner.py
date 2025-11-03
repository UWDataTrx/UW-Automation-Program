import cProfile
import pstats
import sys
from pathlib import Path

# Ensure project root is in sys.path before importing project_settings
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    from project_settings import PROJECT_ROOT

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.append(str(PROJECT_ROOT))

if __name__ == "__main__":
    script_path = (
        sys.argv[1] if len(sys.argv) > 1 else "app.py"
    )  # Allow dynamic script path input
    profile_output = "profile_stats.prof"

    print(f"Profiling {script_path}...\n")
    script_path_obj = Path(script_path)
    cProfile.runctx(
        "exec(compile(script_path_obj.read_text(), str(script_path_obj), 'exec'))",
        {**globals(), "script_path_obj": script_path_obj},
        locals(),
        profile_output,
    )

    # Optional: print top 20 cumulative time functions
    stats = pstats.Stats(profile_output)
    stats.sort_stats(pstats.SortKey.CUMULATIVE).print_stats(20)
