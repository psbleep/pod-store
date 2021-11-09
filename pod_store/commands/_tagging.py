"""Tagging episodes and podcasts."""
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple, Union

import click
from .filtering import Filter, get_filter_from_command_arguments

from ..episodes import Episode
from ..podcasts import Podcast
from ..store import Store

TAG_EPISODES_INTERACTIVE_MODE_HELP_MESSAGE_TEMPLATE = """{tagger.capitalized_performing_action} in interactive mode. Options are:

    y = yes ({tagger.action} this episode as {tagger.tag_listing}
    n = no (do not {tagger.action} this episode as {tagger.tag_listing}
    b = bulk ({tagger.action} this and all following episodes as {tagger.tag_listing}
    q = quit (stop {tagger.performing_action} episodes and quit)
"""


TAG_EPISODES_INTERACTIVE_MODE_PROMPT_MESSAGE_TEMPLATE = (
    "{item.podcast.title} -> [{item.episode_number}] {item.title}\n"
    "{item.short_description}\n\n"
    "{tagger.capitalized_action} as {tagger.tag_listing}?"
)

TAGGED_EPISODE_MESSAGE_TEMPLATE = (
    "{tagger.capitalized_performed_action} as {tagger.tag_listing}: "
    "{item.podcast.title} -> [{item.episode_number}] {item.title}."
)

TAGGED_PODCAST_MESSAGE_TEMPLATE = (
    "{tagger.capitalized_performed_action} as {tagger.tag_listing}: {item.title}."
)


class BaseTagger(ABC):
    def __init__(
        self,
        tags: List[str],
        filter: Filter,
        action: str,
        message_template: str,
        performing_action: str = None,
        performed_action: str = None,
        interactive_mode_help_message_template: Optional[str] = None,
        interactive_mode_prompt_message_template: Optional[str] = None,
    ) -> None:
        self.action = action
        self.capitalized_action = action.capitalize()
        self.performing_action = performing_action or f"{self.action}ing"
        self.capitalized_performing_action = self.performing_action.capitalize()
        self.performed_action = performed_action or f"{self.action}ed"
        self.capitalized_performed_action = self.performed_action.capitalize()

        self._tags = tags
        self._filter = filter
        self._message_template = message_template
        self._interactive_mode_help_message_template = (
            interactive_mode_help_message_template
        )
        self._interactive_mode_prompt_message_template = (
            interactive_mode_prompt_message_template
        )

    @abstractmethod
    def _perform_tagging(self, item: Union[Episode, Podcast]) -> None:
        pass

    @property
    def tag_listing(self) -> str:
        return ", ".join(self._tags)

    def tag_items(self, interactive_mode: bool = False):
        if interactive_mode:
            yield self._interactive_mode_help_message_template.format(tagger=self)
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
            self._interactive_mode_prompt_message_template.format(
                tagger=self, item=item
            )
        )
        if result == "y":
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
        return self._message_template.format(tagger=self, item=item)


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
    tag: str,
    tag_episodes: bool = False,
    is_untagger: bool = False,
    podcast_title: Optional[str] = None,
    filters: Optional[dict] = None,
    **tagger_kwargs,
) -> Tagger:
    filters = filters or {}
    tags = [tag]
    filter = get_filter_from_command_arguments(
        store=store,
        filter_untagged_items=not is_untagger,
        tags=tags,
        filter_episodes=tag_episodes,
        podcast_title=podcast_title,
        **filters,
    )

    if tag_episodes is None:
        tag_episodes = tag_episodes or podcast_title

    tagger_kwargs = _get_tagger_kwargs(
        tag_episodes=tag_episodes,
        **tagger_kwargs,
    )

    if is_untagger:
        return Untagger(filter=filter, tags=tags, **tagger_kwargs)
    else:
        return Tagger(filter=filter, tags=tags, **tagger_kwargs)


def _get_tagger_kwargs(
    tag_episodes: bool,
    action: str,
    message_template: str = None,
    performing_action: str = None,
    performed_action: str = None,
    interactive_mode_help_message_template: Optional[str] = None,
    interactive_mode_prompt_message_template: Optional[str] = None,
) -> dict:
    message_template = message_template or _get_message_template(
        tag_episodes=tag_episodes
    )

    help_message_template = (
        interactive_mode_help_message_template
        or _get_interactive_mode_help_message_template(tag_episodes=tag_episodes)
    )
    prompt_message_template = (
        interactive_mode_prompt_message_template
        or _get_interactive_mode_prompt_message_template(tag_episodes=tag_episodes)
    )

    return {
        "action": action,
        "performing_action": performing_action,
        "performed_action": performed_action,
        "message_template": message_template,
        "interactive_mode_help_message_template": help_message_template,
        "interactive_mode_prompt_message_template": prompt_message_template,
    }


def _get_message_template(tag_episodes: bool) -> str:
    if tag_episodes:
        return TAGGED_EPISODE_MESSAGE_TEMPLATE
    else:
        return TAGGED_PODCAST_MESSAGE_TEMPLATE


def _get_interactive_mode_help_message_template(tag_episodes: bool) -> str:
    if tag_episodes:
        return TAG_EPISODES_INTERACTIVE_MODE_HELP_MESSAGE_TEMPLATE


def _get_interactive_mode_prompt_message_template(tag_episodes: bool) -> str:
    if tag_episodes:
        return TAG_EPISODES_INTERACTIVE_MODE_PROMPT_MESSAGE_TEMPLATE
