from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

import generate
from src.data_models import Commit, Repository, User
from src.github_client import GitHubClient
from src.layout import build_layout
from src.renderer import render_svg


def _make_mixed_fixture(tmp_path: Path) -> Path:
    data = {
        "user": {
            "login": "octo",
            "name": "Octo Dev",
            "avatar_url": "",
            "html_url": "https://github.com/octo",
        },
        "repos": [
            {
                "id": 1,
                "name": "public-alpha",
                "full_name": "octo/public-alpha",
                "html_url": "https://github.com/octo/public-alpha",
                "description": "Public repo",
                "stargazers_count": 40,
                "language": "Python",
                "language_bytes": {"Python": 5000},
                "private": False,
                "pushed_at": "2026-04-10T10:00:00Z",
            },
            {
                "id": 2,
                "name": "secret-vault-project",
                "full_name": "octo/secret-vault-project",
                "html_url": "https://github.com/octo/secret-vault-project",
                "description": "Top secret private project",
                "stargazers_count": 99,
                "language": "Rust",
                "language_bytes": {"Rust": 80000, "Python": 40000},
                "private": True,
                "pushed_at": "2026-04-11T10:00:00Z",
            },
        ],
        "commits": [
            {
                "repo": "octo/public-alpha",
                "repo_name": "public-alpha",
                "sha": "abc1111",
                "message": "Public commit",
                "committed_at": "2026-04-10T10:00:00Z",
                "url": "https://github.com/octo/public-alpha/commit/abc1111",
            },
            {
                "repo": "octo/secret-vault-project",
                "repo_name": "secret-vault-project",
                "sha": "sec9999",
                "message": "Secret internal commit message",
                "committed_at": "2026-04-11T10:00:00Z",
                "url": "https://github.com/octo/secret-vault-project/commit/sec9999",
            },
        ],
    }
    fixture_path = tmp_path / "mixed.json"
    fixture_path.write_text(json.dumps(data), encoding="utf-8")
    return fixture_path


def test_public_only_mode_excludes_private_repos(tmp_path: Path) -> None:
    fixture_path = _make_mixed_fixture(tmp_path)
    out_dir = tmp_path / "out"

    rc = generate.main(
        [
            "--fixture",
            str(fixture_path),
            "--output-dir",
            str(out_dir),
            "--mode",
            "public",
            "--no-avatar",
        ]
    )

    assert rc == 0
    public_svg = out_dir / "solar-system-public.svg"
    all_svg = out_dir / "solar-system-all.svg"
    assert public_svg.exists()
    assert not all_svg.exists()
    text = public_svg.read_text(encoding="utf-8")
    assert "public-alpha" in text
    assert "Rust" not in text
    assert "secret-vault-project" not in text


def test_complete_only_mode_includes_private_languages_without_leaking_metadata(tmp_path: Path) -> None:
    fixture_path = _make_mixed_fixture(tmp_path)
    out_dir = tmp_path / "out"

    rc = generate.main(
        [
            "--fixture",
            str(fixture_path),
            "--output-dir",
            str(out_dir),
            "--mode",
            "all",
            "--no-avatar",
        ]
    )

    assert rc == 0
    public_svg = out_dir / "solar-system-public.svg"
    all_svg = out_dir / "solar-system-all.svg"
    assert not public_svg.exists()
    assert all_svg.exists()
    text = all_svg.read_text(encoding="utf-8")
    assert "Rust" in text
    assert "Python" in text
    assert "Private repository" in text
    assert "secret-vault-project" not in text
    assert "Top secret private project" not in text
    assert "Secret internal commit message" not in text
    assert "sec9999" not in text


def test_both_mode_generates_simultaneous_outputs_and_different_planet_sizes(tmp_path: Path) -> None:
    fixture_path = _make_mixed_fixture(tmp_path)
    out_dir = tmp_path / "out"

    rc = generate.main(
        [
            "--fixture",
            str(fixture_path),
            "--output-dir",
            str(out_dir),
            "--mode",
            "both",
            "--no-avatar",
        ]
    )

    assert rc == 0
    public_svg = (out_dir / "solar-system-public.svg").read_text(encoding="utf-8")
    all_svg = (out_dir / "solar-system-all.svg").read_text(encoding="utf-8")
    assert "Rust" not in public_svg
    assert "Rust" in all_svg
    assert "1 public repositories" in public_svg
    assert "2 authorized repositories" in all_svg

    # Verify planet radii differ between public-only and complete datasets.
    user = User(login="octo", name="Octo Dev")
    pub_repo = Repository(id=1, name="public-alpha", full_name="octo/public-alpha", language_bytes={"Python": 5000}, private=False)
    priv_repo = Repository(id=2, name="secret-vault", full_name="octo/secret-vault", language_bytes={"Python": 40000, "Rust": 80000}, private=True)
    pub_layout = build_layout(user, [pub_repo], GitHubClient.aggregate_languages([pub_repo]))
    all_layout = build_layout(user, [pub_repo, priv_repo], GitHubClient.aggregate_languages([pub_repo, priv_repo]))
    assert pub_layout.planets[0].language == "Python"
    assert all_layout.planets[0].language == "Rust"
    assert len(all_layout.planets) == 2


def test_env_solar_system_mode_controls_generation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture_path = _make_mixed_fixture(tmp_path)
    out_dir = tmp_path / "out"
    monkeypatch.setenv("SOLAR_SYSTEM_MODE", "both")

    rc = generate.main(
        [
            "--fixture",
            str(fixture_path),
            "--output-dir",
            str(out_dir),
            "--no-avatar",
        ]
    )

    assert rc == 0
    assert (out_dir / "solar-system-public.svg").exists()
    assert (out_dir / "solar-system-all.svg").exists()


def test_missing_private_token_never_overwrites_existing_complete_svg(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True)
    existing_all = out_dir / "solar-system-all.svg"
    sentinel = "<svg xmlns='http://www.w3.org/2000/svg'><title>valid-previous</title></svg>"
    existing_all.write_text(sentinel, encoding="utf-8")

    monkeypatch.delenv("SOLAR_SYSTEM_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    rc = generate.main(
        [
            "--username",
            "octo",
            "--output-dir",
            str(out_dir),
            "--mode",
            "all",
            "--no-avatar",
        ]
    )

    assert rc == 1
    assert existing_all.read_text(encoding="utf-8") == sentinel
    assert "Private repository authorization is required" in capsys.readouterr().err


def test_both_mode_writes_public_and_preserves_complete_when_private_auth_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True)
    existing_all = out_dir / "solar-system-all.svg"
    sentinel = "<svg xmlns='http://www.w3.org/2000/svg'><title>valid-previous</title></svg>"
    existing_all.write_text(sentinel, encoding="utf-8")

    monkeypatch.delenv("SOLAR_SYSTEM_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    pub_user = User(login="octo", name="Octo Dev")
    pub_repo = Repository(id=1, name="public-alpha", full_name="octo/public-alpha", languages={"Python": 5000}, private=False)
    pub_langs = GitHubClient.aggregate_languages([pub_repo])

    def fake_fetch(args, *, include_private=False, token=None):
        if include_private:
            raise generate.GitHubError("Private repository authorization failed", 401)
        return pub_user, [pub_repo], pub_langs, [], ""

    with patch.object(generate, "_fetch", side_effect=fake_fetch):
        rc = generate.main(
            [
                "--username",
                "octo",
                "--output-dir",
                str(out_dir),
                "--mode",
                "both",
                "--no-avatar",
            ]
        )

    assert rc == 1
    assert (out_dir / "solar-system-public.svg").exists()
    assert existing_all.read_text(encoding="utf-8") == sentinel


def test_github_client_deduplication_pagination_and_partial_auth() -> None:
    client = GitHubClient(token="ghp_testtoken123456")

    page1 = [
        {"id": 10, "name": "pub", "full_name": "octo/pub", "private": False, "owner": {"login": "octo"}, "language": "Python"},
        {"id": 20, "name": "priv1", "full_name": "octo/priv1", "private": True, "owner": {"login": "octo"}, "language": "Go"},
        {"id": 30, "name": "org-repo", "full_name": "someorg/org-repo", "private": True, "owner": {"login": "someorg"}, "language": "Java"},
    ]
    page2 = [
        {"id": 20, "name": "priv1", "full_name": "octo/priv1", "private": True, "owner": {"login": "octo"}, "language": "Go"},
        {"id": 40, "name": "priv2", "full_name": "octo/priv2", "private": True, "owner": {"login": "octo"}, "language": "Rust"},
    ]

    def fake_request(url, params=None):
        if "user/repos" in url:
            if "page=2" in url or (params and params.get("page") == 2):
                return page2, {}
            return page1, {"Link": '<https://api.github.com/user/repos?page=2>; rel="next"'}
        if "octo/priv2/languages" in url:
            # Simulate partial authorization (403 on one repo's languages endpoint).
            raise generate.GitHubError("Resource not accessible by personal access token", 403)
        if "languages" in url:
            return {"Python": 1000}, {}
        return [], {}

    with patch.object(client, "_request", side_effect=fake_request):
        repos = client.get_repos("octo", include_private=True, max_language_fetches=10)

    names = [r.name for r in repos]
    assert names == ["pub", "priv1", "priv2"]
    assert len(repos) == 3  # deduplicated id=20 and filtered out someorg/org-repo
    # priv2 falls back to primary language when languages endpoint returns 403
    assert repos[2].language_bytes == {}
    assert repos[2].primary_language == "Rust"


def test_private_moons_and_commits_have_zero_identifying_metadata() -> None:
    user = User(login="octo", name="Octo Dev")
    priv_repo = Repository(
        id=99,
        name="classified-rocket",
        full_name="octo/classified-rocket",
        html_url="https://github.com/octo/classified-rocket",
        description="Classified",
        stargazers_count=42,
        language="Rust",
        language_bytes={"Rust": 10000},
        private=True,
    )
    commits = [
        Commit(
            repo="octo/classified-rocket",
            repo_name="classified-rocket",
            sha="deadbeef",
            message="Secret commit",
            committed_at="2026-04-11T10:00:00Z",
            url="https://github.com/octo/classified-rocket/commit/deadbeef",
        )
    ]
    layout = build_layout(user, [priv_repo], GitHubClient.aggregate_languages([priv_repo]), commits=commits)
    assert len(layout.comets) == 0
    svg = render_svg(layout, None)
    assert "classified-rocket" not in svg
    assert "deadbeef" not in svg
    assert "Private repository" in svg
    assert 'href="https://github.com/octo/classified-rocket"' not in svg


def test_validate_svg_rejects_token_patterns() -> None:
    with pytest.raises(ValueError, match="token"):
        generate._validate_svg("<svg xmlns='http://www.w3.org/2000/svg'><text>ghp_secret123</text></svg>")
    with pytest.raises(ValueError, match="token"):
        generate._validate_svg("<svg xmlns='http://www.w3.org/2000/svg'><text>github_pat_abc</text></svg>")


def test_interactive_setup_prompt_selects_mode(tmp_path: Path) -> None:
    fixture_path = _make_mixed_fixture(tmp_path)
    out_dir = tmp_path / "out"

    with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", return_value="3"):
        rc = generate.main(
            [
                "--fixture",
                str(fixture_path),
                "--output-dir",
                str(out_dir),
                "--setup",
                "--no-avatar",
            ]
        )

    assert rc == 0
    assert (out_dir / "solar-system-public.svg").exists()
    assert (out_dir / "solar-system-all.svg").exists()


def test_readme_documents_dual_universe_paths_and_privacy() -> None:
    readme = Path(__file__).resolve().parent.parent / "README.md"
    text = readme.read_text(encoding="utf-8")
    assert "./output/solar-system-public.svg" in text
    assert "./output/solar-system-all.svg" in text
    assert "SOLAR_SYSTEM_MODE" in text
    assert "SOLAR_SYSTEM_TOKEN" in text
    assert "--setup" in text
    assert "Metadata" in text
    assert "indirect" in text.lower()
