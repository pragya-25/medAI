"""Test setup: point the app at a throwaway database BEFORE the app modules are imported."""
import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["MEDAI_DB"] = os.path.join(_tmp, "test.db")
os.environ["MEDAI_OUT"] = os.path.join(_tmp, "heatmaps")
