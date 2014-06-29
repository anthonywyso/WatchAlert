#! /usr/bin/python

import datetime  # import for timestamp
import getopt, sys  # import for passing command line options
import smtplib  # import for connecting to mail server
import time  # import for sleep
import urllib
import urllib2  # import for extracting http
import yaml
import os
from email.mime.text import MIMEText  # import for creating mail

# ################
##### notes #####
#################

#this script scrapes and searches website html for keywords, and then emails the hits to specified user(s)
#default run -- scrapes wus-forum and searches 'halios'; refresh every 15 minutes
#submariner run -- WatchAlert.py -s submariner

#to-do
#1. add functionality of searching multiple keywords, in an array

########################
###### scrapes wus #####
########################



def scrape(scrapesite, scrapefile="scrapefile.html"):
    #opens temporary file for editing
    wus = open(scrapefile, 'wb')

    #opens and saves current frontpage
    response = urllib2.urlopen(scrapesite)
    html = response.read()
    wus.write(html)
    wus.close()


########################
##### searches wus #####
########################


def search(keywords, scrapefile='scrapefile.html', msgfile='msgfile.html', switch=False):
    #searches downloaded wus for keywords, checks the line against the keyword "database", and adds them to email file
    wus = open(scrapefile, 'rb')
    email = open(msgfile, 'wb')
    database = open(keywords, 'ab')
    for line in wus:
        if keywords in line and 'class=\"title"' in line:  #searches keyword & makes sure each hit is a class="title" post
            if checkdatabase(line, keywords) != 0:
                email.write(line)
                database.write(line)
                email.write("<br>")  #formats email with extra linebreaks for easier viewing
                switch = True
    wus.close()

    #add timestamp to email file
    now = datetime.datetime.now()
    email.write(str(now))
    email.close()

    return switch


##########################
##### check database #####
##########################


def checkdatabase(wusline, keywords):
    #checks database for already viewed hits
    database = open(keywords, 'rb')
    for line in database:
        if line == wusline:
            return 0  #returns 0 if the line is already present in database


##########################
##### emails updates #####
##########################


def email(keywords, recipient, switch=False, msgfile='msgfile.html'):
    #server settings
    host = os.environ[config["email_host_origin"]]
    user = os.environ[config["email_user_origin"]]
    passwd = os.environ[config["email_passwd_origin"]]

    #assemble email
    email = open(msgfile, 'rb')
    msg = MIMEText(email.read(), 'html')
    msg['Subject'] = "[WUS] " + keywords + " " + str(datetime.datetime.now())
    msg['From'] = user
    msg['To'] = user

    #connect to server and send email
    if switch == True:
        try:
            server = smtplib.SMTP(host, 587)
            server.starttls()
            server.login(user, passwd)
            server.sendmail(user, recipient, msg.as_string())
            server.quit()
        except:
            print "Email failure", str(datetime.datetime.now())
        else:
            print "Email sent", str(datetime.datetime.now())
    else:
        print "No new matches", str(datetime.datetime.now())

    email.close()

####################################
##### global default variables #####
####################################

refresh = 15 * 60
keywords = 'halios'
url = 'http://forums.watchuseek.com/f29/'
url_beta = 'http://forums.timezone.com/index.php?t=threadt&frm_id=32'
cycle = 1
recipient = [os.environ[config["email_user_origin"]]]
yamlfile = "WatchAlert.yaml"
with open(yamlfile, 'r') as configfile:
    config = yaml.load(configfile)

###############################
##### parse command line ######
###############################

options, remainder = getopt.getopt(sys.argv[1:], 'r:s:u:')

for opt, arg in options:
    if opt in ('-s'):  #specify search terms
        keywords = arg
    if opt in ('-r'):  #specify additional recipients
        recipient.append(arg)
    elif opt in ('-u'):  #specify url to scrape
        url = arg

while __name__ == "__main__":
    print os.environ[config["email_host_origin"]]
    print os.environ[config["email_user_origin"]]
    print os.environ[config["email_passwd_origin"]]
    #print "Cycle:", cycle
    #print "Refresh rate:", refresh, "seconds"
    #print "Search keywords:", keywords
    #print "Search site:", url
    #print "Notify: ", recipient
    #scrape(url)
    #switch = search(keywords)
    #email(keywords, recipient, switch)
    #cycle = cycle + 1
    time.sleep(refresh)