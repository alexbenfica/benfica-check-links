#!/usr/bin/python3
# Alex Benfica <alexbenfica@gmail.com>
import logging
import time
import datetime
import requests

from bs4 import BeautifulSoup
from colorama import Fore

from url import Url


class CheckLink():
    """
    Recursive check for broken links of all internal pages of a website
    Do NOT follow external urls, but check them.
    """
    def __init__(self, base_url, url=None):
        self.base_url = base_url
        Url().load_ignore_list(urls_to_ignore)
        Url().set_base_url(base_url)
        self.urls = dict()
        self.urls_to_check = list()
        self.add_url_to_check(self.base_url, '')
        self.start_session()


    def start_session(self):
        self.session = requests.Session()
        # Use some common user agent header to avoid beibg blocked
        self.requestHeaders = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/47.0.2526.106 Safari/537.36'}


    def start_checking(self):
        self.total_checked = 0
        self.startTime = datetime.datetime.now()
        self.t0 = time.time()
        logging.info('Starting with url: {}'.format(self.base_url))
        while self.urls_to_check:
            # always get the first list element
            # the priority elements to be checked will be added the begining of the list
            # @todo Adding the priority elements to the end might be more effective in time complexity
            self.check_url(self.urls_to_check[0])
            # DEBUG
            # if self.total_checked == 50:
            #     break


    def add_url_to_check(self, url, referrer=""):

        if not self.urls.get(url):
            # if url not on url list, add it!
            self.urls[url] = {'referrers': list(), 'status': 0}

        # add the referrer
        # it is important to keep track of all places when the url is referenced
        self.urls[url]['referrers'] = list(set(self.urls[url]['referrers'] + [referrer]))

        # if already on the list of urls_to_check, do not add again
        if url in self.urls_to_check:
            return False
        if self.is_url_checked(url):
            return False

        # if links are from internal, i.e.: the same domain, then
        # ... add first to ensure max reuse of http connections
        if Url().is_internal(url):
            # add to beginning when it from the same domain
            # @todo check if O(n) time complexity will be an issue here (list insert)
            self.urls_to_check.insert(0, url)
        else:
            # add to the list beginning
            self.urls_to_check.append(url)

        return True


    def is_url_checked(self, url):
        return self.get_url_status(url) != 0

    def get_url_referrers(self, url):
        return self.urls.get(url,dict()).get('referrers',list())
        
    def get_url_status(self, url):
        return self.urls.get(url,dict()).get('status', 0)
        
    def set_url_status(self, url, status):
        self.urls[url]['status'] = status


    def get_urls_from_html(self, html):
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


    @classmethod
    def status_is_error(cls, status):
        if not isinstance(status, int ):
            return True
        if status > 300:
            return True
        return False


    def check_url(self, url):
        self.total_checked += 1
        # get only head when the content is not important! (images and external)
        head_only = not Url().is_internal(url) or Url().is_file(url)

        msg = ''
        if head_only:
            msg += Fore.YELLOW + '(HTTP HEAD) ' + Fore.WHITE
        else:
            msg += '(HTTP GET) '

        if not Url().is_internal(url):
            msg += ' (EXTERNAL) '
        if Url().is_file(url):
            msg += '(FILE) '

        logging.info("\n #%d  Checking url: %s %s" % (self.total_checked, msg, url))
        refs = self.get_url_referrers(url)
        if refs:
             logging.info(Fore.WHITE + "    First linked from: %s " % refs[0])

        t_request = time.time()
        timeout = 15

        try:
            if head_only:
                r = self.session.head(url, timeout=timeout, headers=self.requestHeaders)
                # if link is NOT really a file, download it
                if not self.status_is_error(r.status_code):
                    if Url().is_internal(url):
                        mimeType = r.headers.get('content-type')
                        if mimeType.startswith('text'):
                            msg = ' (It is not a file, it is %s) ' % mimeType
                            logging.info(" {}  Checking url: (HTTP GET)! {} {}".
                                         format(self.total_checked, msg, url))
                            r = self.session.get(url, timeout=timeout, headers=self.requestHeaders)

            else: 
                r = self.session.get(url, timeout=timeout, headers=self.requestHeaders)

            status = r.status_code
            

        except Exception as e:
            status = e.__class__.__name__
            
        self.set_url_status(url, status)
        self.urls_to_check.remove(url)
        t_request = time.time() - t_request

        # Add new urls to list
        new_urls_count = 0
        if not self.status_is_error(status):
            new_urls_count = self.queue_new_urls(r.text, referrer=url)

        # All verbose info grouped here...
        self.total_time = time.time() - self.t0
        self.avg_time = self.total_time / self.total_checked
        eta = int(self.avg_time * len(self.urls_to_check))

        msg = '         +{:.4f}s status {} | Avg:{:.4f}s | Total: {} in {} | +{} new | {} on queue | est. time left: {}'.format(
            t_request,
            status,
            self.avg_time,
            self.total_checked,
            "{}".format(datetime.timedelta(seconds=int(self.total_time))),
            new_urls_count,
            len(self.urls_to_check),
            "{}".format(datetime.timedelta(seconds=eta))
        )

        color = (Fore.GREEN, Fore.RED)[self.status_is_error(status)]
        logging.info(color + msg + Fore.WHITE)



    def queue_new_urls(self, html, referrer):
        """
        Add only new urls to list and return the number of urls added.
        :param html:
        :return:
        """
        urls = list()
        new_urls_count = 0
        urls = self.get_urls_from_html(html)

        sanitized_urls = [Url().sanitize(url, referrer) for url in urls]
        clean_urls = [url for url in sanitized_urls if url]

        # reorder list to get more sessions reused
        clean_urls.sort()
        # add new urls to list, counting the positive returns
        for new_url in clean_urls:
            new_urls_count += self.add_url_to_check(new_url, referrer)
        return new_urls_count



    def get_results(self):
        """
        Return the results of check link process.
        :return:
        """
        return self.urls



    # def createReport(self):
    #     def addTxt(txt=''):
    #         self.markdown_txt += txt + "\r\n"
    #
    #     def addCSV(txt=''):
    #         self.csv_txt += txt + "\r\n"
    #
    #     def addTSV(txt=''):
    #         self.tsv_txt += txt + "\r\n"
    #
    #     self.markdown_txt  = ''
    #     self.csv_txt  = ''
    #     self.tsv_txt  = ''
    #
    #     addTxt('## Base url: [%s](%s)' % (self.base_url, self.base_url))
    #     addTxt('### Some statistics:')
    #     addTxt('* Total urls checked: %d' % self.total_checked)
    #     addTxt('* Start time: %s' % self.startTime.strftime('%d/%m/%Y %H:%M:%S'))
    #     addTxt('* End time: %s' % datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
    #     addTxt('* Total time spent: %s' % "{:0>8}".format(datetime.timedelta(seconds=int(self.total_time))))
    #     addTxt('* Average check time per url: %.2f s' % self.avg_time)
    #
    #     nProblems = 0
    #     for url, value in self.urls.iteritems():
    #         status = self.urls[url].get('status')
    #         if checkLinks.status_is_error(status):
    #             nProblems += 1
    #             addTxt("#### %s | [%s](%s)" % (status, url,url))
    #             addTxt()
    #             # get referers
    #             referrers = self.get_url_referrers(url)
    #             for ref in referrers:
    #                 addTxt("> * Fix here: [%s](%s)" % (ref,ref))
    #                 addCSV("%s,%s,%s,%s" % (self.baseUrlDomain,status,url,ref))
    #                 addTSV("%s\t%s\t%s\t%s" % (self.baseUrlDomain,status,url,ref))
    #
    #     addTxt('#### Total urls with problems: %d' % nProblems)
    #     return self.markdown_txt, self.csv_txt, self.tsv_txt






    # @staticmethod
    # def saveReport(txt, outputReportDir, outPutFile):
    #     # Deal with files and directory names
    #     outputReportDir = os.path.abspath(outputReportDir)
    #     outputFile = os.path.join(outputReportDir, outPutFile)
    #     if not os.path.isdir(outputReportDir):
    #         os.makedirs(outputReportDir)
    #
    #     if 'html' in outPutFile:
    #         resourceDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources')
    #         htmlTemplateFile = os.path.join(resourceDir, 'report-template.html')
    #         cssTemplateFile = os.path.join(resourceDir, 'markdown.css')
    #         cssOutPutFile = os.path.join(outputReportDir, 'markdown.css')
    #
    #         html = codecs.open(htmlTemplateFile,encoding='utf-8').read()
    #         html = html.replace('HTML_HERE',markdown.markdown(txt))
    #
    #         css = codecs.open(cssTemplateFile,encoding='utf-8').read()
    #         codecs.open(cssOutPutFile,'w+',encoding='utf-8').write(css)
    #         txt = html
    #
    #     codecs.open(outputFile,'w+',encoding='utf-8').write(txt)
    #




if __name__ == "__main__":
    import argparse
    import pprint

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Check for broken links in all pages of a website.",
        epilog="Just run and wait for the unified report.")

    parser.add_argument("--url", help="Base url to start checking for broken links. Include protocol  (https:// )")
    parser.add_argument("-o", "--output_file", help="Output file to save report to.", )
    parser.add_argument("-i", "--ignore_url_file", help="File with url patterns to ignore.", )
    args = parser.parse_args()

    urls_to_ignore = list()
    if args.ignore_url_file:
        urls_to_ignore = open(args.ignore_url_file, 'r').read().splitlines()

    # call library

    check_link = CheckLink(args.url, urls_to_ignore)
    check_link.start_checking()
    results = check_link.get_results()

    #pprint.pprint(results)


    #
    # # aggregate reports on HTML and CSV calling stactic method
    # checkLinks.saveReport(markdown_txt, outputDir, 'benfica-link-checker-report.html')
    # checkLinks.saveReport(csv_txt, outputDir, 'benfica-link-checker-report.csv')
    # checkLinks.saveReport(tsv_txt, outputDir, 'benfica-link-checker-report.tsv')