"""GitHub REST API client with pagination, retries and language aggregation."""

from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from .data_models import Commit, Language, Repository, User

API_ROOT = "https://api.github.com"
DEFAULT_USER_AGENT = "github-solar-system"
API_VERSION = "2022-11-28"
MAX_RATE_LIMIT_WAIT = 60.0
DEFAULT_COMMIT_LOOKBACK_DAYS = 7
MAX_AVATAR_BYTES = 2 * 1024 * 1024


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class GitHubError(RuntimeError):
    """Raised when the GitHub API cannot satisfy a request."""

    def __init__(self, message: str, status: int | None = None, url: str | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.url = url


class GitHubClient:
    """Minimal, dependency-free client for the public GitHub REST API.

    Unauthenticated calls are limited to 60 requests per hour, so language
    breakdowns are fetched for a bounded number of repositories. Passing a
    token raises the limit and lets more repositories receive accurate data.
    """

    def __init__(
        self,
        token: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        user_agent: str = DEFAULT_USER_AGENT,
        base_url: str = API_ROOT,
        sleeper=time.sleep,
    ) -> None:
        self.token = token or None
        self.timeout = timeout
        self.max_retries = max(0, int(max_retries))
        self.user_agent = user_agent
        self.base_url = base_url.rstrip("/")
        self._sleeper = sleeper

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": self.user_agent,
            "X-GitHub-Api-Version": API_VERSION,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _url(self, path_or_url: str, params: dict | None = None) -> str:
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            return path_or_url
        url = f"{self.base_url}{path_or_url}"
        if params:
            clean = {key: value for key, value in params.items() if value is not None}
            if clean:
                url = f"{url}?{urllib.parse.urlencode(clean)}"
        return url

    def _open(self, request):
        return urllib.request.urlopen(request, timeout=self.timeout)

    def _backoff(self, attempt: int) -> None:
        self._sleeper(min(2.0**attempt, 8.0))

    def _rate_limit_delay(self, headers) -> float | None:
        if headers is None:
            return None
        try:
            reset = float(headers.get("X-RateLimit-Reset"))
        except (TypeError, ValueError):
            return None
        return max(1.0, reset - time.time()) + 1.0

    def _request(self, path_or_url: str, params: dict | None = None) -> tuple[object, object]:
        url = self._url(path_or_url, params)
        request = urllib.request.Request(url, headers=self._headers())
        attempts = self.max_retries + 1
        last_error: Exception | None = None

        for attempt in range(attempts):
            try:
                with self._open(request) as response:
                    body = response.read()
                    headers = response.headers
            except urllib.error.HTTPError as exc:
                try:
                    exc.read()
                except Exception:
                    pass
                try:
                    exc.close()
                except Exception:
                    pass
                error = GitHubError(f"GitHub API request failed ({exc.code})", exc.code, url)
                last_error = exc
                if attempt == attempts - 1:
                    raise error from exc
                remaining = None
                if getattr(exc, "headers", None) is not None:
                    remaining = exc.headers.get("X-RateLimit-Remaining")
                if exc.code in (403, 429) and remaining == "0":
                    delay = self._rate_limit_delay(exc.headers)
                    if delay is None or delay > MAX_RATE_LIMIT_WAIT:
                        raise error from exc
                    self._sleeper(delay)
                    continue
                if exc.code >= 500:
                    self._backoff(attempt)
                    continue
                raise error from exc
            except (urllib.error.URLError, TimeoutError, ConnectionError, socket.timeout) as exc:
                last_error = exc
                if attempt == attempts - 1:
                    raise GitHubError(f"GitHub API request failed: {exc}", None, url) from exc
                self._backoff(attempt)
                continue
            else:
                try:
                    return json.loads(body), headers
                except ValueError as exc:
                    raise GitHubError(
                        f"GitHub API returned invalid JSON from {url}", None, url
                    ) from exc

        raise GitHubError(f"GitHub API request failed: {last_error}", None, url)

    @staticmethod
    def _next_link(link_header: str | None) -> str | None:
        if not link_header:
            return None
        for part in link_header.split(","):
            segments = part.split(";")
            if len(segments) < 2:
                continue
            target = segments[0].strip()
            if not (target.startswith("<") and target.endswith(">")):
                continue
            target = target[1:-1].strip()
            for segment in segments[1:]:
                key, _, value = segment.strip().partition("=")
                if key.strip().lower() == "rel" and value.strip().strip('"').lower() == "next":
                    return target
        return None

    def _paginate(self, path: str, params: dict | None = None, max_pages: int = 10) -> list[dict]:
        results: list[dict] = []
        url: str | None = path
        query = dict(params or {})
        query.setdefault("per_page", 100)
        seen: set[str] = set()
        pages = 0
        limit = max(0, int(max_pages))

        while url and pages < limit:
            if url in seen:
                break
            seen.add(url)
            data, headers = self._request(url, query if pages == 0 else None)
            if not isinstance(data, list):
                raise GitHubError(f"Expected a list payload from {self._url(url, query)}", None, url)
            results.extend(item for item in data if isinstance(item, dict))
            link = headers.get("Link") if headers is not None else None
            url = self._next_link(link)
            pages += 1
        return results

    def get_user(self, login: str) -> User:
        path = f"/users/{urllib.parse.quote(str(login), safe='')}"
        data, _ = self._request(path)
        if not isinstance(data, dict):
            raise GitHubError(f"Unexpected user payload for {login!r}", None, self._url(path))
        return User.from_api(data)

    def get_repo_languages(self, full_name: str) -> dict[str, int]:
        path = f"/repos/{urllib.parse.quote(str(full_name), safe='/')}/languages"
        data, _ = self._request(path)
        if not isinstance(data, dict):
            return {}
        clean: dict[str, int] = {}
        for name, value in data.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            amount = int(value)
            if amount > 0:
                clean[str(name)] = amount
        return clean

    def _safe_languages(self, full_name: str) -> dict[str, int]:
        try:
            return self.get_repo_languages(full_name)
        except GitHubError:
            return {}

    def get_repos(
        self,
        login: str,
        *,
        include_forks: bool = False,
        include_archived: bool = False,
        fetch_languages: bool = True,
        max_workers: int = 8,
        max_language_fetches: int = 15,
    ) -> list[Repository]:
        path = f"/users/{urllib.parse.quote(str(login), safe='')}/repos"
        raw = self._paginate(
            path, {"type": "owner", "sort": "pushed", "direction": "desc"}
        )

        repos: list[Repository] = []
        for item in raw:
            repository = Repository.from_api(item)
            if repository.fork and not include_forks:
                continue
            if repository.archived and not include_archived:
                continue
            repos.append(repository)

        if fetch_languages and repos:
            targets = repos[: max(0, int(max_language_fetches))]
            workers = max(1, min(int(max_workers), len(targets)))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                mappings = list(
                    executor.map(lambda repo: self._safe_languages(repo.full_name), targets)
                )
            for repository, mapping in zip(targets, mappings):
                repository.apply_languages(mapping)

        return repos

    def get_events(self, login: str, *, max_events: int = 30, max_pages: int = 2) -> list[dict]:
        path = f"/users/{urllib.parse.quote(str(login), safe='')}/events/public"
        wanted = max(1, min(100, int(max_events)))
        raw = self._paginate(path, {"per_page": wanted}, max_pages=max_pages)
        return raw[: max(0, int(max_events))]

    def get_avatar(self, avatar_url: str, *, size: int = 256) -> bytes:
        """Fetch a public avatar image and return its bytes.

        GitHub's avatar CDN can resize on request, so the embedded image stays
        small without requiring an image library in the generator.
        """

        if not avatar_url:
            raise GitHubError("no avatar URL was provided")
        url = avatar_url
        if "avatars.githubusercontent.com" in url:
            separator = "&" if "?" in url else "?"
            if "s=" not in url:
                url = f"{url}{separator}s={max(64, min(512, int(size)))}"
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "image/avif,image/webp,image/png,image/jpeg,image/*",
                "User-Agent": self.user_agent,
            },
        )
        attempts = self.max_retries + 1
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                with self._open(request) as response:
                    data = response.read()
                    content_type = response.headers.get("Content-Type", "")
            except urllib.error.HTTPError as exc:
                try:
                    exc.read()
                    exc.close()
                except Exception:
                    pass
                last_error = exc
                if attempt == attempts - 1:
                    raise GitHubError(
                        f"avatar request failed ({exc.code})", exc.code, url
                    ) from exc
                if exc.code >= 500:
                    self._backoff(attempt)
                    continue
                raise GitHubError(
                    f"avatar request failed ({exc.code})", exc.code, url
                ) from exc
            except (urllib.error.URLError, TimeoutError, ConnectionError, socket.timeout) as exc:
                last_error = exc
                if attempt == attempts - 1:
                    raise GitHubError(f"avatar request failed: {exc}", None, url) from exc
                self._backoff(attempt)
                continue
            else:
                if not data:
                    raise GitHubError("avatar response was empty", None, url)
                if len(data) > MAX_AVATAR_BYTES:
                    raise GitHubError("avatar image was too large", None, url)
                if content_type and not content_type.lower().startswith("image/"):
                    raise GitHubError(
                        f"avatar response was not an image ({content_type})", None, url
                    )
                return data
        raise GitHubError(f"avatar request failed: {last_error}", None, url)

    def get_commits(
        self,
        repositories: list[Repository],
        *,
        lookback_days: int = DEFAULT_COMMIT_LOOKBACK_DAYS,
        now: datetime | None = None,
        max_repos: int = 20,
        max_commits: int = 80,
        max_workers: int = 6,
    ) -> list[Commit]:
        """Fetch recent commits from the supplied repositories.

        Each repository contributes commits from the lookback window. Results
        are deduplicated by repository and SHA, then ordered newest first.
        """

        if not repositories:
            return []
        reference = now or datetime.now(timezone.utc)
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=timezone.utc)
        since = reference - timedelta(days=max(1, int(lookback_days)))
        since_text = since.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

        targets: list[Repository] = []
        for repository in repositories:
            if repository.fork or repository.archived:
                continue
            pushed = _parse_iso(repository.pushed_at)
            if pushed is not None and pushed < since:
                continue
            targets.append(repository)
            if len(targets) >= max(1, int(max_repos)):
                break
        if not targets:
            return []

        def fetch(repository: Repository) -> list[Commit]:
            path = (
                f"/repos/{urllib.parse.quote(str(repository.full_name), safe='/')}/commits"
            )
            try:
                payload, _ = self._request(
                    path,
                    {"since": since_text, "per_page": 100},
                )
            except GitHubError:
                return []
            if not isinstance(payload, list):
                return []
            commits: list[Commit] = []
            for entry in payload:
                if not isinstance(entry, dict):
                    continue
                commit = Commit.from_api(repository.full_name, entry)
                if commit.sha:
                    commits.append(commit)
            return commits

        workers = max(1, min(int(max_workers), len(targets)))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            batches = list(executor.map(fetch, targets))

        deduplicated: dict[tuple[str, str], Commit] = {}
        for batch in batches:
            for commit in batch:
                deduplicated.setdefault(commit.identity, commit)
        ordered = sorted(
            deduplicated.values(),
            key=lambda commit: (
                commit.committed_at or "",
                commit.repo.lower(),
                commit.sha,
            ),
            reverse=True,
        )
        return ordered[: max(0, int(max_commits))]

    @staticmethod
    def aggregate_languages(repositories: list[Repository]) -> list[Language]:
        """Aggregate primary-language byte counts across repositories.

        A repository contributes every byte of its primary language only, so
        each repository belongs to exactly one planet. When a language
        breakdown is unavailable the repository size is used as a fallback so
        the planet still reflects real data instead of disappearing.
        """

        totals: dict[str, list[int]] = {}
        for repository in repositories:
            language = repository.primary_language
            if not language:
                continue
            if repository.language_bytes:
                byte_count = int(repository.language_bytes.get(language) or 0)
            else:
                byte_count = 0
            if byte_count <= 0:
                byte_count = max(1, int(repository.size or 1))
            entry = totals.setdefault(language, [0, 0])
            entry[0] += byte_count
            entry[1] += 1

        languages = [
            Language(name=name, bytes=values[0], repo_count=values[1])
            for name, values in totals.items()
            if values[1] > 0
        ]
        languages.sort(key=lambda language: (-language.bytes, language.name.lower()))
        return languages
