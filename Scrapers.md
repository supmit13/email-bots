# The Scraper Scripts #

  * **YahooMailBot.drvAccountCrawler()** function implements the Yahoo account crawler

  * **GmailBot.drvAccountCrawler()** function implements the Gmail account crawler


# Details #

**YahooMailBot.drvAccountCrawler()** and **GmailBot.drvAccountCrawler()** implement crawlers for the account specified in the configuration file. The configuration filename (including the path to it from the directory where the file YahooMailBot.py exists) may be specified as an argument to the _drvAccountCrawler()_ function. (For more information on the config file and its format, please refer to the section titled 'Configuration Details'). If no config file is specified as argument, the script tries to look for the config file in the default location, which is a directory named 'config' in the same directory as the script itself. Activities performed by the crawlers are:
  1. Log in into the account specified in the configuration file.
  1. Iterate through all folders (both user created folders/labels as well as system folders)
  1. Opens and reads each email message, and stores the data items in an in-memory data structure.
  1. Downloads, opens, reads and attempts to scrape information from all attachments in each email message it processes in step #3.
  1. Dumps the gathered information in the account to data file in one of the supported formats. The filename and the format would be user specified. The data is dumped periodically after processing an entire page of emails listing.
  1. It reads the following info from the config file: acctUserId, acctPasswd, outputFile, outputFormat, numThreads, canResume.
  1. 'acctUserId', 'acctPasswd', 'outputFile', 'outputFormat' and 'numThreads' are self explanatory. 'canResume' determines if the crawler can be paused in the middle of the operation and resumed later from the exact same state at the time it was paused. If 'canResume' is 'True', it can be paused and resumed later. If it is 'False' (or anything other than 'True'), then it cannot not be resumed from the same state.
  1. Supported values for 'outputFormat' are 'csv' and 'xml' (well, XML is NOT yet supported, but I am working on it and hope to release a new version with XML support (amongst other new additions) within the next month).

  * To see what the crawlers do, you may run them from the command line in the following manner:
> > ` $> python YahooMailBot.py `
> > > or

> > `    $> python GmailBot.py `


> (You need to navigate to the directory (named 'EmailBot') containing the YahooMailBot.py and GmailBot.py directory before trying the above exercise)

  * You may also take a look at the code of the crawler functions to see how the methods defined in the various classes have been used.