"""
Process urls for broken link service
"""
from urllib.parse import urlparse
from mimetypes import MimeTypes

class Url():
    allowed_image_extensions = ('.jpg', '.bmp', '.jpeg', '.png', '.tiff', '.gif')
    mime = MimeTypes()

    def __init__(self):
        pass

    @classmethod
    def load_ignore_list(cls, urls_to_ignore):
        cls.urls_to_ignore = urls_to_ignore

    @classmethod
    def set_base_url(cls, base_url):
        cls.base_url = base_url
        cls.base_url_protocol = base_url.split(':')[0]
        cls.base_url_domain = cls.domain(base_url)

    def sanitize(self, url):
        if not url:
            return ''
        # Ignore internal references urls
        if url.startswith('#'):
            return ''
        # ignore mailto urls
        if url.startswith('mailto:'):
            return ''
        # ignore internal respond comments urls (enough for my WordPress blogs)
        if url.endswith('#respond'):
            return ''
        # ignore urls from this ignore list
        if self.must_ignore(url):
            return ''
        # this is an internal URL... so add base_url_protocol (protocol relative urls)
        if url.startswith('//'):
            url = self.base_url_protocol + ':' + url
        else:
            # Add url domain when necessary (relative urls)
            if url.startswith('/'):
                url = self.base_url_protocol + '://' + self.baseUrlDomain + url
        url = url.strip()
        return url


    @classmethod
    def is_internal(cls, url):
        # ignore www when comparing
        return cls.domain(url).replace('www.', '') == cls.base_url_domain.replace('www.','')


    @classmethod
    def domain(cls, url):
        o = urlparse(url)
        domain = "{}".format(o.netloc)
        # ignore www on domain, as it is not important in this use case
        domain = domain.lower().replace('www.','').strip()
        return domain


    def is_file(self, url):
        url = url.lower()
        mime_type = self.mime.guess_type(url)[0]
        if mime_type:
            type, sub_type = mime_type.split('/')
            #print url, type, sub_type
            if type != 'text': return True
        return False

    def must_ignore(self, url):
        for ignorePattern in self.urls_to_ignore:
            if ignorePattern in url:
                return True
        return False
