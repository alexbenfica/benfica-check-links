import logging
import argparse
from checklinks import CheckLink
from __version__ import __version__

if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    # pylint: disable=C0103

    parser = argparse.ArgumentParser(
        description="Check for broken links in all pages of a website.",
        epilog="Just run and wait for the unified report.")

    parser.add_argument("--url", required = True,
                        help="Base url to start checking for broken links. Include protocol  (https:// )", )
    parser.add_argument("-o", "--output_file", help="Output file to save report to.", required = True)
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
