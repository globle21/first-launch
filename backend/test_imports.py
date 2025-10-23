"""Test imports to identify the issue"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("Testing imports...")

try:
    print("1. Importing session_manager...")
    from session_manager import session_manager
    print("   ✅ session_manager imported successfully")
except Exception as e:
    print(f"   ❌ Failed: {e}")

try:
    print("\n2. Importing workflow_async...")
    from workflow_async import run_workflow_async
    print("   ✅ workflow_async imported successfully")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    import traceback
    traceback.print_exc()

print("\n3. Checking src directory...")
src_path = Path(__file__).parent.parent / "src"
print(f"   Src path: {src_path}")
print(f"   Exists: {src_path.exists()}")

if src_path.exists():
    print(f"   Contents: {list(src_path.iterdir())[:5]}")
