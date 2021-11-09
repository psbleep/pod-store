from pod_store.commands.commit_messages import (
    default_commit_message_builder,
    download_commit_message_builder,
    refresh_commit_message_builder,
    tagger_commit_message_builder,
)


def test_default_commit_message_builder_simple_message():
    assert (
        default_commit_message_builder(ctx_params={}, message="hello world")
        == "hello world"
    )


def test_default_commit_message_builder_format_template_from_click_params():
    ctx_params = {"thing": "foo", "other_thing": "bar"}
    message = "hello {thing}, not {other_thing}"
    assert (
        default_commit_message_builder(
            ctx_params=ctx_params, message=message, params=["thing", "other_thing"]
        )
        == "hello foo, not bar"
    )


def test_download_commit_message_builder_for_all_podcasts():
    ctx_params = {"podcast": None}
    assert (
        download_commit_message_builder(ctx_params)
        == "Downloaded new episodes for all podcasts."
    )


def test_download_commit_message_builder_for_tagged_episodes_in_all_podcasts():
    ctx_params = {"podcast": None, "tag": ["hello", "world"], "is_tagged": True}
    assert (
        download_commit_message_builder(ctx_params)
        == "Downloaded new episodes with tags 'hello, world' for all podcasts."
    )


def test_download_commit_message_builder_for_not_tagged_episodes_in_all_podcasts():
    ctx_params = {"podcast": None, "tag": ["hello", "world"], "is_tagged": False}
    assert download_commit_message_builder(ctx_params) == (
        "Downloaded new episodes without tags 'hello, world' for all podcasts."
    )


def test_download_commit_message_builder_for_single_podcast():
    ctx_params = {"podcast": "foo"}
    assert (
        download_commit_message_builder(ctx_params)
        == "Downloaded new episodes for 'foo'."
    )


def test_download_commit_message_builder_tagged_episodes_for_single_podcast():
    ctx_params = {"podcast": "foo", "tag": ["zoo", "bar"], "is_tagged": True}
    assert (
        download_commit_message_builder(ctx_params)
        == "Downloaded new episodes with tags 'zoo, bar' for 'foo'."
    )


def test_download_commit_message_builder_untagged_episodes_for_single_podcast():
    ctx_params = {"podcast": "foo", "tag": ["zoo", "bar"], "is_tagged": False}
    assert (
        download_commit_message_builder(ctx_params)
        == "Downloaded new episodes without tags 'zoo, bar' for 'foo'."
    )


def test_refresh_commit_message_builder_for_all_podcasts():
    ctx_params = {"podcast": None}
    assert refresh_commit_message_builder(ctx_params) == "Refreshed all podcasts."


def test_refresh_commit_message_builder_for_all_tagged_podcasts():
    ctx_params = {"podcast": None, "tag": ["foo", "bar"], "is_tagged": True}
    assert (
        refresh_commit_message_builder(ctx_params)
        == "Refreshed all podcasts with tags: 'foo, bar'."
    )


def test_refresh_commit_message_builder_for_all_podcasts_without_tags():
    ctx_params = {"podcast": None, "tag": ["foo", "bar"], "is_tagged": False}
    assert (
        refresh_commit_message_builder(ctx_params)
        == "Refreshed all podcasts without tags: 'foo, bar'."
    )


def test_refresh_commit_message_builder_for_single_podcast():
    ctx_params = {"podcast": "foobar"}
    assert refresh_commit_message_builder(ctx_params) == "Refreshed 'foobar'."


def test_tagger_commit_message_builder_for_single_podcast():
    assert (
        tagger_commit_message_builder(
            ctx_params={"podcast": "greetings", "episode": None, "tag": "blessed"},
            action="chosen",
        )
        == "Chosen podcast 'greetings' -> 'blessed'."
    )


def test_tagger_commit_message_builder_for_single_episode():
    assert (
        tagger_commit_message_builder(
            ctx_params={"podcast": "greetings", "episode": "aaa", "tag": "blessed"},
            action="chosen",
        )
        == "Chosen 'greetings', episode 'aaa' -> 'blessed'."
    )


def test_tagger_commit_message_builder_for_podcast_episodes_all_podcasts():
    assert (
        tagger_commit_message_builder(
            ctx_params={"podcast": None, "tag": "blessed"},
            action="chosen",
        )
        == "Chosen all podcast episodes -> 'blessed'."
    )


def test_tagger_commit_message_builder_for_podcast_episodes_single_podcast():
    assert (
        tagger_commit_message_builder(
            ctx_params={"podcast": "greetings", "tag": "blessed"}, action="chosen"
        )
        == "Chosen 'greetings' podcast episodes -> 'blessed'."
    )


def test_tagger_commit_message_builder_for_podcast_interactive_mode():
    assert (
        tagger_commit_message_builder(
            ctx_params={"podcast": None, "tag": "blessed", "interactive": True},
            action="chosen",
        )
        == "Chosen all podcast episodes -> 'blessed' in interactive mode."
    )


def test_tagger_commit_message_builder_accepts_tag_passed_in_to_decorator():
    assert (
        tagger_commit_message_builder(
            ctx_params={"podcast": "greetings", "episode": None},
            action="chosen",
            tag="foo",
        )
        == "Chosen podcast 'greetings' -> 'foo'."
    )
