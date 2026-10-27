"""Root-discovery hardening tests (audit t_9d200636, Class C).

``server.is_hermes_root`` accepted any directory containing a ``tools/``
subdirectory. A stray ``tools/`` dir at the Hermes DATA root (e.g. an old
nexus tool install) made the data root masquerade as an agent SOURCE root:
with ``HERMES_HOME=<data root>`` exported, ``candidate_roots()`` picked the
data root, ``sys.path`` gained it, and ``import tools`` resolved to a
namespace package that lacks ``file_tools`` — silently degrading the tool
surface to read-only fallbacks.

A real Hermes agent source root has a regular ``tools`` package
(``tools/__init__.py``) or ``hermes_state.py`` at its top level. Namespace
``tools/`` directories must NOT qualify.
"""

from __future__ import annotations

from pathlib import Path
import os
import json
import subprocess
import sys
import pytest

import server


def _make_fake_root(tmp_path: Path) -> Path:
    fake = tmp_path / "data-root"
    (fake / "tools").mkdir(parents=True)
    (fake / "tools" / "unrelated-script.py").write_text("# stray tool, not a Hermes install\n", encoding="utf-8")
    return fake


def test_is_hermes_root_rejects_namespace_tools_dir(tmp_path):
    """A bare tools/ dir (no __init__.py, no hermes_state.py) is not a root."""
    fake = _make_fake_root(tmp_path)
    assert not server.is_hermes_root(fake)


def test_is_hermes_root_accepts_regular_tools_package(tmp_path):
    real_like = tmp_path / "hermes-agent"
    (real_like / "tools").mkdir(parents=True)
    (real_like / "tools" / "__init__.py").write_text("", encoding="utf-8")
    assert server.is_hermes_root(real_like)


def test_is_hermes_root_accepts_hermes_state_marker(tmp_path):
    """Flat checkouts without tools/__init__.py but with hermes_state.py qualify."""
    real_like = tmp_path / "hermes-agent"
    real_like.mkdir(parents=True)
    (real_like / "hermes_state.py").write_text("", encoding="utf-8")
    assert server.is_hermes_root(real_like)


def test_find_hermes_root_skips_data_root_with_stray_tools_dir(tmp_path, monkeypatch):
    """HERMES_HOME at a data root with a stray tools/ must not be selected."""
    data_root = _make_fake_root(tmp_path)
    monkeypatch.delenv("HERMES_AGENT_ROOT", raising=False)
    # Real agent source root at the default <home>/.hermes/hermes-agent spot.
    real_root = tmp_path / ".hermes" / "hermes-agent"
    (real_root / "tools").mkdir(parents=True)
    (real_root / "tools" / "__init__.py").write_text("", encoding="utf-8")

    monkeypatch.setenv("HERMES_HOME", str(data_root))
    monkeypatch.setattr(server.Path, "home", classmethod(lambda cls: tmp_path))
    # Neutralize pip-metadata candidates so only the two paths above compete.
    monkeypatch.setattr(server.importlib.metadata, "distribution", _raise_distribution_not_found)

    assert server.find_hermes_root() == real_root.resolve()


def _raise_distribution_not_found(name: str):
    raise server.importlib.metadata.PackageNotFoundError(name)


def test_explicit_source_wins_without_changing_data_home(tmp_path, monkeypatch):
    old = tmp_path / 'data' / 'hermes-agent'
    candidate = tmp_path / 'managed' / 'revision' / 'payload'
    for root in (old, candidate):
        (root / 'tools').mkdir(parents=True)
        (root / 'tools' / '__init__.py').touch()
    monkeypatch.setenv('HERMES_HOME', str(old.parent))
    monkeypatch.setenv('HERMES_AGENT_ROOT', str(candidate))
    assert server.find_hermes_root() == candidate.resolve()
    assert server.candidate_roots() == [candidate.resolve()]
    assert os.environ['HERMES_HOME'] == str(old.parent)


@pytest.mark.parametrize('override', ['', 'relative-agent', 'missing', 'data-only'])
def test_invalid_explicit_source_never_falls_back(tmp_path, monkeypatch, override):
    old = tmp_path / 'hermes-agent'
    (old / 'tools').mkdir(parents=True)
    (old / 'tools' / '__init__.py').touch()
    data = _make_fake_root(tmp_path)
    value = str(data) if override == 'data-only' else str(tmp_path / override) if override == 'missing' else override
    monkeypatch.setenv('HERMES_HOME', str(old.parent))
    monkeypatch.setenv('HERMES_AGENT_ROOT', value)
    with pytest.raises(RuntimeError, match='HERMES_AGENT_ROOT'):
        server.find_hermes_root()


def test_invalid_explicit_source_prevents_server_start(tmp_path, monkeypatch):
    monkeypatch.setenv('HERMES_AGENT_ROOT', str(tmp_path / 'missing'))
    monkeypatch.setattr(server, 'IMPORT_ERROR', 'invalid explicit Agent source')
    monkeypatch.setattr(server, '_run_legacy_server', lambda args: pytest.fail('must not start listener'))
    with pytest.raises(RuntimeError, match='imports are unavailable'):
        server.main(['--http'])


def test_source_import_failure_does_not_block_update_helper(monkeypatch):
    import updater
    called = []
    monkeypatch.setenv('HERMES_AGENT_ROOT', 'invalid')
    monkeypatch.setattr(server, 'IMPORT_ERROR', 'invalid explicit source')
    monkeypatch.setattr(updater, 'main', lambda args: called.append(args))
    server.main(['update', '--help'])
    assert called == [['--help']]


@pytest.mark.parametrize('preload_old', [False, True])
def test_fresh_interpreter_verifies_loaded_source_and_operator_status(tmp_path, preload_old):
    old = tmp_path / 'data' / 'hermes-agent'
    candidate = tmp_path / 'managed' / 'payload'
    for root, marker in ((old, 'old'), (candidate, 'candidate')):
        (root / 'tools').mkdir(parents=True)
        (root / 'tools' / '__init__.py').touch()
        for module in ('file_tools', 'memory_tool', 'terminal_tool'):
            (root / 'tools' / f'{module}.py').write_text(f'SOURCE = {marker!r}\n', encoding='utf-8')
    env = dict(os.environ, HERMES_HOME=str(old.parent), HERMES_AGENT_ROOT=str(candidate))
    code = (f'import sys; sys.path.insert(0, {str(old)!r}); from tools import file_tools;\n' if preload_old else '')
    code += "import server,json,os; print(json.dumps({'error':server.IMPORT_ERROR,'source':getattr(server.file_tools,'SOURCE',None),'status':json.loads(server.hermes_operator_status()),'home':os.environ['HERMES_HOME']}))"
    result = subprocess.run([sys.executable, '-c', code], env=env, cwd=Path(__file__).parent, capture_output=True, text=True, timeout=30, check=True)
    observed = json.loads(result.stdout.strip().splitlines()[-1])
    if preload_old:
        assert 'outside HERMES_AGENT_ROOT' in (observed['error'] or '')
        assert observed['source'] is None
    else:
        assert observed['error'] is None
        assert observed['source'] == 'candidate'
        assert observed['status']['hermes_agent_root'] == str(candidate.resolve())
    assert observed['home'] == str(old.parent)
