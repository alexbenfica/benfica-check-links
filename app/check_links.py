#!/usr/bin/python3
"""
Performs link checking following all internal links from a given base url.
Does not follow external links, but checks if they are broken.
Alex Benfica <alexbenfica@gmail.com>
"""
import logging
import time
import datetime
import csv

import requests
from colorama import Fore


if __name__ != "__main__":
    from .url import Url
else:
    from url import Url

# pylint: disable=C0111

class CheckLink():
    """
    Recursive check for broken links of all internal pages of a website
    Do NOT follow external urls, but check them.
    """
    def __init__(self, base_url, urls_to_ignore, request_timeout=15):
        self.base_url = base_url
        self.request_timeout = request_timeout
        Url.load_ignore_list(urls_to_ignore)
        Url.set_base_url(base_url)
        self.urls = dict()
        self.urls_to_check = list()
        self.add_url_to_check(self.base_url, '')
        self.start_session()


    def start_session(self):
        self.session = requests.Session()
        # Use some common user agent header to avoid beibg blocked
        self.request_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/47.0.2526.106 Safari/537.36'}


    def start_checking(self, max_urls_to_check=-1):
        """
        Start checking urls from base_url
        :param max_urls_to_check: the maximum number of urls to be checked. -1 means to check all.
        :return:
        """
        logging.info('Maximum number of urls to check: {}'.format(max_urls_to_check))
        self.total_checked = 0
        self.start_time = time.time()
        logging.info('Starting with url: %s', self.base_url)
        while self.urls_to_check:
            # always get the first list element
            # the priority elements to be checked will be added the beginning of the list
            # @todo Adding priority elements to the end might be more effective in time complexity
            self.check_url(self.urls_to_check[0])

            if self.total_checked == max_urls_to_check:
                break


    def add_url_to_check(self, url, referrer=""):
        # if url not on url list, add it!
        if not self.urls.get(url):
            self.urls[url] = Url(url, referrer)

        # add the referrer: it is important to keep track of all places when the url is referenced
        self.urls[url].add_referrer(referrer)

        # if already on the list of urls_to_check, do not add again
        if url in self.urls_to_check:
            return False
        else:
            u = self.urls[url]
            if u.checked():
                return False

            # if links are from internal, i.e.: the same domain, then
            # ... add first to ensure max reuse of http connections
            if u.internal:
                # add to beginning when it from the same domain
                # @todo check if O(n) time complexity will be an issue here (list insert)
                self.urls_to_check.insert(0, url)
            else:
                # add to the list beginning
                self.urls_to_check.append(url)

            return True


    @classmethod
    def status_is_error(cls, status):
        if not isinstance(status, int):
            return True
        if status > 300:
            return True
        return False


    def check_url(self, url):
        self.total_checked += 1
        u = self.urls[url]

        if u.head_only:
            msg = Fore.YELLOW + '(HTTP HEAD) ' + Fore.WHITE
        else:
            msg = '(HTTP GET) '

        if not u.internal:
            msg += ' (EXTERNAL) '

        if u.binary:
            msg += '(FILE) '

        logging.info("\n #%d  Checking url: %s %s", self.total_checked, msg, url)

        if u.referrers:
            logging.info(Fore.WHITE + "    First linked from: %s " % u.referrers[0])

        t_request = time.time()

        try:
            if u.head_only:
                req = self.session.head(url, timeout=self.request_timeout, headers=self.request_headers)
                # if link is NOT really a file, download it
                if not self.status_is_error(req.status_code):
                    if u.internal:
                        mime_type = req.headers.get('content-type')
                        if mime_type.startswith('text'):
                            msg = ' (It is not a file, it is %s) ' % mime_type
                            logging.info(" %d  Checking url: (HTTP GET)! %s %s", self.total_checked, msg, url)
                            req = self.session.get(url, timeout=self.request_timeout, headers=self.request_headers)

            else:
                req = self.session.get(url, timeout=self.request_timeout, headers=self.request_headers)

            status = req.status_code

        except Exception as exc:
            status = exc.__class__.__name__

        # save the url status
        self.urls[url].status = status

        self.urls_to_check.remove(url)

        t_request = time.time() - t_request

        # Add new urls to list
        new_urls_count = 0
        if not self.status_is_error(status):
            self.urls[url].content_size = len(req.text)
            new_urls_count = self.queue_new_urls(req.text, referrer=url)

        # All verbose info grouped here...
        total_time = time.time() - self.start_time
        avg_time = total_time / self.total_checked
        eta = int(avg_time * len(self.urls_to_check))

        msg = '         '
        msg += '+{:.4f}s status {} | Avg:{:.4f}s | Total: {} in {} | +{} new | {} on queue | est. time left: {}'.\
            format(t_request,
                   status,
                   avg_time,
                   self.total_checked,
                   "{}".format(datetime.timedelta(seconds=int(total_time))),
                   new_urls_count,
                   len(self.urls_to_check),
                   "{}".format(datetime.timedelta(seconds=eta))
                  )

        if self.status_is_error(status):
            color = Fore.RED
        else:
            color = Fore.GREEN

        logging.info(color + msg + Fore.WHITE)



    def queue_new_urls(self, html, referrer):
        """
        Add only new urls to list and return the number of urls added.
        :param html:
        :return:
        """
        urls = list()
        new_urls_count = 0
        urls = Url.get_from_html(html)

        sanitized_urls = [Url.sanitize(url) for url in urls]
        clean_urls = [url for url in sanitized_urls if url]

        # reorder list to get more sessions reused
        clean_urls.sort()
        # add new urls to list, counting the positive returns
        for new_url in clean_urls:
            new_urls_count += self.add_url_to_check(new_url, referrer)
        return new_urls_count



    def get_results(self):
        """
        Return the results of check link process as a dictionary
        :return:
        """
        results = {}
        for url, info in self.urls.items():
            results[url] = info.__dict__
        return results


    def generate_report(self, output_file):
        with open(output_file, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile, delimiter=';', quotechar='|', quoting=csv.QUOTE_MINIMAL)
            for url, info in self.urls.items():
                csv_writer.writerow([url, info.status, info.referrers])


if __name__ == "__main__":

    import argparse
    from __version__ import __version__

    logging.basicConfig(level=logging.INFO)

    # pylint: disable=C0103

    parser = argparse.ArgumentParser(
        description="Check for broken links in all pages of a website.",
        epilog="Just run and wait for the unified report.")

    parser.add_argument("--url", help="Base url to start checking for broken links. Include protocol  (https:// )")
    parser.add_argument("-o", "--output_file", help="Output file to save report to.", )
    parser.add_argument("-i", "--ignore_url_file", help="File with url patterns to ignore.", )
    parser.add_argument("-m", "--max_urls_to_check", help="Maximum number of urls to check.", default=-1, type=int)
    parser.add_argument('--version', action='version', version='%(prog)s {version}'.format(version=__version__))
    args = parser.parse_args()

    url_list_to_ignore = list()
    if args.ignore_url_file:
        url_list_to_ignore = open(args.ignore_url_file, 'r').read().splitlines()

    # call library
    check_link = CheckLink(args.url, url_list_to_ignore)
    check_link.start_checking(args.max_urls_to_check)
    check_link_results = check_link.get_results()

    # logging.debug(check_link_results)
    # for url, info in check_link_results.items():
    #     if info.get('content_size') > 0:
    #         logging.debug(info)

    check_link.generate_report(args.output_file)

    # pylint: enable=C0103
