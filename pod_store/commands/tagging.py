"""Tagging episodes and podcasts."""
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple, Union

import click

from ..episodes import Episode
from ..podcasts import Podcast
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

interactive_mode_prompt_choices = click.Choice(["h", "y", "n", "b", "q"])


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
    ) -> dict:
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


class BaseTagger(ABC):
    def __init__(
        self,
        tags: List[str],
        filter: Filter,
        presenter: TaggerPresenter,
    ) -> None:
        self._tags = tags
        self._filter = filter
        self._presenter = presenter

    @abstractmethod
    def _perform_tagging(self, item: Union[Episode, Podcast]) -> None:
        pass

    @property
    def tag_listing(self) -> str:
        return ", ".join(self._tags)

    def tag_items(self, interactive_mode: bool = False):
        if interactive_mode:
            yield self._presenter.interactive_mode_help_message_template.format(
                presenter=self._presenter
            )
        for item in self._filter.items:
            if interactive_mode:
                interactive_mode, msg = self._handle_item_interactively(item)
            else:
                msg = self._tag_item(item)
            yield msg

    def _handle_item_interactively(
        self, item: Any, interactive_mode: bool = True
    ) -> Tuple[bool, str]:
        """Prompt the user to decide:

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
            raise click.Abort()
        elif result == "b":
            interactive_mode = False
            msg = "Switching to 'bulk' mode.\n" + self._tag_item(item)
        else:
            msg = ""

        return interactive_mode, msg

    def _tag_item(self, item: Union[Episode, Podcast]) -> str:
        self._perform_tagging(item)
        return self._presenter.tagged_message_template.format(
            presenter=self._presenter, item=item
        )


class Tagger(BaseTagger):
    """Applies tags to store items."""

    def _perform_tagging(self, item: Union[Episode, Podcast]) -> None:
        for tag in self._tags:
            item.tag(tag)

    def __repr__(self) -> str:
        return "<Tagger>"


class Untagger(BaseTagger):
    """Removes tags from store items."""

    def _perform_tagging(self, item: Union[Episode, Podcast]) -> None:
        for tag in self._tags:
            item.untag(tag)

    def __repr__(self) -> str:
        return "<Untagger>"


def get_tagger_from_command_arguments(
    store: Store,
    tags: List[str],
    tag_episodes: bool = False,
    podcast_title: Optional[str] = None,
    is_untagger: bool = False,
    filters: Optional[dict] = None,
    **kwargs,
) -> Tagger:
    """Factory for building an appropriate `Tagger` object from the CLI options passed
    in to a command.

    Builds a filter and presenter for the tagger to use.
    """
    filters = filters or {}

    if is_untagger:
        filter_tagged = tags
        filter_untagged = []
    else:
        filter_tagged = []
        filter_untagged = tags

    filter = Filter.from_command_arguments(
        store=store,
        tagged=filter_tagged,
        untagged=filter_untagged,
        filter_for_episodes=tag_episodes,
        podcast_title=podcast_title,
        **filters,
    )

    if tag_episodes is None:
        tag_episodes = tag_episodes or podcast_title

    presenter = TaggerPresenter.from_command_arguments(
        is_untagger=is_untagger, tag_episodes=tag_episodes, tags=tags, **kwargs
    )

    if is_untagger:
        return Untagger(filter=filter, tags=tags, presenter=presenter)
    else:
        return Tagger(filter=filter, tags=tags, presenter=presenter)
