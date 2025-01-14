# (C) Copyright 2020 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
#


import logging

from climetlab.core.settings import SETTINGS
from climetlab.core.statistics import record_statistics
from climetlab.download import get_downloader
from climetlab.utils import tqdm
from climetlab.utils.mirror import DEFAULT_MIRROR

from .file import FileSource

LOG = logging.getLogger(__name__)


def progress_bar(total, initial=0, desc=None):
    return tqdm(
        total=total,
        initial=initial,
        unit_scale=True,
        unit_divisor=1024,
        unit="B",
        disable=False,
        leave=False,
        desc=desc,
    )


class Url(FileSource):
    def __init__(
        self,
        url,
        parts=None,
        filter=None,
        merger=None,
        verify=True,
        force=None,
        chunk_size=1024 * 1024,
        range_method="auto",
        http_headers=None,
        update_if_out_of_date=False,
        mirror=DEFAULT_MIRROR,
        fake_headers=None,  # When HEAD is not allowed but you know the size
    ):

        super().__init__(filter=filter, merger=merger)

        # TODO: re-enable this feature
        extension = None

        self.url = url
        LOG.debug("URL %s", url)

        self.update_if_out_of_date = update_if_out_of_date

        if mirror:
            url = mirror(url)

        self.downloader = get_downloader(
            url,
            chunk_size=chunk_size,
            timeout=SETTINGS.get("url-download-timeout"),
            verify=verify,
            parts=parts,
            range_method=range_method,
            http_headers=http_headers,
            fake_headers=fake_headers,
            statistics_gatherer=record_statistics,
            progress_bar=progress_bar,
        )

        if extension and extension[0] != ".":
            extension = "." + extension

        if extension is None:
            extension = self.downloader.extension()

        self.path = self.downloader.local_path()
        if self.path is not None:
            return

        if force is None:
            force = self.out_of_date

        def download(target, url):
            self.downloader.download(target)
            return self.downloader.cache_data()

        self.path = self.cache_file(
            download,
            url,
            extension=extension,
            force=force,
            hash_extra=parts,
        )

    def out_of_date(self, url, path, cache_data):
        if SETTINGS.get("check-out-of-date-urls"):
            return False

        if self.downloader.out_of_date(path, cache_data):
            if SETTINGS.get("download-out-of-date-urls") or self.update_if_out_of_date:
                LOG.warning(
                    "Invalidating cache version and re-downloading %s",
                    self.url,
                )
                return True
            else:
                LOG.warning(
                    "To enable automatic downloading of updated URLs set the 'download-out-of-date-urls'"
                    " setting to True",
                )
        return False

    def __repr__(self) -> str:
        return f"Url({self.url})"


source = Url
