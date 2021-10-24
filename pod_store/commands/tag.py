TAG_COMMIT_MESSAGE = "{action}ged {target} -> {tag}."


def tag_commit_message_builder(ctx_params: dict, action: str) -> str:
    podcast_title = ctx_params.get("podcast")
    target = f"podcast {podcast_title!r}"
    episode_id = ctx_params.get("episode")
    if episode_id:
        target = f"{target}, episode {episode_id!r}"
    tag = ctx_params.get("tag")
    return TAG_COMMIT_MESSAGE.format(action=action, target=target, tag=tag)
