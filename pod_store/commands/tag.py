TAG_COMMIT_MESSAGE = "{action} {target} -> {tag}."


def tag_commit_message_builder(ctx_params: dict, action: str) -> str:
    """Builds a `git` commit message for tagging/untagging a podcast or episode.

    Specifies what was tagged/untagged and the tag used.

    Pass in the `action` string to indicate whether things are being tagged or untagged.
    """
    action = action.capitalize()

    podcast_title = ctx_params.get("podcast")
    target = f"podcast {podcast_title!r}"
    episode_id = ctx_params.get("episode")
    if episode_id:
        target = f"{target}, episode {episode_id!r}"
    tag = ctx_params.get("tag")
    return TAG_COMMIT_MESSAGE.format(action=action, target=target, tag=tag)
