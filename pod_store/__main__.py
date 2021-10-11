import functools
from typing import List, Optional

import click

from . import DOWNLOADS_PATH, STORE_PATH, store
from .episode import Episode
from .exc import (
    EpisodeDoesNotExistError,
    GitCommandError,
    PodcastDoesNotExistError,
    PodcastExistsError,
    StoreExistsError,
)
from .podcast import Podcast
from .util import run_git_command


def catch_pod_store_errors(f):
    @functools.wraps(f)
    def catch_pod_store_errors_inner(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except EpisodeDoesNotExistError as err:
            msg = str(err)
            click.secho(f"Episode not found: {msg}", fg="red")
        except GitCommandError as err:
            msg = str(err)
            click.secho(f"Error running git command: {msg}", fg="red")
        except PodcastDoesNotExistError as err:
            msg = str(err)
            if msg == "None":
                msg = "not specified"
            click.secho(f"Podcast not found: {msg}", fg="red")
        except PodcastExistsError as err:
            msg = str(err)
            click.secho(f"Podcast with title already exists: {msg}", fg="red")
        except StoreExistsError as err:
            msg = str(err)
            click.secho(f"Store already initialized: {msg}", fg="red")

    return catch_pod_store_errors_inner


def git_add_and_commit(msg: str):
    def git_add_and_commit_wrapper(f: callable):
        @functools.wraps(f)
        def git_add_and_commit_inner(*args, **kwargs):
            resp = f(*args, **kwargs)
            run_git_command("add .")
            try:
                run_git_command(f"commit -m {msg!r}")
            except GitCommandError:
                pass
            return resp

        return git_add_and_commit_inner

    return git_add_and_commit_wrapper


@click.group()
def cli() -> None:
    pass


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
    store.init_store(setup_git=git, git_url=git_url)
    click.echo(f"Store created: {STORE_PATH}")
    click.echo(f"Podcast episodes will be downloaded to {DOWNLOADS_PATH}")

    if git:
        git_msg = "Git tracking enabled: "
        if git_url:
            git_msg = git_url
        else:
            git_msg = "no remote repo specified. You can manually add one later."
        click.echo(f"Git tracking enabled: {git_msg}")


@cli.command()
@click.argument("title")
@click.argument("feed")
@git_add_and_commit("Added podcast")
@catch_pod_store_errors
def add(title: str, feed: str) -> None:
    """Add a podcast to the store.

    TITLE: title that will be used for tracking in the store
    FEED: rss feed url for updating podcast info
    """
    store.add_podcast(title=title, feed=feed)


@cli.command()
@click.option(
    "-p",
    "--podcast",
    default=None,
    help="(podcast title) Download only episodes for the specified podcast.",
)
@git_add_and_commit("Downloaded podcast episodes")
@catch_pod_store_errors
def download(podcast: Optional[str]) -> None:
    """Download podcast episode(s)"""
    if podcast:
        podcasts = [store.get_podcast(podcast)]
    else:
        podcasts = store.list_podcasts_with_new_episodes()
    _download_podcast_episodes(podcasts)


def _download_podcast_episodes(podcasts: List[Podcast]) -> None:
    """Helper method for downloading all new episodes for a batch of podcasts."""
    for pod in podcasts:
        for episode in pod.list_new_episodes():
            click.echo(f"Downloading {pod.title} -> {episode.title}")
            episode.download()


@cli.command()
@catch_pod_store_errors
@click.argument("cmd", nargs=-1)
def git(cmd: str) -> None:
    """Run arbitrary git commands in the `pod-store` repo."""
    output = run_git_command(" ".join(cmd))
    click.echo(output)


@cli.command()
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
def ls(new: bool, episodes: bool, podcast: Optional[str]) -> None:
    """List store entries.

    By default, this will list podcasts that have new episodes. Adjust the output using
    the provided flags and command options.
    """
    if episodes:
        output = _ls_episodes(new=new)
    elif podcast:
        podcast = store.get_podcast(podcast)
        output = _ls_podcast_episodes(podcast, new=new)
    else:
        output = _ls_podcasts(new=new)
    click.echo(output)


def _ls_episodes(new: bool) -> str:
    """Helper method for listing episodes."""
    if new:
        podcasts = store.list_podcasts_with_new_episodes()
    else:
        podcasts = store.list_podcasts()

    output = []

    for pod in podcasts:
        if new:
            episodes = pod.list_new_episodes()
        else:
            episodes = pod.list_episodes()

        output.extend(
            [f"{pod.title} -> [{e.episode_number}] {e.title}" for e in episodes]
        )

    return "\n".join(output)


def _ls_podcasts(new: bool = True) -> str:
    """Helper method for listing podcasts."""
    if new:
        podcasts = store.list_podcasts_with_new_episodes()
    else:
        podcasts = store.list_podcasts()
    return "\n".join([p.title for p in podcasts])


def _ls_podcast_episodes(podcast: str, new: bool = True) -> str:
    """Helper method for listing podcast episodes."""
    if new:
        episodes = podcast.list_new_episodes()
    else:
        episodes = podcast.list_episodes()
    return "\n".join([f"[{e.episode_number}] {e.title}" for e in episodes])


@cli.command()
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
@git_add_and_commit("Marked podcast episodes")
@catch_pod_store_errors
def mark(podcast: Optional[str], interactive: bool) -> None:
    """Mark 'new' episodes as old."""
    if podcast:
        podcasts = [store.get_podcast(podcast)]
    else:
        podcasts = store.list_podcasts_with_new_episodes()

    if interactive:
        click.echo(
            "Marking in interactive mode. Options are:\n\n"
            "y = yes (mark as downloaded)\n"
            "n = no (do not mark as downloaded)\n"
            "b = bulk (mark this and all following episodes as 'downloaded')\n"
        )

    for pod in podcasts:
        for episode in pod.list_new_episodes():
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
@click.argument("old")
@click.argument("new")
@git_add_and_commit("Renamed podcast")
@catch_pod_store_errors
def mv(old: str, new: str) -> None:
    """Rename a podcast in the store."""
    store.rename_podcast(old, new)


@cli.command()
@click.option(
    "-p", "--podcast", default=None, help="Refresh only the specified podcast."
)
@git_add_and_commit("Refreshed podcast feed")
@catch_pod_store_errors
def refresh(podcast: Optional[str]) -> None:
    """Refresh podcast data from RSS feeds."""
    if podcast:
        podcasts = [store.get_podcast(podcast)]
    else:
        podcasts = store.list_podcasts()

    for podcast in podcasts:
        click.echo(f"Refreshing {podcast.title}")
        podcast.refresh()


@cli.command()
@click.argument("title")
@git_add_and_commit("Removed podcast")
@catch_pod_store_errors
def rm(title: str) -> None:
    """Remove specified podcast from the store."""
    store.remove_podcast(title)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
