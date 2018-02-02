import sys
sys.path.append("/checklinks")


from unittest import TestCase
from url import Url

class TestUrl(TestCase):

    def setUp(self):
        Url.set_base_url('https://www.google.com.br/')
        Url.load_ignore_list([])

    def test__sanitize(self):
        self.assertEqual(Url.sanitize('//yahoo.com/'), 'https://yahoo.com/')
        self.assertEqual(Url.sanitize('//www.yahoo.com/'), 'https://www.yahoo.com/')

