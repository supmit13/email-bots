# Introduction #

This project (email-bots) consists of a few python packages and scripts for scraping email messages from various popular email service providers like Gmail and Yahoo. Currently these are the only providers that are supported, but in future there are plans to add Rediffmail and Hotmail (or Outlook).

In order to make the scripts work, you need to add your gmail or yahoo account credentials in a configuration file. The location and structure of the configuration files are specified in the section **Configuration Details**.

Please note that this bunch of code is not exhaustively tested. I have been running them to perform some of my day-to-day email scraping jobs, and till today, they have successfully served their purpose (for me). But,  even so, they will have their share of issues (some known to me). Thus, prior to using them, you might want to do a bit of testing on them, and, if possible, email the bugs to codexaddict@gmail.com

# Details #

The code is organized as follows:

  * There is a base class for all the bots: It is called **EmailBot**, and it is defined in **EmailBot.py**.
  * For each service provider (like Gmail and Yahoo), a class is defined and implemented. For example, a bot for Gmail is implemented in GmailBot.py as a class **GmailBot**. Similarly, for Yahoo, a class named **YahooMailBot** is defined in **YahooMailBot.py**. At present these are the 2 service providers that have been implemented. Each of these classes are derived from the class **EmailBot.EmailBot**.
  * The python module for each service provider (GmailBot.py and YahooMailBot.py) has a function named **drvAccountCrawler**. This function implements a scraper to scrape messages from one of the configured accounts in the config file for the service provider. You may take a look at this code in order to see how to use a method of any of the classes.
  * Configuration files are located in a directory named _config_ in the same directory as GmailBot.py, YahooMailBot.py and EmailBot.py. Config files are used only by the _drvAccountCrawler_ function. If you plan to just import the classes in your code, you would not need them. The config file for Gmail is named **GmailBot.cfg**, and the one for Yahoo is named **YahooMailBot.cfg**.
  * A module named **Tools.Utils** (in _./Tools/Utils.py_) is also used by these classes and scripts. This module contains some utility functions that do not fit in the bot classes.