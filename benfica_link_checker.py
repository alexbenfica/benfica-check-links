#!/usr/bin/python -tt
# -*- coding: utf-8 -*-
# Alex Benfica <alexbenfica@gmail.com>

import os
import sys
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
from mimetypes import MimeTypes
from arguments import *

# Solving encoding issues when running from cron.
# https://fedoraproject.org/wiki/Features/PythonEncodingUsesSystemLocale
reload(sys)
sys.setdefaultencoding('utf-8')


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
        self.startSession()
        self.mime = MimeTypes()
        
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

    def isUrlOfFile(self,url):        
        url = url.lower()
        mime_type = self.mime.guess_type(url)[0]
        if mime_type:
            type, sub_type = mime_type.split('/')        
            #print url, type, sub_type
            if type != 'text': return True            
        return False
    
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
        # ignore mailto urls
        if url.startswith('mailto:'): return ''
        # ignore ?replytocom and #respond urls on WordPress ... ok... it should be in configuration file!
        if '?replytocom' in url: return ''
        if url.endswith('#respond'): return ''
        # Add url domain when necessary        
        if url.startswith('/'): url = 'http://' + self.baseUrlDomain + url
        return url

    
    def addUrlToCheck(self, url, ref):        
        url = self.sanitizeUrl(url, ref)
        if not url: return 0

        # if not on list or urls, add it!
        if not self.urls.get(url,{}): self.urls[url] = {'ref':[], 'status':0}   
        
        # if already on the list of urlsToCheck, do not add againg
        if url in self.urlsToCheck: return 0                    
        if self.isUrlChecked(url): return 0
        
        # add referer
        self.addUrlRef(url,ref)
        
        # if links are from the same domain, add first to ensure max reuse of http connections
        nCharsToCompare = min(20,len(url),len(ref))
        if url[0:nCharsToCompare] == ref[0:nCharsToCompare]:            
            # add to beginning when it from the same domain
            self.urlsToCheck.insert(0,url)
        else:
            # add to the list beginning
            self.urlsToCheck.append(url)
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
        
        
    def startSession(self):
        self.session = requests.Session()
        # Use some common user agent header to avoid beibg blocked
        self.requestHeaders = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36'}
    
    def checkUrl(self, url):             
        self.totalUrlsChecked += 1                
        msg = ''        
        # get only head when the content is not important! (images and external)        
        onlyHead = not self.isUrlInternal(url) or self.isUrlOfFile(url)            
        if onlyHead: msg += Fore.YELLOW + '(HTTP HEAD) ' + Fore.WHITE
        else: msg += '(HTTP GET) '
        if not self.isUrlInternal(url): msg += ' (EXTERNAL) '
        if self.isUrlOfFile(url): msg += '(FILE) '
        
        print "\n #%d  Checking url: %s %s" % (self.totalUrlsChecked, msg, url)
        refs = self.getUrlRef(url)        
        if refs: 
            print Fore.WHITE + "    First linked from: %s " % refs[0]

        tRequest = time.time()
        timeout = 15
        try:
            if onlyHead: 
                r = self.session.head(url, timeout=timeout, headers=self.requestHeaders)                            
            else: 
                r = self.session.get(url, timeout=timeout, headers=self.requestHeaders)
            status = r.status_code
            
            # if the real content type is text and not binary, get the complete content!
            # only get again if urls exists!
            if onlyHead and r.status_code < 399 and self.isUrlInternal(url):
                mimeType = r.headers.get('content-type')
                if mimeType.startswith('text'):                    
                    msg = ' (It is not a file, it is %s) ' % mimeType
                    print " #%d  Checking url: (HTTP GET)! %s %s" % (self.totalUrlsChecked, msg, url)
                    r = self.session.get(url, timeout=timeout, headers=self.requestHeaders)                    
                    status = r.status_code          
                    
        except Exception as exception: status = exception.__class__.__name__
            
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
                
                # reorder list to get more sessions reused
                urls.sort()
        
        
        # All verbose info grouped here...
        self.totalTime = time.time() - self.t0
        self.avgTime = self.totalTime / self.totalUrlsChecked

        eta = int(self.avgTime * len(self.urlsToCheck))
        
        msg = '         +%.2fs ~%.2fs   %s  | status %s | +%d new of %d | %d on queue | time left: %s' % (             
            tRequest,
            self.avgTime,             
            "{:0>8}".format(datetime.timedelta(seconds=int(self.totalTime))),             
            status, 
            newUrlsAddedCount, 
            len(urls), 
            len(self.urlsToCheck), 
            "{:0>8}".format(datetime.timedelta(seconds=eta))
        )
        
        color = (Fore.GREEN, Fore.RED)[checkLinks.statusIsError(status)]
        
        print color + msg + Fore.WHITE


        
    def start(self):
        self.totalUrlsChecked = 0
        self.startTime = datetime.datetime.now()
        self.t0 = time.time()
        while self.urlsToCheck:            
            url = self.urlsToCheck[0]
            self.checkUrl(url)            
            #if self.totalUrlsChecked == 2: break
        
        
    def createReport(self):
        def addTxt(txt=''): 
            self.markdown_txt += txt + "\r\n"

        def addCSV(txt=''): 
            self.csv_txt += txt + "\r\n"
            
            
        self.markdown_txt  = ''        
        self.csv_txt  = ''        
        
        addTxt('## Base url: [%s](%s)' % (self.baseUrl, self.baseUrl))
        addTxt('### Some statistics:')
        addTxt('* Total urls checked: %d' % self.totalUrlsChecked)
        addTxt('* Start time: %s' % self.startTime.strftime('%d/%m/%Y %H:%M:%S'))
        addTxt('* End time: %s' % datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
        addTxt('* Total time spent: %s' % "{:0>8}".format(datetime.timedelta(seconds=int(self.totalTime))))
        addTxt('* Average check time per url: %.2f s' % self.avgTime)
        
        minHttpCodeAsError = 300
        nProblems = 0
        for url, value in self.urls.iteritems():        
            status = self.urls[url].get('status')
            if checkLinks.statusIsError(status):
                nProblems += 1
                addTxt("#### %s | [%s](%s)" % (status, url,url))
                addTxt()
                # get referers
                referrers = self.getUrlRef(url)                
                for ref in referrers: 
                    addTxt("> * Fix here: [%s](%s)" % (ref,ref))                                    
                    addCSV("%s,%s,%s,%s" % (self.baseUrlDomain,status,url,ref))
        
        addTxt('#### Total urls with problems: %d' % nProblems)        
        return self.markdown_txt, self.csv_txt



    @staticmethod
    def statusIsError(status):
        if not isinstance(status, int ): return 1
        if status > 300: return 1
        return 0



    @staticmethod
    def saveReport(txt, outputReportDir, outPutFile):
        # Deal with files and directory names
        outputReportDir = os.path.abspath(outputReportDir)        
        outputFile = os.path.join(outputReportDir, outPutFile)
        if not os.path.isdir(outputReportDir): 
            os.makedirs(outputReportDir)        
        
        if 'html' in outPutFile:
            resourceDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources')                
            htmlTemplateFile = os.path.join(resourceDir, 'report-template.html')
            cssTemplateFile = os.path.join(resourceDir, 'markdown.css')
            cssOutPutFile = os.path.join(outputReportDir, 'markdown.css')
            
            html = codecs.open(htmlTemplateFile,encoding='utf-8').read()        
            html = html.replace('HTML_HERE',markdown.markdown(txt))
            
            css = codecs.open(cssTemplateFile,encoding='utf-8').read()        
            codecs.open(cssOutPutFile,'w+',encoding='utf-8').write(css)
            txt = html
                
        codecs.open(outputFile,'w+',encoding='utf-8').write(txt)        
        



# Parameters from command line. (Seel arguments.py file)
urls = args.urls
outputDir = args.outputDir

markdown_txt = ''
csv_txt = ''

for url in urls:
    # Call checker for each url
    cLink = checkLinks(url)                
    cLink.start()    
    
    # Create reports in txt
    m_txt, c_txt = cLink.createReport()
    markdown_txt += m_txt
    csv_txt += c_txt
    
    # Remove object from memory
    del cLink
    
    
# aggregate reports on HTML and CSV calling stactic method
checkLinks.saveReport(markdown_txt, outputDir, 'benfica-link-checker-report.html')    
checkLinks.saveReport(csv_txt, outputDir, 'benfica-link-checker-report.csv')    
    