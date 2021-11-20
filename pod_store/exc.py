"""Custom `pod-store` exceptions.

Custom exceptions are used here for easily catching known errors and (hopefully)
gracefully displaying error messages to the CLI user.

This behavior happens in the
`pod_store.commands.decorators.catch_pod_store_errors` decorator.
"""


class AmbiguousEpisodeError(Exception):
    pass


class EpisodeDoesNotExistError(Exception):
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


class ShellCommandError(Exception):
    pass


class StoreDoesNotExistError(Exception):
    pass


class StoreExistsError(Exception):
    pass


class StoreIsNotEncrypted(Exception):
    pass
