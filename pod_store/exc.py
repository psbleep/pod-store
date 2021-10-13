class EpisodeDoesNotExistError(Exception):
    pass


class GitCommandError(Exception):
    pass


class GPGCommandError(Exception):
    pass


class NoEpisodesFoundError(Exception):
    pass


class NoPodcastsFoundError(Exception):
    pass


class PodcastDoesNotExistError(Exception):
    pass


class PodcastExistsError(Exception):
    pass


class StoreExistsError(Exception):
    pass
