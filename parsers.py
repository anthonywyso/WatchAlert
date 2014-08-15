import requests
import re
from lxml import html
from datetime import datetime, timedelta


class Parser(object): #needs work, cl parser, cut redundancy
    """
    Scrapes targeted website; builds new items dicts
    IN: source
    OUT: list of dicts w/ new items
    """
    def __init__(self, source):
        self.source_urls = {'wus': 'http://forums.watchuseek.com/f29/',
                            'boc': 'http://www.blowoutcards.com/forums/basketball-singles-buy-sell-trade/',
                            'sd': 'http://slickdeals.net/forums/forumdisplay.php?f=9&order=desc&pp=100&sort=lastpost',
                            'cl': 'http://philadelphia.craigslist.org/sss',
                            'clsf': 'http://sfbay.craigslist.org/search/sfc/roo?query=mission&sale_date=-&minAsk=1&maxAsk=1000',
                            'ebay': 'http://www.ebay.com'}
        self.url = self.source_urls[source]
        self.column_names = ["title_description", "source", "member_posted", "date_posted"]
        self.relative_day = {'today': datetime.today().strftime('%Y-%m-%d'),
                             'yesterday': (datetime.today()-timedelta(days=1)).strftime('%Y-%m-%d')}

    def get_tree(self):
        r = requests.get(self.url)
        tree = html.fromstring(r.text)
        return tree

    def parse_tree(self):
        pass

    def _organize_scrape(self, title_description, column_values):
        scraped_items = []
        for index in xrange(len(title_description)):
            scraped_items.append({c: column_values[i][index] for i, c in enumerate(self.column_names)})
        return scraped_items


class WUSParser(Parser):

    def parse_tree(self, tree):
        scraped_items = []
        title_description = tree.xpath('//a[starts-with(@class, "title")]/text()')
        title_description = [x.lower() for x in title_description]
        source = tree.xpath('//a[starts-with(@class, "title")]/@href')
        member_posted = tree.xpath('//div[@class="author"]/span[@class="label"]/a/text()')
        date_posted = tree.xpath('//div[@class="threadmeta"]/div[@class="author"]/span[@class="label"]/text()')
        date_posted = [x.strip().lower() for x in date_posted]
        date_posted = [x.replace(u',\xa0', '') for x in date_posted]
        date_posted = filter(None, [x.replace('started by', '') for x in date_posted])

        column_values = [title_description, source, member_posted, date_posted]
        for index in xrange(len(title_description)):
            scraped_items.append({c: column_values[i][index] for i, c in enumerate(self.column_names)})
        return scraped_items


class BOCParser(Parser):  #date_posted = most recent post

    def parse_tree(self, tree):
        scraped_items = []
        title_description = tree.xpath('//a[starts-with(@id, "thread_title")]/text()')
        title_description = [x.lower() for x in title_description]
        source = tree.xpath('//a[starts-with(@id, "thread_title")]/@href')
        member_posted = tree.xpath('//td[starts-with(@id, "td_threadtitle")]/div[@class="smallfont"]/span/text()')
        date_posted = tree.xpath('//td[starts-with(@title, "Replies")]/div[@class="smallfont"]/text()')
        time_posted = tree.xpath('//td[starts-with(@title, "Replies")]/div[@class="smallfont"]/span/text()')
        date_posted = [x.strip().lower() for x in date_posted]
        date_posted = filter(None, [x.replace('by', '') for x in date_posted])
        for i, c in enumerate(date_posted):
            if c in self.relative_day:
                c = self.relative_day[c]
            date_posted[i] = " ".join([c, str(datetime.strptime(str(time_posted[i]), '%I:%M %p').strftime('%H:%M'))])

        column_values = [title_description, source, member_posted, date_posted]
        for index in xrange(len(title_description)):
            scraped_items.append({c: column_values[i][index] for i, c in enumerate(self.column_names)})

        return scraped_items


class SDParser(Parser):

    def parse_tree(self, tree):
        scraped_items = []
        title_description = tree.xpath('//td[starts-with(@id, "td_threadtitle")]/div/a[starts-with(@id, "thread_title")]/text()')
        title_description = [x.lower() for x in title_description]
        source = tree.xpath('//a[starts-with(@id, "thread_title")]/@href')
        source = [''.join(['http://www.slickdeals.net', x]) for x in source]
        member_posted = tree.xpath('//td[starts-with(@id, "td_postdate")]/div/a/text()')
        date_posted = tree.xpath('//td[starts-with(@id, "td_postdate")]/div[@class="smallfont "]/text()')
        time_posted = tree.xpath('//td[starts-with(@id, "td_postdate")]/div[@class="smallfont "]/span/text()')
        date_posted = filter(None, [x.strip().lower() for x in date_posted])
        for i, c in enumerate(date_posted):
            if c in self.relative_day:
                c = self.relative_day[c]
            date_posted[i] = " ".join([c, str(datetime.strptime(str(time_posted[i]), '%I:%M %p').strftime('%H:%M'))])

        column_values = [title_description, source, member_posted, date_posted]
        for index in xrange(len(title_description)):
            scraped_items.append({c: column_values[i][index] for i, c in enumerate(self.column_names)})

        return scraped_items


class CLParser(Parser):  #under development

    def parse_tree(self, tree):
        scraped_items = []
        title_description = tree.xpath('//div[@class="content"]/p[@class="row"]/span/span[@class="pl"]/a/text()')
        location = tree.xpath('//div[@class="content"]/p[@class="row"]/span/span[@class="l2"]/span[@class="pnr"]/small/text()')
        price = tree.xpath('//div[@class="content"]/p[@class="row"]/span/span[@class="l2"]/span[@class="price"]/text()')
        title_description = [" ".join([re.sub(r'[^\x00-\x7F]+', '', c), location[i].strip().lower(), price[i]]) for i, c in enumerate(title_description)]
        source = tree.xpath('//div[@class="content"]/p[@class="row"]/span/span[@class="pl"]/a/@href')
        source = [''.join(['http://sfbay.craigslist.org', x]) for x in source]
        member_posted = [" " for _ in enumerate(title_description)]
        date_posted = [self.relative_day['today'] for _ in enumerate(title_description)]

        column_values = [title_description, source, member_posted, date_posted]
        for index in xrange(len(title_description)):
            scraped_items.append({c: column_values[i][index] for i, c in enumerate(self.column_names)})

        return scraped_items