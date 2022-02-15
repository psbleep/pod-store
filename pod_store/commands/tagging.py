"""Tagging episodes and podcasts."""
from typing import Any, Callable, List, Optional, Tuple

import click

from ..store import Store
from .filtering import Filter

TAG_EPISODES_INTERACTIVE_MODE_HELP_MESSAGE_TEMPLATE = """{presenter.capitalized_performing_action} in interactive mode. Options are:

    h = help (display this message)
    y = yes ({presenter.action} this episode as {presenter.tag_listing}
    n = no (do not {presenter.action} this episode as {presenter.tag_listing}
    b = bulk ({presenter.action} this and all following episodes as {presenter.tag_listing}
    q = quit (stop {presenter.performing_action} episodes and quit)
"""  # noqa: E501

TAG_PODCASTS_INTERACTIVE_MODE_HELP_MESSAGE_TEMPLATE = """{presenter.capitalized_performing_action} in interactive mode. Options are:

    h = help (display this message)
    y = yes ({presenter.action} this podcast as {presenter.tag_listing}
    n = no (do not {presenter.action} this podcast as {presenter.tag_listing}
    b = bulk ({presenter.action} this and all following podcasts as {presenter.tag_listing}
    q = quit (stop {presenter.performing_action} podcasts and quit)
"""  # noqa: E501


TAG_EPISODES_INTERACTIVE_MODE_PROMPT_MESSAGE_TEMPLATE = (
    "{item.podcast.title} -> [{item.episode_number}] {item.title}\n"
    "{item.short_description}\n\n"
    "{presenter.capitalized_action} as {presenter.tag_listing}?"
)

TAG_PODCASTS_INTERACTIVE_MODE_PROMPT_MESSAGE_TEMPLATE = (
    "{presenter.capitalized_action} {item.title} as {presenter.tag_listing}?"
)


TAGGED_EPISODE_MESSAGE_TEMPLATE = (
    "{presenter.capitalized_performed_action} as {presenter.tag_listing}: "
    "{item.podcast.title} -> [{item.padded_episode_number}] {item.title}."
)

TAGGED_PODCAST_MESSAGE_TEMPLATE = (
    "{presenter.capitalized_performed_action} as {presenter.tag_listing}: {item.title}."
)


class StopBulkTagging(Exception):
    pass


interactive_mode_prompt_choices = click.Choice(["h", "y", "n", "b", "q"])


def apply_tags(tags: List[str], item: Any) -> None:
    """Apply a list of tags to an item in the store.

    Used to compose a `Tagger` object. See the `Tagger.tagging_action` parameter.
    """
    for tag in tags:
        item.tag(tag)


def remove_tags(tags: List[str], item: Any) -> None:
    """Remove a list of tags from an item  in the store.

    Used to compose a `Tagger` object. See the `Tagger.tagging_action` parameter.
    """
    for tag in tags:
        item.untag(tag)


class TaggerPresenter:
    """Stores information about how to present tagger activities to the user.

    tagged_message_template: str
        string template for output when an item has been tagged

    tag_listing: str
        comma-separated list of tags that have been applied

    action: str
        what the tagger does (default: 'tag')

    performing_action: str
        what the tagger is doing (default: 'tagging')

    performed_action: str
        what the tagger has done (default: 'tagged')

    interactive_mode_help_message_template: str
        string template for showing the user a help message in interactive tagging mode

    interactive_mode_prompt_message_template: str
        string template for prompting the user whether to tag an item in interactive
        mode
    """

    def __init__(
        self,
        tagged_message_template: str,
        tag_listing: str,
        action: str,
        performing_action: str,
        performed_action: str,
        interactive_mode_help_message_template: Optional[str] = None,
        interactive_mode_prompt_message_template: Optional[str] = None,
    ) -> None:
        self.tagged_message_template = tagged_message_template
        self.tag_listing = tag_listing

        self.action = action
        self.capitalized_action = action.capitalize()
        self.performing_action = performing_action
        self.capitalized_performing_action = self.performing_action.capitalize()
        self.performed_action = performed_action
        self.capitalized_performed_action = self.performed_action.capitalize()

        self.interactive_mode_help_message_template = (
            interactive_mode_help_message_template
        )
        self.interactive_mode_prompt_message_template = (
            interactive_mode_prompt_message_template
        )

    @classmethod
    def from_command_arguments(
        cls,
        is_untagger: bool,
        tag_episodes: bool,
        tags: List[str],
        tagged_message_template: Optional[str] = None,
        action: Optional[str] = None,
        performing_action: Optional[str] = None,
        performed_action: Optional[str] = None,
        interactive_mode_help_message_template: Optional[str] = None,
        interactive_mode_prompt_message_template: Optional[str] = None,
    ):
        """Converts the arguments passed into a command via the CLI into a tagger
        presenter, accepting specified custom arguments for most things but
        providing defaults where custom output is not needed.
        """
        tag_listing = ", ".join(tags)
        if not action:
            action, performing_action, performed_action = cls.get_actions(is_untagger)
        else:
            performing_action = performing_action or f"{action}ing"
            performed_action = performed_action or f"{action}ed"
        tagged_message_template = (
            tagged_message_template
            or cls.get_tagged_message_template(tag_episodes=tag_episodes)
        )

        help_message_template = (
            interactive_mode_help_message_template
            or cls.get_interactive_mode_help_message_template(tag_episodes=tag_episodes)
        )
        prompt_message_template = (
            interactive_mode_prompt_message_template
            or cls.get_interactive_mode_prompt_message_template(
                tag_episodes=tag_episodes
            )
        )
        return cls(
            tagged_message_template=tagged_message_template,
            tag_listing=tag_listing,
            action=action,
            performing_action=performing_action,
            performed_action=performed_action,
            interactive_mode_help_message_template=help_message_template,
            interactive_mode_prompt_message_template=prompt_message_template,
        )

    @staticmethod
    def get_actions(is_untagger: bool) -> str:
        if is_untagger:
            return "untag", "untagging", "untagged"
        else:
            return "tag", "tagging", "tagged"

    @staticmethod
    def get_tagged_message_template(tag_episodes: bool) -> str:
        if tag_episodes:
            return TAGGED_EPISODE_MESSAGE_TEMPLATE
        else:
            return TAGGED_PODCAST_MESSAGE_TEMPLATE

    @staticmethod
    def get_interactive_mode_help_message_template(tag_episodes: bool) -> str:
        if tag_episodes:
            return TAG_EPISODES_INTERACTIVE_MODE_HELP_MESSAGE_TEMPLATE
        else:
            return TAG_PODCASTS_INTERACTIVE_MODE_HELP_MESSAGE_TEMPLATE

    @staticmethod
    def get_interactive_mode_prompt_message_template(tag_episodes: bool) -> str:
        if tag_episodes:
            return TAG_EPISODES_INTERACTIVE_MODE_PROMPT_MESSAGE_TEMPLATE
        else:
            return TAG_PODCASTS_INTERACTIVE_MODE_PROMPT_MESSAGE_TEMPLATE


class Tagger:
    """Performs tagging operations (e.g. tagging, untagging) on groups of items from
    the store.

    tags (list): list of tags to apply the tagging action to
    filter (Filter): collection of store items (podcasts or episodes)
    presenter (TaggerPresenter): handles logic about presenting output to the user

    tagging_action (callable):
        function that does the tagging action (e.g. adding or removing tags).
        see the `apply_tags` and `remove_tags` functions in this module.
    """

    def __init__(
        self,
        tags: List[str],
        pod_store_filter: Filter,
        presenter: TaggerPresenter,
        tagging_action: Callable,
    ) -> None:
        self._tags = tags
        self._pod_store_filter = pod_store_filter
        self._presenter = presenter
        self._perform_tagging_action = tagging_action

    @classmethod
    def from_command_arguments(
        cls,
        store: Store,
        tags: List[str],
        tag_episodes: bool = False,
        podcast_title: Optional[str] = None,
        episode_number: Optional[int] = None,
        is_untagger: bool = False,
        filters: Optional[dict] = None,
        **tagger_kwargs,
    ):
        """Constructs an appropriate `Tagger` object from arguments passed into a
        command in the CLI.

        Constructs appropriate `Filter` and `TaggerPresenter` objects for use in the
        tagger, and selects with `tagging_action` function to use.
        """
        filters = filters or {}

        if is_untagger:
            filter_tagged = tags
            filter_untagged = []
        else:
            filter_tagged = []
            filter_untagged = tags

        pod_store_filter = Filter.from_command_arguments(
            store=store,
            tagged=filter_tagged,
            untagged=filter_untagged,
            filter_for_episodes=tag_episodes,
            podcast_title=podcast_title,
            episode_number=episode_number,
            **filters,
        )

        if tag_episodes is None:
            tag_episodes = tag_episodes or podcast_title

        presenter = TaggerPresenter.from_command_arguments(
            is_untagger=is_untagger,
            tag_episodes=tag_episodes,
            tags=tags,
            **tagger_kwargs,
        )

        if is_untagger:
            tagging_action = remove_tags
        else:
            tagging_action = apply_tags

        return cls(
            pod_store_filter=pod_store_filter,
            tags=tags,
            presenter=presenter,
            tagging_action=tagging_action,
        )

    def tag_items(self, interactive_mode: bool = False):
        """Perform the tagging action on the collection of items.

        If the `intercative_mode` flag is set, the user will be prompted interactively
        to choose which items to tag or untag.
        """
        if interactive_mode:
            yield self._presenter.interactive_mode_help_message_template.format(
                presenter=self._presenter
            )
        for item in self._pod_store_filter.items:
            try:
                if interactive_mode:
                    interactive_mode, msg = self._handle_item_interactively(item)
                else:
                    msg = self._tag_item(item)
                yield msg
            except StopBulkTagging:
                return

    def _handle_item_interactively(
        self, item: Any, interactive_mode: bool = True
    ) -> Tuple[bool, str]:
        """Prompt the user to decide:

        - display a help message
        - tag the episode
        - do not tag the episode
        - switch away from interactive mode and tag all the remaining episodes
        - quit

        Returns a tuple with a bool indicating whether to continue in interactive mode
        and a message to display to the user.
        """
        result = click.prompt(
            self._presenter.interactive_mode_prompt_message_template.format(
                presenter=self._presenter, item=item
            ),
            type=interactive_mode_prompt_choices,
        )
        if result == "h":
            click.echo(
                self._presenter.interactive_mode_help_message_template.format(
                    presenter=self._presenter
                )
            )
            return self._handle_item_interactively(item)
        elif result == "y":
            msg = self._tag_item(item)
        elif result == "q":
            raise StopBulkTagging()
        elif result == "b":
            interactive_mode = False
            msg = "Switching to 'bulk' mode.\n" + self._tag_item(item)
        else:
            msg = ""

        return interactive_mode, msg

    def _tag_item(self, item: Any) -> str:
        """Apply the tagging action to an item from the store.

        Run the `tagging_action` command passed in when the tagger object was
        constructed.

        Return output to the user from the presenter object to indicate that the action
        was performed.
        """
        self._perform_tagging_action(tags=self._tags, item=item)
        return self._presenter.tagged_message_template.format(
            presenter=self._presenter, item=item
        )

    def __repr__(self) -> str:
        return "<Tagger>"
