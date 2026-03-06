"""Knowledge Tool package - Auto-setup paths for src modules."""

import sys
from pathlib import Path

# Auto-setup: Add src directory to path when package is imported
# This allows direct imports like "from models import Doc" to work from anywhere
_package_dir = Path(__file__).parent
_src_dir = _package_dir / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))
