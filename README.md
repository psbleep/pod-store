# pod-store

`pod-store` is an encrypted CLI podcast tracker that syncs across devices using `git`. Inspired by [pass](https://www.passwordstore.org/), "the standard unix password manager."

The state of your podcasts and episodes is tracked in a JSON-structured store file. [git](https://git-scm.com/) is used to share that store file between devices. [GPG](https://gnupg.org/) keys encrypt the store file for security.

Synchronization and encryption features are optional. `pod-store` can be used as an unecrypted CLI podcast tracker for a single device.

This is a very young/alpha-stage project. Use at your own risk, of course.

## Requirements

Written for Linux environments running Python 3.7 and above. May work on MacOS but probably does not work on Windows. Apart from Python library requirements, `pod-store` requires `git` (for syncing across devices) and `gpg` (for encryption).

## Why?

When I was looking for CLI podcast trackers I did not love any of the options I found. `pass` has been my password manager for a while now, and the concept of a `pass`-like interface for podcast tracking appealed to me.

In particular, I like that `pass`:

 - Mimics core utilities commands in name and (some) parameters where sensible (`ls`, `rm`, etc)
 - Handles syncing across devices with a standard version control system (`git`)
 - Provides security using a basic public/private key encryption standard (`gpg`)

There are other things about the `pass` philosophy that I obviously ignore in this project. In particular, I do not aspire for `pod-store` to be "the standard unix" _anything_. That frees me from having to write it in shell script.

## Installation

Install the current release version using `pip`:

    pip install pod-store

Or install the cutting edge directly from the repo using `pip`:

    pip install git+https://github.com/psbleep/pod-store.git

I recommend you install this in a Python [virtual environment](https://docs.python.org/3.7/tutorial/venv.html).

## Usage

`pod-store` tracks your podcast data in a JSON file (which I will refer to as "the store"). To get started, set up your store. If you have already have a remote `git` repo you want to sync your podcasts with, you can provide that directly during set up. Currently only SSH authentication is supported. For encrypting the store, pass in the GPG ID from your keychain that you want to use:

    pod init --git-url git@git.foo.bar:foobar/pods.git --gpg-id foo@bar.com

Leave off the `git-url` option and you can set up your remote `git` path manually. Leave off the `gpg-id` option and your store will not be encrypted.

You can avoid setting up `git` with your store at all using the `--no-git` flag:

    pod init --no-git

Once your store is set up you will want to add a podcast to it. Supply the name you want to use in the store for this podcast, and the RSS feed URL for the podcast episodes:

    pod add podcast-name https://pod.cast/episodes/rss

You can list which podcasts in your store have new episodes, or list all podcasts in your store:

    pod ls
    pod ls --all

Get more detail with any `ls` command by adding the `--verbose` flag:

    pod ls --verbose --all

List new episodes, list all episodes, list new episodes for a specific podcast, list data for only a single podcast episode:

    pod ls --episodes
    pod ls --all --episodes
    pod ls -p podcast-name
    pod ls -p podcast-name -e episode-number

Refresh episode data for all podcasts from their RSS feeds, or just a specific podcast:

    pod refresh
    pod refresh -p podcast-name

Sometimes you may want to save data about a podcast in the store, but not continue refreshing the podcast from the RSS feed:

    pod set-inactive podcast-name

Using `pod refresh` and specifying the podcast by title will force an RSS feed refresh:

    pod refresh -p inactive-podcast-name

To reactivate a podcast and resume updating it from RSS feed data regularly:

    pod set-active podcast-name

Download all new episodes, or new episodes for just a specific podcast, or episodes for podcasts with a certain tags, or episodes for podcasts without certain tags, or episodes with certain tags, or just a single episode:

    pod download
    pod download -p podcast-name
    pod download -pt tag-name
    pod download -up tag-name
    pod download -t tag-name
    pod download -p podcast-name -e episode-number

By default podcast episodes will be downloaded to e.g. `/home/<username>/Podcasts/<podcast-name>/<001-episode-title>.mp3`. See the configuration section for how to adjust the download path.

Sometimes you may want to mark an episode as being not-new without actually downloading it. Do that using the `mark-as-old` command. By default you will interactively choose which episodes to mark, or you can bulk-mark all episodes. Either of these strategies can be applied to _all_ new episodes, or just the episodes of a specific podcast:

    pod mark-as-old
    pod mark-as-old --bulk

    pod mark-as-old -p podcast-name

The reverse can be accomplished as well, if you want to download episodes that have been previously marked as "old". All the same command options apply:

    pod mark-as-new

Rename a podcast in the store:

    pod mv old-name new-name

Remove a podcast from the store:

    pod rm podcast-name

Run an arbitrary git command within the `pod-store` repo:

    pod git push

Encrypt a store with keys from your GPG keyring:

    pod encrypt-store <gpg-id>

This command works either to encrypt a previously-unencrypted store, or to switch which GPG keys are used to encrypt the store.

Unencrypt a store that is set up as encrypted:

    pod unencrypt-store

Podcasts and episodes can be marked with tags. The `tag` command allows tagging a single podcast or episode:

    pod tag -p podcast-name -t tag-name
    pod tag -p podcast-name -e episode-number -t tag-name

You can also tag groups of podcasts, or episodes, or episodes for a particular podcast:

    pod tag --podcasts -t tag-name
    pod tag --episodes -t tag-name
    pod tag -p podcast-name --episodes -t tag-name

By default, the `tag` command works on groups of items. By default, it tags episodes.

When tagging groups of items, you can interactively select which items to tag or apply the tag to the whole group by using the `interactive` and `bulk` mode options:

    pod tag --podcasts --interactive -t tag-name
    pod tag --episodes --bulk -t tag-name

By default, group tagging operations are run in interactive mode. Bulk mode tagging operations will prompt the user for a single confirmation, unless you pass in the `force` flag:

    pod tag --episodes --bulk --force -t tag-name

Any of the tagging commands can be used to remove tags (rather than apply them) using the `untag` option:

    pod tag --untag --episodes -t tag-name

## Configuration

`pod-store` allows the user to override some default behavior by setting env vars:

    POD_STORE_PATH  # defaults to /home/<username>/.pod-store
    POD_STORE_FILE_NAME  # defaults to "pod-store.json" if not encrypted, "pod-store.gpg" if encrypted
    POD_STORE_PODCAST_DOWNLOAD_PATH  # defaults to /home/<username>/Podcasts
    POD_STORE_PODCAST_REFRESH_TIMEOUT  # seconds to wait before timing out a podcast RSS refresh. defaults to 15 seconds
    POD_STORE_EPISODE_DOWNLOAD_TIMEOUT  # seconds to wait before timing out an episode download. defaults to the value of `POD_STORE_PODCAST_REFRESH_TIMEOUT`
    POD_STORE_GPG_ID_FILE  # defaults to <POD_STORE_PATH>/.gpg-id
    POD_STORE_SECURE_GIT_MODE  # set this to remove some identifying information from git commit messages
    POD_STORE_EXTREME_SECURE_GIT_MODE  # set this to use hashes of the current timestamp as git commit messages to remove all identifying information
    DO_NOT_SET_POD_STORE_EPISODE_METADATA  # set this to prevent setting metadata on downloaded episodes

The default GPG ID file is automatically included in the git repo's `.gitignore` file. If you want to track it for some reason you can remove the entry from the `.gitignore` file (or remove the `.gitignore` file entirely).

## Contributing

Feel free to file issues on Github or open pull requests. Since this is a personal project I do in my spare time I am not going to work much on stuff that doesn't interest me, but I am open to any bug reports/feature requests/contributions offered in a friendly spirit.

To work on the code:

 - Fork this repo on Github
 - Clone your copy of the repo
 - `pip install -r requirements.txt` into your development environment
 - Make a branch for your changes. If it is targetted at an existing Github issue, name the branch in the style `012-change-these-things`, where `012` is the zero-padded three digit Github issue number and `change-these-things` is a short description of what you are working on.
 - When you are finished, open a PR from your fork and branch into the `main` branch on this repo.

Write tests for your changes!

The CLI is built using the [Click](https://click.palletsprojects.com/) library, so some familiarity with that library will help in understanding/contributing to the code.

This project uses [flake8](https://flake8.pycqa.org/en/latest/) for linting, [black](https://github.com/psf/black) for code formatting, and [https://pycqa.github.io/isort/](isort) for import standards. [PEP-8](https://www.python.org/dev/peps/pep-0008/) is generally followed, with the exception of an 88 character line limit rather than 79 characters (which is in line with the default behavior for `black`).

Tests are run using [pytest](https://docs.pytest.org/) and run against multiple Python versions using [tox](https://tox.wiki/en/latest/).

Code will not be accepted that doesn't pass the test suite or the code style checks. You can run the linters and tests yourself locally before opening the PR. These commands should do it (run from the root directory of the git repo):

    flake8 .
    black .
    isort .
    pytest
