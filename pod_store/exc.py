class EpisodeDoesNotExistError(Exception):
    pass


class GitCommandError(Exception):
    pass


class MultiplePodcastsFound(Exception):
    pass


class PodcastDoesNotExistError(Exception):
    pass


class PodcastExistsError(Exception):
    pass


class StoreExistsError(Exception):
    pass
