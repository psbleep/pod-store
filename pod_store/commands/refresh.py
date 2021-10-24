"""Helpers for the `refresh` Click command defined in `__main__`

Includes a commit message builder function.
"""
REFRESH_COMMIT_MESSAGE = "Refreshed {podcasts} podcast {quantifier}{tags}."


def refresh_commit_message_builder(ctx_params: dict) -> str:
    """Builds a `git` commit message for refreshing podcast data from RSS.

    Specifies whether downloads were run for all podcasts or just a certain podcast,
    and any tag lookups that were used.
    """
    podcast_name = ctx_params.get("podcast")
    if podcast_name:
        podcasts = f"{podcast_name!r}"
        quantifier = "feed"
    else:
        podcasts = "all"
        quantifier = "feeds"

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

    return REFRESH_COMMIT_MESSAGE.format(
        podcasts=podcasts, quantifier=quantifier, tags=tags
    )
