import click
import pytest

from pod_store.podcasts import Podcast
from pod_store.taggers import PodcastEpisodeTagger


TEST_INTERACTIVE_MODE_TAGGER_HELP_MESSAGE = """Tagging in interactive mode. Options are:

    y = yes (tag this episode as 'picked')
    n = no (do not tag this episode as 'picked')
    b = bulk (tag this and all following episodes as 'picked')
    q = quit (stop tagging episodes and quit)
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
def interactive_mode_tagger():
    return PodcastEpisodeTagger(
        action="tag",
        performing_action="tagging",
        performed_action="tagged",
        tag="picked",
        interactive_mode=True,
    )


def test_podcast_episode_tagger_bulk_mode_tags_all_episodes_and_returns_output(
    podcasts,
):
    pod1, pod2 = podcasts

    tagger = PodcastEpisodeTagger(
        action="mark",
        tag="marked",
        interactive_mode=False,
    )
    assert list(tagger.tag_podcast_episodes(podcasts)) == [
        "Marked as 'marked': greetings -> [0023] hello",
        "Marked as 'marked': greetings -> [0011] goodbye",
        "Marked as 'marked': farewell -> [0001] gone",
        "Marked as 'marked': farewell -> [0002] not forgotten",
    ]
    assert not pod1.episodes.list(marked=False)
    assert not pod2.episodes.list(marked=False)


def test_podcast_episode_untagger_removes_tags(
    podcasts,
):
    pod1, pod2 = podcasts

    tagger = PodcastEpisodeTagger(
        action="unmark",
        tag="new",
        interactive_mode=False,
        is_untagger=True,
    )
    assert list(tagger.tag_podcast_episodes(podcasts)) == [
        "Unmarked as 'new': greetings -> [0023] hello",
        "Unmarked as 'new': farewell -> [0001] gone",
    ]
    assert not pod1.episodes.list(new=True)
    assert not pod2.episodes.list(new=True)


def test_podcast_episode_interactive_mode_shows_help_message_tags_episode_when_prompted(
    mocker, podcasts, interactive_mode_tagger
):
    mocked_click_prompt = mocker.patch(
        "pod_store.taggers.click.prompt", return_value="y"
    )

    pod1, pod2 = podcasts

    assert list(interactive_mode_tagger.tag_podcast_episodes(podcasts)) == [
        TEST_INTERACTIVE_MODE_TAGGER_HELP_MESSAGE,
        "Tagged as 'picked': greetings -> [0023] hello",
        "Tagged as 'picked': greetings -> [0011] goodbye",
        "Tagged as 'picked': farewell -> [0001] gone",
        "Tagged as 'picked': farewell -> [0002] not forgotten",
    ]

    # verify the prompt is called by checking the last call
    mocked_click_prompt.assert_called_with(
        "farewell -> [0002] not forgotten\nnever forgotten\n\nTag as 'picked'?"
    )

    assert not pod1.episodes.list(picked=False)
    assert not pod2.episodes.list(picked=False)


def test_podcast_episode_interactive_mode_does_not_tag_episode_if_not_prompted(
    mocker, podcasts, interactive_mode_tagger
):
    mocked_click_prompt = mocker.patch(
        "pod_store.taggers.click.prompt", return_value="n"
    )

    pod1, pod2 = podcasts

    assert list(interactive_mode_tagger.tag_podcast_episodes(podcasts)) == [
        TEST_INTERACTIVE_MODE_TAGGER_HELP_MESSAGE,
        "",
        "",
        "",
        "",
    ]

    # verify the prompt is called by checking the last call
    mocked_click_prompt.assert_called_with(
        "farewell -> [0002] not forgotten\nnever forgotten\n\nTag as 'picked'?"
    )

    assert not pod1.episodes.list(picked=True)
    assert not pod2.episodes.list(picked=True)


def test_podcast_episode_interactive_mode_switches_to_bulk_mode_when_prompted(
    mocker, podcasts, interactive_mode_tagger
):
    mocked_click_prompt = mocker.patch(
        "pod_store.taggers.click.prompt", return_value="b"
    )

    pod1, pod2 = podcasts

    assert list(interactive_mode_tagger.tag_podcast_episodes(podcasts)) == [
        TEST_INTERACTIVE_MODE_TAGGER_HELP_MESSAGE,
        "Switching to 'bulk' mode.\nTagged as 'picked': greetings -> [0023] hello",
        "Tagged as 'picked': greetings -> [0011] goodbye",
        "Tagged as 'picked': farewell -> [0001] gone",
        "Tagged as 'picked': farewell -> [0002] not forgotten",
    ]

    assert not pod1.episodes.list(picked=False)
    assert not pod2.episodes.list(picked=False)

    # verify the prompt does not continue to be called once the switch to bulk mode
    # is made
    mocked_click_prompt.assert_called_once()


def test_podcast_episode_interactive_mode_quits_when_prompted(
    mocker, podcasts, interactive_mode_tagger
):
    mocked_click_prompt = mocker.patch(
        "pod_store.taggers.click.prompt", return_value="q"
    )

    pod1, pod2 = podcasts

    with pytest.raises(click.Abort):
        list(interactive_mode_tagger.tag_podcast_episodes(podcasts))

    # verify the prompt is not called again after the user quits
    mocked_click_prompt.assert_called_once()

    assert not pod1.episodes.list(picked=True)
    assert not pod2.episodes.list(picked=True)
