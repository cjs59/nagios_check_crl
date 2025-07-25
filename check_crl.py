#!/usr/bin/python3
# Copyright (C) 2013 - Remy van Elst

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Chris Share <cjs59@cam.ac.uk> - 2025-7-17
# Changelog: - fix UnicodeDecodeError when reading a DER CRL
#            - make output format more consistent with other Nagios plugins
#            - change getopt to argparse, allowing options in a file

# Mark Ruys <mark.ruys@peercode.nl> - 2015-8-27
# Changelog: - catch openssl parsing errors
#            - clean up temporary file on error
#            - add support for PEM CRL's
#            - fix message when CRL has been expired
#            - pretty print duration

# Jeroen Nijhof <jnijhof@digidentity.eu>
# Changelog: - fixed timezone bug by comparing GMT with GMT
#            - changed hours to minutes for even more precision

# Remy van Elst - raymii.org - 2012
# 05.11.2012
# Changelog: - check with hours instead of dates for more precision,
#            - URL errors are now also catched as nagios exit code.

# Michele Baldessari - Leitner Technologies - 2011
# 23.08.2011

import time
import datetime
import argparse
import os
import pprint
import subprocess
import sys
import tempfile
import urllib.request, urllib.parse, urllib.error


class FileArgumentParser(argparse.ArgumentParser):
    """Arguments file split on spaces, not newlines."""

    def convert_arg_line_to_args(self, arg_line):
        return arg_line.split()


def check_crl(url, warn, crit):
    tmpcrl = tempfile.mktemp(".crl")
    try:
        urllib.request.urlretrieve(url, tmpcrl)
    except:
        print ("CRITICAL: CRL could not be retrieved: %s" % url)
        os.remove(tmpcrl)
        sys.exit(2)

    try:
        inform = 'DER'
        crlfile = open(tmpcrl, "r", errors="ignore")
        for line in crlfile:
            if "BEGIN X509 CRL" in line:
                inform = 'PEM'
                break
        crlfile.close()

        ret = subprocess.check_output(["/usr/bin/openssl", "crl", "-inform", inform, "-noout", "-nextupdate", "-in", tmpcrl], stderr=subprocess.STDOUT)
    except:
        print ("UNKNOWN: CRL could not be parsed: %s %s" % url)
        os.remove(tmpcrl)
        sys.exit(3)

    nextupdate = ret.strip().decode('utf-8').split("=")
    os.remove(tmpcrl)
    eol = time.mktime(time.strptime(nextupdate[1],"%b %d %H:%M:%S %Y GMT"))
    today = time.mktime(datetime.datetime.utcnow().timetuple())
    minutes = (eol - today) / 60
    if abs(minutes) < 4 * 60:
        expires = minutes
        unit = "minutes"
    elif abs(minutes) < 2 * 24 * 60:
        expires = minutes / 60
        unit = "hours"
    else:
        expires = minutes / (24 * 60)
        unit = "days"
    gmtstr = time.asctime(time.localtime(eol))
    if minutes < 0:
        msg = "CRL CRITICAL - %s expired %d %s ago (on %s GMT)" % (url, -expires, unit, gmtstr)
        exitcode = 2
    elif minutes <= crit:
        msg = "CRL CRITICAL - %s expires in %d %s (on %s GMT)" % (url, expires, unit, gmtstr)
        exitcode = 2
    elif minutes <= warn:
        msg = "CRL WARNING - %s expires in %d %s (on %s GMT)" % (url, expires, unit, gmtstr)
        exitcode = 1
    else:
        msg = "CRL OK - %s expires in %d %s (on %s GMT)" % (url, expires, unit, gmtstr)
        exitcode = 0

    print (msg)
    sys.exit(exitcode)

def main():
    parser = FileArgumentParser(
        description = "Check the expiry of the CRL at a URL",
        epilog = "Example with a warning threshold of 8 hours and critical threshold of 6 hours:\n\n"
                 "  ./check_crl.py -u 'http://domain.tld/url/crl.crl' -w 480 -c 360\n\n"
                 "Example with a warning threshold of 60 days and critical threshold of 30 days:\n\n"
                 "  ./check_crl.py -u 'http://domain.tld/url/crl.crl' -w 86400 -c 43200",
        formatter_class = argparse.RawDescriptionHelpFormatter,
        fromfile_prefix_chars = "@"
    )
    parser.add_argument("-u", "--url", help="CRL URL", required=True)
    parser.add_argument("-w", "--warning", help="Expiry warning threshold in minutes", required=True)
    parser.add_argument("-c", "--critical", help="Expiry critical threshold in minutes", required=True)

    args = parser.parse_args()

    check_crl(args.url, int(args.warning), int(args.critical))


if __name__ == "__main__":
    main()
