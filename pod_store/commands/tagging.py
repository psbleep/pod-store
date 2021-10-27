from abc import ABC, abstractmethod, abstractstaticmethod
from typing import List, Optional, Union

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


TAGGER_COMMIT_MESSAGE_TEMPLATE = (
    "{tagger.capitalized_performed_action} {target} -> {tag!r}{mode}."
)


class BaseTagger(ABC):
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

    def tag_episode(self, episode: Episode, tag: Optional[str] = None):
        tag = tag or self.default_tag
        self._tag_item(episode, tag)
        return TAGGED_EPISODE_MESSAGE_TEMPLATE.format(
            capitalized_performed_action=self.capitalized_performed_action,
            tag=tag,
            episode=episode,
        )

    def tag_podcast(self, podcast: Podcast, tag: Optional[str] = None):
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
                    interactive_mode, msg = self._handle_episode_interactively(
                        episode, tag=tag
                    )
                else:
                    msg = self.tag_episode(episode, tag=tag)
                yield msg

    @abstractstaticmethod
    def _get_podcast_episode_tag_filters(tag: str):
        pass

    def _handle_episode_interactively(
        self, episode: Episode, tag: str, interactive_mode: bool = True
    ):
        result = click.prompt(
            INTERACTIVE_MODE_PROMPT_MESSAGE_TEMPLATE.format(
                episode=episode,
                tag=tag,
                capitalized_action=self.capitalized_action,
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

    @abstractmethod
    def _tag_item(self, item: Union[Episode, Podcast], tag: str):
        pass


class Tagger(BaseTagger):
    @staticmethod
    def _get_podcast_episode_tag_filters(tag: str):
        return {tag: False}

    def _tag_item(self, item: Union[Episode, Podcast], tag: str):
        item.tag(tag)


class Untagger(BaseTagger):
    @staticmethod
    def _get_podcast_episode_tag_filters(tag: str):
        return {tag: True}

    def _tag_item(self, item: Union[Episode, Podcast], tag: str):
        item.untag(tag)


def build_commit_message_from_tagger(ctx_params: dict, tagger: BaseTagger) -> str:
    target = _get_commit_message_target(ctx_params)
    tag = ctx_params.get("tag") or tagger.default_tag
    mode = _get_commit_message_mode(ctx_params)
    return TAGGER_COMMIT_MESSAGE_TEMPLATE.format(
        tagger=tagger, target=target, tag=tag, mode=mode
    )


def _get_commit_message_target(ctx_params: dict) -> str:
    if "podcast" in ctx_params and "episode" not in ctx_params:
        podcast = ctx_params.get("podcast")
        if podcast:
            return f"{podcast!r} podcast episodes"
        else:
            return "all podcast episodes"
    else:
        podcast = ctx_params.get("podcast")
        episode = ctx_params.get("episode")
        if episode:
            return f"{podcast!r}, episode {episode!r}"
        else:
            return f"podcast {podcast!r}"


def _get_commit_message_mode(ctx_params: dict) -> str:
    if ctx_params.get("interactive"):
        return " in interactive mode"
    else:
        return ""


marker = Tagger(action="mark", default_tag="new")
unmarker = Untagger(action="unmark", default_tag="new")
tagger = Tagger(action="tag", performing_action="tagging", performed_action="tagged")
untagger = Untagger(
    action="untag", performing_action="untagging", performed_action="untagged"
)
