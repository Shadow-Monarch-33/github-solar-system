"""Typed models for GitHub users, repositories, languages and commits."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class User:
    login: str
    id: int | None = None
    avatar_url: str = ""
    html_url: str = ""
    name: str | None = None
    company: str | None = None
    blog: str | None = None
    location: str | None = None
    bio: str | None = None
    public_repos: int = 0
    followers: int = 0
    following: int = 0

    @classmethod
    def from_api(cls, data: dict) -> "User":
        return cls(
            login=str(data.get("login") or ""),
            id=data.get("id"),
            avatar_url=str(data.get("avatar_url") or ""),
            html_url=str(data.get("html_url") or ""),
            name=data.get("name"),
            company=data.get("company"),
            blog=data.get("blog"),
            location=data.get("location"),
            bio=data.get("bio"),
            public_repos=int(data.get("public_repos") or 0),
            followers=int(data.get("followers") or 0),
            following=int(data.get("following") or 0),
        )


@dataclass
class Repository:
    name: str
    full_name: str
    html_url: str = ""
    description: str | None = None
    language: str | None = None
    languages: list[str] = field(default_factory=list)
    language_bytes: dict[str, int] = field(default_factory=dict)
    stargazers_count: int = 0
    forks_count: int = 0
    size: int = 0
    fork: bool = False
    archived: bool = False
    created_at: str | None = None
    pushed_at: str | None = None
    updated_at: str | None = None
    default_branch: str = "main"
    id: int | None = None

    @classmethod
    def from_api(cls, data: dict) -> "Repository":
        return cls(
            name=str(data.get("name") or ""),
            full_name=str(data.get("full_name") or data.get("name") or ""),
            html_url=str(data.get("html_url") or ""),
            description=data.get("description"),
            language=data.get("language"),
            stargazers_count=int(data.get("stargazers_count") or 0),
            forks_count=int(data.get("forks_count") or 0),
            size=int(data.get("size") or 0),
            fork=bool(data.get("fork", False)),
            archived=bool(data.get("archived", False)),
            created_at=data.get("created_at"),
            pushed_at=data.get("pushed_at"),
            updated_at=data.get("updated_at"),
            default_branch=str(data.get("default_branch") or "main"),
            id=data.get("id"),
        )

    def apply_languages(self, mapping: dict | None) -> None:
        clean: dict[str, int] = {}
        for name, value in (mapping or {}).items():
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                continue
            amount = int(value)
            if amount > 0:
                clean[str(name)] = amount
        self.language_bytes = clean
        self.languages = [
            name for name, _ in sorted(clean.items(), key=lambda item: (-item[1], item[0].lower()))
        ]

    @property
    def primary_language(self) -> str | None:
        if self.language_bytes:
            return max(self.language_bytes, key=lambda name: self.language_bytes[name])
        return self.language or None


@dataclass(frozen=True)
class Language:
    name: str
    bytes: int
    repo_count: int = 0

    @property
    def kilobytes(self) -> float:
        return self.bytes / 1024.0


@dataclass(frozen=True)
class Commit:
    """A verified commit from a public repository.

    ``repo`` is the ``owner/name`` full name, ``repo_name`` is the short
    repository name shown beside the comet.
    """

    repo: str
    repo_name: str
    sha: str
    url: str = ""
    message: str = ""
    committed_at: str = ""
    author: str | None = None

    @property
    def identity(self) -> tuple[str, str]:
        return (self.repo.lower(), self.sha.lower())

    @classmethod
    def from_api(cls, repo: str, payload: dict) -> "Commit":
        commit = payload.get("commit") if isinstance(payload.get("commit"), dict) else {}
        author = payload.get("author") if isinstance(payload.get("author"), dict) else {}
        date = commit.get("author", {}).get("date") if isinstance(commit.get("author"), dict) else None
        return cls(
            repo=str(repo),
            repo_name=str(repo).split("/")[-1],
            sha=str(payload.get("sha") or ""),
            url=str(payload.get("html_url") or ""),
            message=str((commit.get("message") or "").split("\n")[0]),
            committed_at=str(date or ""),
            author=author.get("login"),
        )

    @classmethod
    def from_fixture(cls, payload: dict) -> "Commit":
        repo = str(payload.get("repo") or payload.get("full_name") or "")
        return cls(
            repo=repo,
            repo_name=str(payload.get("repo_name") or repo.split("/")[-1]),
            sha=str(payload.get("sha") or ""),
            url=str(payload.get("html_url") or ""),
            message=str(payload.get("message") or ""),
            committed_at=str(payload.get("committed_at") or payload.get("date") or ""),
            author=payload.get("author"),
        )


@dataclass
class SolarSystem:
    user: User
    repositories: list[Repository]
    languages: list[Language]
    events: list[dict] = field(default_factory=list)
    commits: list[Commit] = field(default_factory=list)
