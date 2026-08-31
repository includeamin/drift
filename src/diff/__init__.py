from diff.delta import Delta
from diff.diff import diff
from diff.patch import patch

# Kept in sync with pyproject.toml by .github/workflows/release.yml.
__version__ = "0.13.0"

__all__ = ["Delta", "__version__", "diff", "patch"]
