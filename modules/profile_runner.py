import modules.error_reporter
import cProfile
import pstats
import sys

# Ensure error logging is initialized (makes import 'used')
modules.error_reporter.setup_error_logging()

if __name__ == "__main__":
    script_path = (
        sys.argv[1] if len(sys.argv) > 1 else "app.py"
    )  # Allow dynamic script path input
    profile_output = "profile_stats.prof"

    print(f"Profiling {script_path}...\n")
    cProfile.runctx(
        "exec(compile(open(script_path).read(), script_path, 'exec'))",
        globals(),
        locals(),
        profile_output,
    )

    # Optional: print top 20 cumulative time functions
    stats = pstats.Stats(profile_output)
    stats.sort_stats(pstats.SortKey.CUMULATIVE).print_stats(20)
