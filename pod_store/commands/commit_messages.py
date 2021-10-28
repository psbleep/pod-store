from typing import List, Optional


DOWNLOAD_COMMIT_MESSAGE_TEMPLATE = "Downloaded new episodes{tags} for {podcast}."
REFRESH_COMMIT_MESSAGE_TEMPLATE = "Refreshed {podcast}{tags}."


def default_commit_message_builder(
    ctx_params: dict, message: str, params: Optional[List[str]] = None
) -> str:
    """Helper to build `git` commit messages from the Click command context.

    `message` should be the intended `git` commit message.

    If `message` is a template string, `params` acts as a list of Click context
    param names that will be passed to the `message` template string as
    keyword arguments.

    Example:

        default_commit_message_builder(
            ctx_params={"thing": "world"},
            message="Hello {thing}.",
            params=["thing"]
        )

    Output:

        Hello world.

    See the `git_add_and_commit` decorator for more information.
    """
    params = params or []
    message_kwargs = {p: ctx_params[p] for p in params}
    return message.format(**message_kwargs)


def download_commit_message_builder(ctx_params: dict) -> str:
    """Builds a `git` commit message for when downloads are run.

    Specifies whether downloads were run for all podcasts or just a certain podcast,
    and any tag lookups that were used.
    """
    tag_list = ctx_params.get("tag")
    if tag_list:
        tag_msg = ", ".join(tag_list)
        if ctx_params.get("is_tagged"):
            qualifier = "with"
        else:
            qualifier = "without"
        tags = f" {qualifier} tags {tag_msg!r}"
    else:
        tags = ""

    podcast_name = ctx_params.get("podcast")
    if podcast_name:
        podcast = f"{podcast_name!r}"
    else:
        podcast = "all podcasts"

    return DOWNLOAD_COMMIT_MESSAGE_TEMPLATE.format(tags=tags, podcast=podcast)


def refresh_commit_message_builder(ctx_params: dict) -> str:
    """Builds a `git` commit message for refreshing podcast data from RSS.

    Specifies whether downloads were run for all podcasts or just a certain podcast,
    and any tag lookups that were used.
    """
    podcast_name = ctx_params.get("podcast")
    if podcast_name:
        podcast = f"{podcast_name!r}"
    else:
        podcast = "all podcasts"

    tag_list = ctx_params.get("tag")
    if tag_list:
        tag_msg = ", ".join(tag_list)
        if ctx_params.get("is_tagged"):
            qualifier = "with"
        else:
            qualifier = "without"
        tags = f" {qualifier} tags: {tag_msg!r}"
    else:
        tags = ""

    return REFRESH_COMMIT_MESSAGE_TEMPLATE.format(podcast=podcast, tags=tags)
