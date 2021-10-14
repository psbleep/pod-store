import os
from typing import Any, List, Optional

import click

from . import GPG_ID, PODCAST_DOWNLOADS_PATH, STORE_FILE_PATH, STORE_PATH
from .cmd_decorators import (
    catch_pod_store_errors,
    git_add_and_commit,
    optional_podcast_commit_message_builder,
    save_store_changes,
)
from .episodes import Episode
from .podcasts import Podcast
from .store import Store
from .store_file_handlers import EncryptedStoreFileHandler, UnencryptedStoreFileHandler
from .util import run_git_command


def _abort_if_false(ctx: click.Context, _, value: Any):
    """Callback for aborting a Click command from within an argument or option."""
    if not value:
        ctx.abort()


@click.group()
@click.pass_context
def cli(ctx) -> None:
    if os.path.exists(STORE_FILE_PATH):
        if GPG_ID:
            file_handler = EncryptedStoreFileHandler(
                gpg_id=GPG_ID, store_file_path=STORE_FILE_PATH
            )
        else:
            file_handler = UnencryptedStoreFileHandler(store_file_path=STORE_FILE_PATH)
        ctx.obj = Store(
            store_path=STORE_PATH,
            podcast_downloads_path=PODCAST_DOWNLOADS_PATH,
            file_handler=file_handler,
        )


@cli.command()
@click.option(
    "--git/--no-git", default=True, help="initialize git repo for tracking changes"
)
@click.option("-u", "--git-url", default=None, help="remote URL for the git repo")
@click.option("-g", "--gpg-id", default=None, help="GPG ID for store encryption keys")
@catch_pod_store_errors
def init(git: bool, git_url: Optional[str], gpg_id: Optional[str]) -> None:
    """Set up the pod store.

    `pod-store` tracks changes using `git`.
    """
    git = git or git_url
    Store.init(
        store_path=STORE_PATH,
        store_file_path=STORE_FILE_PATH,
        podcast_downloads_path=PODCAST_DOWNLOADS_PATH,
        setup_git=git,
        git_url=git_url,
        gpg_id=gpg_id,
    )
    click.echo(f"Store created: {STORE_PATH}")
    click.echo(f"Podcast episodes will be downloaded to {PODCAST_DOWNLOADS_PATH}")

    if git:
        if git_url:
            git_msg = git_url
        else:
            git_msg = "no remote repo specified. You can manually add one later."
        click.echo(f"Git tracking enabled: {git_msg}")

    if gpg_id:
        click.echo("GPG ID set for store encryption.")


@cli.command()
@click.pass_context
@click.argument("gpg-id")
@click.option(
    "-f",
    "--force",
    is_flag=True,
    callback=_abort_if_false,
    expose_value=False,
    prompt="Are you sure you want to encrypt the pod store?",
)
@git_add_and_commit("Encrypted the store.")
def encrypt_store(ctx: click.Context, gpg_id: str):
    """Encrypt the pod store file with the provided GPG ID keys."""
    store = ctx.obj

    store.encrypt(gpg_id=gpg_id)
    click.echo("Store encrypted with GPG ID.")


@cli.command()
@click.pass_context
@click.option(
    "-f",
    "--force",
    is_flag=True,
    callback=_abort_if_false,
    expose_value=False,
    prompt="Are you sure you want to unencrypt the pod store?",
)
@git_add_and_commit("Unencrypted the store.")
def unencrypt_store(ctx: click.Context):
    """Unencrypt the pod store, saving the data in plaintext instead."""
    store = ctx.obj

    store.unencrypt()
    click.echo("Store was unencrypted.")


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
    store = ctx.obj
    store.podcasts.add(title=title, feed=feed)


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
    store = ctx.obj

    podcast_filters = {"has_new_episodes": True}
    if podcast:
        podcast_filters["title"] = podcast

    podcasts = store.podcasts.list(allow_empty=False, **podcast_filters)
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
def ls(ctx: click.Context, new: bool, episodes: bool, podcast: Optional[str]) -> None:
    """List store entries.

    By default, this will list podcasts that have new episodes. Adjust the output using
    the provided flags and command options.
    """
    store = ctx.obj

    if episodes:
        if podcast:
            podcasts = [store.podcasts.get(podcast)]
        else:
            podcasts = store.podcasts.list(allow_empty=False)

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
        entries = [
            str(p) for p in store.podcasts.list(allow_empty=False, **podcast_filters)
        ]

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
    store = ctx.obj

    podcast_filters = {"has_new_episodes": True}
    if podcast:
        podcast_filters["title"] = podcast

    podcasts = store.podcasts.list(allow_empty=False, **podcast_filters)

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
    store = ctx.obj
    store.podcasts.rename(old, new)


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
    store = ctx.obj

    if podcast:
        podcasts = [store.podcasts.get(podcast)]
    else:
        podcasts = store.podcasts.list(allow_empty=False)

    for podcast in podcasts:
        click.echo(f"Refreshing {podcast.title}")
        podcast.refresh()


@cli.command()
@click.pass_context
@click.argument("title")
@click.option(
    "-f",
    "--force",
    is_flag=True,
    callback=_abort_if_false,
    expose_value=False,
    prompt="Are you sure you want to delete this podcast?",
)
@git_add_and_commit("Removed podcast: {}.", "title")
@save_store_changes
@catch_pod_store_errors
def rm(ctx: click.Context, title: str) -> None:
    """Remove specified podcast from the store."""
    store = ctx.obj
    store.podcasts.delete(title)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
