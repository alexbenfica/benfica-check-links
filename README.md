# check-links


If you are seeing this on GitHub, you should know that this is a mirror from Gitlab: https://gitlab.com/alexbenfica/check-links/
Issues and and milestones are all there!

# What does it do?

Allows you to check for broken links in all internal pages of a website and more:
- export results to comma separated values (.csv)
- can also be imported as module

It is used for some specific tasks:
- find broken urls on pages
- as a desired side effect, load pages and forces caching creation
- created to run in a daily basis reporting broken links of multi site network

# How to use it?

```python3 check_links.py --help```

It is simple and really fast as it reuses http socket connections!

Enjoy it!
