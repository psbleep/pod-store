import click

from typing import List

from .episodes import Episode
from .podcasts import Podcast

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


class PodcastEpisodeTagger:
    def __init__(
        self,
        action: str,
        tag: str,
        interactive_mode: bool,
        performing_action: str = None,
        performed_action: str = None,
        is_untagger: bool = False,
    ) -> None:
        self._action = action
        self._capitalized_action = action.capitalize()
        self._performing_action = performing_action or f"{self._action}ing"
        self._capitalized_performing_action = self._performing_action.capitalize()
        self._performed_action = performed_action or f"{self._action}ed"
        self._capitalized_performed_action = self._performed_action.capitalize()

        self._tag = tag
        self._interactive_mode = interactive_mode
        self._is_untagger = is_untagger

    def tag_podcast_episodes(self, podcasts: List[Podcast]) -> str:
        if self._interactive_mode:
            yield INTERACTIVE_MODE_HELP_MESSAGE_TEMPLATE.format(
                capitalized_performing_action=self._capitalized_performing_action,
                action=self._action,
                performing_action=self._performing_action,
                tag=self._tag,
            )

        for podcast in podcasts:
            for episode in podcast.episodes.list(**{self._tag: self._is_untagger}):
                yield self._handle_episode(episode)

    def _handle_episode(self, episode: Episode):
        if self._interactive_mode:
            return self._handle_episode_interactively(episode)
        return self._tag_episode(episode)

    def _handle_episode_interactively(self, episode: Episode):
        result = click.prompt(
            INTERACTIVE_MODE_PROMPT_MESSAGE_TEMPLATE.format(
                episode=episode,
                capitalized_action=self._capitalized_action,
                tag=self._tag,
            )
        )
        if result == "y":
            return self._tag_episode(episode)
        elif result == "q":
            raise click.Abort()
        elif result == "b":
            self._interactive_mode = False
            return "Switching to 'bulk' mode.\n" + self._tag_episode(episode)
        else:
            return ""

    def _tag_episode(self, episode: Episode):
        if self._is_untagger:
            episode.untag(self._tag)
        else:
            episode.tag(self._tag)
        return TAGGED_EPISODE_MESSAGE_TEMPLATE.format(
            capitalized_performed_action=self._capitalized_performed_action,
            tag=self._tag,
            episode=episode,
        )
