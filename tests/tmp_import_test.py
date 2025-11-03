import pathlib
print('cwd:', pathlib.Path('.').resolve())
try:
    from modules.merge import merge_files
    print('Imported merge_files:', merge_files)
except Exception as e:
    print('IMPORT ERROR:', type(e).__name__, e)
