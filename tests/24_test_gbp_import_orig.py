# vim: set fileencoding=utf-8 :
"""Test L{gbp.scripts.import_orig}"""

import os
import unittest

from collections import namedtuple

from gbp.scripts.import_orig import (debian_branch_merge_by_replace,
                                     GbpError,
                                     is_30_quilt)
from gbp.scripts.common.import_orig import download_orig
from . testutils import DebianGitTestRepo


@unittest.skipUnless(os.getenv("GBP_NETWORK_TESTS"), "network tests disabled")
class TestImportOrigDownload(DebianGitTestRepo):
    HOST = 'git.sigxcpu.org'

    def setUp(self):
        DebianGitTestRepo.setUp(self)
        os.chdir(self.repo.path)

    def test_404_download(self):
        with self.assertRaisesRegexp(GbpError, "404 Client Error: Not Found for url"):
            download_orig("https://{host}/does_not_exist".format(host=self.HOST))

    def test_200_download(self):
        pkg = 'hello-debhelper_2.6.orig.tar.gz'
        url = "https://{host}/cgit/gbp/deb-testdata/tree/dsc-3.0/{pkg}".format(host=self.HOST,
                                                                               pkg=pkg)
        self.assertEqual(download_orig(url).path, '../%s' % pkg)


class TestIs30Quilt(DebianGitTestRepo):
    Options = namedtuple('Options', 'debian_branch')
    format_file = 'debian/source/format'

    def setUp(self):
        DebianGitTestRepo.setUp(self)
        os.chdir(self.repo.path)
        os.makedirs('debian/source/')

    def test_30_quilt(self):
        options = self.Options(debian_branch='master')
        with open(self.format_file, 'w') as f:
            f.write('3.0 (quilt)\n')
        self.repo.add_files([self.format_file])
        self.repo.commit_all("Add %s" % self.format_file)
        self.assertEquals(self.repo.branch, options.debian_branch)
        self.assertTrue(is_30_quilt(self.repo, options))

    def test_no_format(self):
        options = self.Options(debian_branch='master')
        self.assertFalse(os.path.exists(self.format_file))
        self.assertFalse(is_30_quilt(self.repo, options))

    def test_no_quilt(self):
        options = self.Options(debian_branch='master')
        with open(self.format_file, 'w') as f:
            f.write('3.0 (nonexistent)')
        self.assertFalse(is_30_quilt(self.repo, options))

    def test_30_quilt_empty_repo(self):
        options = self.Options(debian_branch='master')
        self.assertFalse(is_30_quilt(self.repo, options))


class TestMergeModeReplace(DebianGitTestRepo):
    debian_branch = 'master'

    def setUp(self):
        DebianGitTestRepo.setUp(self)
        os.chdir(self.repo.path)

    def testDebianDir(self):
        """Test that dropping upstream's debian/ workd (#881750)"""
        self.add_file("debian/control")
        self.repo.create_branch("upstream")
        self.repo.set_branch("upstream")
        self.add_file("upstream_file")
        self.add_file("debian/changelog")
        self.repo.set_branch("master")
        self.repo.create_tag('upstream/1.0', "Upstream 1.0", "upstream")
        debian_branch_merge_by_replace(self.repo, "upstream/1.0", "1.0", self)
        self.assertTrue(os.path.exists("debian/control"))
        # Upstream files must end up on debian branch…
        self.assertTrue(os.path.exists("upstream_file"))
        # … but upsream's debian dir must not
        self.assertFalse(os.path.exists("debian/changelog"))
