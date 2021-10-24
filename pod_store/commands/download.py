"""Helpers for the `download` Click command defined in `__main__`

Includes a commit message builder function.
"""
DOWNLOAD_COMMIT_MESSAGE = "Downloaded {podcasts} new podcast episodes{tags}."


def download_commit_message_builder(ctx_params: dict) -> str:
    """Builds a `git` commit message for when downloads are run.

    Specifies whether downloads were run for all podcasts or just a certain podcast,
    and any tag lookups that were used.
    """
    podcast_name = ctx_params.get("podcast")
    if podcast_name:
        podcasts = f"{podcast_name!r}:"
    else:
        podcasts = "all"

    tag_list = ctx_params.get("tag")
    if tag_list:
        tag_msg = ", ".join(tag_list)
        if ctx_params.get("is_tagged"):
            qualifier = "with"
        else:
            qualifier = "without"
        tags = f" {qualifier} tags -> {tag_msg}"
    else:
        tags = ""

    return DOWNLOAD_COMMIT_MESSAGE.format(podcasts=podcasts, tags=tags)
