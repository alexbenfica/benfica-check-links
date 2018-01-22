import sys
sys.path.append("/app")

from unittest import TestCase

from url import Url


class TestUrl(TestCase):

    def setUp(self):
        self.url = Url()
        self.url.set_base_url('https://www.google.com.br/')
        self.url.load_ignore_list([])

    def test__sanitize(self):
        self.assertEqual(self.url.sanitize('//yahoo.com/'), 'https://yahoo.com/')
        self.assertEqual(self.url.sanitize('//www.yahoo.com/'), 'https://www.yahoo.com/')

