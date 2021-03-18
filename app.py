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
import tempfile

import click
import yaml
from git import Repo
from thoth.common import init_logging
from thoth.common import __version__ as thoth_common_version
from thoth.storages import CephStore
from thoth.storages import __version__ as thoth_storages_version

init_logging()

_LOGGER = logging.getLogger("thoth.prescription_sync_job")

__version__ = "0.0.0"
__component_version__ = f"{__version__}+common.{thoth_common_version}.storages.{thoth_storages_version}"


def _print_version(ctx: click.Context, _, value: str):
    """Print component version and exit."""
    if not value or ctx.resilient_parsing:
        return

    click.echo(__component_version__)
    ctx.exit()


@click.group()
@click.pass_context
@click.option(
    "-v", "--verbose", is_flag=True, envvar="THOTH_PRESCRIPTION_SYNC_DEBUG", help="Be verbose about what's going on.",
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
    "--prescription-path",
    "-p",
    type=str,
    envvar="THOTH_PRESCRIPTION_SYNC_PATH",
    default="prescription.yaml",
    metavar="PATH",
    required=True,
    help="A path to prescription within the repository.",
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
def sync(repo_url: str, prescription_path: str, no_release_adjustment: bool) -> None:
    """Sync the given prescription document."""
    with tempfile.TemporaryDirectory() as dir_name:
        _LOGGER.info("Cloning %r", repo_url)
        repo = Repo.clone_from(repo_url, dir_name, depth=1)
        sha = repo.head.commit.hexsha

        _LOGGER.info("Loading prescription from %r", prescription_path)
        with open(os.path.join(dir_name, prescription_path)) as prescription_file:
            content = yaml.safe_load(prescription_file)

    if not no_release_adjustment:
        content["spec"]["release"] = f"{content['spec']['release']}.{sha}"

    prescription = yaml.safe_dump(content)

    prefix = f"{os.environ['THOTH_CEPH_BUCKET_PREFIX']}/{os.environ['THOTH_DEPLOYMENT_NAME']}"
    _LOGGER.info("Storing prescription with hash %r to remote Ceph using prefix %r", sha, prefix)

    ceph = CephStore(prefix)
    ceph.connect()
    ceph.store_blob(prescription, prescription_path)


__name__ == "__main__" and cli()
