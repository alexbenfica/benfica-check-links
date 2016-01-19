#!/usr/bin/python -tt
# -*- coding: utf-8 -*-
import os
import argparse

# This module will parse each argument


parser = argparse.ArgumentParser(
    description="Check for broken links on many websites at once.",
    epilog="Just run and wait for the unified report.")

parser.add_argument("--urls", 
    help="Base urls to start checking for broken links.",                                        
    nargs='+')

parser.add_argument("-o","--outputDir", 
    help="Output directory to save reports.",)

args = parser.parse_args()