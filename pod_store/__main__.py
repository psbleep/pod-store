"""Define a CLI for `pod-store`. Uses the `Click` library."""
import os
from typing import Any, List, Optional

import click
import requests

from . import (
    GPG_ID,
    PODCAST_DOWNLOADS_PATH,
    STORE_FILE_PATH,
    STORE_PATH,
    get_default_store_file_name,
)
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
from .commands.filtering import Filter
from .commands.helpers import abort_if_false, display_pod_store_error_from_exception
from .commands.listing import Lister
from .commands.tagging import Tagger
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
    "-e",
    "--episode",
    type=int,
    default=None,
    help="(episode number): Download a single episode. "
    "Note that you must specify the podcast this episode belongs to using the "
    "`--podcast` option.",
)
@click.option(
    "--tagged",
    "-t",
    multiple=True,
    help="Download episodes that have been tagged. Multiple tags can be provided.",
)
@click.option(
    "--untagged",
    "-u",
    multiple=True,
    help="Download episodes that have NOT been tagged. Multiple tags can be provided.",
)
@click.option(
    "--podcast-tagged",
    "-pt",
    multiple=True,
    help="Download episodes for podcasts that have been tagged. "
    "Multiple tags can be provided.",
)
@click.option(
    "--podcast-untagged",
    "-up",
    multiple=True,
    help="Download episodes for podcasts that have NOT been tagged. "
    "Multiple tags can be provided.",
)
@catch_pod_store_errors
@require_store
@git_add_and_commit(
    secure_git_mode_message="Downloaded episodes.",
    commit_message_builder=download_commit_message_builder,
)
@save_store_changes
def download(
    ctx: click.Context,
    podcast: Optional[str],
    episode: Optional[int],
    tagged: Optional[List[str]],
    untagged: Optional[List[str]],
    podcast_tagged: Optional[List[str]],
    podcast_untagged: Optional[List[str]],
):
    """Download podcast episodes. Use the command options to download all new episodes,
    only new episodes for a specific podcast, only episodes with specific tags, or only
    a single episode.

    By default, only new episodes will be downloaded, but when specifying a single
    episode it will be downloaded whether or not it is marked as 'new'.
    """
    store = ctx.obj
    tagged = list(tagged or [])
    untagged = list(untagged or [])

    pod_store_filter = Filter.from_command_arguments(
        store=store,
        new_episodes=True,
        filter_for_episodes=True,
        podcast_title=podcast,
        episode_number=episode,
        tagged=tagged,
        untagged=untagged,
        podcasts_tagged=podcast_tagged,
        podcasts_untagged=podcast_untagged,
    )

    for ep in pod_store_filter.items:
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
    git = git or git_url

    if git_url:
        click.echo("Please note, this could take a minute or two...")

    store_file_name = os.getenv(
        "POD_STORE_FILE_NAME", get_default_store_file_name(gpg_id)
    )

    Store.init(
        store_path=STORE_PATH,
        store_file_name=store_file_name,
        setup_git=git,
        git_url=git_url,
        gpg_id=gpg_id,
    )

    store_file_path = os.path.join(STORE_PATH, store_file_name)
    click.echo(f"Store created: {store_file_path}")
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
    default=None,
    help="(flag): List episodes or podcasts. Defaults to `--podcasts`.",
)
@click.option(
    "-p",
    "--podcast",
    default=None,
    help="(podcast title): List only episodes for the specified podcast.",
)
@click.option(
    "-e",
    "--episode",
    type=int,
    default=None,
    help="(episode number): List a single podcast episode. "
    "Note that you must specify a podcast this episode belongs to using the "
    "`--podcast` option.",
)
@click.option(
    "--tagged",
    "-t",
    multiple=True,
    help="Filter results by tag. Multiple tags can be provided.",
)
@click.option(
    "--untagged",
    "-u",
    multiple=True,
    help="Filter results by asence of tag. Multiple tags can be provided.",
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
    episodes: Optional[bool],
    podcast: Optional[str],
    episode: Optional[int],
    tagged: Optional[List[str]],
    untagged: Optional[List[str]],
    verbose: bool,
):
    """List data from the store.

    By default, this will list podcasts that have new episodes. Adjust the output using
    the provided flags and command options.
    """
    # It is important to set the `--episodes/--podcasts` option to `None` by default,
    # rather than `False`. A null value indicates that it has not been set by
    # explicitly the user, which triggers behavior for inferring the value from other
    # command arguments.

    store = ctx.obj
    tagged = list(tagged or [])
    untagged = list(untagged or [])

    lister = Lister.from_command_arguments(
        store=store,
        new_episodes=new,
        list_episodes=episodes,
        podcast_title=podcast,
        episode_number=episode,
        tagged=tagged,
        untagged=untagged,
    )
    for msg in lister.list_items(verbose=verbose):
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
@conditional_confirmation_prompt(interactive=False, override="force")
@catch_pod_store_errors
@require_store
@git_add_and_commit(
    secure_git_mode_message="Tagged items.",
    commit_message_builder=tagger_commit_message_builder,
    action="marked",
    tag="new",
)
@save_store_changes
def mark_as_new(
    ctx: click.Context,
    podcast: Optional[str],
    interactive: bool,
    force: Optional[bool],
):
    """Add the `new` tag to a group of episodes."""
    store = ctx.obj
    tagger = Tagger.from_command_arguments(
        store=store,
        tags=["new"],
        tag_episodes=True,
        podcast_title=podcast,
        action="mark",
    )

    for msg in tagger.tag_items(interactive_mode=interactive):
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
@conditional_confirmation_prompt(interactive=False, override="force")
@catch_pod_store_errors
@require_store
@git_add_and_commit(
    secure_git_mode_message="Tagged items.",
    commit_message_builder=tagger_commit_message_builder,
    action="unmarked",
    tag="new",
)
@save_store_changes
def mark_as_old(
    ctx: click.Context,
    podcast: Optional[str],
    interactive: bool,
    force: Optional[bool],
):
    """Remove the `new` tag from a group of episodes."""
    store = ctx.obj
    tagger = Tagger.from_command_arguments(
        store=store,
        tags=["new"],
        tag_episodes=True,
        podcast_title=podcast,
        is_untagger=True,
        action="unmark",
    )

    for msg in tagger.tag_items(interactive_mode=interactive):
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
    "--tagged",
    "-t",
    multiple=True,
    help="Filter podcasts by tag. Multiple tags can be provided.",
)
@click.option(
    "--untagged",
    "-u",
    multiple=True,
    help="Filter podcasts by absence of tag. Multiple tags can be provided.",
)
@catch_pod_store_errors
@require_store
@git_add_and_commit(
    secure_git_mode_message="Refreshed podcasts.",
    commit_message_builder=refresh_commit_message_builder,
)
@save_store_changes
def refresh(
    ctx: click.Context,
    podcast: Optional[str],
    tagged: Optional[List[str]],
    untagged: Optional[List[str]],
):
    """Refresh podcast episode data from the RSS feed."""
    store = ctx.obj
    tagged = list(tagged or [])
    untagged = list(untagged or [])

    if not podcast:
        untagged.append("inactive")

    pod_store_filter = Filter.from_command_arguments(
        store=store,
        new_episodes=False,
        filter_for_episodes=False,
        podcast_title=podcast,
        tagged=tagged,
        untagged=untagged,
    )
    for podcast in pod_store_filter.items:
        click.echo(f"Refreshing {podcast.title}.")
        try:
            podcast.refresh()
        except requests.ConnectTimeout:
            click.secho("Error: timed out when reading RSS feed.", fg="red")


@cli.command()
@click.pass_context
@click.argument("podcast")
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
@git_add_and_commit(message="Removed podcast: {podcast!r}.", params=["podcast"])
@save_store_changes
def rm(ctx: click.Context, podcast: str):
    """Remove a podcast from the store. This command will NOT delete the podcast
    episodes that have been downloaded.

    PODCAST: title of podcast to remove
    """
    store = ctx.obj
    store.podcasts.delete(podcast)


@cli.command()
@click.pass_context
@click.argument("podcast")
@catch_pod_store_errors
@require_store
@git_add_and_commit(
    secure_git_mode_message="Tagged items.",
    commit_message_builder=tagger_commit_message_builder,
)
@save_store_changes
def set_active(ctx: click.Context, podcast: str):
    """Set a podcast to `active`. The RSS feed data be refreshed.

    Reverses the `set-inactive` command.

    PODCAST: title of podcast to set as 'active'
    """
    store = ctx.obj

    podcast = store.podcasts.get(podcast)
    podcast.untag("inactive")


@cli.command()
@click.pass_context
@click.argument("podcast")
@catch_pod_store_errors
@require_store
@git_add_and_commit(
    secure_git_mode_message="Tagged items.",
    commit_message_builder=tagger_commit_message_builder,
)
@save_store_changes
def set_inactive(ctx: click.Context, podcast: str):
    """Set a podcast to `inactive`. The RSS feed data will no longer be refreshed.

    PODCAST: title of podcast to set as 'inactive'
    """
    store = ctx.obj

    podcast = store.podcasts.get(podcast)
    podcast.tag("inactive")


@cli.command()
@click.pass_context
@click.option("--tag", "-t", multiple=True, required=True, help="Tags to apply.")
@click.option(
    "--untag",
    "-u",
    is_flag=True,
    help="Remove the specified tags (rather than apply them).",
)
@click.option(
    "--podcast", "-p", default=None, help="(podcast title): Tag a single podcast."
)
@click.option(
    "-e",
    "--episode",
    type=int,
    default=None,
    help="(episode number): Tag a single podcast episode. "
    "Note that you must specify a podcast this episode belongs to using the "
    "`--podcast` option.",
)
@click.option(
    "--episodes/--podcasts", default=True, help="Tag episodes or podcasts in groups."
)
@click.option(
    "--interactive/--bulk",
    default=True,
    help="Interactively determine which items to tag, or apply the tag to all items.",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Skip confirmation prompt for bulk mode actions.",
)
@conditional_confirmation_prompt(
    interactive=False, episode=None, podcast=None, override="force"
)
@catch_pod_store_errors
@require_store
@git_add_and_commit(
    secure_git_mode_message="Tagged items.",
    commit_message_builder=tagger_commit_message_builder,
)
@save_store_changes
def tag(
    ctx: click.Context,
    tag: List[str],
    untag: bool,
    podcast: Optional[str],
    episode: Optional[int],
    episodes: bool,
    interactive: bool,
    force: bool,
):
    """Tag (or untag) podcasts or episodes with arbitrary tags.

    By default, this command works on groups (rather than individual items). Determine
    which type of item to tag using the `--episodes` or `--podcasts` option.
    (Defaults to episodes.)

    When working in group mode, you can interactively determine which items to tag
    using the `--interactive` option, or apply the tag to all items in the group using
    the `--bulk` tag. (Defaults to interactive mode.)

    In bulk mode, a single confirmation prompt will be shown unless the user passes in
    the `--force` flag.

    It is possible to tag individual items instead using the `--podcast` and `--episode`
    options. Specify a podcast by title to tag the podcast. To tag an episode, specify
    the podcast by title and then specify the episode by episode number.
    """
    tag_episodes = bool(not podcast or episode) and bool(episodes or episode)
    store = ctx.obj
    tagger = Tagger.from_command_arguments(
        store=store,
        tags=tag,
        tag_episodes=tag_episodes,
        podcast_title=podcast,
        episode_number=episode,
        is_untagger=untag,
    )
    for msg in tagger.tag_items(interactive_mode=interactive):
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


def main() -> None:
    """Run the Click application."""
    cli()


if __name__ == "__main__":
    main()
