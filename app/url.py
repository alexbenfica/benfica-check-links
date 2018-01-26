"""
Process urls for broken link service
"""
from urllib.parse import urlparse
from mimetypes import MimeTypes
from bs4 import BeautifulSoup


STATUS_NOT_CHECKED = 0

class Url():
    """
    Urls specific methods related to check links script.
    Most of methods do not depend on each url url, but only on base url.
    The url context is not base on each evaluated url but on base_url used in check links.

    """
    allowed_image_extensions = ('.jpg', '.bmp', '.jpeg', '.png', '.tiff', '.gif')
    mime = MimeTypes()

    def __init__(self, url, referrer):
        self.url = url
        self.internal = self.is_internal(url)
        self.referrers = [referrer,]
        self.status = STATUS_NOT_CHECKED
        self.binary = self.is_file(url)
        # get only head when the content is not important! (images and external)
        self.head_only = not self.internal or self.binary
        self.content_size = -1


    def add_referrer(self, referrer):
        self.referrers = list(set(self.referrers + [referrer]))

    def checked(self):
        return self.status != 0

    def __repr__(self):
        return "{}({},{}) internal:{} status:{} binary:{}".format(__class__.__name__,
                                                        self.url,
                                                        self.referrers,
                                                        self.internal,
                                                        self.status,
                                                        self.binary)

    @classmethod
    def load_ignore_list(cls, regex_urls_to_ignore):
        """Receive and loads a list with regex urls to replace."""
        cls.regex_urls_to_ignore = regex_urls_to_ignore or []

    @classmethod
    def set_base_url(cls, base_url):
        """Load the base url and its derived urls."""
        cls.base_url = base_url
        cls.base_url_protocol = base_url.split(':')[0]
        cls.base_url_domain = cls.domain(base_url)

    @classmethod
    def sanitize(cls, url):
        """Clean and validate urls that should be verified as broken links."""
        if not url:
            return ''
        # Ignore internal references urls
        if url.startswith('#'):
            return ''
        # ignore mailto urls
        if url.startswith('mailto:'):
            return ''
        # ignore internal respond comments urls (enough for some of my WordPress blogs)
        if url.endswith('#respond'):
            return ''
        # ignore urls from this ignore list
        if cls.must_ignore(url):
            return ''
        # this is an internal URL... so add base_url_protocol (protocol relative urls)
        if url.startswith('//'):
            url = cls.base_url_protocol + ':' + url
        else:
            # Add url domain when necessary (relative urls)
            if url.startswith('/'):
                url = cls.base_url_protocol + '://' + cls.base_url_domain + url
        url = url.strip()
        return url


    @classmethod
    def is_internal(cls, url):
        """Check if url is from the same domain as the base_url. Ignores www on this checking."""
        return cls.domain(url).replace('www.', '') == cls.base_url_domain.replace('www.', '')


    @classmethod
    def domain(cls, url):
        """Get the domain from a url. Ignores 'www' as it is not important for the objective."""
        url_info = urlparse(url)
        domain = "{}".format(url_info.netloc)
        # ignore www on domain, as it is not important in this use case
        domain = domain.lower().replace('www.', '').strip()
        return domain


    def is_file(self, url):
        """Check if a url if from a file by guessing based on url text."""
        url = url.lower()
        guessed_types = self.mime.guess_type(url)[0]
        if guessed_types:
            mime_type, _ = guessed_types.split('/')
            if mime_type != 'text':
                return True
        return False


    @classmethod
    def must_ignore(cls, url):
        """Check if url must be ignored by check links based on ignore list."""
        for ignore_pattern in cls.regex_urls_to_ignore:
            if ignore_pattern in url:
                return True
        return False


    @classmethod
    def get_from_html(cls, html):
        """
        Get all urls of links and images inside an HTML
        :param html: html content of a page.
        :return: set of links found in html
        """
        url_list = list()
        soup = BeautifulSoup(html, "html.parser")

        for item in soup.find_all(attrs={'href': ''}):
            for link in item.find_all('a'):
                url_list.append(link.get('href'))

        for item in soup.find_all(attrs={'src': ''}):
            for link in item.find_all('img'):
                url_list.append(link.get('src'))

        # return without duplicates
        return list(set(url_list))
