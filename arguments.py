#!/usr/bin/python -tt
# -*- coding: utf-8 -*-
import os
import argparse

# This module will parse each argument

parser = argparse.ArgumentParser(
    description="Check for broken links on many websites at once.",
    epilog="Just run and wait for the unified report.")

parser.add_argument("--urls",
    type=lambda s: unicode(s, 'utf8'),
    help="Base urls to start checking for broken links.",                                        
    nargs='+')

parser.add_argument("-o","--outputDir", 
    type=lambda s: unicode(s, 'utf8'),
    help="Output directory to save reports.",)

parser.add_argument("-i","--ignoreListFile", 
    type=lambda s: unicode(s, 'utf8'),
    help="File with urls match patterns to ignore.",)

args = parser.parse_args()