from app.collectors.runner import run_sync

if __name__ == "__main__":
    result = run_sync()
    print("Intelligence enrichment complete.")
    print(f"Observed candidates: {result.get('observed', 0)}")
    for name, count in sorted(result.get("collectors", {}).items()):
        print(f"{name}: {count}")
