from .taggers import PodcastEpisodeTagger


MARK_NEW_INTERACTIVE_MODE_HELP = """Marking in interactive mode. Options are:

    y = yes (mark this episode as 'new')
    n = no (do not mark this episode as 'new')
    b = bulk (mark this and all following episodes as 'new')
    q = quit (stop marking episodes and quit)
"""

MARK_NEW_COMMIT_MESSAGE_TEMPLATE = (
    "{capitalized_action}ed {target} podcast episodes as 'new' in {mode} mode."
)


def mark_episodes_commit_message_builder(ctx_params: dict, action: str) -> str:
    """Builds a `git` commit message for tagging/untagging a group of episodes.

    Specifies which episodes were tagged/untagged and the tag used.

    Pass in the `action` string to indicate whether episodes are being tagged or
    untagged.
    """
    podcast_title = ctx_params.get("podcast")
    if podcast_title:
        target = f"{podcast_title!r}"
    else:
        target = "all"

    if ctx_params.get("interactive"):
        mode = "interactive"
    else:
        mode = "bulk"

    return MARK_NEW_COMMIT_MESSAGE_TEMPLATE.format(
        capitalized_action=action.capitalize(), target=target, mode=mode
    )


def get_episode_marker(interactive_mode: bool, mark_as_new: bool = True):
    if mark_as_new:
        action = "mark"
        is_untagger = False
    else:
        action = "unmark"
        is_untagger = True
    return PodcastEpisodeTagger(
        action=action,
        tag="new",
        interactive_mode=interactive_mode,
        is_untagger=is_untagger,
    )
