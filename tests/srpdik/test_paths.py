"""Tests for srpdik.paths: CWD-independent, repo-relative path resolution, no hardcoded paths."""

import ast
import inspect

from srpdik import paths


def _code_only_source(module) -> str:
    """Module source with its top-level docstring stripped (docstrings may legitimately mention
    example paths/split names; only the executable code must avoid them)."""
    source = inspect.getsource(module)
    tree = ast.parse(source)
    code_only_lines = set(range(1, len(source.splitlines()) + 1))
    docstring_node = tree.body[0] if tree.body else None
    if isinstance(docstring_node, ast.Expr) and isinstance(docstring_node.value, ast.Constant):
        code_only_lines -= set(range(docstring_node.lineno, docstring_node.end_lineno + 1))
    lines = [line for i, line in enumerate(source.splitlines(), start=1) if i in code_only_lines]
    return "\n".join(lines)


def test_all_srpdik_submodules_import_cleanly():
    import srpdik  # noqa: F401
    import srpdik.config  # noqa: F401
    import srpdik.constants  # noqa: F401
    import srpdik.data  # noqa: F401
    import srpdik.data.split_guard  # noqa: F401
    import srpdik.dls_lock  # noqa: F401
    import srpdik.envs  # noqa: F401
    import srpdik.evaluation  # noqa: F401
    import srpdik.exceptions  # noqa: F401
    import srpdik.features  # noqa: F401
    import srpdik.kaggle  # noqa: F401
    import srpdik.manifests  # noqa: F401
    import srpdik.paths  # noqa: F401
    import srpdik.policy  # noqa: F401
    import srpdik.training  # noqa: F401


def test_repo_root_is_the_real_repo_root():
    root = paths.repo_root()
    assert (root / "CLAUDE.md").is_file()
    assert (root / "srpdik").is_dir()


def test_repo_root_independent_of_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert paths.repo_root() == paths.REPO_ROOT
    assert paths.srpdik_config_dir() == paths.REPO_ROOT / "configs" / "srpdik"


def test_srpdik_config_dir_and_path():
    assert paths.srpdik_config_dir() == paths.repo_root() / "configs" / "srpdik"
    assert (
        paths.srpdik_config_path("dls_locked.json")
        == paths.srpdik_config_dir() / "dls_locked.json"
    )


def test_srpdik_auxiliary_dirs_repo_relative():
    root = paths.repo_root()
    assert paths.srpdik_tests_dir() == root / "tests" / "srpdik"
    assert paths.srpdik_notebooks_dir() == root / "notebooks" / "srpdik"
    assert paths.srpdik_results_dir() == root / "results" / "srpdik"
    assert paths.srpdik_docs_dir() == root / "docs" / "srpdik"


def test_no_absolute_path_literals_in_module_code():
    code = _code_only_source(paths)
    assert "D:\\\\" not in code
    assert "C:\\\\" not in code
    assert "/home/" not in code


def test_no_default_frozen_test_path_in_module_code():
    # The module docstring may explain the frozen-test policy in prose; the executable code must
    # never reference it as a default path.
    code = _code_only_source(paths)
    assert "frozen_test" not in code
    assert "validation" not in code
    assert "development" not in code
