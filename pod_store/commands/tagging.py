from abc import ABC, abstractmethod
from typing import List, Union

import click

from ..episodes import Episode
from ..podcasts import Podcast

INTERACTIVE_MODE_HELP_MESSAGE_TEMPLATE = """{capitalized_performing_action} in interactive mode. Options are:

    y = yes ({action} this episode as {tag!r})
    n = no (do not {action} this episode as {tag!r})
    b = bulk ({action} this and all following episodes as {tag!r})
    q = quit (stop {performing_action} episodes and quit)
"""


INTERACTIVE_MODE_PROMPT_MESSAGE_TEMPLATE = (
    "{episode.podcast.title} -> [{episode.episode_number}] {episode.title}\n"
    "{episode.short_description}\n\n"
    "{capitalized_action} as {tag!r}?"
)

TAGGED_EPISODE_MESSAGE_TEMPLATE = (
    "{capitalized_performed_action} as {tag!r}: "
    "{episode.podcast.title} -> [{episode.episode_number}] {episode.title}"
)


class BaseTagger(ABC):
    def __init__(
        self,
        action: str,
        performing_action: str = None,
        performed_action: str = None,
    ) -> None:
        self._action = action
        self._capitalized_action = action.capitalize()
        self._performing_action = performing_action or f"{self._action}ing"
        self._capitalized_performing_action = self._performing_action.capitalize()
        self._performed_action = performed_action or f"{self._action}ed"
        self._capitalized_performed_action = self._performed_action.capitalize()

    def tag_podcast_episodes(
        self,
        podcasts: List[Podcast],
        tag: str,
        interactive_mode: bool = False,
    ) -> str:
        if interactive_mode:
            yield INTERACTIVE_MODE_HELP_MESSAGE_TEMPLATE.format(
                capitalized_performing_action=self._capitalized_performing_action,
                action=self._action,
                performing_action=self._performing_action,
                tag=tag,
            )

        for podcast in podcasts:
            for episode in podcast.episodes.list(**self._get_tag_filters(tag)):
                if interactive_mode:
                    interactive_mode, msg = self._handle_episode_interactively(
                        episode, tag=tag
                    )
                else:
                    msg = self.tag_episode(episode, tag=tag)
                yield msg

    def _handle_episode_interactively(
        self, episode: Episode, tag: str, interactive_mode: bool = True
    ):
        result = click.prompt(
            INTERACTIVE_MODE_PROMPT_MESSAGE_TEMPLATE.format(
                episode=episode,
                tag=tag,
                capitalized_action=self._capitalized_action,
            )
        )
        if result == "y":
            msg = self.tag_episode(episode, tag)
        elif result == "q":
            raise click.Abort()
        elif result == "b":
            interactive_mode = False
            msg = "Switching to 'bulk' mode.\n" + self.tag_episode(episode, tag)
        else:
            msg = ""

        return interactive_mode, msg

    def tag_episode(self, episode: Episode, tag: str):
        self._tag_item(episode, tag)
        return TAGGED_EPISODE_MESSAGE_TEMPLATE.format(
            capitalized_performed_action=self._capitalized_performed_action,
            tag=tag,
            episode=episode,
        )

    @abstractmethod
    def _tag_item(self, item: Union[Episode, Podcast], tag: str):
        pass


class Tagger(BaseTagger):
    def _get_tag_filters(self, tag: str):
        return {tag: False}

    def _tag_item(self, item: Union[Episode, Podcast], tag: str):
        item.tag(tag)


class Untagger(BaseTagger):
    def _get_tag_filters(self, tag: str):
        return {tag: True}

    def _tag_item(self, item: Union[Episode, Podcast], tag: str):
        item.untag(tag)
