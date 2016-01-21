#!/usr/bin/python -tt
# -*- coding: utf-8 -*-
# Alex Benfica <alexbenfica@gmail.com>

import os
import time
import codecs
import datetime
import requests
import markdown
import tldextract
import pprint as pp

from urlparse import urlparse
from bs4 import BeautifulSoup
from colorama import Fore

from arguments import *


# Recursive check for broken links of all internal pages of a website
# Does not follow external urls.
class checkLinks():   
    
    imageExtensions = ('.jpg','.bmp','.jpeg','.png', '.tiff', '.gif')
    
    def __init__(self, baseUrl):
        print 'Starting checkLink class with base url: %s' % baseUrl        
        self.baseUrl = baseUrl
        self.baseUrlDomain = self.getUrlDomain(self.baseUrl)
        print 'Domain is: %s' % self.baseUrlDomain        
        self.urls = {}        
        self.urlsToCheck = []
        self.addUrlToCheck(self.baseUrl, '')
        
    def getUrlDomain(self,url):                
        ext = tldextract.extract(url)        
        # ignore www. The subdomain is only important when it is something else
        if ext.subdomain == 'www': domain = '.'.join(ext[1:3])
        else: domain = '.'.join(ext[0:3])        
        domain = domain.strip().strip('.').lower()
        return domain
        
    def isUrlInternal(self, url):        
        # ignore www when comparing
        urlDomain = self.getUrlDomain(url).replace('www.','')
        baseUrlDomain = self.baseUrlDomain.replace('www.','')
        return urlDomain == baseUrlDomain
    
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
    
    def sanitizeUrl(self, url, ref):                
        if not url: return ''
        # Ignore internal references urls
        if url.startswith('#'): return ''
        # Add url domain when necessary
        if url.startswith('/'): url = 'http://' + self.baseUrlDomain + url
        return url

    def statusIsError(self, status):
        if not isinstance(status, int ): return 1
        if status > 399: return 1
        return 0
    
    def addUrlToCheck(self, url, ref):        
        url = self.sanitizeUrl(url, ref)
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
        
        soup = BeautifulSoup(html, "html.parser")
        for item in soup.find_all(attrs={'href': ''}):
            for link in item.find_all('a'):                
                url_list.append(link.get('href'))
                
        for item in soup.find_all(attrs={'src': ''}):
            for link in item.find_all('img'):                
                url_list.append(link.get('src'))
        
        # remove duplicates from urls
        url_list = list(set(url_list))       
        return url_list
        
        
    def checkUrl(self, url):             
        self.totalUrlsChecked += 1                
        msg = ''
        if not self.isUrlInternal(url): msg += ' (EXTERNAL) '
        if self.isUrlOfImage(url): msg += '(IMAGE) '
        # get only head when the content is not important! (images and external)        
        onlyHead = not self.isUrlInternal(url) or self.isUrlOfImage(url)            
        if onlyHead: msg += '(HEAD ONLY) '
        
        print "\n #%d  Checking url: %s %s" % (self.totalUrlsChecked, msg, url)
        refs = self.getUrlRef(url)        
        if refs: print Fore.YELLOW + u"  \u21b8" +  Fore.WHITE + "    First linked from: %s " % refs[0]

        tRequest = time.time()
        timeout = 15
        try:
            if onlyHead: r = requests.head(url, timeout=timeout)            
            else: r = requests.get(url, timeout=timeout)
            status = r.status_code
        except Exception as exception:
            #except requests.exceptions.ConnectionError:
            status = exception.__class__.__name__
            
        tRequest = time.time() - tRequest
                
        self.setUrlStatus(url,status)
        self.urlsToCheck.remove(url)
        
        newUrlsAddedCount = 0        
        urls=[]        
        # if status is a number...
        if isinstance(status, int ):
            if r.text:
                urls = self.getUrlsFromHtml(r.text)
                # Add new urls to list
                ref = url # for clarity reasons only
                for newUrls in urls: newUrlsAddedCount += self.addUrlToCheck(newUrls, ref)
        
        # All verbose info grouped here...
        self.totalTime = time.time() - self.t0
        self.avgTime = self.totalTime / self.totalUrlsChecked

        eta = int(self.avgTime * len(self.urlsToCheck))
        
        msg = '         +%.2fs ~%.2fs   %s %s  | status %s | +%d new of %d | %d on queue | time left: %s' % (             
            tRequest,
            self.avgTime, 
            u"\u03A3",            
            "{:0>8}".format(datetime.timedelta(seconds=int(self.totalTime))),             
            status, 
            newUrlsAddedCount, 
            len(urls), 
            len(self.urlsToCheck), 
            "{:0>8}".format(datetime.timedelta(seconds=eta))
        )
        
        color = (Fore.GREEN, Fore.RED)[self.statusIsError(status)]
        
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
    