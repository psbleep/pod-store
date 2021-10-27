import click
import pytest

from pod_store.podcasts import Podcast
from pod_store.commands.tagging import Tagger, Untagger


TEST_INTERACTIVE_MODE_TAGGER_HELP_MESSAGE = """Choosing in interactive mode. Options are:

    y = yes (choose this episode as 'blessed')
    n = no (do not choose this episode as 'blessed')
    b = bulk (choose this and all following episodes as 'blessed')
    q = quit (stop choosing episodes and quit)
"""


@pytest.fixture
def podcasts(now, yesterday, podcast, other_podcast_episode_data):
    other_podcast = Podcast(
        title="farewell",
        feed="http://goodbye.world/rss",
        episode_data=other_podcast_episode_data,
        created_at=yesterday,
        updated_at=now,
    )
    return [podcast, other_podcast]


@pytest.fixture
def tagger():
    return Tagger(
        action="choose",
        performing_action="choosing",
        performed_action="chosen",
    )


def test_tagger_tag_podcast_episodes_bulk_mode_tags_all_podcast_episodes(
    podcasts, tagger
):
    pod1, pod2 = podcasts

    assert list(tagger.tag_podcast_episodes(podcasts, tag="blessed")) == [
        "Chosen as 'blessed': greetings -> [0023] hello",
        "Chosen as 'blessed': greetings -> [0011] goodbye",
        "Chosen as 'blessed': farewell -> [0001] gone",
        "Chosen as 'blessed': farewell -> [0002] not forgotten",
    ]
    assert not pod1.episodes.list(blessed=False)
    assert not pod2.episodes.list(blessed=False)


def test_tagger_tag_podcast_episodes_interactive_mode_tags_episode_when_prompted(
    mocker, podcasts, tagger
):
    mocked_click_prompt = mocker.patch(
        "pod_store.commands.tagging.click.prompt", return_value="y"
    )

    pod1, pod2 = podcasts

    assert list(
        tagger.tag_podcast_episodes(podcasts, tag="blessed", interactive_mode=True)
    ) == [
        TEST_INTERACTIVE_MODE_TAGGER_HELP_MESSAGE,
        "Chosen as 'blessed': greetings -> [0023] hello",
        "Chosen as 'blessed': greetings -> [0011] goodbye",
        "Chosen as 'blessed': farewell -> [0001] gone",
        "Chosen as 'blessed': farewell -> [0002] not forgotten",
    ]

    # verify the prompt is called by checking the last call
    mocked_click_prompt.assert_called_with(
        "farewell -> [0002] not forgotten\nnever forgotten\n\nChoose as 'blessed'?"
    )

    assert not pod1.episodes.list(blessed=False)
    assert not pod2.episodes.list(blessed=False)


def test_tagger_tag_podcast_episodes_interactive_mode_does_not_tag_episodes_if_prompted(
    mocker, podcasts, tagger
):
    mocked_click_prompt = mocker.patch(
        "pod_store.commands.taggers.click.prompt", return_value="n"
    )

    pod1, pod2 = podcasts

    assert list(
        tagger.tag_podcast_episodes(podcasts, tag="blessed", interactive_mode=True)
    ) == [
        TEST_INTERACTIVE_MODE_TAGGER_HELP_MESSAGE,
        "",
        "",
        "",
        "",
    ]

    # verify the prompt is called by checking the last call
    mocked_click_prompt.assert_called_with(
        "farewell -> [0002] not forgotten\nnever forgotten\n\nChoose as 'blessed'?"
    )

    assert not pod1.episodes.list(blessed=True)
    assert not pod2.episodes.list(blessed=True)


def test_tagger_tag_podcast_episodes_interactive_mode_switches_to_bulk_mode_if_prompted(
    mocker, podcasts, tagger
):
    mocked_click_prompt = mocker.patch(
        "pod_store.commands.taggers.click.prompt", return_value="b"
    )

    pod1, pod2 = podcasts

    assert list(
        tagger.tag_podcast_episodes(podcasts, tag="blessed", interactive_mode=True)
    ) == [
        TEST_INTERACTIVE_MODE_TAGGER_HELP_MESSAGE,
        "Switching to 'bulk' mode.\nChosen as 'blessed': greetings -> [0023] hello",
        "Chosen as 'blessed': greetings -> [0011] goodbye",
        "Chosen as 'blessed': farewell -> [0001] gone",
        "Chosen as 'blessed': farewell -> [0002] not forgotten",
    ]

    assert not pod1.episodes.list(blessed=False)
    assert not pod2.episodes.list(blessed=False)

    # verify the prompt does not continue to be called once the switch to bulk mode
    # is made
    mocked_click_prompt.assert_called_once()


def test_tagger_tag_podcast_episodes_interactive_mode_quits_if_prompted(
    mocker, podcasts, tagger
):
    mocked_click_prompt = mocker.patch(
        "pod_store.commands.taggers.click.prompt", return_value="q"
    )

    pod1, pod2 = podcasts

    with pytest.raises(click.Abort):
        list(
            tagger.tag_podcast_episodes(podcasts, tag="blessed", interactive_mode=True)
        )

    # verify the prompt is not called again after the user quits
    mocked_click_prompt.assert_called_once()

    assert not pod1.episodes.list(blessed=True)
    assert not pod2.episodes.list(blessed=True)


def test_untagger_tag_podcast_episodes_untags_episodes(podcasts):
    pod1, pod2 = podcasts

    untagger = Untagger(
        action="unchoose",
        performing_action="unchoosing",
        performed_action="unchosen",
    )

    assert list(untagger.tag_podcast_episodes(podcasts, tag="new")) == [
        "Unchosen as 'new': greetings -> [0023] hello",
        "Unchosen as 'new': farewell -> [0001] gone",
    ]
    assert not pod1.episodes.list(new=True)
    assert not pod2.episodes.list(new=True)
