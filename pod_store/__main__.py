import functools
from typing import Callable, List, Optional

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


def _default_commit_message_builder(
    ctx_params: dict, commit_message_template: str, *param_names
) -> str:
    """Helper to build `git` commit messages from the Click command context.

    See the `git_add_and_commit` decorator for more information.
    """
    template_args = [ctx_params[p] for p in param_names]
    return commit_message_template.format(*template_args)


def _optional_podcast_commit_message_builder(
    ctx_params: dict, commit_message_template: str
) -> str:
    """Helper to build `git` commit messages for Click commands that
    have an optional `podcast` argument.

    See the `git_add_and_commit` decorator for more information.
    """
    podcast_name = ctx_params.get("podcast") or "all"
    return commit_message_template.format(podcast_name)


def git_add_and_commit(
    *builder_args,
    commit_message_builder: Callable = _default_commit_message_builder,
):
    """Decorator for checking in and commiting changes made after running a command.
    Requires the `click.Context` object as a first argument to the decorated function.
    (see `click.pass_context`)

    By default, pass in a template str for building the commit message and a list of
    param names to grab from the `click.Context.params` dict to populate it.

        @click.pass_context
        @git_add_and_commit("Hello {}.", "recepient")
        def cmd(ctx):
            ...

    Assuming the `click.Context.params` dict had a key `recepient` with the value
    "world", the resulting commit message would be:

        "Hello world."

    Pass in a callable as a keyword arugment for `commit_message_builder` to get custom
    behavior when building commit messages.

    The message builder callable will receive a `ctx_params` dict
    (passed in from `click.Context.params`), and any positional `builder_args`
    provided to the decorator. It should return the commit message as a string.


        def commit_message_builder(_, value):
            return "This commit message is {}.".format(value)

        @click.pass_context
        @git_add_and_commit("arbitrary", commit_message_builder=custom_builder)
        def cmd(ctx):
            ...

    Here the resulting commit message would be:

        "This commit message is arbitrary."
    """

    def git_add_and_commit_wrapper(f: Callable):
        @functools.wraps(f)
        def git_add_and_commit_inner(ctx: click.Context, *args, **kwargs):
            resp = f(ctx, *args, **kwargs)
            run_git_command("add .")
            commit_msg = commit_message_builder(ctx.params, *builder_args)
            try:
                run_git_command(f"commit -m {commit_msg!r}")
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
@click.pass_context
@click.argument("title")
@click.argument("feed")
@git_add_and_commit("Added podcast: {}.", "title")
@catch_pod_store_errors
def add(ctx: click.Context, title: str, feed: str) -> None:
    """Add a podcast to the store.

    TITLE: title that will be used for tracking in the store
    FEED: rss feed url for updating podcast info
    """
    store.add_podcast(title=title, feed=feed)


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
    commit_message_builder=_optional_podcast_commit_message_builder,
)
@catch_pod_store_errors
def download(ctx: click.Context, podcast: Optional[str]) -> None:
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
@click.argument("cmd", nargs=-1)
@catch_pod_store_errors
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
    commit_message_builder=_optional_podcast_commit_message_builder,
)
@catch_pod_store_errors
def mark(ctx: click.Context, podcast: Optional[str], interactive: bool) -> None:
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
@click.pass_context
@click.argument("old")
@click.argument("new")
@git_add_and_commit("Renamed podcast: {} -> {}", "old", "new")
@catch_pod_store_errors
def mv(ctx: click.Context, old: str, new: str) -> None:
    """Rename a podcast in the store."""
    store.rename_podcast(old, new)


@cli.command()
@click.pass_context
@click.option(
    "-p", "--podcast", default=None, help="Refresh only the specified podcast."
)
@git_add_and_commit(
    "Refreshed {} podcast feed.",
    commit_message_builder=_optional_podcast_commit_message_builder,
)
@catch_pod_store_errors
def refresh(ctx: click.Context, podcast: Optional[str]) -> None:
    """Refresh podcast data from RSS feeds."""
    if podcast:
        podcasts = [store.get_podcast(podcast)]
    else:
        podcasts = store.list_podcasts()

    for podcast in podcasts:
        click.echo(f"Refreshing {podcast.title}")
        podcast.refresh()


@cli.command()
@click.pass_context
@click.argument("title")
@git_add_and_commit("Removed podcast: {}.", "title")
@catch_pod_store_errors
def rm(ctx: click.Context, title: str) -> None:
    """Remove specified podcast from the store."""
    store.remove_podcast(title)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
