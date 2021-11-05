"""Tagging episodes and podcasts."""
from abc import ABC, abstractmethod, abstractstaticmethod
from typing import List, Optional, Tuple, Union

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
    "{episode.podcast.title} -> [{episode.episode_number}] {episode.title}."
)

TAGGED_PODCAST_MESSAGE_TEMPLATE = (
    "{capitalized_performed_action} as {tag!r}: {podcast.title}."
)


class BaseTagger(ABC):
    """Base class for the different tagger classes.

    Tagger classes encapsulate logic about how to perform a tagging action.
    The main tagging actions are 'tagging' and 'untagging'.

    Instances of a tagger class provide details about what language to use in reporting
    on actions to the user. Examples include 'tagging' vs 'marking' (which are the same
    action, but presented using different language.

    Examples are provided to help clarify the attributes used to construct output:

    action: mark
    capitalized_action: Mark
    performing_action: marking
    capitalized_performing_action: Marking
    performed_action: marked
    capitalized_performed_action: Marked

    default_tag: str (optional)
        if provided, by default the tagger will work with this tag
    """

    def __init__(
        self,
        action: str,
        performing_action: str = None,
        performed_action: str = None,
        default_tag: Optional[str] = None,
    ) -> None:
        self.action = action
        self.capitalized_action = action.capitalize()
        self.performing_action = performing_action or f"{self.action}ing"
        self.capitalized_performing_action = self.performing_action.capitalize()
        self.performed_action = performed_action or f"{self.action}ed"
        self.capitalized_performed_action = self.performed_action.capitalize()

        self.default_tag = default_tag

    def tag_episode(self, episode: Episode, tag: Optional[str] = None) -> str:
        """Tag an episode and return output to the user.

        If no tag is provided and the tagger has a `default_tag` attribute, that will
        be used.
        """
        tag = tag or self.default_tag
        self._tag_item(episode, tag)
        return TAGGED_EPISODE_MESSAGE_TEMPLATE.format(
            capitalized_performed_action=self.capitalized_performed_action,
            tag=tag,
            episode=episode,
        )

    def tag_podcast(self, podcast: Podcast, tag: Optional[str] = None) -> str:
        """Tag a podcast and return output to the user.

        If no tag is provided and the tagger has a `default_tag` attribute, that will
        be used.
        """
        tag = tag or self.default_tag
        self._tag_item(podcast, tag)
        return TAGGED_PODCAST_MESSAGE_TEMPLATE.format(
            capitalized_performed_action=self.capitalized_performed_action,
            tag=tag,
            podcast=podcast,
        )

    def tag_podcast_episodes(
        self,
        podcasts: List[Podcast],
        tag: Optional[str] = None,
        interactive_mode: bool = False,
    ) -> str:
        """Tag a group of podcast episodes and return output to the user.

        If no tag is provided and the tagger has a `default_tag` attribute, that will
        be used.

        If the `interactive_mode` flag is set, the user will be prompted to decide
        which episodes to tag or not.
        """
        tag = tag or self.default_tag

        if interactive_mode:
            yield INTERACTIVE_MODE_HELP_MESSAGE_TEMPLATE.format(
                capitalized_performing_action=self.capitalized_performing_action,
                action=self.action,
                performing_action=self.performing_action,
                tag=tag,
            )

        for podcast in podcasts:
            for episode in podcast.episodes.list(
                **self._get_podcast_episode_tag_filters(tag)
            ):
                if interactive_mode:
                    # The user can opt to switch from interactive mode. As such, the
                    # method for handling an episode interactively returns tuple:
                    #
                    #     (bool, str)
                    #
                    # Where the bool indicates whether to continue in interactive mode
                    # and the str is the message that will be displayed to the user.
                    interactive_mode, msg = self._handle_episode_interactively(
                        episode, tag=tag
                    )
                else:
                    msg = self.tag_episode(episode, tag=tag)
                yield msg

    @abstractstaticmethod
    def _get_podcast_episode_tag_filters(tag: str) -> dict:
        pass

    def _handle_episode_interactively(
        self, episode: Episode, tag: str, interactive_mode: bool = True
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
            INTERACTIVE_MODE_PROMPT_MESSAGE_TEMPLATE.format(
                episode=episode,
                tag=tag,
                capitalized_action=self.capitalized_action,
            )
        )
        if result == "y":
            msg = self.tag_episode(episode, tag) + "\n"
        elif result == "q":
            raise click.Abort()
        elif result == "b":
            interactive_mode = False
            msg = "Switching to 'bulk' mode.\n" + self.tag_episode(episode, tag)
        else:
            msg = ""

        return interactive_mode, msg

    @abstractmethod
    def _tag_item(self, item: Union[Episode, Podcast], tag: str):
        pass


class Tagger(BaseTagger):
    """Applies tags to store items."""

    @staticmethod
    def _get_podcast_episode_tag_filters(tag: str) -> dict:
        """Build the filter dict for looking up episodes.

        Since we are applying the tag, we want to look for episodes that do not have it.
        """
        return {tag: False}

    def _tag_item(self, item: Union[Episode, Podcast], tag: str) -> None:
        """Apply the tag to a store item."""
        item.tag(tag)


class Untagger(BaseTagger):
    """Removes tags from store items."""

    @staticmethod
    def _get_podcast_episode_tag_filters(tag: str):
        """Build the filter dict for looking up episodes.

        Since we are removing the tag, we want to look for episodes that already have
        it.
        """
        return {tag: True}

    def _tag_item(self, item: Union[Episode, Podcast], tag: str):
        """Remove the tag from a store item."""
        item.untag(tag)


# These instances of the tagger classes are used to customize the language used in
# displaying output to the user. The marker/unmarker objects also work with a default
# tag.
marker = Tagger(action="mark", default_tag="new")
tagger = Tagger(action="tag", performing_action="tagging", performed_action="tagged")

unmarker = Untagger(action="unmark", default_tag="new")
untagger = Untagger(
    action="untag", performing_action="untagging", performed_action="untagged"
)
