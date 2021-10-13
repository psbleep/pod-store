import os
from typing import List, Optional

import click

from . import PODCAST_DOWNLOADS_PATH, STORE_FILE_PATH, STORE_PATH
from .cmd_decorators import (
    catch_pod_store_errors,
    git_add_and_commit,
    optional_podcast_commit_message_builder,
    save_store_changes,
)
from .episodes import Episode
from .exc import PodcastDoesNotExistError
from .podcasts import Podcast
from .store import Store
from .store_file_handlers import UnencryptedStoreFileHandler
from .util import run_git_command


@click.group()
@click.pass_context
def cli(ctx) -> None:
    if os.path.exists(STORE_FILE_PATH):
        ctx.obj = Store(
            store_path=STORE_PATH,
            podcast_downloads_path=PODCAST_DOWNLOADS_PATH,
            file_handler=UnencryptedStoreFileHandler(STORE_FILE_PATH),
        )


@cli.command()
@click.option(
    "--git/--no-git", default=True, help="initialize git repo for tracking changes"
)
@click.option("-g", "--git-url", default=None, help="remote URL for the git repo")
@catch_pod_store_errors
def init(git: bool, git_url: Optional[str]) -> None:
    """Set up the pod store.

    `pod-store` tracks changes using `git`.
    """
    git = git or git_url
    Store.create(
        store_path=STORE_PATH,
        store_file_path=STORE_FILE_PATH,
        podcast_downloads_path=PODCAST_DOWNLOADS_PATH,
        setup_git=git,
        git_url=git_url,
    )
    click.echo(f"Store created: {STORE_PATH}")
    click.echo(f"Podcast episodes will be downloaded to {PODCAST_DOWNLOADS_PATH}")

    if git:
        if git_url:
            git_msg = git_url
        else:
            git_msg = "no remote repo specified. You can manually add one later."
        click.echo(f"Git tracking enabled: {git_msg}")


@cli.command()
@click.pass_context
@click.argument("title")
@click.argument("feed")
@git_add_and_commit("Added podcast: {}.", "title")
@save_store_changes
@catch_pod_store_errors
def add(ctx: click.Context, title: str, feed: str) -> None:
    """Add a podcast to the store.

    TITLE: title that will be used for tracking in the store
    FEED: rss feed url for updating podcast info
    """
    ctx.obj.podcasts.add(title=title, feed=feed)


@cli.command()
@click.pass_context
@click.option(
    "-p",
    "--podcast",
    default=None,
    help="(podcast title) Download only episodes for the specified podcast.",
)
@git_add_and_commit(
    "Downloaded {} new episodes.",
    commit_message_builder=optional_podcast_commit_message_builder,
)
@save_store_changes
@catch_pod_store_errors
def download(ctx: click.Context, podcast: Optional[str]) -> None:
    """Download podcast episode(s)"""
    podcast_filters = {"has_new_episodes": True}
    if podcast:
        podcast_filters["title"] = podcast

    podcasts = ctx.obj.podcasts.list(**podcast_filters)
    _download_podcast_episodes(podcasts)


def _download_podcast_episodes(podcasts: List[Podcast]) -> None:
    """Helper method for downloading all new episodes for a batch of podcasts."""
    for pod in podcasts:
        for episode in pod.episodes.list(downloaded_at=None):
            click.echo(f"Downloading {pod.title} -> {episode.title}")
            episode.download()


@cli.command()
@click.argument("cmd", nargs=-1)
@catch_pod_store_errors
def git(cmd: str) -> None:
    """Run arbitrary git commands in the `pod-store` repo."""
    output = run_git_command(" ".join(cmd))
    click.echo(output)


@cli.command()
@click.pass_context
@click.option(
    "--new/--all", default=True, help="look for new episodes or include all episodes"
)
@click.option("--episodes/--podcasts", default=False, help="list episodes or podcasts")
@click.option(
    "-p",
    "--podcast",
    default=None,
    help="(podcast title) if listing episodes, limit results to the specified podcast",
)
@catch_pod_store_errors
def ls(ctx, new: bool, episodes: bool, podcast: Optional[str]) -> None:
    """List store entries.

    By default, this will list podcasts that have new episodes. Adjust the output using
    the provided flags and command options.
    """
    if episodes:
        if podcast:
            podcasts = [ctx.obj.podcasts.get(podcast)]
        else:
            podcasts = ctx.obj.podcasts.list()

        episode_filters = {}
        if new:
            episode_filters["downloaded_at"] = None

        entries = []
        for pod in podcasts:
            pod_episodes = pod.episodes.list(**episode_filters)
            if not pod_episodes:
                continue
            entries.append(f"{pod.title}\n")
            entries.extend([str(e) for e in pod_episodes])
            entries.append("\n")
        entries = entries[:-1]

    else:
        podcast_filters = {}
        if podcast:
            podcast_filters["title"] = podcast
        if new:
            podcast_filters["has_new_episodes"] = True
        entries = [str(p) for p in ctx.obj.podcasts.list(**podcast_filters)]

        if podcast and not entries:
            raise PodcastDoesNotExistError(podcast)

    click.echo("\n".join(entries))


@cli.command()
@click.pass_context
@click.option(
    "-p",
    "--podcast",
    default=None,
    help="Mark episodes for only the specified podcast.",
)
@click.option(
    "--interactive/--bulk",
    default=True,
    help="Run the command in interactive mode to select which episodes to mark",
)
@git_add_and_commit(
    "Marked {} podcast episodes.",
    commit_message_builder=optional_podcast_commit_message_builder,
)
@save_store_changes
@catch_pod_store_errors
def mark(ctx: click.Context, podcast: Optional[str], interactive: bool) -> None:
    """Mark 'new' episodes as old."""
    podcast_filters = {"has_new_episodes": True}
    if podcast:
        podcast_filters["title"] = podcast

    podcasts = ctx.obj.podcasts.list(**podcast_filters)

    if interactive:
        click.echo(
            "Marking in interactive mode. Options are:\n\n"
            "y = yes (mark as downloaded)\n"
            "n = no (do not mark as downloaded)\n"
            "b = bulk (mark this and all following episodes as 'downloaded')\n"
        )

    for pod in podcasts:
        for episode in pod.episodes.list(downloaded_at=None):
            if interactive:
                confirm, interactive = _mark_episode_interactively(pod, episode)
            else:
                confirm = True

            if confirm:
                click.echo(
                    f"Marking {pod.title} -> [{episode.episode_number}] {episode.title}"
                )
                episode.mark_as_downloaded()


def _mark_episode_interactively(podcast: Podcast, episode: Episode) -> (bool, bool):
    interactive = True

    result = click.prompt(
        f"{podcast.title}: [{episode.episode_number}] {episode.title}",
        type=click.Choice(["y", "n", "b"], case_sensitive=False),
    )

    if result == "y":
        confirm = True
    elif result == "n":
        confirm = False
    else:
        confirm = True
        interactive = False

    return confirm, interactive


@cli.command()
@click.pass_context
@click.argument("old")
@click.argument("new")
@git_add_and_commit("Renamed podcast: {} -> {}", "old", "new")
@save_store_changes
@catch_pod_store_errors
def mv(ctx: click.Context, old: str, new: str) -> None:
    """Rename a podcast in the store."""
    ctx.obj.podcasts.rename(old, new)


@cli.command()
@click.pass_context
@click.option(
    "-p", "--podcast", default=None, help="Refresh only the specified podcast."
)
@git_add_and_commit(
    "Refreshed {} podcast feed.",
    commit_message_builder=optional_podcast_commit_message_builder,
)
@save_store_changes
@catch_pod_store_errors
def refresh(ctx: click.Context, podcast: Optional[str]) -> None:
    """Refresh podcast data from RSS feeds."""
    if podcast:
        podcasts = [ctx.obj.podcasts.get(podcast)]
    else:
        podcasts = ctx.obj.podcasts.list()

    for podcast in podcasts:
        click.echo(f"Refreshing {podcast.title}")
        podcast.refresh()


@cli.command()
@click.pass_context
@click.argument("title")
@git_add_and_commit("Removed podcast: {}.", "title")
@save_store_changes
@catch_pod_store_errors
def rm(ctx: click.Context, title: str) -> None:
    """Remove specified podcast from the store."""
    ctx.obj.podcasts.delete(title)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
