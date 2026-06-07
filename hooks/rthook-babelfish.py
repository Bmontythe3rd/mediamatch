# Runtime hook: runs before any imports in the frozen bundle.
# Patches pkg_resources.resource_stream to fall back to direct _MEIPASS
# path resolution if the normal lookup fails — covers edge cases where
# pkg_resources can't find the distribution metadata in a frozen env.
import os
import sys

if not hasattr(sys, '_MEIPASS'):
    # Not frozen; nothing to patch.
    pass
else:
    try:
        import pkg_resources as _pkg

        _orig_resource_stream = _pkg.resource_stream

        def _patched_resource_stream(package_or_requirement, resource_name):
            try:
                return _orig_resource_stream(package_or_requirement, resource_name)
            except Exception:
                # Direct fallback: walk from _MEIPASS using the package path
                if isinstance(package_or_requirement, str):
                    pkg_parts = package_or_requirement.replace('.', os.sep)
                    candidate = os.path.join(sys._MEIPASS, pkg_parts, resource_name)
                    if os.path.exists(candidate):
                        return open(candidate, 'rb')
                    # Also try the top-level package directory
                    top = package_or_requirement.split('.')[0]
                    candidate = os.path.join(sys._MEIPASS, top, resource_name)
                    if os.path.exists(candidate):
                        return open(candidate, 'rb')
                raise

        _pkg.resource_stream = _patched_resource_stream
    except ImportError:
        pass
