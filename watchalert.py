import argparse  # import for command line parse
import csv
from datetime import datetime, timedelta  # import for timestamp
import os  # import for environment variables
import time  # import for sleep
import yaml  # import for config files
from collections import defaultdict

import smtplib  # import for connecting to mail server
from email.mime.text import MIMEText  # import for creating mail
from parsers import WUSParser, BOCParser, CLParser, SDParser


class WatchAlerter(object):
    """
    Scrapes and searches sites for keywords, emails the matches to specified user(s)
    CONFIG -- Set environment variables (in ~/.bash_profile) for sensitive info -- email settings
    USAGE: watchalert.py [-h] [-s SEARCH] [-r RECIPIENT] [-u URL] [-c]

        optional arguments:
          -h, --help            show this help message and exit
          -k KEYWORD, --keyword KEYWORD
                                keyword search
          -r RECIPIENT, --recipient RECIPIENT
                                recipient for email alerts; must be individually declared
          -s SOURCE, --source SOURCE     source site to scrape (under development)
          -c, --continuous      continuously run the script
    """

    def __init__(self, settings):
        with open("watchalert.yaml", 'r') as configfile:
            self.config = yaml.load(configfile)
        self.email_host = os.environ[self.config["email_host_origin"]]
        self.email_user = os.environ[self.config["email_user_origin"]]
        self.email_passwd = os.environ[self.config["email_passwd_origin"]]

        self.source = settings['source']
        self.recipients = settings['recipient']
        self.keywords = settings['keyword'].lower()
        self.refresh = settings['refresh']

        self.now = str(datetime.now().strftime('%Y-%m-%d %H:%M'))
        self.database = "database.csv"
        self.column_names = ["keyword_match", "title_description", "source", "member_posted", "date_posted", "date_recorded"]
        self.source_parsers = {'wus': WUSParser, 'boc': BOCParser, 'sd': SDParser, 'cl': CLParser, 'clsf': CLParser}

    def track(self):
        items = self.scrape()
        email_update = self.search(items)
        if email_update:
            self.send_email(email_update)
        else:
            print ">Result: No new matches"
        print "Cycle complete:", self.now, "\n"

        if self.refresh:
            time.sleep(self.refresh)
            self.now = str(datetime.now())
            self.track()

    def display_settings(self):
        print "Search site:", self.source
        print "Search keywords:", self.keywords
        print "Notify: ", self.recipients
        if self.refresh:
            print " ".join(["Refresh rate:", str(self.refresh), "seconds"])

    def scrape(self):
        p = self.source_parsers[self.source](self.source)
        s = p.get_tree()
        return p.parse_tree(s)

    def search(self, recent_posts):
        """
        Searches recent postings for keywords; checks each line against the database; adds new matches to email body
        IN: list of recent posts from site
        OUT: list of new matches if available
        """
        email_msg = []
        new_matches = []
        for post in recent_posts:
            if self.keywords in post['title_description']:
                if self.check_database(post['title_description']):
                    email_msg.extend([post["title_description"], "\n", post["source"], "\n\n"])
                    new_matches.append(post)

        if new_matches:
            with open(self.database, 'ab') as db:
                writer = csv.DictWriter(db, delimiter=',', fieldnames=self.column_names)
                for match in new_matches:
                    match['keyword_match'] = self.keywords
                    match['date_recorded'] = self.now
                    writer.writerow(match)

        return email_msg

    def check_database(self, title_description):
        """
        Checks database for already seen title_description; creates database if unavailable
        IN: match from site
        OUT: returns True for new match, False for duplicate match
        """
        try:
            with open(self.database, 'rb') as db:
                reader = csv.DictReader(db)
                for row in reader:
                    if row['title_description'] == title_description:
                        return False
                return True
        except IOError:
            with open(self.database, 'wb') as db:
                writer = csv.DictWriter(db, delimiter=',', fieldnames=self.column_names)
                writer.writeheader()
                return True

    def send_email(self, contents):
        """
        Assemble and send email alert
        IN: list of new matches
        OUT: N/A
        """
        contents.extend(["\n", self.now])  #adds timestamp to email content
        contents_string = " ".join(contents)
        msg = MIMEText(contents_string, 'plain')
        msg['Subject'] = " ".join(["[", self.source, "]", self.keywords, self.now])
        msg['From'] = self.email_user
        msg['To'] = ", ".join(self.recipients)

        server = smtplib.SMTP(self.email_host, 587)
        server.starttls()
        server.login(self.email_user, self.email_passwd)
        server.sendmail(self.email_user, self.recipients, msg.as_string())
        server.quit()
        print ">>>Result: Email sent"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-k", "--keyword", help="keyword search", required=True)
    parser.add_argument("-r", "--recipient", help="recipient for email alerts; must be individually declared", action="append")
    parser.add_argument("-s", "--source", help="source site to scrape (wus,boc,ebay,cl,sd)", required=True)
    parser.add_argument("-c", "--continuous", help="continuously run the script", action="store_true")
    args = parser.parse_args()

    inputs = defaultdict(list)
    inputs['keyword'] = args.keyword
    inputs['recipient'] = args.recipient
    inputs['source'] = args.source
    if args.continuous:
        inputs['refresh'] = 15 * 60

    return inputs


if __name__ == "__main__":
    settings = parse_args()
    w = WatchAlerter(settings)
    w.display_settings()
    w.track()