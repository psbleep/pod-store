import pytest

from pod_store.commands.filtering import EpisodeFilter, PodcastFilter
from pod_store.commands.tagging import (
    TAG_EPISODES_INTERACTIVE_MODE_HELP_MESSAGE_TEMPLATE,
    TAG_EPISODES_INTERACTIVE_MODE_PROMPT_MESSAGE_TEMPLATE,
    TAG_PODCASTS_INTERACTIVE_MODE_HELP_MESSAGE_TEMPLATE,
    TAG_PODCASTS_INTERACTIVE_MODE_PROMPT_MESSAGE_TEMPLATE,
    TAGGED_EPISODE_MESSAGE_TEMPLATE,
    TAGGED_PODCAST_MESSAGE_TEMPLATE,
    Tagger,
    TaggerPresenter,
    apply_tags,
    interactive_mode_prompt_choices,
    remove_tags,
)

MESSAGE_TEMPLATE = (
    "{presenter.capitalized_performing_action} the following tag(s) for {item.title}: "
    "{presenter.tag_listing}."
)

HELP_MESSAGE_TEMPLATE = "{presenter.capitalized_action} the podcasts."

PROMPT_MESSAGE_TEMPLATE = (
    "{presenter.capitalized_action} {item.title} with tag(s) {presenter.tag_listing}?"
)


@pytest.fixture
def tagger(store):
    pod_store_filter = PodcastFilter(store=store, new_episodes=True)
    presenter = TaggerPresenter(
        tagged_message_template=MESSAGE_TEMPLATE,
        tag_listing="foo",
        action="choose",
        performing_action="choosing",
        performed_action="chosen",
        interactive_mode_help_message_template=HELP_MESSAGE_TEMPLATE,
        interactive_mode_prompt_message_template=PROMPT_MESSAGE_TEMPLATE,
    )
    return Tagger(
        tags=["foo"],
        pod_store_filter=pod_store_filter,
        presenter=presenter,
        tagging_action=apply_tags,
    )


def test_tagger_presenter_from_command_arguments_default_podcast_tagger():
    presenter = TaggerPresenter.from_command_arguments(
        tag_episodes=False, is_untagger=False, tags=["hello", "world"]
    )
    assert presenter.tagged_message_template == TAGGED_PODCAST_MESSAGE_TEMPLATE
    assert presenter.tag_listing == "hello, world"
    assert presenter.action == "tag"
    assert presenter.performing_action == "tagging"
    assert presenter.performed_action == "tagged"
    assert (
        presenter.interactive_mode_help_message_template
        == TAG_PODCASTS_INTERACTIVE_MODE_HELP_MESSAGE_TEMPLATE
    )
    assert (
        presenter.interactive_mode_prompt_message_template
        == TAG_PODCASTS_INTERACTIVE_MODE_PROMPT_MESSAGE_TEMPLATE
    )


def test_tagger_presenter_from_command_arguments_default_episode_tagger():
    presenter = TaggerPresenter.from_command_arguments(
        tag_episodes=True, is_untagger=False, tags=["hello", "world"]
    )
    assert presenter.tagged_message_template == TAGGED_EPISODE_MESSAGE_TEMPLATE
    assert (
        presenter.interactive_mode_help_message_template
        == TAG_EPISODES_INTERACTIVE_MODE_HELP_MESSAGE_TEMPLATE
    )
    assert (
        presenter.interactive_mode_prompt_message_template
        == TAG_EPISODES_INTERACTIVE_MODE_PROMPT_MESSAGE_TEMPLATE
    )


def test_tagger_presenter_from_command_arugments_default_untagger():
    presenter = TaggerPresenter.from_command_arguments(
        tag_episodes=False, is_untagger=True, tags=["hello", "world"]
    )
    assert presenter.action == "untag"
    assert presenter.performing_action == "untagging"
    assert presenter.performed_action == "untagged"


def test_tagger_presenter_from_command_arguments_accepts_custom_actions():
    presenter = TaggerPresenter.from_command_arguments(
        tag_episodes=False,
        is_untagger=False,
        tags=["hello", "world"],
        action="mark",
        performing_action="marking",
        performed_action="marked",
    )
    assert presenter.action == "mark"
    assert presenter.performing_action == "marking"
    assert presenter.performed_action == "marked"


def test_tagger_applies_tags_to_filter_items_and_returns_formatted_messages(
    store, tagger
):
    assert list(tagger.tag_items()) == [
        "Choosing the following tag(s) for farewell: foo.",
        "Choosing the following tag(s) for greetings: foo.",
    ]

    assert "foo" in store.podcasts.get("farewell").tags
    assert "foo" in store.podcasts.get("greetings").tags


def test_untagger_removes_tags_from_filter_items_and_returns_formatted_messages(store):
    pod_store_filter = EpisodeFilter(store=store, foo=True)
    presenter = TaggerPresenter(
        tagged_message_template=MESSAGE_TEMPLATE,
        tag_listing="foo",
        action="unchoose",
        performing_action="unchoosing",
        performed_action="unchosen",
    )
    untagger = Tagger(
        tags=["foo"],
        pod_store_filter=pod_store_filter,
        presenter=presenter,
        tagging_action=remove_tags,
    )
    assert list(untagger.tag_items()) == [
        "Unchoosing the following tag(s) for not forgotten: foo.",
        "Unchoosing the following tag(s) for goodbye: foo.",
    ]


def test_tagger_interactive_mode_tags_items_when_prompted(mocker, store, tagger):
    mocked_click_prompt = mocker.patch(
        "pod_store.commands.tagging.click.prompt", return_value="y"
    )

    assert list(tagger.tag_items(interactive_mode=True)) == [
        "Choose the podcasts.",
        "Choosing the following tag(s) for farewell: foo.",
        "Choosing the following tag(s) for greetings: foo.",
    ]

    # verify the prompt is called by checking the last call
    mocked_click_prompt.assert_called_with(
        "Choose greetings with tag(s) foo?", type=interactive_mode_prompt_choices
    )

    assert "foo" in store.podcasts.get("farewell").tags
    assert "foo" in store.podcasts.get("greetings").tags


def test_tagger_interactive_mode_does_not_tag_items_when_not_prompted(
    mocker, store, tagger
):
    mocked_click_prompt = mocker.patch(
        "pod_store.commands.tagging.click.prompt", return_value="n"
    )

    assert list(tagger.tag_items(interactive_mode=True)) == [
        "Choose the podcasts.",
        "",
        "",
    ]

    # verify the prompt is called by checking the last call
    mocked_click_prompt.assert_called_with(
        "Choose greetings with tag(s) foo?", type=interactive_mode_prompt_choices
    )

    assert "foo" not in store.podcasts.get("farewell").tags
    assert "foo" not in store.podcasts.get("greetings").tags


def test_tagger_interactive_mode_quits_when_prompted(mocker, store, tagger):
    mocked_click_prompt = mocker.patch(
        "pod_store.commands.tagging.click.prompt", return_value="q"
    )

    assert list(tagger.tag_items(interactive_mode=True)) == [
        "Choose the podcasts.",
    ]

    # verify the prompt is called by checking the last call
    mocked_click_prompt.assert_called_with(
        "Choose farewell with tag(s) foo?", type=interactive_mode_prompt_choices
    )

    assert "foo" not in store.podcasts.get("farewell").tags
    assert "foo" not in store.podcasts.get("greetings").tags


def test_tagger_interactive_mode_switches_to_bulk_mode_when_prompted(
    mocker, store, tagger
):
    mocked_click_prompt = mocker.patch(
        "pod_store.commands.tagging.click.prompt", return_value="b"
    )

    assert list(tagger.tag_items(interactive_mode=True)) == [
        "Choose the podcasts.",
        "Switching to 'bulk' mode.\n"
        "Choosing the following tag(s) for farewell: foo.",
        "Choosing the following tag(s) for greetings: foo.",
    ]

    # verify the prompt is called by checking the last call
    mocked_click_prompt.assert_called_with(
        "Choose farewell with tag(s) foo?", type=interactive_mode_prompt_choices
    )

    assert "foo" in store.podcasts.get("farewell").tags
    assert "foo" in store.podcasts.get("greetings").tags


def test_tagger_interactive_mode_displays_help_message_when_prompted(
    mocker, store, tagger
):
    mocker.patch("pod_store.commands.tagging.click.prompt", side_effect=["h", "q"])
    mocked_click_echo = mocker.patch("pod_store.commands.tagging.click.echo")

    list(tagger.tag_items(interactive_mode=True))

    mocked_click_echo.assert_called_with("Choose the podcasts.")
