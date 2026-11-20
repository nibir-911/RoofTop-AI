from app.main import app
print("FastAPI app imports OK")
# Collect all route paths
all_paths = []
for r in app.routes:
    if hasattr(r, 'path'):
        all_paths.append(r.path)
    elif hasattr(r, 'routes'):
        for sr in r.routes:
            if hasattr(sr, 'path'):
                all_paths.append(sr.path)

print("Registered routes:")
for p in sorted(all_paths):
    print(f"  {p}")

expected = [
    '/api/preferences',
    '/api/roof/grid',
    '/api/roof/visualize',
    '/api/garden/layout',
    '/api/plants',
    '/api/suppliers',
    '/api/plant-doctor/analyze',
    '/api/health',
]
print("\nExpected route checks:")
for r in expected:
    matched = any(r in p for p in all_paths)
    status = "PASS" if matched else "MISSING"
    print(f"  [{status}] {r}")
print("Done.")
