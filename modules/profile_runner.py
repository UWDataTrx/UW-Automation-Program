import cProfile
import pstats
import sys

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
