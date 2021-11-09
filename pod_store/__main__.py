"""Define a CLI for `pod-store`. Uses the `Click` library."""
import os
from typing import Any, List, Optional

import click
import requests

from . import GPG_ID, PODCAST_DOWNLOADS_PATH, STORE_FILE_PATH, STORE_PATH
from .commands.commit_messages import (
    download_commit_message_builder,
    refresh_commit_message_builder,
    tagger_commit_message_builder,
)
from .commands.decorators import (
    catch_pod_store_errors,
    conditional_confirmation_prompt,
    git_add_and_commit,
    require_store,
    save_store_changes,
)
from .commands.filtering import get_filter_from_command_arguments
from .commands.helpers import abort_if_false, display_pod_store_error_from_exception
from .commands.listing import get_lister_from_command_arguments
from .commands.tagging import marker, tagger, unmarker, untagger
from .store import Store
from .store_file_handlers import EncryptedStoreFileHandler, UnencryptedStoreFileHandler
from .util import run_git_command


class PodStoreGroup(click.Group):
    """Custom `click.Group` class that enables properly handling the `pod git` command.

    The purpose of the `pod git` command is to conveniently run `git` commands against
    the pod store repo without having to navigate to the correct file path or do another
    workaround:

        cd ~/.pod-store
        git push

    Because Click will intercept and parse any options/flags passed to this command,
    without intervention this command breaks on any `git` commands the user runs that
    include options/flags intended for `git`:

        pod git push -u origin master

    The solution here is to intercept any invocation of `pod git <args>` and manually
    run the `git` command, display the output, and handle error messages outside the
    normal Click cycle.

    `pod git --help` still uses the default Click behavior for displaying the help
    message.

    Note: the pod `git` command is still defined below, so that it will appear in the
    list of available commands/provide a help message.
    """

    def invoke(self, ctx: click.Context) -> Any:
        """Custom group behavior: intercept `pod git <args>` and handle that manually.

        Standard `click.Group.invoke` behavior in all other situations.
        """
        if ctx.protected_args == ["git"] and "--help" not in ctx.args:
            self._handle_pod_store_git_command(ctx.args)
        else:
            return super().invoke(ctx)

    @staticmethod
    def _handle_pod_store_git_command(ctx_args: List[str]) -> None:
        """Constructs and executes the intended `git` command, displaying output and
        errors to the user.
        """
        git_cmd_args = []
        for a in ctx_args:
            # Parse multi-word `args` tokens back into quote-enclosed strings for
            # consumption by `git`.
            if " " in a:
                git_cmd_args.append(f"{a!r}")
            else:
                git_cmd_args.append(a)
        git_cmd = " ".join(git_cmd_args)
        try:
            click.echo(run_git_command(git_cmd))
        except Exception as exception:
            display_pod_store_error_from_exception(exception)


@click.command(cls=PodStoreGroup)
@click.pass_context
def cli(ctx):
    """pod-store is an encrypted CLI podcast tracker that syncs your info accross
    devices. Based on `git` and `gpg`. Inspired by `pass`, the universal UNIX password
    manager.

    Get started with the `--help` flag on any of the following commands.
    Start with the `init` command to set up the store, the `add` command to track your
    podcasts, and the `download` command to download your podcast episodes.
    """
    if os.path.exists(STORE_FILE_PATH):
        if GPG_ID:
            file_handler = EncryptedStoreFileHandler(
                gpg_id=GPG_ID, store_file_path=STORE_FILE_PATH
            )
        else:
            file_handler = UnencryptedStoreFileHandler(store_file_path=STORE_FILE_PATH)

        ctx.obj = Store(
            store_path=STORE_PATH,
            file_handler=file_handler,
        )


@cli.command()
@click.pass_context
@click.argument("title")
@click.argument("feed")
@catch_pod_store_errors
@require_store
@git_add_and_commit(
    secure_git_mode_message="Added podcast.",
    message="Added podcast: {title!r}.",
    params=["title"],
)
@save_store_changes
def add(ctx: click.Context, title: str, feed: str):
    """Add a podcast to the store.

    TITLE: title that will be used for tracking in the store

    FEED: rss url for updating podcast episode data
    """
    store = ctx.obj
    store.podcasts.add(title=title, feed=feed)


@cli.command()
@click.pass_context
@click.option(
    "-p",
    "--podcast",
    default=None,
    help="(podcast title): Download only episodes for the specified podcast.",
)
@click.option(
    "--is-tagged/--not-tagged",
    default=True,
    help="(flag): Search for episodes with or without the supplied tags. "
    "Defaults to `is-tagged`. Has no effect if no tags are indicated.",
)
@click.option(
    "--tag",
    "-t",
    multiple=True,
    default=[],
    help="Supply tags to search for episodes with. Multiple tags can be provided.",
)
@catch_pod_store_errors
@require_store
@git_add_and_commit(
    secure_git_mode_message="Downloaded episodes.",
    commit_message_builder=download_commit_message_builder,
)
@save_store_changes
def download(
    ctx: click.Context, podcast: Optional[str], is_tagged: bool, tag: List[str]
):
    """Download podcast episodes."""
    store = ctx.obj

    filter = get_filter_from_command_arguments(
        store=store,
        new_episodes=True,
        filter_episodes=True,
        podcast_title=podcast,
        tags=tag,
        filter_untagged_items=not is_tagged,
    )

    for ep in filter.episodes:
        click.echo(f"Downloading: {ep.download_path}.")
        try:
            with ep.download() as download:
                with click.progressbar(download, length=download.length) as bar:
                    for _ in bar:
                        pass
        except requests.ConnectTimeout:
            click.secho("Error: timed out when downloading episode.", fg="red")


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
    help="Skip the confirmation prompt.",
)
@catch_pod_store_errors
@require_store
@git_add_and_commit(
    secure_git_mode_message="Set up store.", message="Encrypted the store."
)
def encrypt_store(ctx: click.Context, gpg_id: str):
    """Encrypt the pod store file with the provided gpg keys.

    GPG_ID: Keys to use for encryption.

    This command works to encrypt a previously unencrypted store, or to
    re-encrypt an already encrypted store using new keys (assuming you have access to
    both the old and new keys).
    """
    store = ctx.obj

    store.encrypt(gpg_id=gpg_id)
    click.echo("Store encrypted with GPG ID.")


@cli.command()
@click.argument("cmd", nargs=-1)
def git(cmd: str):
    """Run a `git` command against the pod store repo.

    CMD: any `git` command
    """
    # To deal with flags passed in to the `git` command, this is handled with custom
    # behavior in the `PodStoreGroup` class.
    pass


@cli.command()
@click.option(
    "--git/--no-git",
    default=True,
    help="(flag): Indicates whether to initialize a git repo for tracking changes. "
    "Defaults to `--git`.",
)
@click.option(
    "-u", "--git-url", default=None, help="(optional): Remote URL for the git repo."
)
@click.option(
    "-g",
    "--gpg-id",
    default=None,
    help="(optional) GPG ID for the keys to encrypt the store with. "
    "If not provided, the store will not be encrypted. You can still encrypt the "
    "store later using the `encrypt-store` command.",
)
@catch_pod_store_errors
def init(git: bool, git_url: Optional[str], gpg_id: Optional[str]):
    """Set up the pod store.

    pod-store tracks changes using `git` and encrypts data using `gpg`. Use the command
    flags to configure your git repo and gpg encryption.
    """
    if git_url:
        click.echo("Please note, this could take a minute or two...")
    git = git or git_url
    Store.init(
        store_path=STORE_PATH,
        store_file_path=STORE_FILE_PATH,
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
@click.option(
    "--new/--all",
    default=True,
    help="(flag): Look for new episodes only, or include all episodes. "
    "Defaults to `--new`.",
)
@click.option(
    "--episodes/--podcasts",
    default=False,
    help="(flag): List episodes or podcasts. Defaults to `--podcasts`.",
)
@click.option(
    "-p",
    "--podcast",
    default=None,
    help="(podcast title): List only episodes for the specified podcast.",
)
@click.option(
    "--list-tagged/--not-tagged",
    default=True,
    help="(flag): Search for episodes with or without the supplied tags. "
    "Defaults to `--list-tagged`. Has no effect if no tags are indicated.",
)
@click.option(
    "--tag",
    "-t",
    multiple=True,
    default=[],
    help="Supply tags to search for episodes with. Multiple tags can be provided.",
)
@click.option(
    "--verbose/--not-verbose",
    default=False,
    help="(flag): Determines how much detail to provide in the listing. "
    "Defaults to `--not-verbose`.",
)
@catch_pod_store_errors
@require_store
def ls(
    ctx: click.Context,
    new: bool,
    episodes: bool,
    podcast: Optional[str],
    list_tagged: bool,
    tag: List[str],
    verbose: bool,
):
    """List data from the store.

    By default, this will list podcasts that have new episodes. Adjust the output using
    the provided flags and command options.
    """
    store = ctx.obj
    lister = get_lister_from_command_arguments(
        store=store,
        new_episodes=new,
        list_episodes=episodes,
        podcast_title=podcast,
        list_untagged_items=not list_tagged,
        tags=tag,
    )
    for msg in lister.list(verbose=verbose):
        click.echo(msg)


@cli.command()
@click.pass_context
@click.option(
    "-p",
    "--podcast",
    default=None,
    help="(podcast title): Mark episodes for only the specified podcast.",
)
@click.option(
    "--interactive/--bulk",
    default=True,
    help="(flag): Run this command in interactive mode to select which episodes to "
    "mark, or bulk mode to mark all episodes. Defaults to `--interactive`.",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Skip confirmation prompt for bulk mode actions.",
)
@conditional_confirmation_prompt(param="interactive", value=False, override="force")
@catch_pod_store_errors
@require_store
@git_add_and_commit(
    secure_git_mode_message="Tagged items.",
    commit_message_builder=tagger_commit_message_builder,
    tagger=marker,
)
@save_store_changes
def mark_as_new(
    ctx: click.Context,
    podcast: Optional[str],
    interactive: bool,
    force: Optional[bool],
):
    """Add the `new` tag to a group of episodes.

    See the `tag-episodes` command help for usage options.
    """
    store = ctx.obj
    filter = get_filter_from_command_arguments(store=store, podcast_title=podcast)

    for msg in marker.tag_podcast_episodes(
        filter.podcasts, interactive_mode=interactive
    ):
        click.echo(msg)


@cli.command()
@click.pass_context
@click.option(
    "-p",
    "--podcast",
    default=None,
    help="(podcast title): Mark episodes for only the specified podcast.",
)
@click.option(
    "--interactive/--bulk",
    default=True,
    help="(flag): Run this command in interactive mode to select which episodes to "
    "mark, or bulk mode to mark all episodes. Defaults to `--interactive`.",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Skip confirmation prompt for bulk mode actions.",
)
@conditional_confirmation_prompt(param="interactive", value=False, override="force")
@catch_pod_store_errors
@require_store
@git_add_and_commit(
    secure_git_mode_message="Tagged items.",
    commit_message_builder=tagger_commit_message_builder,
    tagger=unmarker,
)
@save_store_changes
def mark_as_old(
    ctx: click.Context,
    podcast: Optional[str],
    interactive: bool,
    force: Optional[bool],
):
    """Remove the `new` tag from a group of episodes. Alias for the `untag` command."""
    store = ctx.obj
    filter = get_filter_from_command_arguments(store=store, podcast_title=podcast)
    for msg in unmarker.tag_podcast_episodes(
        filter.podcasts, interactive_mode=interactive
    ):
        click.echo(msg)


@cli.command()
@click.pass_context
@click.argument("old")
@click.argument("new")
@catch_pod_store_errors
@require_store
@git_add_and_commit(
    message="Renamed podcast: {old!r} -> {new!r}.", params=["old", "new"]
)
@save_store_changes
def mv(ctx: click.Context, old: str, new: str):
    """Rename a podcast in the store.

    OLD: old podcast title

    NEW: new podcast title
    """
    store = ctx.obj
    store.podcasts.rename(old, new)


@cli.command()
@click.pass_context
@click.option(
    "-p",
    "--podcast",
    default=None,
    help="(podcast title): Refresh only the specified podcast.",
)
@click.option(
    "--is-tagged/--not-tagged",
    default=True,
    help="(flag): Search for podcasts with or without the tags supplied. "
    "Defaults to `--is-tagged`. Has no effect if no tags are indicated.",
)
@click.option(
    "--tag",
    "-t",
    multiple=True,
    default=[],
    help="Filter podcasts by tag. Multiple tags can be provided.",
)
@catch_pod_store_errors
@require_store
@git_add_and_commit(
    secure_git_mode_message="Refreshed podcasts.",
    commit_message_builder=refresh_commit_message_builder,
)
@save_store_changes
def refresh(
    ctx: click.Context, podcast: Optional[str], is_tagged: bool, tag: List[str]
):
    """Refresh podcast episode data from the RSS feed."""
    store = ctx.obj
    filter = get_filter_from_command_arguments(
        store=store,
        podcast_title=podcast,
        tags=tag,
        filter_untagged_items=not is_tagged,
    )
    for podcast in filter.podcasts:
        click.echo(f"Refreshing {podcast.title}")
        try:
            podcast.refresh()
        except requests.ConnectTimeout:
            click.secho("Error: timed out when reading RSS feed.", fg="red")


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
    help="Skip confirmation prompt.",
)
@catch_pod_store_errors
@require_store
@git_add_and_commit(message="Removed podcast: {title!r}.", params=["title"])
@save_store_changes
def rm(ctx: click.Context, title: str):
    """Remove a podcast from the store. This command will NOT delete the podcast
    episodes that have been downloaded.

    TITLE: title of podcast to remove
    """
    store = ctx.obj
    store.podcasts.delete(title)


@cli.command()
@click.pass_context
@click.argument("podcast")
@click.argument("tag")
@click.option(
    "-e",
    "--episode",
    default=None,
    help="(episode ID): Episode to tag. "
    "Note that this is the ID from the `ls --episodes --verbose` listing, not the "
    "episode number.",
)
@catch_pod_store_errors
@require_store
@git_add_and_commit(
    secure_git_mode_message="Tagged items.",
    commit_message_builder=tagger_commit_message_builder,
    tagger=tagger,
)
@save_store_changes
def tag(ctx: click.Context, podcast: str, tag: str, episode: Optional[str]):
    """Tag a single podcast or episode with an arbitrary text tag. If the optional
    episode ID is provided, it will be tagged. Otherwise, the podcast itself will
    be tagged.

    Note that tagging an episode requires the user to provide the podcast AND episode.

    PODCAST: title of podcast
    TAG: arbitrary text tag
    """
    store = ctx.obj

    pod = store.podcasts.get(podcast)
    if episode:
        ep = pod.episodes.get(episode)
        click.echo(tagger.tag_episode(ep, tag=tag))
    else:
        click.echo(tagger.tag_podcast(pod, tag=tag))


@cli.command()
@click.pass_context
@click.argument("tag")
@click.option(
    "-p",
    "--podcast",
    default=None,
    help="(podcast title): Tag episodes for only the specified podcast.",
)
@click.option(
    "--interactive/--bulk",
    default=True,
    help="(flag): Run this command in interactive mode to select which episodes to "
    "tag, or bulk mode to tag all episodes in the group. Defaults to `--interactive`.",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Skip confirmation prompt for bulk mode actions.",
)
@conditional_confirmation_prompt(param="interactive", value=False, override="force")
@catch_pod_store_errors
@require_store
@git_add_and_commit(
    secure_git_mode_message="Tagged items.",
    commit_message_builder=tagger_commit_message_builder,
    tagger=tagger,
)
@save_store_changes
def tag_episodes(
    ctx: click.Context,
    tag: str,
    podcast: Optional[str],
    interactive: bool,
    force: Optional[bool],
):
    """Tag episodes in groups.

    TAG: arbitrary text tag to apply
    """
    store = ctx.obj
    filter = get_filter_from_command_arguments(store=store, podcast_title=podcast)
    for msg in tagger.tag_podcast_episodes(
        filter.podcasts, tag=tag, interactive_mode=interactive
    ):
        click.echo(msg)


@cli.command()
@click.pass_context
@click.option(
    "-f",
    "--force",
    is_flag=True,
    callback=abort_if_false,
    expose_value=False,
    prompt="Are you sure you want to unencrypt the pod store?",
    help="Skip the confirmation prompt.",
)
@catch_pod_store_errors
@require_store
@git_add_and_commit(
    secure_git_mode_message="Set up store.", message="Unencrypted the store."
)
def unencrypt_store(ctx: click.Context):
    """Unencrypt the pod store, saving the data in plaintext instead."""
    store = ctx.obj
    store.unencrypt()
    click.echo("Store was unencrypted.")


@cli.command()
@click.pass_context
@click.argument("podcast")
@click.argument("tag")
@click.option(
    "-e",
    "--episode",
    default=None,
    help="(episode ID): Episode to untag. "
    "Note that this is the ID from the `ls --episodes --verbose` listing, not the "
    "episode number.",
)
@catch_pod_store_errors
@require_store
@git_add_and_commit(
    secure_git_mode_message="Tagged items.",
    commit_message_builder=tagger_commit_message_builder,
    tagger=untagger,
)
@save_store_changes
def untag(ctx: click.Context, podcast: str, tag: str, episode: Optional[str]):
    """Untag a single podcast or episode. If the optional episode ID is provided,
    it will be untagged. Otherwise, the podcast itself will be untagged.

    Note that untagging an episode requires the user to provide both the podcast
    AND episode.

    PODCAST: title of podcast
    TAG: arbitrary text tag
    """

    store = ctx.obj

    pod = store.podcasts.get(podcast)
    if episode:
        ep = pod.episodes.get(episode)
        click.echo(untagger.tag_episode(ep, tag=tag))
    else:
        click.echo(untagger.tag_podcast(pod, tag=tag))


@cli.command()
@click.pass_context
@click.argument("tag")
@click.option(
    "-p",
    "--podcast",
    default=None,
    help="(podcast title): Untag episodes for only the specified podcast.",
)
@click.option(
    "--interactive/--bulk",
    default=True,
    help="(flag): Run this command in interactive mode to select which episodes to "
    "untag, or bulk mode to untag all episodes in the group. Defaults to "
    "`--interactive`.",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Skip confirmation prompt for bulk mode actions.",
)
@conditional_confirmation_prompt(param="interactive", value=False, override="force")
@catch_pod_store_errors
@require_store
@git_add_and_commit(
    secure_git_mode_message="Tagged items.",
    commit_message_builder=tagger_commit_message_builder,
    tagger=untagger,
)
@save_store_changes
def untag_episodes(
    ctx: click.Context,
    tag: str,
    podcast: Optional[str],
    interactive: bool,
    force: Optional[bool],
):
    """Untag episodes in groups.

    TAG: tag to remove
    """
    store = ctx.obj
    filter = get_filter_from_command_arguments(store=store, podcast_title=podcast)
    for msg in untagger.tag_podcast_episodes(
        filter.podcasts, tag=tag, interactive_mode=interactive
    ):
        click.echo(msg)


def main() -> None:
    """Run the Click application."""
    cli()


if __name__ == "__main__":
    main()
