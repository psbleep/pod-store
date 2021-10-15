# pod-store

`pod-store` is a CLI podcast tracker inspired by [pass](https://www.passwordstore.org/), "the standard unix password manager."

The state of your podcasts is tracked in a JSON-structured file that is synced across devices using `git`.

Optionally, you can encrypt this podcast store file using [GPG](https://gnupg.org/) keys for security.

This is a very young/alpha-stage project. Use at your own risk, of course.

## Requirements

Written for Linux environments running Python 3.7 and above. (Tested against 3.7, 3.8 and 3.9). May work on MacOS but probably does not work on Windows. Apart from Python library requirements, `pod-store` requires `git` (for syncing across devices) and `gpg` (for encryption).

## Installation

Install the current release version using `pip`:

    pip install pod-store

Or install directly from the repo using `pip`:

    pip install git+https://github.com/psbleep/pod-store.git

I recommend you install this in a Python [virtual environment](https://docs.python.org/3.7/tutorial/venv.html).

## Motivations

When I was looking for CLI podcast trackers I did not love any of the options I found. `pass` has been my password manager for a while now, and the concept of a `pass`-like interface for podcast tracking appealed to me.

In particular, I like that `pass`:

 - Mimics core utilities commands in name and arguments where sensible (`ls`, `rm`, etc)
 - Handles syncing across devices with `git` (which I already use for managing dotfiles, etc)
 - Provides security using a basic public/private key encryption standard (`gpg`)

There are other things about the `pass` philosophy that I obviously ignore in this project. In particular, I do not aspire for `pod-store` to be "the standard unix" _anything_. That frees me from having to write it in shell script.

## Usage

`pod-store` tracks your podcast data in a JSON file, referred to as the "pod-store file."

To get started, set up your store. If you have a remote `git` repo you want to sync your podcasts with, you can provide that directly during set up. (Alternatively, you can set it up manually later on.) Currently only SSH authentication is supported:

    pod init --git-url git@git.foo.bar:foobar/pods.git

If you want an encrypted store, pass in the GPG ID of the keys you want to use.

    pass init --gpg-id foo@bar.com

Once your store is set up you will want to add a podcast to it. Supply the name you want to track your podcast with and the RSS feed URL for the episodes:

    pod add podcast-name https://pod.cast/episodes/rss

You can see the which podcasts in your store have new episodes, or a list of all podcasts in your store:

    pod ls
    pod ls --all


List new episodes, list all episodes, list new episodes for a specific podcast:

    pod ls --episodes
    pod ls --all --episodes
    pod ls --episodes -p podcast-name

Refresh episode data for all podcasts from their RSS feeds, or just a specific podcast:

    pod refresh
    pod refresh -p podcast-name

Download all new episodes, or new episodes for just a specific podcast:

    pod download
    pod download -p podcast-name

By default podcast episodes will be downloaded to e.g. `/home/<username>/Podcasts/<podcast-name>/<001-episode-title>.mp3`. See the configuration section for how to adjust the download path.

Sometimes you may want to mark an episode as being not-new without actually downloading it. Do that using the `mark` command, either interactively or by bulk marking all new episodes. Do either of these for all episodes, or just episodes of a specific podcast:

    pod mark
    pod mark --bulk
    pod mark --bulk -p podcast-name

Rename a podcast in the store:

    pod mv old-name new-name

Remove a podcast from the store:

    pod rm podcast-name

Run an arbitrary git command from inside the `pod-store` repo. (This command is pretty limited, it does not work with any flags).

    pod git push

Encrypt a store that is set up as unencrypted:

    pod encrypt-store <gpg-id>

Unencrypt a store that is set up as encrypted:

    pod unencrypt-store

## Configuration

`pod-store` allows the user to override some default behavior by setting env vars:

    POD_STORE_PATH  # defaults to /home/<username>/.pod-store
    POD_STORE_FILE_NAME  # defaults to "pod-store.json"
    POD_STORE_PODCASTS_DOWNLOAD_PATH  # defaults to /home/<username>/Podcasts

If encryption is used, the GPG ID will be read from a plaintext file located at `<POD_STORE_PATH>/.gpg-id`. (The location of that file is currently not configurable, but maybe it should be.) This file is included in the git repo's `.gitignore` file by default.


## Contributing

Feel free to file issues on Github or open pull requests. Since this is a personal project I do in my spare time I am not going to work much on stuff that doesn't interest me, but I am open to any bug reports/feature requests/contributions offered in a friendly spirit.

To work on the code:

 - Fork this repo on Github
  - Clone your copy of the repo
  - `pip install -r requirements.txt` into your development environment
  - Make a branch for your changes. If it is targetted at an existing Github issue, name the branch in the style `012-change-these-things`, where `012` is the zero-padded three digit Github issue number and `change-these-things` is a short description of what you are working on.
  - When you are finished, open a PR from your fork and branch into the `main` branch on this repo.

Write tests for your changes!

This project uses [black](https://github.com/psf/black) for code formatting/linting, and [https://pycqa.github.io/isort/](isort) for import linting. [PEP-8](https://www.python.org/dev/peps/pep-0008/) is generally followed, with the exception of an 88 character line limit rather than 79 characters (which is in line with the default behavior for `black`).

Tests are run using [pytest](https://docs.pytest.org/) and run against multiple Python versions using [tox](https://tox.wiki/en/latest/).

Code will not be accepted that doesn't pass the test suite or the code style checks. You can run the linters and tests yourself locally before opening the PR. These commands should do it (run from the root directory of the git repo):

    black .
    isort .
    pytest
