"""Define a CLI for `pod-store`. Uses the `Click` library."""
import os
from typing import Optional

import click

from . import GPG_ID, PODCAST_DOWNLOADS_PATH, STORE_FILE_PATH, STORE_PATH
from .commands.decorators import (
    catch_pod_store_errors,
    git_add_and_commit,
    optional_podcast_commit_message_builder,
    required_podcast_optional_episode_commit_message_builder,
    save_store_changes,
)
from .commands.helpers import abort_if_false, get_episodes, get_podcasts
from .commands.ls import list_podcast_episodes
from .commands.untag import INTERACTIVE_MODE_HELP, handle_episode_untagging
from .store import Store
from .store_file_handlers import EncryptedStoreFileHandler, UnencryptedStoreFileHandler
from .util import run_git_command


@click.group()
@click.pass_context
def cli(ctx):
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
def init(git: bool, git_url: Optional[str], gpg_id: Optional[str]):
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
    callback=abort_if_false,
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
    callback=abort_if_false,
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
def add(ctx: click.Context, title: str, feed: str):
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
def download(ctx: click.Context, podcast: Optional[str]):
    """Download podcast episode(s)"""
    store = ctx.obj
    episodes = get_episodes(store=store, new=True, podcast_title=podcast)

    for ep in episodes:
        click.echo(f"Downloading: {ep.download_path}")
        ep.download()


@cli.command()
@click.argument("cmd", nargs=-1)
@catch_pod_store_errors
def git(cmd: str):
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
def ls(ctx: click.Context, new: bool, episodes: bool, podcast: Optional[str]):
    """List store entries.

    By default, this will list podcasts that have new episodes. Adjust the output using
    the provided flags and command options.
    """
    store = ctx.obj

    # assume we are listing episodes if an individual podcast was specified
    list_episodes = episodes or podcast

    podcasts = get_podcasts(store=store, has_new_episodes=new, title=podcast)

    if list_episodes:
        for pod in podcasts:
            episode_listing = list_podcast_episodes(
                store=store, new=new, podcast_title=pod.title
            )
            if episode_listing:
                click.echo(episode_listing)
    else:
        podcast_listing = "\n".join([str(p) for p in podcasts])
        click.echo(podcast_listing)


@cli.command()
@click.pass_context
@click.argument("old")
@click.argument("new")
@git_add_and_commit("Renamed podcast: {} -> {}", "old", "new")
@save_store_changes
@catch_pod_store_errors
def mv(ctx: click.Context, old: str, new: str):
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
def refresh(ctx: click.Context, podcast: Optional[str]):
    """Refresh podcast data from RSS feeds."""
    store = ctx.obj
    podcasts = get_podcasts(store=store, title=podcast)

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
    callback=abort_if_false,
    expose_value=False,
    prompt="Are you sure you want to delete this podcast?",
)
@git_add_and_commit("Removed podcast: {}.", "title")
@save_store_changes
@catch_pod_store_errors
def rm(ctx: click.Context, title: str):
    """Remove specified podcast from the store."""
    store = ctx.obj
    store.podcasts.delete(title)


@cli.command()
@click.pass_context
@click.argument("podcast")
@click.argument("tag")
@click.option("-e", "--episode", default=None)
@git_add_and_commit(
    "Tagged {}{}-> {}.",
    "tag",
    commit_message_builder=required_podcast_optional_episode_commit_message_builder,
)
@save_store_changes
@catch_pod_store_errors
def tag(ctx: click.Context, podcast: str, tag: str, episode: Optional[str]):
    """Tag a podcast or episode with an arbitrary text tag."""
    store = ctx.obj

    podcast = store.podcasts.get(podcast)
    if episode:
        ep = podcast.episodes.get(episode)
        ep.tag(tag)
        click.echo(f"Tagged {podcast.title}, episode {episode} -> {tag}.")
    else:
        click.echo(f"Tagged {podcast.title} -> {tag}.")
        podcast.tag(tag)


@cli.command()
@click.pass_context
@click.argument("podcast")
@click.argument("tag")
@click.option("-e", "--episode", default=None)
@git_add_and_commit(
    "Untagged {}{}-> {}.",
    "tag",
    commit_message_builder=required_podcast_optional_episode_commit_message_builder,
)
@save_store_changes
@catch_pod_store_errors
def untag(ctx: click.Context, podcast: str, tag: str, episode: Optional[str]):
    """Untag a podcast or episode."""
    store = ctx.obj

    podcast = store.podcasts.get(podcast)
    if episode:
        ep = podcast.episodes.get(episode)
        ep.untag(tag)
        click.echo(f"Untagged {podcast.title}, episode {episode} -> {tag}.")
    else:
        click.echo(f"Untagged {podcast.title} -> {tag}.")
        podcast.untag(tag)


@cli.command()
@click.pass_context
@click.argument("tag")
@click.option(
    "-p",
    "--podcast",
    default=None,
    help="Untag episodes for only the specified podcast.",
)
@click.option(
    "--interactive/--bulk",
    default=True,
    help="Run this command in interactive mode to select which episodes to untag",
)
@git_add_and_commit(
    "Untagged {} podcast episodes.",
    commit_message_builder=optional_podcast_commit_message_builder,
)
@save_store_changes
@catch_pod_store_errors
def untag_episodes(
    ctx: click.Context, tag: str, podcast: Optional[str], interactive: bool
):
    """Untag episodes in groups."""
    store = ctx.obj
    interactive_mode = interactive
    podcasts = get_podcasts(store=store, has_new_episodes=True, title=podcast)

    click.echo(f"Untagging: {tag}.")

    if interactive:
        click.echo(INTERACTIVE_MODE_HELP)

    for pod in podcasts:
        for ep in pod.episodes.list(new=True):
            # `interactive` can get switched from True -> False here, if the user
            # decides to switch from interactive to bulk-assignment partway through
            # the list of episodes.
            marked, interactive_mode = handle_episode_untagging(
                tag=tag, interactive_mode=interactive_mode, podcast=pod, episode=ep
            )
            if marked:
                click.echo(f"Untagged {pod.title} -> [{ep.episode_number}] {ep.title}")


def main() -> None:
    """Run the Click application."""
    cli()


if __name__ == "__main__":
    main()
