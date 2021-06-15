#!/usr/bin/env python3
# project template
# Copyright(C) 2021 Fridolin Pokorny
#
# This program is free software: you can redistribute it and / or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""Sync prescription from a repo to Ceph so it is available in deployment."""

import logging

import os
import click
import yaml
from git import Repo
from thoth.common import init_logging
from thoth.common import __version__ as thoth_common_version

init_logging()

_LOGGER = logging.getLogger("thoth.prescription_sync_job")
_PRESCRIPTION_METADATA_FILE = "_prescription_metadata.yaml"

__version__ = "0.0.1"
__component_version__ = f"{__version__}+common.{thoth_common_version}"


def _print_version(ctx: click.Context, _, value: str):
    """Print component version and exit."""
    if not value or ctx.resilient_parsing:
        return

    click.echo(__component_version__)
    ctx.exit()


@click.group()
@click.pass_context
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    envvar="THOTH_PRESCRIPTION_SYNC_DEBUG",
    help="Be verbose about what's going on.",
)
@click.option(
    "--version",
    is_flag=True,
    is_eager=True,
    callback=_print_version,
    expose_value=False,
    help="Print prescription-sync version and exit.",
)
def cli(ctx=None, verbose: bool = False):
    """Thoth prescription-sync command line interface."""
    if ctx:
        ctx.auto_envvar_prefix = "THOTH_PRESCRIPTION_SYNC"

    if verbose:
        _LOGGER.setLevel(logging.DEBUG)

    _LOGGER.debug("Debug mode is on")
    _LOGGER.info("Version: %s", __component_version__)


@cli.command("sync")
@click.option(
    "--repo-url",
    "-r",
    type=str,
    envvar="THOTH_PRESCRIPTION_SYNC_REPO",
    metavar="REPO",
    default="https://github.com/thoth-station/prescriptions",
    required=True,
    help="A repository where prescription is stored.",
)
@click.option(
    "--output",
    "-o",
    type=str,
    envvar="THOTH_PRESCRIPTION_SYNC_OUTPUT",
    metavar="PATH",
    required=True,
    help="A path where prescriptions should be cloned.",
)
@click.option(
    "--no-release-adjustment",
    "-A",
    type=str,
    envvar="THOTH_PRESCRIPTION_SYNC_NO_RELEASE_ADJUSTMENT",
    is_flag=True,
    required=False,
    help="Do not add Git SHA info to the prescription release.",
)
def sync(repo_url: str, output: str, no_release_adjustment: bool) -> None:
    """Clone prescriptions and place them to output directory."""
    _LOGGER.info("Cloning %r to %r", repo_url, output)
    repo = Repo.clone_from(repo_url, output, depth=1)

    if not no_release_adjustment:
        sha = repo.head.commit.hexsha

        _LOGGER.info("Adjusting release information in %r to include commit sha %r", _PRESCRIPTION_METADATA_FILE, sha)

        metadata_path = os.path.join(output, _PRESCRIPTION_METADATA_FILE)

        with open(metadata_path) as f:
            content = yaml.safe_load(f)

        content["prescription"]["release"] = f"{content['prescription']['release']}.{sha}"

        with open(metadata_path, "w") as f:
            yaml.safe_dump(content, f)


__name__ == "__main__" and cli()
