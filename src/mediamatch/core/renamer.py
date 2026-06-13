"""Generate Plex/Jellyfin-compliant target names and apply renames.

A rename for a TV show may include the top folder, each season folder, and
every individual episode file. Movies include the top folder and the main
video file. All planned operations are collected into a RenamePlan and
applied bottom-up so paths remain valid.
"""
from __future__ import annotations

import logging
from pathlib import Path

from .parser import parse_name, ParsedMedia
from .scanner import (
    MediaItem, MediaType, RenameOp, RenamePlan, EpisodeFile, MovieFile,
)
from .tmdb import TMDbClient, TMDbResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Name construction
# ---------------------------------------------------------------------------

def _sanitize(name: str) -> str:
    """Remove characters forbidden in folder names on Windows/macOS/Linux."""
    forbidden = r'\/:*?"<>|'
    for ch in forbidden:
        name = name.replace(ch, "")
    return name.strip(" .")


def build_movie_name(title: str, year: int | None, tmdb_id: int | None = None) -> str:
    base = _sanitize(title)
    if year:
        base = f"{base} ({year})"
    if tmdb_id:
        base = f"{base} {{tmdb-{tmdb_id}}}"
    return base


def build_tv_name(title: str, year: int | None, tmdb_id: int | None = None) -> str:
    base = _sanitize(title)
    if year:
        base = f"{base} ({year})"
    if tmdb_id:
        base = f"{base} {{tmdb-{tmdb_id}}}"
    return base


def build_season_folder(season: int) -> str:
    """Plex uses 'Season 00' for specials and 'Season XX' for everything else."""
    return f"Season {season:02d}"


def build_episode_filename(
    show_title: str,
    show_year: int | None,
    season: int,
    episode: int,
    episode_end: int | None = None,
    episode_title: str | None = None,
    ext: str = ".mkv",
) -> str:
    """Plex episode standard:
        ShowName (year) - sXXeYY[-eZZ][ - Title].ext
    """
    show = _sanitize(show_title)
    if show_year:
        show = f"{show} ({show_year})"
    ep_part = f"s{season:02d}e{episode:02d}"
    if episode_end and episode_end != episode:
        ep_part = f"{ep_part}-e{episode_end:02d}"
    name = f"{show} - {ep_part}"
    if episode_title:
        clean = _sanitize(episode_title)
        if clean:
            name = f"{name} - {clean}"
    return f"{name}{ext.lower()}"


def build_movie_filename(title: str, year: int | None, ext: str = ".mkv") -> str:
    base = _sanitize(title)
    if year:
        base = f"{base} ({year})"
    return f"{base}{ext.lower()}"


# ---------------------------------------------------------------------------
# Plan construction
# ---------------------------------------------------------------------------

def _propose_top_folder(item: MediaItem, title: str, year: int | None) -> str:
    if item.media_type == MediaType.MOVIE:
        return build_movie_name(title, year, item.tmdb_id)
    return build_tv_name(title, year, item.tmdb_id)


def _build_tv_plan(
    item: MediaItem,
    show_title: str,
    show_year: int | None,
    tmdb_client: TMDbClient | None,
) -> RenamePlan:
    plan = RenamePlan()

    # 1. Top folder rename
    new_top = _propose_top_folder(item, show_title, show_year)
    plan.ops.append(RenameOp(
        src=item.path,
        dst_name=new_top,
        kind="folder",
    ))

    # 2. Season folder renames — collect unique parent dirs of episodes that
    #    sit directly under the show root (i.e. the season folder).
    season_dirs: dict[Path, int] = {}
    for ep in item.episodes:
        if ep.season is None:
            continue
        for ancestor in ep.path.parents:
            if ancestor.parent == item.path:
                # ancestor is the season folder directly under show root
                season_dirs[ancestor] = ep.season
                break

    seen = set()
    for sdir, snum in season_dirs.items():
        if sdir in seen:
            continue
        seen.add(sdir)
        desired = build_season_folder(snum)
        if sdir.name != desired:
            plan.ops.append(RenameOp(
                src=sdir,
                dst_name=desired,
                kind="season",
            ))

    # 3. Episode file renames
    for ep in item.episodes:
        if ep.season is None or ep.episode is None:
            continue
        ep_title = ep.parsed_title
        if tmdb_client and tmdb_client.available and item.tmdb_id:
            fetched = tmdb_client.get_episode_title(item.tmdb_id, ep.season, ep.episode)
            if fetched:
                ep_title = fetched
        new_name = build_episode_filename(
            show_title=show_title,
            show_year=show_year,
            season=ep.season,
            episode=ep.episode,
            episode_end=ep.episode_end,
            episode_title=ep_title,
            ext=ep.path.suffix,
        )
        if ep.path.name != new_name:
            plan.ops.append(RenameOp(
                src=ep.path,
                dst_name=new_name,
                kind="file",
            ))

    _mark_conflicts(plan)
    return plan


def _build_movie_plan(
    item: MediaItem,
    title: str,
    year: int | None,
) -> RenamePlan:
    plan = RenamePlan()
    new_top = _propose_top_folder(item, title, year)
    plan.ops.append(RenameOp(
        src=item.path,
        dst_name=new_top,
        kind="folder",
    ))
    if item.movie_file:
        new_file = build_movie_filename(title, year, ext=item.movie_file.path.suffix)
        if item.movie_file.path.name != new_file:
            plan.ops.append(RenameOp(
                src=item.movie_file.path,
                dst_name=new_file,
                kind="file",
            ))
    _mark_conflicts(plan)
    return plan


def _mark_conflicts(plan: RenamePlan) -> None:
    """Flag ops whose destination already exists on disk or collides with a
    sibling op's destination."""
    # Sibling collisions: two ops in the same parent dir going to the same name.
    by_parent: dict[Path, dict[str, list[RenameOp]]] = {}
    for op in plan.ops:
        parent = op.src.parent
        by_parent.setdefault(parent, {}).setdefault(op.dst_name.lower(), []).append(op)
    for groups in by_parent.values():
        for ops in groups.values():
            if len(ops) > 1:
                for op in ops:
                    op.conflict = True
                    op.error = "Collides with another planned rename"

    # On-disk conflicts: skip the case where dst_name == src.name (no-op).
    for op in plan.ops:
        if op.conflict or not op.needs_rename:
            continue
        target = op.src.parent / op.dst_name
        if target.exists() and target != op.src:
            op.conflict = True
            op.error = f"Target already exists: {op.dst_name}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def propose_name(item: MediaItem, tmdb_client: TMDbClient | None = None) -> MediaItem:
    """Fill item.proposed_name and item.rename_plan without touching the filesystem."""
    hint = "tv" if item.media_type == MediaType.TV_SHOW else "movie"
    parsed: ParsedMedia = parse_name(item.original_name, media_type_hint=hint)

    tmdb_result: TMDbResult | None = None
    if tmdb_client and tmdb_client.available:
        if item.media_type == MediaType.MOVIE:
            tmdb_result = tmdb_client.search_movie(parsed.title, parsed.year)
        else:
            tmdb_result = tmdb_client.search_tv(parsed.title, parsed.year)

    if tmdb_result:
        item.tmdb_id = tmdb_result.tmdb_id
        item.tmdb_title = tmdb_result.title
        item.tmdb_year = tmdb_result.year
        item.confidence = tmdb_result.confidence
        title = tmdb_result.title
        year = tmdb_result.year
    else:
        title = parsed.title
        year = parsed.year
        item.confidence = 0.5 if parsed.title else 0.0

    if item.media_type == MediaType.MOVIE:
        item.rename_plan = _build_movie_plan(item, title, year)
    else:
        item.rename_plan = _build_tv_plan(item, title, year, tmdb_client)

    item.proposed_name = _propose_top_folder(item, title, year)
    return item


def apply_plan(item: MediaItem, dry_run: bool = False) -> tuple[list[tuple[Path, Path]], list[RenameOp]]:
    """Execute the rename plan bottom-up.

    Returns (successful_renames, failed_ops). Each successful entry is
    (old_path, new_path) so the caller can record an undo batch.

    Renames are performed file → season → folder so that a parent folder
    rename never invalidates an in-flight child src path.
    """
    if not item.enabled or item.rename_plan is None:
        return [], []

    KIND_ORDER = {"file": 0, "season": 1, "folder": 2}
    ops = sorted(
        item.rename_plan.enabled_ops(),
        key=lambda o: (KIND_ORDER.get(o.kind, 99), -len(o.src.parts)),
    )

    successes: list[tuple[Path, Path]] = []
    failures: list[RenameOp] = []

    for op in ops:
        # Recompute src in case an ancestor was renamed earlier — but since
        # we go child-first, that doesn't happen. Still, guard against missing.
        if not op.src.exists():
            op.error = f"Source no longer exists: {op.src.name}"
            failures.append(op)
            continue
        target = op.src.parent / op.dst_name
        if target.exists() and target != op.src:
            op.error = f"Target already exists: {op.dst_name}"
            op.conflict = True
            failures.append(op)
            continue
        if dry_run:
            op.done = True
            successes.append((op.src, target))
            continue
        try:
            op.src.rename(target)
            successes.append((op.src, target))
            op.src = target
            op.done = True
            # Keep child ops' src paths valid: any subsequent op whose src is
            # below `op.src`'s old location needs to be relocated under target.
            # We sort child-first, so this is only relevant if a parent folder
            # rename came before a child (shouldn't happen with our ordering),
            # but we handle it defensively.
        except OSError as exc:
            op.error = str(exc)
            failures.append(op)

    # If the top folder was renamed, sync item.path/original_name/proposed_name.
    for op in ops:
        if op.kind == "folder" and op.done:
            item.path = op.src  # op.src has been reassigned to target on success
            item.original_name = op.src.name
            item.proposed_name = ""
            break

    return successes, failures


# Backwards-compat shim: a few tests and callers still use the old function name.
def apply_rename(item: MediaItem) -> bool:
    """Legacy single-step rename used by older callers and tests."""
    successes, failures = apply_plan(item, dry_run=False)
    return bool(successes) and not failures
