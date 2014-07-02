import argparse  # import for command line parse
import csv
import datetime  # import for timestamp
import os  # import for environment variables
import time  # import for sleep
import yaml  # import for config files

import requests
from lxml import html

import smtplib  # import for connecting to mail server
from email.mime.text import MIMEText  # import for creating mail


class WatchAlerter(object):
    """
    Scrapes and searches WUS Forum for keywords, emails the matches to specified user(s)
    CONFIG -- Set environment variables (in ~/.bash_profile) for sensitive info -- email settings
    USAGE: WatchAlert.py [-h] [-s SEARCH] [-r RECIPIENT] [-u URL] [-c]

        optional arguments:
          -h, --help            show this help message and exit
          -s SEARCH, --search SEARCH
                                search keyword
          -r RECIPIENT, --recipient RECIPIENT
                                recipient for email alerts; must be individually declared
          -u URL, --url URL     url to scrape (under development)
          -c, --continuous      continuously run the script

        Default -- WatchAlert.py -- Scrapes wus-forum and searches 'halios'
    """

    def __init__(self, websites='http://forums.watchuseek.com/f29/', search_keywords='halios'):
        with open("WatchAlert.yaml", 'r') as configfile:
            self.config = yaml.load(configfile)
        self.email_host = os.environ[self.config["email_host_origin"]]
        self.email_user = os.environ[self.config["email_user_origin"]]
        self.email_passwd = os.environ[self.config["email_passwd_origin"]]

        parser = argparse.ArgumentParser()
        parser.add_argument("-s", "--search", help="search keyword")
        parser.add_argument("-r", "--recipient", help="recipient for email alerts; must be individually declared", action="append")
        parser.add_argument("-u", "--url", help="url to scrape (under development)")
        parser.add_argument("-c", "--continuous", help="continuously run the script", action="store_true")
        args = parser.parse_args()

        if args.search:
            self.search_keywords = args.search.lower()
        else:
            self.search_keywords = search_keywords.lower()

        if args.recipient:
            self.email_recipients = [args.recipient]
        else:
            self.email_recipients = [os.environ[self.config["email_user_origin"]]]

        if args.url:
            pass#self.websites = args.url
        else:
            self.websites = websites

        if args.continuous:
            self.refresh = 15 * 60

        self.now = str(datetime.datetime.now())
        self.database = "WatchDatabase.csv"
        self.column_names = ["keyword_match", "title_description", "source", "member_posted", "date_posted", "date_recorded"]

    def __call__(self, *args, **kwargs):
        self.display_options()
        while 1:
            watches = self.scrape()
            email_update = self.search(watches)
            if email_update:
                self.send_email(email_update)
            else:
                print "No new matches", str(datetime.datetime.now())
            try:
                time.sleep(self.refresh)
            except AttributeError:
                break

    def display_options(self):
        print "Search site:", self.websites
        print "Search keywords:", self.search_keywords
        print "Notify: ", self.email_recipients
        try:
            print " ".join(["Refresh rate:", str(self.refresh), "seconds"])
        except AttributeError:
            print " ".join(["Refresh rate: None"])

    def scrape(self):
        """
        Scrapes targeted website; build item dictionary
        IN: N/A
        OUT: list of scraped values
        """
        r = requests.get(self.websites)
        tree = html.fromstring(r.text)
        scraped_items = []
        title_description = tree.xpath('//a[starts-with(@class, "title")]/text()')
        title_description = [x.lower() for x in title_description]
        source = tree.xpath('//a[starts-with(@class, "title")]/@href')
        member_posted = tree.xpath('//div[@class="author"]/span[@class="label"]/a/text()')
        date_posted = tree.xpath('//div[@class="author"]/span[@class="label"]/a/@title')
        keyword_match = [self.search_keywords for _ in title_description]
        date_recorded = [self.now for _ in title_description]
        column_values = [keyword_match, title_description, source, member_posted, date_posted, date_recorded]

        for index in xrange(len(title_description)):
            scraped_items.append({c: column_values[i][index] for i, c in enumerate(self.column_names)})

        return scraped_items

    def search(self, recent_posts):
        """
        Searches recent postings for keywords; checks each line against the database; adds new matches to email file
        IN: list of recent posts from site
        OUT: list of new matches if available
        """
        email_msg = []
        new_matches = []
        for post in recent_posts:
            if self.search_keywords in post['title_description']:
                if self.check_database(post['title_description']):
                    email_msg.extend([post["title_description"], "\n", post["source"], "\n\n"])
                    new_matches.append(post)

        if email_msg:
            email_msg.extend(["\n", self.now])

        if new_matches:
            with open(self.database, 'ab') as db:
                writer = csv.writer(db)
                for match in new_matches:
                    insert_match = [match[column] for column in self.column_names]
                    writer.writerows([insert_match])

        return email_msg

    def check_database(self, title_description):
        """
        Checks database for already seen title_description; creates database if unavailable
        IN: match from site
        OUT: returns True for new match
        """
        try:
            with open(self.database, 'rb') as csv_file:
                reader = csv.reader(csv_file)
                for row in reader:
                    if row[1] == title_description:
                        return False
                return True
        except IOError:
            with open(self.database, 'wb') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerows([self.column_names])
                return True

    def send_email(self, contents):
        """
        Assemble and send email alert
        IN: list of new matches
        OUT: N/A
        """
        contents_string = " ".join(contents)
        msg = MIMEText(contents_string, 'plain')
        msg['Subject'] = " ".join(["[WUS]", self.search_keywords, self.now])
        msg['From'] = self.email_user
        msg['To'] = ", ".join(self.email_recipients)

        try:
            server = smtplib.SMTP(self.email_host, 587)
            server.starttls()
            server.login(self.email_user, self.email_passwd)
            server.sendmail(self.email_user, self.email_recipients, msg.as_string())
            server.quit()
            print "Email sent", str(datetime.datetime.now())
        except:
            print "Email failure", str(datetime.datetime.now())

if __name__ == "__main__":
    w = WatchAlerter()
    w()
