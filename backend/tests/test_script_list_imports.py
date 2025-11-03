import sys
import importlib
import types
import pytest

# Modules to mock to avoid importing heavy native libraries during test-time.
HEAVY_MOCKS = [
    "cv2",
    "torch",
    "timm",
    "tensorflow",
    "torchvision",
    "faiss",
    "skimage",
]


MODULES_TO_TEST = [
    "backend.src.ingest",
    "backend.src.probe_media",
    "backend.src.validate_media",
    "backend.src.scene_detect",
    "backend.src.sample_frames",
    "backend.src.normalize_frames",
    "backend.src.build_manifest",
    "backend.src.analyze_metadata",
    "backend.src.models.ela_detector",
    "backend.src.models.noise_detector",
    "backend.src.models.df_detector",
]


@pytest.mark.parametrize("module_name", MODULES_TO_TEST)
def test_script_modules_importable(module_name):
    """Ensure script modules from script_list import without blowing up on missing native libs.

    This test does NOT execute heavy model code — it simply ensures the modules are importable
    in a CI environment by inserting light-weight mock modules for common heavy dependencies
    (OpenCV, torch, etc.). This gives early feedback if simple syntax/runtime errors exist in
    the script entrypoints.
    """
    # Inject lightweight module objects for heavy native dependencies that may not be
    # available in the minimal CI environment.
    for name in HEAVY_MOCKS:
        if name not in sys.modules:
            sys.modules[name] = types.ModuleType(name)

    # Some modules import subpackages (e.g. timm.optim) — ensure a simple package mapping
    # so imports like `from timm.something import x` don't fail on attribute error.
    for name in list(sys.modules.keys()):
        if name in HEAVY_MOCKS:
            # ensure the module has a .__path__ so it behaves like a package when needed
            setattr(sys.modules[name], "__path__", [])

    # Now attempt the import; the test passes if import completes without raising.
    try:
        mod = importlib.import_module(module_name)
    except Exception as exc:
        pytest.fail(f"Importing {module_name} failed: {exc}")

    # Basic sanity: module object was retrieved and has at least one attribute.
    assert mod is not None
    assert len(dir(mod)) > 0
