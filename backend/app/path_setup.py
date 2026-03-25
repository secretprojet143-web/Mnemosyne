import sys
import os

# Add project root FIRST so app/ resolves to the real app/
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Clear any cached 'app' modules so they re-resolve to project root
_to_remove = [k for k in sys.modules if k == 'app' or k.startswith('app.')]
for k in _to_remove:
    del sys.modules[k]
