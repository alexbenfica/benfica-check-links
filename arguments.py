#!/usr/bin/python -tt
# -*- coding: utf-8 -*-
import os
import argparse

# This module will parse each argument

parser = argparse.ArgumentParser(
    description="Check for broken links in all pages of a website.",
    epilog="Just run and wait for the unified report.")

parser.add_argument("--url", help="Base url to start checking for broken links.",nargs='+')

parser.add_argument("-o","--output_file", help="Output file to save report to.",)

parser.add_argument("-i","--ignore_list", help="File with url patterns to ignore.",)

args = parser.parse_args()