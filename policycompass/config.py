"""Application settings, with explicit compatibility for WACC library locations."""
import os


def setting(name, default):
    """Prefer PolicyCompass settings; accept the corresponding legacy WACC name."""
    return os.environ.get("POLICYCOMPASS_" + name, os.environ.get("WACC_" + name, default))
