#!/usr/bin/env python3
"""Compatibility shim: run Context Shrink from a repository checkout.

The implementation lives in ``context_shrink.py`` — an importable module, so it
can be packaged and published. This hyphenated file stays runnable for existing
configs and docs that point at ``context-shrink.py``:

    python context-shrink.py

For an installed, no-checkout setup use the packaged command instead — see the
README "Install (one line)" section::

    uvx --from context-shrink-mcp context-shrink
"""

from context_shrink import main

if __name__ == "__main__":
    main()
