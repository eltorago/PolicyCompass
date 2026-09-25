"""PolicyCompass application settings."""
import os


def setting(name, default):
    """Read a namespaced setting or use the supplied default."""
    return os.environ.get("POLICYCOMPASS_" + name, default)
