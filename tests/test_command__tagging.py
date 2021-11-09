import click
import pytest

from pod_store.commands.filtering import EpisodeFilter, PodcastFilter

from pod_store.commands._tagging import Tagger, Untagger


MESSAGE_TEMPLATE = (
    "{tagger.capitalized_performing_action} the following tag(s) for {item.title}: "
    "{tagger.tag_listing}."
)

HELP_MESSAGE_TEMPLATE = "{tagger.capitalized_action} the podcasts."

PROMPT_MESSAGE_TEMPLATE = (
    "{tagger.capitalized_action} {item.title} with tag(s) {tagger.tag_listing}?"
)


@pytest.fixture
def tagger(store):
    filter = PodcastFilter(store=store, new_episodes=True)
    return Tagger(
        filter=filter,
        tags=["foo"],
        action="choose",
        performing_action="choosing",
        performed_action="chosen",
        message_template=MESSAGE_TEMPLATE,
        interactive_mode_help_message_template=HELP_MESSAGE_TEMPLATE,
        interactive_mode_prompt_message_template=PROMPT_MESSAGE_TEMPLATE,
    )


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
    filter = EpisodeFilter(store=store, foo=True)
    tagger = Untagger(
        filter=filter,
        tags=["foo"],
        action="unchoose",
        performing_action="unchoosing",
        performed_action="unchosen",
        message_template=MESSAGE_TEMPLATE,
    )
    assert list(tagger.tag_items()) == [
        "Unchoosing the following tag(s) for not forgotten: foo.",
        "Unchoosing the following tag(s) for goodbye: foo.",
    ]


def test_tagger_interactive_mode_tags_items_when_prompted(mocker, store, tagger):
    mocked_click_prompt = mocker.patch(
        "pod_store.commands._tagging.click.prompt", return_value="y"
    )

    assert list(tagger.tag_items(interactive_mode=True)) == [
        "Choose the podcasts.",
        "Choosing the following tag(s) for farewell: foo.",
        "Choosing the following tag(s) for greetings: foo.",
    ]

    # verify the prompt is called by checking the last call
    mocked_click_prompt.assert_called_with("Choose greetings with tag(s) foo?")

    assert "foo" in store.podcasts.get("farewell").tags
    assert "foo" in store.podcasts.get("greetings").tags


def test_tagger_interactive_mode_does_not_tag_items_when_not_prompted(
    mocker, store, tagger
):
    mocked_click_prompt = mocker.patch(
        "pod_store.commands._tagging.click.prompt", return_value="n"
    )

    assert list(tagger.tag_items(interactive_mode=True)) == [
        "Choose the podcasts.",
        "",
        "",
    ]

    # verify the prompt is called by checking the last call
    mocked_click_prompt.assert_called_with("Choose greetings with tag(s) foo?")

    assert "foo" not in store.podcasts.get("farewell").tags
    assert "foo" not in store.podcasts.get("greetings").tags


def test_tagger_interactive_mode_quits_when_prompted(mocker, store, tagger):
    mocked_click_prompt = mocker.patch(
        "pod_store.commands._tagging.click.prompt", return_value="q"
    )

    with pytest.raises(click.Abort):
        assert list(tagger.tag_items(interactive_mode=True)) == [
            "Choose the podcasts.",
        ]

    # verify the prompt is called by checking the last call
    mocked_click_prompt.assert_called_with("Choose farewell with tag(s) foo?")

    assert "foo" not in store.podcasts.get("farewell").tags
    assert "foo" not in store.podcasts.get("greetings").tags


def test_tagger_interactive_mode_switches_to_bulk_mode_when_prompted(
    mocker, store, tagger
):
    mocked_click_prompt = mocker.patch(
        "pod_store.commands._tagging.click.prompt", return_value="b"
    )

    assert list(tagger.tag_items(interactive_mode=True)) == [
        "Choose the podcasts.",
        "Switching to 'bulk' mode.\n"
        "Choosing the following tag(s) for farewell: foo.",
        "Choosing the following tag(s) for greetings: foo.",
    ]

    # verify the prompt is called by checking the last call
    mocked_click_prompt.assert_called_with("Choose farewell with tag(s) foo?")

    assert "foo" in store.podcasts.get("farewell").tags
    assert "foo" in store.podcasts.get("greetings").tags
