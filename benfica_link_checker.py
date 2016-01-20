#!/usr/bin/python -tt
# -*- coding: utf-8 -*-
# Alex Benfica <alexbenfica@gmail.com>

import os
import urllib2
import socket
from urlparse import urlparse
import time
import markdown
import pprint as pp
from bs4 import BeautifulSoup
import codecs
from arguments import *

# pip install colorama
from colorama import Fore


# Recursive check for broken links of all internal pages of a website
# Does not follow external urls.
class checkLinks():   
    
    imageExtensions = ('.jpg','.bmp','.jpeg','.png', '.tiff', '.gif')
    
    def __init__(self, baseUrl):
        print 'Starting checkLink class with base url: %s' % baseUrl        
        self.baseUrl = baseUrl
        self.baseUrlDomain = self.getUrlDomain(self.baseUrl)
        self.urls = {}        
        self.urlsToCheck = []
        self.addUrlToCheck(self.baseUrl, '')
        
    def getUrlDomain(self,url):
        parsed_uri = urlparse(url)
        domain = '{uri.netloc}'.format(uri=parsed_uri)
        return domain
        
    def isUrlInternal(self, url):
        return self.getUrlDomain(url) == self.baseUrlDomain
    
    def isUrlChecked(self,url):        
        return self.getUrlStatus(url) > 0

    def isUrlOfImage(self,url):        
        return url.lower().endswith(self.imageExtensions)
    
    def addUrlRef(self, url, ref):
        # no need to check for repeats as a url will not have the same referer twice
        ref = ref.strip()
        if not ref: return
        self.urls[url]['ref'].append(ref)
        
    def getUrlRef(self, url):
        return self.urls[url].get('ref',[])

    def getUrlRef(self, url):
        return self.urls.get(url,{}).get('ref',[])
        
    def getUrlStatus(self, url):
        return self.urls.get(url,{}).get('status',0)
        
    def setUrlStatus(self, url, status):
        self.urls[url]['status'] = status
    
    def sanitizeUrl(self, url):        
        # Add url domain when necessary
        if url.startswith('/'): url = 'http://' + self.baseUrlDomain + url
        return url
    
    def addUrlToCheck(self, url, ref):        
        url = self.sanitizeUrl(url)
        if not url: return 0
        
        # if not on list or urls, add it!
        if not self.urls.get(url,{}): self.urls[url] = {'ref':[], 'status':0}

        # add referer
        self.addUrlRef(url,ref)
        
        # if already on the list of urlsToCheck, do not add againg
        if url in self.urlsToCheck: return 0            
        
        if self.isUrlChecked(url): return 0
        
        # add external links first, as they broke more often
        # the referer is not need here as it were already add to the main dict self.urls        
        # add to the end...
        if self.isUrlInternal(url):            
            self.urlsToCheck.append(url)
        else:
            # add to the list beginning
            self.urlsToCheck.insert(0,url)
        return 1


    def getUrlsFromHtml(self, html):
        url_list= []        
        forbidden_urls = ['#', None, ""]
        
        soup = BeautifulSoup(html, "html.parser")
        for item in soup.find_all(attrs={'href': ''}):
            for link in item.find_all('a'):
                url = link.get('href')        
                if url not in forbidden_urls:
                    url_list.append(url)
                
        for item in soup.find_all(attrs={'src': ''}):
            for link in item.find_all('img'):
                url = link.get('src')        
                if url not in forbidden_urls:
                    url_list.append(url)
        
        # remove duplicates from urls
        url_list = list(set(url_list))       
        return url_list
        
        
    def checkUrl(self, url):             
        msg = ''
        if not self.isUrlInternal(url): msg += ' (EXTERNAL) '
        if self.isUrlOfImage(url): msg += '(IMAGE) '
        
        print "\nChecking url: %s %s" % (msg, url)
        
        self.totalUrlsChecked += 1        
        try:
            response = urllib2.urlopen(url, timeout = 10)
            code = response.code
            encoding = response.headers.getparam('charset')
        
        # @todo (show each error meaning on reports)
        except urllib2.URLError: code = 999
        except ValueError: code = 998
        

        self.setUrlStatus(url,code)
        self.urlsToCheck.remove(url)
        
        newUrlsAddedCount = 0        
        urls=[]
        # if no error detected...
        if code < 400:
            # if internal and not image, follow...
            if self.isUrlInternal(url):                
                if not self.isUrlOfImage(url):
                    html = response.read().decode(encoding)                
                    urls = self.getUrlsFromHtml(html)
                    # Add new urls to list
                    ref = url # for clarity reasons only
                    for newUrls in urls: 
                        newUrlsAddedCount += self.addUrlToCheck(newUrls, ref)
        
        # All verbose info grouped here...
        self.totalTime = time.time() - self.t0
        self.avgTime = self.totalTime / self.totalUrlsChecked

        
        

        
        msg = '#%d  %.1fs  ~%.2fs | status %d | %d found | +%d added | %d on queue (ETA %.0fs)' % (
            self.totalUrlsChecked, 
            self.totalTime, 
            self.avgTime, 
            code, 
            len(urls), 
            newUrlsAddedCount, 
            len(self.urlsToCheck), 
            self.avgTime * len(self.urlsToCheck)
        )
        
        
        
        if code < 399: color = Fore.GREEN
        else: color = Fore.RED
        
        print color + msg + Fore.WHITE


        
    def start(self):
        self.totalUrlsChecked = 0
        self.t0 = time.time()
        while self.urlsToCheck:            
            url = self.urlsToCheck[0]
            self.checkUrl(url)            
            #if self.totalUrlsChecked == 2: break            
        
        
    def createReport(self):
        def addTxt(txt=''): self.markdown_txt += txt + "\r\n"
            
        self.markdown_txt  = ''        
        addTxt('## Base url: [%s](%s)' % (self.baseUrl, self.baseUrl))
        addTxt('### Some statistics:')
        addTxt('* Total urls checked: %d' % self.totalUrlsChecked)
        addTxt('* Total time spent: %d s' % self.totalTime)
        addTxt('* Average check time per url: %.2f s' % self.avgTime)
        
        minHttpCodeAsError = 399
        nProblems = 0
        for url in self.urls.keys():            
            if self.getUrlStatus(url) > minHttpCodeAsError:
                nProblems += 1
                status = "%s " % self.urls[url].get('status')                
                addTxt('####' + status + "| [%s](%s)" % (url,url))
                addTxt()
                # get referers
                referrers = self.getUrlRef(url)                
                refToShow = len(referrers)
                if refToShow:
                    if refToShow > 5:
                        refToShow = 5
                        addTxt('Too many referrers for this url. Showing first %d of %d.' % (refToShow, len(referrers)))
                        addTxt()
                    
                for ref in referrers[0:refToShow]: addTxt("> * Fix here: [%s](%s)" % (ref,ref))
                
        addTxt('#### Total urls with problems: %d' % nProblems)        
        return self.markdown_txt



    @staticmethod
    def saveHTMLReport(markdown_txt, outputReportTo):
        # Deal with files and directory names
        outputReportTo = os.path.abspath(outputReportTo)        
        resourceDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources')
        print resourceDir
        htmlTemplateFile = os.path.join(resourceDir, 'report-template.html')
        cssTemplateFile = os.path.join(resourceDir, 'markdown.css')
        htmlOutputFile = os.path.join(outputReportTo, 'benfica-link-checker-report.html')
        cssOutPutFile = os.path.join(outputReportTo, 'markdown.css')
        if not os.path.isdir(outputReportTo): os.makedirs(outputReportTo)        
        
        html = codecs.open(htmlTemplateFile,encoding='utf-8').read()        
        html = html.replace('HTML_HERE',markdown.markdown(markdown_txt))
        codecs.open(htmlOutputFile,'w+',encoding='utf-8').write(html)        
        
        css = codecs.open(cssTemplateFile,encoding='utf-8').read()        
        codecs.open(cssOutPutFile,'w+',encoding='utf-8').write(css)
                
        



# Parameters from command line. (Seel arguments.py file)
urls = args.urls
outputDir = args.outputDir

markdown_txt = ''
for url in urls:
    # Call checker for each url
    cLink = checkLinks(url)                
    cLink.start()    
    # Save reports to to file...
    markdown_txt += cLink.createReport()
    
# aggregate reports on HTML    
cLink.saveHTMLReport(markdown_txt, outputDir)    
    