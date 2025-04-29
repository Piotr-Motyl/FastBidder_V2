try:
    import magic

    print("Import successful")
    print(
        f"Magic version: {magic.__version__ if hasattr(magic, '__version__') else 'unknown'}"
    )
except Exception as e:
    print(f"Import failed: {e}")
