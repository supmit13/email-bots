import os, sys, re
import urllib, urllib2, htmllib
from urlparse import urlparse
import httplib
from BeautifulSoup import BeautifulSoup
import StringIO
import gzip
import time
import simplejson as json
from EmailBot import EmailBot, NoRedirectHandler
from Tools import Utils
from LogHandler import Logger
import datetime
import json
import random
import string
import cookielib



class YahooMailBot(EmailBot):
    
    startUrl=r"https://mail.yahoo.com/"
    logoutTagPattern = re.compile(r"<a\s+href\s*=\s*[\"\']?([^\"\']+)[\"\']?\s+[^>]+>\s+sign\s+out\s*<\/a>", re.IGNORECASE | re.MULTILINE | re.DOTALL)

    """
    Initialization would include fetching the login page of the email service.
    """
    def __init__(self, username="",passwd=""):
        # Create the opener object(s). Might need more than one type if we need to get pages with unwanted redirects.
        self.opener = urllib2.build_opener() # This is my normal opener....
        self.no_redirect_opener = urllib2.build_opener(urllib2.HTTPHandler(), urllib2.HTTPSHandler(), NoRedirectHandler()) # ... and this one won't handle redirects. We will mostly use this one for our purpose of scraping the yahoo mail account.
        #self.debug_opener = urllib2.build_opener(urllib2.HTTPHandler(debuglevel=1))
        # Initialize some object properties.
        self.sessionCookies = ""
        self.httpHeaders = { 'User-Agent' : r'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.2.10) Gecko/20111103 Firefox/3.6.24',  'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Accept-Language' : 'en-us,en;q=0.5', 'Accept-Encoding' : 'gzip,deflate', 'Accept-Charset' : 'ISO-8859-1,utf-8;q=0.7,*;q=0.7', 'Keep-Alive' : '115', 'Connection' : 'keep-alive', }
        self.homeDir = os.getcwd()
        self.requestUrl = self.__class__.startUrl
        parsedUrl = urlparse(self.requestUrl)
        self.baseUrl = parsedUrl.scheme + "://" + parsedUrl.netloc + "/"
        # First, get the Yahoo mail login page.
        self.pageRequest = urllib2.Request(self.requestUrl, None, self.httpHeaders)
        self.pageResponse = None
        self.requestMethod = "GET"
        self.postData = {}
        try:
            self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
            headers = self.pageResponse.info()
            if headers.has_key("Location"):
                self.requestUrl = headers["Location"]
                self.pageRequest = urllib2.Request(self.requestUrl, None, self.httpHeaders)
                try:
                    self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
                except:
                    print "Couldn't fetch page due to limited connectivity. Please check your internet connection and try again."
                    sys.exit()
        except:
            print "Couldn't fetch page due to limited connectivity. Please check your internet connection and try again"
            sys.exit()
        self.httpHeaders["Referer"] = self.requestUrl
        self.sessionCookies = self.__class__._getCookieFromResponse(self.pageResponse)
        self.httpHeaders["Cookie"] = self.sessionCookies
        # Initialize the account related variables...
        self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
        self.username = username
        self.password = passwd
        self.isLoggedIn = False
        self.lastChecked = None
        self.currentPageEmailsDict = {} # Holds the dict of emails listed on the page that is being read.
        self.currentPageEmailsDict2 = {} # Holds the dict of emails listed on the page that is being read.
        self.currentFolderLabel = "" # Holds the folder that is currently being read.
        self.currentPageNumber = -1 # Page number of the page that is currently being read.
        self.maxPageNumberCurrentFolder = 0 # Maximum page number for the folder that is currently being processed.
        self.currentInterfaceFormat = "html" # The value would be either "html" or "json". Default is "html". This attribute is also related to the 'newInterface' attribute. If this value is "html", then 'newInterface' has to be False and if it is "json" then 'newInterface' has to be True.
        self._totalEmailsInCurrentFolder = 0
        self.perPageEmailsCount = 25 # By default Yahoo mail displays 25 emails per page.
        self.accountActivity = [] # This will be a list of the memory usage line and the 'Last Account Activity' line.
        self.attachmentLocalStorage = None
        self.newInterface = False # We expect 2 types of interfaces. One is the older HTML interface and the other is the newer ajax interface. By default, we assume it is the older interface.
        self.newInterfaceMessagesList = [] # If 'newInterface' is True, then this list will contain data pertaining to the messages in the inbox (by default, inbox messages from the first page).
        self.wssid = ""
        self.signoutUrl = ""
	self.captchaUsername = ""
	self.captchaPassword = ""
	self.captchaService = "DeathByCaptcha"

    """
    Method to perform the login into the user account. It parses the login form to retrieve all the form variables that might be needed,
    builds the 'postData' and then submits the form to the appropriate URL.
    """
    def doLogin(self, username, passwd):
        if username != "":
            self.username = username
        if passwd != "":
            self.password = passwd
        if not self.username or not self.password:
            print "Can't login without credentials. Please set 'username' and 'password' and call again."
            return None
        soup = BeautifulSoup(self.currentPageContent)
        form = soup.find("form")
        # Now we need all the elements... We expect "input" tags only. 
        esoup = BeautifulSoup(form.renderContents())
        inputTags = esoup.findAll("input")
        # Some of the form variables need to be set to specific values for the login to work. On
        # the browser window, the javascript in the page accomplishes this task.
        for tag in inputTags:
            if tag.has_key("name"):
                if tag["name"] == "login":
                    self.postData[tag["name"]] = self.username
                    continue
                elif tag["name"] == "passwd":
                    self.postData[tag["name"]] = self.password
                    continue
                elif tag["name"] == ".ws":
                    self.postData[tag["name"]] = "1"
                    continue
                else:
                    self.postData[tag["name"]] = ""
            if tag.has_key("value"):
                self.postData[tag["name"]] = tag["value"]
        # Now get the form method and action too..
        if form.has_key("method"):
            self.requestMethod = form.get("method")
        else:
            self.requestMethod = "GET"
        if form.has_key("action"):
            self.requestUrl = form.get("action")
        urlencodedData = urllib.urlencode(self.postData) + "&.save=&passwd_raw=&passwd_raw="
        self.requestUrl = self.requestUrl[:-1]
        self.pageRequest = urllib2.Request(self.requestUrl, urlencodedData, self.httpHeaders)
        try:
            self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
        except:
            print "Could not post the form data to login - Error: " + sys.exc_info()[1].__str__()
            return None
        # First, get the session cookies...
        self.sessionCookies = self.__class__._getCookieFromResponse(self.pageResponse)
        self.httpHeaders["Cookie"] = self.sessionCookies
        self.httpHeaders["Referer"] = self.requestUrl
        # Next, get the content returned with the response... We expect this to be containing a json data structure.
        self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
        # Now, this data structure may be a redirect URL specifier or a Captcha challenge
        jsonDataStructure = json.loads(self.currentPageContent)
        # We expect this data structure to be a dictionary containing the keys 'status' and 'url' and also the values for those.
        if jsonDataStructure.has_key('url'):
            self.requestUrl = jsonDataStructure['url']
        else:
            print "The POST request encountered an error. Probably encountered a captcha."
            return (None)
        self.pageRequest = urllib2.Request(self.requestUrl, None, self.httpHeaders)
        try:
            self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
        except:
            print "Could not login in to account... Error: " + sys.exc_info()[1].__str__()
            print "Please try again after reviewing your credentials."
            return None
        self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
        # Now, the page content contains a meta http-equiv tag to refresh the page. We need to extract that.
        msoup = BeautifulSoup(self.currentPageContent)
        metaTag = msoup.find("meta", {'http-equiv' : "Refresh"})
        if metaTag and metaTag.has_key("content"):
            metaContent = metaTag.get("content")
            expectedPattern = re.compile(r"^0;\s*url=(.*)$", re.IGNORECASE)
            url = expectedPattern.search(metaContent).groups()[0]
            self.requestUrl = url
        else:
            print "Could not find any meta tag in content."
        tmpHttpHeaders = {}
        # Somehow, the browser skips the 'SSL' cookie. We need to do that, but I have no idea why we should.
        sslCookiePattern = re.compile(r"SSL=([^;]+);")
        for hdr in self.httpHeaders.keys():
            if hdr == "Referer":
                continue
            if hdr == "Cookie":
                cookies = self.httpHeaders['Cookie']
                cookies = re.sub(sslCookiePattern, "", cookies)
                tmpHttpHeaders['Cookie'] = cookies
                continue
            tmpHttpHeaders[hdr] = self.httpHeaders[hdr]
        self.pageRequest = urllib2.Request(self.requestUrl, None, tmpHttpHeaders)
        try:
            self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
        except:
            print "Could not login - Error: " + sys.exc_info()[1].__str__()
            return None
        # Now replace the cookie in httpHeaders with the value of the cookie sent
        self.httpHeaders['Cookie'] = tmpHttpHeaders['Cookie']
        self.httpHeaders['Referer'] = self.requestUrl
        self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
        self.isLoggedIn = self._assertLogin()
        if self.isLoggedIn:
            print "Successfully logged into the account for " + self.username
        return (self.isLoggedIn)


    def _getCookieFromResponse(cls, lastHttpResponse):
        cookies = ""
        responseCookies = lastHttpResponse.info().getheaders("Set-Cookie")
        pathCommaPattern = re.compile(r"path=/,", re.IGNORECASE)
        domainPattern = re.compile(r"Domain=[^;]+;", re.IGNORECASE)
        expiresPattern = re.compile(r"Expires=[^;]+;", re.IGNORECASE)
        if responseCookies.__len__() > 1:
            for cookie in responseCookies:
                cookieParts = cookie.split("path=/")
                cookieParts[0] = re.sub(domainPattern, "", cookieParts[0])
                cookieParts[0] = re.sub(expiresPattern, "", cookieParts[0])
                cookies += cookieParts[0]
            return(cookies)

    _getCookieFromResponse = classmethod(_getCookieFromResponse)

    """
    This method looks for the string 'You are signed in as'. If that is found in the page content,
    the method returns True. Otherwise this method will return False. 
    Note: Calling this also sets the 'signoutURL' attribute of the 'YahooMailBot' object.
    """
    def _assertLogin(self):
        assertPattern = re.compile(r"You are signed in as", re.MULTILINE | re.DOTALL)
        assertSearch = assertPattern.search(self.currentPageContent)
        if assertSearch:
	    self._getLogoutUrl()
            return (True)
        else:
            return (False)


    # This method gets the logout (or signout) URL and sets <obj>.signoutUrl with it.
    def _getLogoutUrl(self):
	if not self.currentPageContent:
	    self.signoutUrl = None
	    return None
	logoutTagSearch = self.__class__.logoutTagPattern.search(self.currentPageContent)
	if logoutTagSearch is not None:
	    self.signoutUrl = logoutTagSearch.groups()[0]
	    self.signoutUrl = Utils.decodeHtmlEntities(self.signoutUrl)
	else:
	    self.signoutUrl = None
	return(self.signoutUrl)


    """
    This method looks for the "Check Mail" button on the page and emulates the click event on it. Hence
    this method would be successful only if the page content has the "Check Mail" button somewhere.
    TO DO: This method cannot fetch the login page when the user has changed the skin to some value other than the default.
    """
    def fetchInboxPage(self):
        webPagePath = self.__class__._getPathToPage(self.requestUrl)
        soup = BeautifulSoup(self.currentPageContent)
        foundInboxUrl = False
        # First, we try to find out the form named 'frmChkMailtop'.
        topForm = soup.find("form", {'name' : 'frmChkMailtop'})
        if not topForm:
            self.newInterface = True # First, we rectify our assumption about the interface we are dealing with.
            self.currentInterfaceFormat = "json" # If 'newInterface' is True, then interface format has to be "json".
            # Could not find any form named 'frmChkMailtop'. 
            # Probably we are dealing with a co.<CountryCode> domain (like co.in or co.uk) or rocketmail.com or ymail.com (one with the newer interface)
            # If so, we are already in a page with the inbox emails list. However, we might not be in the proper ('Inbox') tab. But we will get the Inbox tab's
            # data right here in this page. The data for all emails in the inbox will appear after the string "NC.msgListObj=" in this page. Since
            # we expect this to be a json data structure, we will processes it accordingly.
            # Get the content between the <script></script> tags that contain the string 'NC.msgListObj='
            neoConfigPattern = re.compile(r"NC.msgListObj=\s*(.*);NC.msgListTmpl=.*$", re.DOTALL | re.MULTILINE)
            allScriptTags = soup.findAll("script")
            neoConfigContent = ""
            for script in allScriptTags:
                scriptContent = script.renderContents()
                scriptSearch = neoConfigPattern.search(scriptContent)
                if not scriptSearch:
                    continue
                neoConfigContent = scriptSearch.groups()[0]
                break
            # Remove invalid escape characters from content
            neoConfigContent = neoConfigContent.replace("\\ ", "\\")
	    if neoConfigContent == "": # If we couldn't find the script tag, may be we should search the entire page for the pattern
		scriptSearch = neoConfigPattern.search(self.currentPageContent)
		if scriptSearch is not None:
		    neoConfigContent = scriptSearch.groups()[0]
            jsonNeoConfigData = json.loads(neoConfigContent)
            messagesList = 0
            self.newInterfaceMessagesList = jsonNeoConfigData
            self.currentFolderLabel = "Inbox"
            self.currentPageNumber = 1
            self._totalEmailsInCurrentFolder = self.newInterfaceMessagesList.__len__()
            self.maxPageNumberCurrentFolder = int(self._totalEmailsInCurrentFolder/self.perPageEmailsCount) + 1
            wssidPattern = re.compile(r"wssid:\"([^\"]+)\",", re.DOTALL | re.MULTILINE)
            wssidSearch = wssidPattern.search(self.currentPageContent)
            if not wssidSearch:
                print "Could not retrieve the value of wssid from the page. Can't fetch the target message."
                return None
            self.wssid = wssidSearch.groups()[0]
            foundInboxUrl = True
        else:
            # First, get the request method and action URL (Method is not necessary, but we capture it for the sake of ... whatever!!!)
            if topForm.has_key("method"):
                self.requestMethod = topForm.get("method")
            else:
                self.requestMethod = "GET"
            if topForm.has_key("action"):
                self.requestUrl = topForm.get("action")
            if not self.__class__._isAbsoluteUrl(self.requestUrl):
                self.requestUrl = webPagePath + "/" + self.requestUrl
            foundInboxUrl = True
        if not foundInboxUrl:
            print "Could not find any link to the inbox page"
            return None
        if self.newInterface:
            return (self.currentPageContent)
        self.pageRequest = urllib2.Request(self.requestUrl, None, self.httpHeaders)
        try:
            self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
        except:
            print "Could not fetch the inbox page - Error: " + sys.exc_info()[1].__str__()
            return None
        self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
        self.currentFolderLabel = "Inbox"
        self.currentPageNumber = 1
        return (self.currentPageContent)

    """
    This method fetches the spam emails listing page (bulk folder). The contents of the page are
    returned as is, Since we request the result in JSON format, Yahoo sends a JSON output and the
    return value from this method is a JSON data structure. The page fetches the start page by 
    default and contains 20 email messages by default. User may override these values by passing a
    value for the second and third parameters. This method may be called anytime after logging in.
    """
    def fetchSpamPageJSON(self, page_num=1, num_emails=20):
	startInfo = page_num - 1
	self.requestUrl = "http://us.mg5.mail.yahoo.com/ws/mail/v2.0/formrpc?appid=YahooMailNeo&m=ListMessages&o=json&fid=%2540B%2540Bulk&sortKey=date&sortOrder=down&startInfo=" + startInfo.__str__() + "&numInfo=" + num_emails.__str__() + "&wssid=" + self.wssid
	self.pageRequest = urllib2.Request(self.requestUrl, None, self.httpHeaders)
	try:
	    self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
	except:
	    print "Could not fetch the spam listing page %s: Error %s\n"%(page_num.__str__(), sys.exc_info()[1].__str__())
	    return None
	self.currentPageContent = self.__class__.decodeGzippedContent(self.getPageContent())
	self.currentFolderLabel = "Spam"
	self.currentPageNumber = page_num
	return (self.currentPageContent)

    """
    This method returns a dictionary comprising of all the folders that the user has created.
    The folder names are the keys and their URLs are the values. The count of unread messages
    in each of these folders appear as a bracketted ("(\d)") entry with the folder names.
    """
    def getCustomFolders(self):
        webPagePath = self.__class__._getPathToPage(self.requestUrl)
        foldersDict = {}
        soup = BeautifulSoup(self.currentPageContent)
        if not self.newInterface:
            orderedListTag = soup.find("ol", {'class' : 'listings custom'})
            if not orderedListTag:
                print "Could not find any custom folders information on this page. Possibly you do not have any."
                return {}
            olContents = orderedListTag.renderContents()
            osoup = BeautifulSoup(olContents)
            allAnchorTags = osoup.findAll("a")
            for atag in allAnchorTags:
                url = ""
                if atag.has_key("href"):
                    url = atag.get("href")
                    if not self.__class__._isAbsoluteUrl(url):
                        url = webPagePath + "/" + url
                folderName = atag.renderContents()
                foldersDict[folderName] = url
        else:
            foldersPattern = re.compile(r";NC.folders=\s*(.*);NC.mailboxListTmpl=", re.DOTALL | re.MULTILINE)
            allScriptTags = soup.findAll("script")
            foldersData = ""
            for script in allScriptTags:
                scriptContent = script.renderContents()
                folderSearch = foldersPattern.search(scriptContent)
                if not folderSearch:
                    continue
                foldersData = folderSearch.groups()[0]
                break
	    if foldersData == "": # If we couldn't get the 'foldersData', may be we should search the entire page
		folderSearch = foldersPattern.search(self.currentPageContent)
		if folderSearch is not None:
		    foldersData = folderSearch.groups()[0]
            foldersDataStruct = json.loads(foldersData)
            if type(foldersDataStruct) == dict and foldersDataStruct.has_key("folder"):
                foldersList = foldersDataStruct['folder']
                for folder in foldersList:
                    if folder.has_key("isSystem") and folder['isSystem']:
                        continue
                    if not folder['isSystem']:
                        folderName = folder['folderInfo']['name']
                        fid = folder['folderInfo']['fid']
                        foldersDict[folderName] = fid
        return(foldersDict)
    

    """
    This method returns a dictionary with the built-in folder names as keys and
    their URLs as values. The count of unread messages in each folder also 
    appears alongwith the names in the keys.
    """
    def getAvailableFolders(self):
        webPagePath = self.__class__._getPathToPage(self.requestUrl)
        foldersDict = {}
        soup = BeautifulSoup(self.currentPageContent)
        if not self.newInterface:
            divTag = soup.find("div", {'id' : 'defaultfolders'})
            if not divTag: # Could not find the available folders.... probably because we have encountered the new yahoo interface.
                return ({}) # TO DO: Handle the new interface here...
            divContents = divTag.renderContents()
            asoup = BeautifulSoup(divContents)
            allAnchorTags = asoup.findAll("a")
            for atag in allAnchorTags:
                url = ""
                if atag.has_key("href"):
                    url = atag.get("href")
                    if not self.__class__._isAbsoluteUrl(url):
                        url = webPagePath + "/" + url
                folderName = atag.renderContents()
		folderName = re.sub(self.__class__.htmlTagPattern, "", folderName)
		folderName = folderName.strip()
		if folderName == "":
		    continue
		if folderName == "Drafts":
		    folderName = "Draft"
                foldersDict[folderName] = url
        else:
            ulTag = soup.find("ul", {'id' : 'system-folders'})
	    ulContents = ""
	    if not ulTag:
		ulPattern = re.compile(r"<ul\s+id=\"system-folders\"\s+[^>]+>(.*)</ul>", re.IGNORECASE | re.MULTILINE | re.DOTALL)
		ulSearch = ulPattern.search(self.currentPageContent)
		if ulSearch is not None:
		    ulContents = ulSearch.groups()[0]
	    else:
            	ulContents = ulTag.renderContents()
            ulSoup = BeautifulSoup(ulContents)
            allLiTags = ulSoup.findAll("li")
            for liTag in allLiTags:
                liContents = liTag.renderContents()
                liSoup = BeautifulSoup(liContents)
                aTag = liSoup.find("a")
                iTag = liSoup.find("i")
		if not iTag:
		    continue
                folderName = iTag.renderContents()
                url = aTag.get("href")
		folderName = folderName.strip()
		if folderName == "":
		    continue
		if folderName == "Drafts":
		    folderName = "Draft"
                foldersDict[folderName] = url
        return(foldersDict)
            

    """
    This won't be implemented for Yahoo mail as there is no straight forward method
    to find the date and time at which the current user logged in previously. (In fact,
    I am not sure if yahoo provides that sort of info in any way in their mail service
    interface. Any idea if they do ????)
    """
    def getAccountActivity(self):
        pass


    """
    This method fetches the list of emails on the page currently being processed.
    (The current page content will be in 'currentPageContent' attribute.)
    This method populates the 'currentPageEmailsDict' attribute of the caller object.
    The keys of the dictionary are subjects of the listed emails while the values
    are lists containing the following information in the order specified:
    sender, msgUrl, partialContent, dateReceived.
    Note: Please call this method in a try/except block so that unicode characters
    existing as part of subject lines or message contents do not throw an error.
    TODO: Add unicode support.
    """
    def listEmailsOnPage(self, folder="Inbox", page=1):
        pageBaseUrl = self.__class__._getPathToPage(self.requestUrl)
        self.currentPageEmailsDict = {}
        self.currentPageEmailsDict2 = {}
	if self.currentFolderLabel.lower() != "inbox":
	    self._listEmailsInCurrentFolderPage()
	    return(self.currentPageEmailsDict2)
        if not self.newInterface:
	    content = self.currentPageContent
	    messagesListBlockTopPattern = re.compile(r"Flag\s+for\s+Follow-up", re.IGNORECASE | re.MULTILINE | re.DOTALL)
	    pageParts1 = messagesListBlockTopPattern.split(content)
	    if pageParts1.__len__() > 1:
		content = pageParts1[1]
            soup = BeautifulSoup(content)
            tableTag = soup.find("table", {"id" : "datatable"})
            if not tableTag:
                print "Could not find any emails in the current folder."
                return ({})
            dataTableContents = tableTag.renderContents()
            dataSoup = BeautifulSoup(dataTableContents)
            allTrs = dataSoup.findAll("tr")
            for tr in allTrs:
                trSoup = BeautifulSoup(tr.renderContents())
                sender, subject, msgUrl, recvdDate, readFlag = (None, None, None, None, True)
                if tr.has_key("class") and tr["class"] == "msgnew":
                    readFlag = False # Unread message
                # Find all td tags in the tr 
                allTds = trSoup.findAll("td")
                senderTd = None
                for td in allTds:
                    if td.has_key("title"):
                        senderTd = td
                        break
                sender = ""
                if senderTd:
                    sender = senderTd.get("title")
                h2Tag = trSoup.find("h2")
                if h2Tag:
                    hSoup = BeautifulSoup(h2Tag.renderContents())
                    subjectATag = hSoup.find("a")
                    msgUrl = subjectATag.get("href")
                    subject = subjectATag.renderContents()
                    subject.strip()
                else:
                    subject = ""
                    msgUrl = ""
                if not self.__class__._isAbsoluteUrl(msgUrl):
                    msgUrl = pageBaseUrl + "/" + msgUrl
                dateTdTag = trSoup.find("td", {"class" : "sortcol"})
                recvdDate = ""
                if dateTdTag:
                    recvdDate = dateTdTag.renderContents
                self.currentPageEmailsDict[subject] = [sender, msgUrl, "", recvdDate, readFlag]
                self.currentPageEmailsDict2[msgUrl] = [sender, msgUrl, subject, recvdDate, readFlag]
        else:
            unreadPattern = re.compile(r"unread", re.IGNORECASE)
            for message in self.newInterfaceMessagesList:
                subject = message['subject']
                sender = ""
                if message.has_key("fromObj"):
                    sender = message['fromObj']
                elif message.has_key("from"):
                    senderObj = message["from"]
                    if senderObj.has_key("email"):
                        sender = senderObj["email"]
                    elif senderObj.has_key("name"):
                        sender = senderObj["name"]
                    else:
                        sender = "Unidentified"
                else:
                    sender = "Unidentified"
                mid = message['mid']
                readFlag = 'True'
                flags = ""
                if message.has_key("flags"):
                    flags = message['flags']
                    if type(flags) == dict:
                        if flags["isRead"]:
                            readFlag = 'True'
                        else:
                            readFlag = 'False'
                    elif unreadPattern.search(flags):
                        readFlag = 'False'
                content = "" # Initialize 'content'
                partialContent = content + " ..."
                if len(content) > 25:
                    partialContent = content[:25] + " ..." # We will store the first 25 characters as the partial content if content exceeds 25 characters.
                recvdDate = ""
                if message.has_key('rawDate'):
                    recvdDate = message['rawDate'].__str__()
                elif message.has_key('receivedDate'):
                    recvdDate = message['receivedDate'].__str__()
                msgUrl = mid
                self.currentPageEmailsDict[subject] = [sender, msgUrl, partialContent, recvdDate, readFlag]
                self.currentPageEmailsDict2[msgUrl] = [sender, msgUrl, subject, recvdDate, readFlag]
        return(self.currentPageEmailsDict2)


    def getNextPageUrl(self):
        webPagePath = self.__class__._getPathToPage(self.requestUrl)
        nextPageUrl = webPagePath
        if not self.newInterface:
            searchPattern = re.compile(r"Next\s*Page", re.IGNORECASE)
            soup = BeautifulSoup(self.currentPageContent)
            allAnchors = soup.findAll("a")
            for anchor in allAnchors:
                aText = anchor.getText()
                aSearch = searchPattern.search(aText)
                if aSearch:
                    url = anchor.get("href")
                    if not self.__class__._isAbsoluteUrl(url):
                        nextPageUrl += "/" + url
                    else:
                        nextPageUrl = url
                    break
                continue
            return(nextPageUrl)
        else:
            if self.currentPageNumber <= int(self._totalEmailsInCurrentFolder / self.perPageEmailsCount) + 1:
                parsedUrl = urlparse(self.requestUrl)
                self.baseUrl = parsedUrl.scheme + "://" + parsedUrl.netloc + "/"
                startNumber = self.currentPageNumber * self.perPageEmailsCount
                endNumber = startNumber + self.perPageEmailsCount
                nextPageUrl = self.baseUrl + "ws/mail/v2.0/formrpc?appid=YahooMailNeo&m=ListMessages&o=json&fid=" + self.currentFolderLabel + "&sortKey=date&sortOrder=down&startInfo=" + startNumber.__str__() + "&numInfo=" + endNumber.__str__() + "&wssid=" + self.wssid
            else:
                nextPageUrl = None # Probably there are no more pages.
            return(nextPageUrl)
        

    # This method calls the 'getNextPageUrl()' method and fetches the next page of listing for the folder
    # being processed currently. The current folder can be obtained from '<ybotObj>.currentFolderLabel'.
    def getNextPage(self):
        if not self.newInterface:
            self.requestUrl = self.getNextPageUrl()
            if not self.requestUrl:
                return None
            self.pageRequest = urllib2.Request(self.requestUrl, None, self.httpHeaders)
            try:
                self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
            except:
                print "Could not fetch the next page."
                return None
            self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
            self.currentPageNumber += 1
            return(self.currentPageContent)
        else:
            nextPageUrl = self.getNextPageUrl()
            print "Fetching next page through URL: %s"%nextPageUrl.__str__()
            if not nextPageUrl:
                print "There is no next page."
                return None
            else:
                self.requestUrl = nextPageUrl
                tmpHttpHeaders = {}
                for hk in self.httpHeaders.keys():
                    tmpHttpHeaders[hk] = self.httpHeaders[hk]
                self.pageRequest = urllib2.Request(self.requestUrl, None, tmpHttpHeaders)
                try:
                    self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
                except:
                    print "Could not fetch next page - Error: " + sys.exc_info()[1].__str__()
                self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
                jsonNeoConfigData = json.loads(self.currentPageContent)
                messagesList = 0
                newMessagesList = None
                if jsonNeoConfigData.has_key("messageInfo"):
                    newMessagesList = jsonNeoConfigData["messageInfo"]
                self.newInterfaceMessagesList = newMessagesList
                self.currentPageNumber += 1
            return(self.currentPageContent)
        
    
    # The following 2 methods 'openFolderPage' and 'getFolderPage' perform the same 
    # function: they both navigate to the Folder page whose name is passed in as an
    # argument. However, they are different in terms of the state of the object at 
    # the end of the method. 'openFolderPage' doesn not modify the caller object much,
    # whereas the 'getFolderPage' method sets the caller objects attributes like 
    # 'currentPageContent', 'requestUrl', 'pageRequest', 'pageResponse', 
    # 'maxPageNumberCurrentFolder', '_totalEmailsInCurrentFolder' and 'newInterfaceMessagesList'. 
    # The attributes 'currentFolderLabel' and 'currentPageNumber' are set by both methods.
    def openFolderPage(self, foldername):
	if not self.wssid or self.wssid == "":
	    print "Cannot navigate to %s folder - wssid is not set."%foldername
	    return (None)
	rval = int(time.time() * 1000)
	parsedUrl = urlparse(self.requestUrl)
        self.baseUrl = parsedUrl.scheme + "://" + parsedUrl.netloc + "/"
	folderPageUrl = self.baseUrl + "ws/mail/v2.0/formrpc?appid=YahooMailNeo&m=ListMessages&o=json&fid=%s&sortKey=date&sortOrder=down&startInfo=0&numInfo=50&wssid=%s&r=%s"%(foldername, self.wssid, rval.__str__())
	folderPageRequest = urllib2.Request(folderPageUrl, None, self.httpHeaders)
	folderPageContent = ""
	try:
            folderPageResponse = self.no_redirect_opener.open(folderPageRequest)
	    folderPageContent = self.__class__._decodeGzippedContent(folderPageResponse.read())
        except:
            print "Could not fetch '%s' folder page - Error: %s"%(foldername, sys.exc_info()[1].__str__())
	self.currentFolderLabel = foldername
        self.currentPageNumber = 1
	return (folderPageContent)


    # Please refer to the explanation for 'openFolderPage()' method above.
    def getFolderPage(self, foldername):
	if not self.wssid or self.wssid == "":
	    print "Cannot navigate to %s folder - wssid is not set."%foldername
	    return (None)
	rval = int(time.time() * 1000)
	parsedUrl = urlparse(self.requestUrl)
        self.baseUrl = parsedUrl.scheme + "://" + parsedUrl.netloc + "/"
	self.requestUrl = self.baseUrl + "ws/mail/v2.0/formrpc?appid=YahooMailNeo&m=ListMessages&o=json&fid=%s&sortKey=date&sortOrder=down&startInfo=0&numInfo=50&wssid=%s&r=%s"%(foldername, self.wssid, rval.__str__())
	print "Folder '%s' page URL: %s"%(foldername, self.requestUrl)
	self.pageRequest = urllib2.Request(self.requestUrl, None, self.httpHeaders)
	try:
            self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
	    self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
        except:
            print "Could not fetch '%s' folder page - Error: %s"%(foldername, sys.exc_info()[1].__str__())
	    return(None)
	# Set the following attributes: self.newInterfaceMessagesList, self.currentFolderLabel, self._totalEmailsInCurrentFolder, self.currentPageNumber and self.maxPageNumberCurrentFolder
	self.currentFolderLabel = foldername
        self.currentPageNumber = 1
	self._totalEmailsInCurrentFolder = 0
	# We need to parse the 'self.currentPageContent' value to retrieve the values of self._totalEmailsInCurrentFolder, self.newInterfaceMessagesList, and self.maxPageNumberCurrentFolder. We will use regexes for that. So, here we go...
	ncFoldersPattern = re.compile(r";\s*NC\.folders\s*=\s*", re.MULTILINE | re.DOTALL)
	ncMailBotListTmplPatterrn = re.compile(r";\s*NC\.mailboxListTmpl\s*=\s*\{", re.MULTILINE | re.DOTALL)
	foldersInfoJSONString = None
	contentParts = re.split(ncFoldersPattern, self.currentPageContent)
	if contentParts.__len__() > 1:
	    moreParts = re.split(ncMailBotListTmplPatterrn, contentParts[1])
	    foldersInfoJSONString = moreParts[0]
	else:
	    moreParts = re.split(ncMailBotListTmplPatterrn, contentParts[0])
	    foldersInfoJSONString = moreParts[0]
	if foldersInfoJSONString is None:
	    self._totalEmailsInCurrentFolder = None
	    print "Could not find the number of emails contained in the current folder '%s'."%self.currentFolderLabel
	    return (self.currentPageContent)
	folderInfoJSONDS = json.loads(foldersInfoJSONString)
	if folderInfoJSONDS.has_key('folder'):
	    allFoldersInfo = folderInfoJSONDS['folder']
	    if type(allFoldersInfo) == list:
	    	for finfo in allFoldersInfo:
		    finfo = dict(finfo)
		    if finfo.has_key('folderInfo') and finfo['folderInfo'].has_key('name') and finfo['folderInfo']['name'].lower() == foldername.lower():
		    	if finfo.has_key('unread'):
		    	    self._totalEmailsInCurrentFolder = finfo['unread']
		    	if finfo.has_key('read'):
			    self._totalEmailsInCurrentFolder += finfo['read']
		    	break
	    else:
		self._totalEmailsInCurrentFolder = folderInfoJSONDS['folder']['total']
	self.maxPageNumberCurrentFolder = int(self._totalEmailsInCurrentFolder/self.perPageEmailsCount) + 1
	return (self.currentPageContent)


    # This method extracts the list of emails from the json data structure returned as the contents of the folder. 
    # It is relevant for all folders except 'Inbox', which is taken care of by the method 'listEmailsOnPage()'. Actually,
    # this method is called from within 'listEmailsOnPage()', so calling 'listEmailsOnPage()' handles all folders.
    # Like 'listEmailsOnPage()', it populates the attributes 'currentPageEmailsDict' and currentPageEmailsDict2', and
    # returns 'currentPageEmailsDict2' of the YahooMailBot object. Please note that this method handles only the new
    # interface case. The older interface with HTML content is not handled by this method (and trying to use it in such
    # cases raises an exception).
    def _listEmailsInCurrentFolderPage(self):
	if not self.newInterface: # Works for new interface only.
	    return (None)
	pageBaseUrl = self.__class__._getPathToPage(self.requestUrl)
        self.currentPageEmailsDict = {}
        self.currentPageEmailsDict2 = {}
	pageContent = self.currentPageContent
	if self.currentFolderLabel.lower() == "inbox":
	    return None
	# We expect the page content to be a JSON data structure. Also, this method handles only the new interface case.
	jsonDS = json.loads(self.currentPageContent)
	if type(jsonDS) != dict: # if the data structure is not a dict, then we probably have a problem.
	    print "Did not receive a dictionary object. Probably not a data structure we were expecting for the folder '%s'"%self.currentFolderLabel
	    return(None)
	messagesList = []
	if jsonDS.has_key("messageInfo"):
	    messagesList = jsonDS['messageInfo'] # This would be a list of dictionaries.
	else:
	    return (self.currentPageEmailsDict2) # The folder has no messages.
	for messageDict in messagesList:
	    sender = ""
	    if messageDict.has_key("from"):
		sender = messageDict['from']['email']
	    msgUrl = ""
	    if messageDict.has_key("mid"):
		msgUrl = messageDict['mid']
	    subject = ""
	    if messageDict.has_key("subject"):
		subject = messageDict['subject']
	    recvdDate = ""
	    if messageDict.has_key("receivedDate"):
		recvdDate = messageDict['receivedDate'] # This is a timestamp.
	    readFlag = False
	    if messageDict.has_key("flags"):
		if messageDict['flags']['isRead'] == 1:
		    readFlag = True
	    self.currentPageEmailsDict2[msgUrl] = [sender, msgUrl, subject, recvdDate, readFlag]
	    self.currentPageEmailsDict[subject] = [sender, msgUrl, "", recvdDate, readFlag] # Partial content is not available in new interface.
	return(self.currentPageEmailsDict2)


    def getTotalMailsInCurrentFolder(self):
        if not self.newInterface:
	    count = 0
	    expectedPattern = re.compile(r"Messages\s+\d+-\d+\s+of\s+(\d+)")
            soup = BeautifulSoup(self.currentPageContent)
            divTag = soup.find("div", {'role' : "navigation"})
	    if divTag is not None:
            	divSearch = expectedPattern.search(divTag.renderContents())
            	if not divSearch:
                    print "Could not find the total count of emails in current folder"
                    return (0)
            	count = divSearch.groups()[0]
	    else:
		expectedPatternSearch = expectedPattern.search(self.currentPageContent)
		if expectedPatternSearch is not None:
		    count = expectedPatternSearch.groups()[0]
            self._totalEmailsInCurrentFolder = count
	else:
	    pass
	    # For new interface, try to fetch the email counts in each folder in the 'getAvailableFolders()' and 'getCustomFolders()' methods.
        return(int(self._totalEmailsInCurrentFolder))

    """
    Fetches the message content whose URL (or 'mid' for new interface) has been passed in as argument. Returns the message content.
    Note: For the older interface (HTML interface), the content is returned as well as the 'currentPageContent' attribute is
    modified. However, for the newer version, the 'currentPageContent' attribute is not affected since the response is a json
    data structure and assigning that to 'currentPageContent' would not be appropriate. So it would be safer if you use the
    returned value from this method rather than trying to figure what 'currentPageContent' contains after calling it.
    TO DO: Handle unicode.
    """
    def fetchEmailMessage(self, msgUrl):
        if not self.newInterface:
            msgRequest = urllib2.Request(msgUrl, None, self.httpHeaders)
            try:
                msgResponse = self.no_redirect_opener.open(msgRequest)
            except:
                print "Could not fetch the message - Error: " + sys.exc_info()[1].__str__()
                return None
            msgContent = self.__class__._decodeGzippedContent(msgResponse.read())
            return (msgContent)
        else: # If it is the new interface then we need to make a POST request with json data.
            parsedUrl = urlparse(self.requestUrl)
            self.baseUrl = parsedUrl.scheme + "://" + parsedUrl.netloc + "/"
            rval = int(time.time() * 1000)
            msgRequestUrl = self.baseUrl + r"ws/mail/v2.0/jsonrpc?appid=YahooMailNeo&m=GetDisplayMessage&wssid=%s&r=%s"%(self.wssid, rval.__str__())
            jsonData = '{"method":"GetDisplayMessage","params":[{"fid":"Inbox","enableRetry":true,"textToHtml":true,"urlDetection":true,"emailDetection":true,"emailComposeUrl":"mailto:%e%","truncateAt":100000,"charsetHint":"","annotateOption":{"annotateText":"inline"},"message":[{"blockImages":"none","restrictCSS":true,"expandCIDReferences":true,"enableWarnings":true,"mid":"' + msgUrl + '"}]}]}'
            tmpHttpHeaders = {}
            for hk in self.httpHeaders.keys():
                tmpHttpHeaders[hk] = self.httpHeaders[hk]
            tmpHttpHeaders["Content-Type"] = "application/json; charset=UTF-8"
            tmpHttpHeaders["Accept"] = "application/json"
            tmpHttpHeaders["Content-Length"] = len(jsonData)
            tmpHttpHeaders["Pragma"] = "no-cache"
            tmpHttpHeaders["Cache-Control"] = "no-cache"
            msgRequest = urllib2.Request(msgRequestUrl, jsonData, tmpHttpHeaders)
            msgResponse = None
            messageContent = ""
            try:
                msgResponse = self.no_redirect_opener.open(msgRequest)
                messageContent = self.__class__._decodeGzippedContent(msgResponse.read())
            except:
                print "Could not fetch message - Error: " + sys.exc_info()[1].__str__()
                return None
            # Note: messageContent is json data. So you would want to parse it before using it.
            return (messageContent)
        return (None)

    """
    This method enables the user to send emails through the account currently being probed. 'msgDict' is a dictionary
    with the following keys: 'Subject', 'Sender', 'Recipients', 'CcRecipients', 'BccRecipients', 'MessageBody', 'Attachments'.
    The keys are mostly self explanatory. 'Subject' specifies the subject line string, 'Sender' specifies the sender's email
    Id, 'Recipients', 'CcRecipients' and 'BccRecipients' are lists of strings for specifying recipients, cc and bcc fields,
    'MessageBody' specifies the actual message content and 'Attachments' specify the attached filename and its path (if any).
    Status: Needs a lot of testing. Doesn't work always as expected. Needs to be fine-tuned.
    """
    def sendEmailMessage(self, msgDict):
        webPagePath = self.__class__._getPathToPage(self.requestUrl)
        foundFlag = False
        # First, get the compose page...
        if not self.newInterface:
            soup = BeautifulSoup(self.currentPageContent)
            composePattern = re.compile(r"compose\?&", re.MULTILINE | re.DOTALL)
            allForms = soup.findAll("form")
            for form in allForms:
                if form.has_key("action"):
                    composeSearch = composePattern.search(form["action"])
                    if not composeSearch:
                        continue
                    else:
                        self.requestUrl = webPagePath + "/" + form["action"]
                        foundFlag = True
                        break
            if not foundFlag:
                print "Could not find the 'New' button to compose email. Please check if you are logged out."
                return None
            self.pageRequest = urllib2.Request(self.requestUrl, None, self.httpHeaders)
            try:
                self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
            except:
                print "Could not fetch the page to compose message.... Something didn't work right. Please try again"
                print "If you encounter this problem repeatedly, please let me know (you_know_who_13@rocketmail.com)."
            self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
            # At this point we have the page where we need to type in our email message.
            soup = BeautifulSoup(self.currentPageContent)
            form = soup.find("form", {'name' : "Compose"})
            formSoup = BeautifulSoup(form.renderContents())
            self.requestUrl = webPagePath + "/" + form["action"]
            # Find all input tags
            allInputTags = formSoup.findAll("input")
            textarea = formSoup.find("textarea", {'name' : 'Content'})
            messageData = {}
            for input in allInputTags:
                if input["type"] == "hidden":
                    name = input["name"]
                    messageData[name] = input["value"]
                elif input["type"] == "text":
                    name = input["name"]
                    if name == "to":
                        recipientsString = ",".join(msgDict['Recipients'])
                        messageData[name] = recipientsString
                    elif name == "cc":
                        ccString = ",".join(msgDict['CcRecipients'])
                        messageData[name] = ccString
                    elif name == "bcc":
                        bccString = ",".join(msgDict['BccRecipients'])
                        messageData[name] = bccString
                    elif name == "Subj":
                        subjectString = msgDict['Subject']
                        messageData[name] = subjectString
                    else:
                        if input.has_key("value"):
                            messageData[name] = input["value"]
                        else:
                            messageData[name] = ""
            messageData['Content'] = msgDict['MessageBody']
            # Some specific parameters....
            messageData['ymcjs'] = '1'
            messageData['action_msg_send'] = "Send"
            encodedMessageData = urllib.urlencode(messageData)
            tmpHttpHeaders = {}
            for hk in self.httpHeaders.keys():
                tmpHttpHeaders[hk] = self.httpHeaders[hk]	
            tmpHttpHeaders["Content-Type"] = "application/x-www-form-urlencoded"
            tmpHttpHeaders["Content-Length"] = len(encodedMessageData)
            self.pageRequest = urllib2.Request(self.requestUrl, encodedMessageData, tmpHttpHeaders)
            try:
                self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
            except:
                print "Could not send message - Error: " + sys.exc_info()[1].__str__()
                return None
            self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
            if self._assertMessageSent(self.currentPageContent):
                print "Message sent successfully."
            else:
                # Message could not be sent as yet. That means we might have encountered a captcha or we might have erred elsewhere. First, we try to see if a captcha challenge has been thrown.
                captchaSoup = BeautifulSoup(self.currentPageContent)
                captchaDiv = captchaSoup.find("div", {'id' : 'captchacontent'})
                if not captchaDiv: # Some other error has taken place... We give up our chance to send the email for now.
                    print "Failed to send the message. Try again."
                    return None
                # Captcha challenge encountered. We try to retrieve the captcha image.
                captchaImage = captchaDiv.findNext("img")
                captchaUrl = ""
                if captchaImage and captchaImage.has_key("src"):
                    captchaUrl = captchaImage["src"]
                else:
                    print "Could not find captcha image URL. Check if the captcha container tag ID has changed"
                    return None
                # Add 3 more fields to the POST data ...
                messageData['notFirst'] = '1'
                messageData['send'] = 'Continue'
                messageData['answer'] = "" # This will be the captcha string value. We will now try to solve the captcha and populate this field.
                # Get the captcha file
                captchaRequest = urllib2.Request(captchaUrl, None, self.httpHeaders)
                try:
                    captchaResponse = self.no_redirect_opener.open(captchaRequest)
                except:
                    print "Could not fetch captcha image - Error: " + sys.exc_info()[1].__str__()
                    return None
                ## Solve captcha here....
                captchaImage = captchaResponse.read()
                ## Once that is done, make a POST request again with the data in messageData
                encodedMessageData = urllib.urlencode(messageData)
                tmpHttpHeaders['Content-Length'] = len(encodedMessageData)
                self.pageRequest = urllib2.Request(self.requestUrl, encodedMessageData, tmpHttpHeaders)
                try:
                    self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
                except:
                    print "Could not send message - Error: " + sys.exc_info()[1].__str__()
                    return None
                self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
                if self._assertMessageSent(self.currentPageContent):
                    print "Message sent successfully."
                else:
                    print "Aborting message send operation."
            return(self.currentPageContent)
        else:
            pass

    def _assertMessageSent(self, pageContent):
        if not self.newInterface:
            soup = BeautifulSoup(pageContent)
            div = soup.find("div", {'class' : 'msgContent'})
            if div:
                h2Text = div.findNext("h2").renderContents()
                if h2Text == "Message Sent":
                    return True
            else:
                return False
        else:
            pass

    """
    This method fetches the contents of the page whose URL is passed in as argument.
    This method is supposed to be a shortcut for accessing any of the folder or message pages.
    Status: Yet to be implemented.
    """
    def getPage(self, pageUrl):
        pass

    """
    This method will try to retrieve the message pointed to by the 'msgUrl' parameter, and then
    try to get any attachments that might exist in the email.
    Status: Yet to be implemented
    """
    def getAttachmentsFromMessage(self, msgUrl, localDir):
        self.attachmentLocalStorage = localDir
	messageContent = msgHTML
	soup = BeautifulSoup(messageContent)


    """
    This method retrieves the list of all the attachments in your emails. By default, it takes you to
    the first page, but specifying a page number will take you to the specified page. It returns the
    HTML of the page which is retrieved.
    Status: Yet to be implemented
    """
    def getAttachmentsPage(self, page=1):
        pass


    # Method to logout of the account. Depends on whether the 'signoutUrl' had been
    # extracted while asserting the success of 'doLogin()' method. Thus, this will 
    # not be able to perform successfully if '_assertLogin()' was never called.
    def doLogout(self):
	if not self.signoutUrl:
	    print "Signout URL is not available. Cannot logout of account."
	    return(None)
	self.requestUrl = self.signoutUrl
	self.pageRequest = urllib2.Request(self.requestUrl, None, self.httpHeaders)
	try:
	    self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
	    headers = self.pageResponse.info()
            if headers.has_key("Location"):
                self.requestUrl = headers["Location"]
                self.pageRequest = urllib2.Request(self.requestUrl, None, self.httpHeaders)
                try:
                    self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
		    print "Logged out of account completely."
		    return(1)
                except:
                    print "Couldn't complete logout action - Error: %s"%sys.exc_info()[1].__str__()
		    return (None)
	    else:
		print "Could not logout completely as expected. Unknown error."
		return(None)
        except:
            print "Could not logout - Error: %s"%sys.exc_info()[1].__str__()
            return (None)


    # Method to extract the email message from the HTML content of the message page.
    # Handling of old interface cases is still not perfect. The new interface is handled
    # successfully. The method strips all HTML tags that are part of the message and 
    # returns only the unformatted text content of the message.
    def extractEmailMessage(self, htmlContent):
	messageText = None
	if not self.newInterface:
	    bsoup = BeautifulSoup(htmlContent)
	    divTag = bsoup.find("div", { 'id' : 'mailContent' })
	    if divTag is not None:
		divContents = divTag.renderContents()
		divSoup = BeautifulSoup(divContents)
		tableTag = divSoup.find("table", {'class' : re.compile(r"yiv\d+container")})
		if not tableTag:
		    messageText = divContents
		else:
		    messageText = tableTag.renderContents()
	    else:
		print "Could not find the message text from the HTML."
		messageText = ""
	    # Strip the 'messageText' off the 'tr', 'td' and 'tbody' start and end tags
	    tdTagPattern = re.compile(r"<\/?td>", re.IGNORECASE | re.MULTILINE | re.DOTALL)
	    trTagPattern = re.compile(r"<\/?tr>", re.IGNORECASE | re.MULTILINE | re.DOTALL)
	    tbodyTagPattern = re.compile(r"<\/?tbody>", re.IGNORECASE | re.MULTILINE | re.DOTALL)
	    messageText = re.sub(tbodyTagPattern, "", messageText)
	    messageText = re.sub(trTagPattern, "", messageText)
	    messageText = re.sub(tdTagPattern, "", messageText)
	    return(messageText)
	# Code for new interface
	divMsgPattern = re.compile(r"aria-label=\"Message\s+Body\"", re.MULTILINE | re.DOTALL)
	quickReplyPattern = re.compile(r"<div\s+id=\"quick-reply\"", re.MULTILINE | re.DOTALL)
	message = htmlContent
	htmlParts = divMsgPattern.split(message)
	if htmlParts.__len__() > 1:
	    message = htmlParts[1]
	htmlParts2 = quickReplyPattern.split(message)
	if htmlParts2.__len__() > 1:
	    message = htmlParts2[0]
	message = re.sub(EmailBot.htmlTagPattern, " ", message)
	# Now extract the actual message text from the JSON string that we have in message.
	try:
	    jsonDS = json.loads(message)
	    messageText = jsonDS['result']['message'][0]['part'][0]['text']
	except:
	    print "Could not interpret the contents as expected - %s"%(sys.exc_info()[1].__str__())
	    print "Returning the message content unaltered."
	    messageText = message
	return(messageText)


    # This method retrieves all the account settings and loads
    # the dictionary 'accountSettings' (inherited from 'EmailBot').
    # It also dumps the data structure as an XML file if 'dumpFile'
    # argument is specified as a path to a file in a writable dir.
    # By default, however, it doesn't dump the account settings.
    def getAccountSettings(self, dumpFile=None):
	pass

    # Get all available contacts information. This method populates the 
    # 'self.allContacts' dictionary (inherited from 'EmailBot') with the 
    # collected contacts information. This method should be called before
    # navigating to any of the folders or inbox page. The return value 
    # is the count of keys in 'self.allContacts' dictionary. If something 
    # fails while operation, the method returns 'None'.
    # Note: Best time to call this method is immediately after 'doLogin()'.
    def getContactsInfo(self):
	pageBaseUrl = self.__class__._getPageBaseURL(self.currentPageContent)
	#soup = BeautifulSoup(self.currentPageContent)
	# Use regex to get the 'data-guid'
	dataGuidPattern = re.compile(r"data\-guid\s*=\s*\"([^\"]+)\"", re.MULTILINE | re.DOTALL)
	dataGuidSearch = dataGuidPattern.search(self.currentPageContent)
	data_guid = None
	self.allContacts = {}
	if dataGuidSearch:
	    data_guid = dataGuidSearch.groups()[0]
	else:
	    print "Could not retrieve data-guid to fetch contacts info."
	    return (None)
	rval = int(time.time() * 1000)
	contactsUrl = "http://in.mg61.mail.yahoo.com/yab-fe/dc/ws/sd?/v1/user/%s/contacts;out=guid,nickname,email,yahooid,otherid,phone,jobtitle,company,notes,link,custom,name,address,birthday,anniversary;count=max?format=json&view=compact&wssid=%s&_sc=0&r=%s"%(data_guid, self.wssid, rval.__str__())
	contactsRequest = urllib2.Request(contactsUrl, None, self.httpHeaders)
	try:
            contactsResponse = self.no_redirect_opener.open(contactsRequest)
        except:
            print "Could not fetch Contacts information - Error: " + sys.exc_info()[1].__str__()
            return None
        contactsPageContent = self.__class__._decodeGzippedContent(contactsResponse.read())
	contactsDS = json.loads(contactsPageContent)
	if not contactsDS.has_key("contacts"):
	    return(0)
	if not contactsDS['contacts'].has_key('contact'):
	    return(0)
	contactsList = contactsDS['contacts']['contact']
	for contact in contactsList:
	    if contact.has_key('fields'):
		contactAttribList = contact['fields']
		email = ""
		name = ""
		for attrib in contactAttribList:
		    if attrib['type'] == 'email':
			email = attrib['value']
		    elif attrib['type'] == 'name':
			nameDataStructure = attrib['value']
			if type(nameDataStructure) == dict:
			    if nameDataStructure.has_key('givenName'):
			    	name = nameDataStructure['givenName'] + " "
			    if nameDataStructure.has_key('familyName'):
				name += nameDataStructure['familyName']
			else:
			    name = attrib['value'].__str__()
		    else:
			pass
		self.allContacts[email] = name
	    else:
		print "No contacts found!"
		return(0)
	return(self.allContacts.__len__())


    """
    This method should be called as a class method only.
    The parameters 'username' and 'password' are mandatory, while the rest 
    of them are optional. The process of registration starts from the page
    "https://mail.yahoo.com/". It tries to find the hyperlink labelled
    'Create New Account' on that page and then follows the process. Also,
    provide 2 elements for SecurityQuestions and SecurityAnswers for a 
    valid create account request. And BirthDay is in "dd-mm-yyyy" format.
    NOTE: This method is still under construction.
    """
    def createNewAccount(cls, username, password, FirstName=None, LastName=None, AltEmail=None, Gender='f', BirthDay='01-01-1970', Country='us', Language='en-US', SecurityQuestions=[], SecurityAnswers=[]):
	YahooDomains = ['ymail.com', 'yahoo.com', 'yahoo.co.uk', 'yahoo.co.in', 'rocketmail.com'] # May add more later
	RandomFlag = False
	if username is None:
	    RandomFlag = True
	def createOpenerWithCookieJar():
	    import cookielib
	    cj = cookielib.CookieJar()
	    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	    return(opener)
	opener = createOpenerWithCookieJar()
	loginPageResponse = opener.open("https://mail.yahoo.com")
	loginPageContent = EmailBot._decodeGzippedContent(loginPageResponse.read())
	# Find the "Create New Account" link...
	signUpButtonPattern = re.compile(r"<a\s+id=\"signUpBtn\"\s+[^>]+\s+href='([^']+)'", re.IGNORECASE | re.MULTILINE | re.DOTALL)
	signUpButtonSearch = signUpButtonPattern.search(loginPageContent)
	signUpPageUrl = None
	if signUpButtonSearch:
	    signUpPageUrl = signUpButtonSearch.groups()[0]
	signUpPageContent = ""
	if signUpPageUrl:
	    signUpPageResponse = opener.open(signUpPageUrl)
	    signUpPageRespHeaders = signUpPageResponse.info()
	    signUpPageContent = EmailBot._decodeGzippedContent(signUpPageResponse.read())
	# Now, if the 'signUpPageContent' is not empty, then find the registration form
	regFormPattern = re.compile(r"<form\s+id=\"regFormBody\"\s+name=\"([^\"]+)\"\s+action=\"([^\"]+)\"[^>]+>(.*?)</form>", re.MULTILINE | re.DOTALL | re.IGNORECASE)
	regFormSearch = regFormPattern.search(signUpPageContent)
	formName = ""
	formAction = ""
	formContent = ""
	if regFormSearch:
	    searchResults = regFormSearch.groups()
	    formName = searchResults[0]
	    formAction = searchResults[1]
	    formContent = searchResults[2]
	if formContent.__len__() == 0:
	    print "Couldn't fetch sign up form content... check the 'regFormPattern' variable if it still reflects the registration form correctly. Leaving execution now"
	    return (None)
	# Collect form elements and their default values
	formSoup = BeautifulSoup(formContent)
	formElementsDict = {}
	allHiddens = formSoup.findAll("input", { 'type' : 'hidden' })
	allSelects = formSoup.findAll("select")
	allTexts = formSoup.findAll("input", { 'type' : 'text' })
	allPasswords = formSoup.findAll("input", { 'type' : 'password' })
	for hidden in allHiddens:
	    if hidden.has_key("name") and hidden.has_key("value"):
		formElementsDict[hidden["name"]] = hidden["value"]
	    elif hidden.has_key("id") and hidden.has_key("value"):
		formElementsDict[hidden["id"]] = hidden["value"]
	    elif hidden.has_key("name") and not hidden.has_key("value"):
	 	formElementsDict[hidden["name"]] = None
	    elif hidden.has_key("id") and not hidden.has_key("value"):
		formElementsDict[hidden["id"]] = None
	    else:
		pass
	if Gender is not None:
	    formElementsDict["gender"] = Gender
	else:
	    formElementsDict["gender"] = 'f'
	if Country is not None:
	    formElementsDict["country"] = Country
	else:
	    formElementsDict["country"] = 'us'
	if Language is not None:
	    formElementsDict["language"] = Language
	else:

	    formElementsDict["language"] = 'en-US'
	birthDayPattern = re.compile(r"(\d{1,2})\-(\d{1,2})\-(\d{4})")
	dd, mm, yyyy = "", "", ""
	if BirthDay is not None:
	    birthDaySearch = birthDayPattern.search(BirthDay)
	    if birthDaySearch:
		dd, mm, yyyy = birthDaySearch.groups()
	if mm.__str__().__len__ > 0:
	    formElementsDict["mm"] = mm.__str__()
	if dd.__str__().__len__ > 0:
	    formElementsDict["dd"] = dd.__str__()
	if yyyy.__str__().__len__ > 0:
	    formElementsDict["yyyy"] = yyyy.__str__()
	for select in allSelects:
	    if select.has_key("name") and (select["name"] == "gender" or select["name"] == "country" or select["name"] == "language" or select["name"] == "mm"):
		continue
	    selectName = ""
	    selectValue = ""
	    if select.has_key("name"):
		selectName = select['name']
	    elif select.has_key("id"):
		selectName = select['id']
	    allOptions = select.findAll("option") # This should give us a list
	    selectedOptionIndex = random.randrange(0, (allOptions.__len__() - 1))
	    selectedOption = allOptions[selectedOptionIndex]
	    if selectedOption.has_key("value"):
	    	selectValue = selectedOption["value"]
	    formElementsDict[selectName] = selectValue
            # Hope this will take care of most 'select' elements...
	if password is None or password == "":	# Generate a random password
	    char_set = string.ascii_lowercase + string.digits
	    password = ''.join(random.sample(char_set,8))
	for passwordElem in allPasswords:
	    formElementsDict[passwordElem['name']] = password
	# Now, if username is provided and is None, then let us check if it is available. Firstly, check if a domain name has been specified with the username or not.
	userWithDomainPattern = re.compile(r"@(.*)$")
	domainName = ""
	if username is not None and not userWithDomainPattern.search(username): # randomly select a domain name.
	    domainIndex = random.randrange(0, (YahooDomains.__len__() - 1))
	    domainName = YahooDomains[domainIndex]
	    formElementsDict['domain'] = domainName
	    formElementsDict['yahooid'] = username
	elif username is not None:
	    user,dom = username.split("@")
	    username = user
	    formElementsDict['domain'] = dom
	    formElementsDict['yahooid'] = username
	if RandomFlag: # If username is specified as None:
	    char_set = string.ascii_lowercase + string.digits
	    username = ''.join(random.sample(char_set,8))
	    formElementsDict['yahooid'] = username
	else:
	    formElementsDict['yahooid'] = username
	invalidUsernameSearch = re.compile("^(\d+)(\w+)$").search(formElementsDict['yahooid'])
	if invalidUsernameSearch:
	    formElementsDict['yahooid'] = invalidUsernameSearch.groups([1]) + invalidUsernameSearch.groups([2])
	if not RandomFlag and FirstName is not None:
	    formElementsDict['firstname'] = FirstName
	else:
	    char_set = string.ascii_lowercase
	    formElementsDict['firstname'] = ''.join(random.sample(char_set,8)) # Note: Firstname cannot contain anything apart from alphabets and ' or . characters. We are not handling the special 2 characters just now...
	if not RandomFlag and LastName is not None:
	    formElementsDict['secondname'] = LastName
	else:
	    char_set = string.ascii_lowercase
	    formElementsDict['secondname'] = ''.join(random.sample(char_set,8)) # Note: LastName cannot contain anything apart from alphabets and ' or . characters. We are not handling the special 2 characters just now...
	print "Checking if the username '%s' is available...."%formElementsDict['yahooid']
	isAvailableUsername = False
	isAvailableUsername = cls.__isUserNameAvailable(opener, formElementsDict)
	if isAvailableUsername:
	    print "username '%s' is available for use"%formElementsDict['yahooid']
	    isAvailableUsername = True
	else:
	    print "username '%s' is NOT available for use. Returning 'None' from the method."%formElementsDict['yahooid']
	    return(None)
	for text in allTexts:
	    if text.has_key("name") and text['name'] == "secquestionanswer":
		char_set = string.ascii_lowercase
		formElementsDict['secquestionanswer'] = ''.join(random.sample(char_set,4))
	    elif text.has_key("name") and text['name'] == "secquestionanswer2":
		char_set = string.ascii_lowercase
		formElementsDict['secquestionanswer2'] = ''.join(random.sample(char_set,4))
	    elif text.has_key("name") and text["name"] == "postalcode":
		zipcodesList = Utils.listAmericanZipCodes()
		formElementsDict['postalcode'] = zipcodesList[random.randrange(0, zipcodesList.__len__() - 1)]
	    elif text.has_key("name") and text["name"] == "altemail":
		formElementsDict["altemail"] = "" # We will not do anything here as it is an optional argument.
	    elif text.has_key("name") and text["name"] == "customsecquestion1":
		formElementsDict["customsecquestion1"] = ""
	    elif text.has_key("name") and text["name"] == "customsecquestion2":
		formElementsDict["customsecquestion2"] = ""
	    else:
		pass
	# Now, to load some captcha params, fetch the CaptchaWSProxyService URL:
	captchaProxyServiceURL = "https://na.edit.yahoo.com/captcha/CaptchaWSProxyService.php?cid=V5&lang=en-US&intl=us&action=createlazy&initial_view=visual&u=%s&t=%s"%(formElementsDict['u'], formElementsDict['t'])
	captchaProxyServiceResponse = opener.open(captchaProxyServiceURL)
	captchaProxyServiceResponseText = cls._decodeGzippedContent(captchaProxyServiceResponse.read())
	captchaProxyServiceResponseText = captchaProxyServiceResponseText.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", "'").replace("\n", " ")
	captchaProxyServiceParts = captchaProxyServiceResponseText.split("<CaptchaScript>")
	captchaServiceContent = captchaProxyServiceParts[0]
	captchaSoup = BeautifulSoup(captchaServiceContent)
	allCaptchaHiddenElements = captchaSoup.findAll("input", { 'type' : 'hidden' })
	allCaptchaTextElements = captchaSoup.findAll("input", { 'type' : 'text' })
	captchaImageUrlImageElement = captchaSoup.find("img", { 'id' : 'captchaV5ClassicCaptchaImg' })
	captchaImageUrl = ""
	if captchaImageUrlImageElement and captchaImageUrlImageElement.has_key("src"):
	    captchaImageUrl = captchaImageUrlImageElement["src"]
	# Send the captchaImageUrl to the captcha service handlers.
	for hiddenElements in allCaptchaHiddenElements:
	    if hiddenElements.has_key("name") and hiddenElements.has_key("value"):
		formElementsDict[hiddenElements["name"]] = hiddenElements["value"]
	for textElements in allCaptchaTextElements:
	    if textElements["name"] == "captchaAnswer":
		continue
	    if textElements.has_key("name") and textElements.has_key("value"):
		formElementsDict[textElements["name"]] = textElements["value"]
	captchaString = cls._processCaptchaUsingDBC(captchaImageUrl)
	if captchaString is not None:
	    formElementsDict['captchaAnswer'] = captchaString
	else:
	    formElementsDict['captchaAnswer'] = ""
	# Few things to be hard-coded here...
	formElementsDict['IAgreeBtn'] = "Create My Account"
	formElementsDict['audioCaptchaClicked'] = "0"
	formElementsDict['audioCaptchaReplayClicked'] = "0"
	formElementsDict['tmps'] = "true"
	formElementsDict['binMapFld'] = ""
	formElementsDict['tmp_hid'] = ""
	formElementsDict['rf'] = ""
	formElementsDict['d_i'] = ""
	formElementsDict['d_i_h'] = ""
	formElementsDict['timeSpent'] = ""
	if formElementsDict.has_key("jsenabled"):
	    formElementsDict["jsenabled"] = '1'
	signUpPageTmpHidPattern = re.compile(r"tmpdata:\s+\"([^\"]+)\"")
	signUpPageTmpHidSearch = signUpPageTmpHidPattern.search(signUpPageContent)
	if signUpPageTmpHidSearch:
	    formElementsDict["tmp_hid"] = signUpPageTmpHidSearch.groups()[0]
	print "==========================================================================="
	print formElementsDict
	print "==========================================================================="
	formElementsData = urllib.urlencode(formElementsDict)
	# Now we are ready for the request to create the account for us.
	if not EmailBot._isAbsoluteUrl(formAction):
	    signUpUrlParts = signUpPageUrl.split("/")
	    signUpUrlParts.pop()
	    signUpUrlParts.append(formAction)
	    formAction = "/".join(signUpUrlParts)
	httpHeaders = { 'User-Agent' : r'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.2.10) Gecko/20111103 Firefox/3.6.24',  'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Accept-Language' : 'en-us,en;q=0.5', 'Accept-Encoding' : 'gzip,deflate', 'Accept-Charset' : 'ISO-8859-1,utf-8;q=0.7,*;q=0.7', 'Keep-Alive' : '115', 'Connection' : 'keep-alive', }
	httpHeaders['Content-Type'] = "application/x-www-form-urlencoded"
	httpHeaders['Content-Length'] = formElementsData.__len__()
	print "CJ = " + cj.__str__()
	regRequest = urllib2.Request(formAction, formElementsData, httpHeaders)
	regResponsePageContent = ""
	try:
	    regResponse = opener.open(regRequest)
	    print "CODE: %s - Message: %s"%(regResponse.getcode(), regResponse.msg)
	    regResponsePageContent = cls._decodeGzippedContent(regResponse.read())
	except:
	    print "Could not send request for registration - Reason: %s"%sys.exc_info()[1].__str__()
	    return (False)
	f = open("Yahoo/yahooRegistrationService.html", "w")
	f.write(regResponsePageContent)
	f.close()

    createNewAccount = classmethod(createNewAccount)

    
    # Internal method for use in the 'createNewAccount' method. Should be called after most form elements have been populated.
    def __isUserNameAvailable(cls, opener, formElementsDict):
	checkUrl = r"https://na.edit.yahoo.com/reg_json?PartnerName=yahoo_default&RequestVersion=1&AccountID=%s@%s&GivenName=%s&FamilyName=%s&ApiName=ValidateFields&intl=us&u=%s&t=%s"%(formElementsDict['yahooid'], formElementsDict['domain'], formElementsDict['firstname'], formElementsDict['secondname'], formElementsDict['u'], formElementsDict['t'])
	#print checkUrl

	try:
	    checkResponse = opener.open(checkUrl)
	    checkContent = cls._decodeGzippedContent(checkResponse.read())
	    jsonDataDict = json.loads(checkContent)
	    if jsonDataDict.has_key("ResultCode") and jsonDataDict['ResultCode'].upper() == "SUCCESS" or jsonDataDict['ResultCode'].upper() == "TRUE":
	    	return(True)
	    else:
		return(False)
	except:
	    print "Tried checking if the username specified was valid or not. The request failed: %s"%sys.exc_info()[1].__str__()
	    return(False)

    __isUserNameAvailable = classmethod(__isUserNameAvailable)

    """
    Captcha processing methods: Using DeathByCaptcha ('processCaptchaUsingDBC') service and Decaptcher API ('')
    """
    def _processCaptchaUsingDBC(cls, captchaUrl):
        apiPath = os.getcwd() + os.path.sep + "CaptchaAPI"
        sys.path.append(apiPath)
        import deathbycaptcha
	captchaUsername = "supmit"
	captchaPassword = "spmprx"
	captchaTimeout = 30
	captchaMinBalance = 0
        try:
            client = deathbycaptcha.SocketClient(captchaUsername, captchaPassword)
            captchaImageResponse = urllib2.urlopen(captchaUrl)
            captchaImage = captchaImageResponse.read()
            strIoCaptchaImage = StringIO.StringIO(captchaImage)
            balance = client.get_balance()
	    print "BALANCE: " + balance.__str__()
            captcha = client.decode(strIoCaptchaImage, captchaTimeout)
            #if balance < captchaMinBalance:
            #    print "Warning: Your DeathByCaptcha service balance is low. Please renew/recharge the service balance to enjoy uninterrupted service."
            if captcha:
                return (captcha["text"])
        except:
            print "Could not retrieve captcha text from deathbycaptcha service. Please check your credentials or balance: %s"%(sys.exc_info()[1].__str__())
            return(None)

    _processCaptchaUsingDBC = classmethod(_processCaptchaUsingDBC)


# Thats it I guess.... 



##################### Driver implementations for various tasks #######################
# Implements a crawl of the specified account. Activities performed are:
#	1. Log in into the account
#	2. Iterate through all folders (both user created folders/labels as well as system folders)
# 	3. Opens and reads each email message, and stores the data items in an in-memory data structure.
#	4. Downloads, opens, reads and attempts to scrape information from all attachments in each email message it processes in step #3.
#	5. Dumps the gathered information in the account to data file in one of the supported formats. The filename and the format would be user specified. The data is dumped periodically after processing an entire page of emails listing.
# It reads the following info from the config file: acctUserId, acctPasswd, outputFile, outputFormat, numThreads, canResume.
# 'acctUserId', 'acctPasswd', 'outputFile', 'outputFormat' and 'numThreads' are self explanatory. 'canResume' determines if the crawler can be 
# paused in the middle of the operation and resumed later from the exact same state at the time it was paused. If 'canResume' is 'True', it can be
# paused and resumed later. If it is 'False' (or anything other than 'True'), then it cannot not be resumed from the same state. 
# Supported values for 'outputFormat' are 'csv' and 'xml'.
def drvAccountCrawler(configFile="./config/YahooMailBot.cfg"):
    cfgDict = Utils.readBasicConfig(configFile) # read config file
    # Process config params - set default values if values are not available in config.
    if not cfgDict:
	return(None)
    outfile = None
    outdir = None
    attachmentdir = None
    if cfgDict.has_key('outputDir'):
	outdir = cfgDict['outputDir']
	if EmailBot.pathEndingWithSlashPattern.search(outdir):
	    outdir = outdir[:-1]
	if not os.path.isdir(outdir):
	    os.makedirs(outdir)
    else:
	print "No configuration specified for output dir. The 'outputDir' is a mandatory parameter in the config file. Can't proceed without it.\n"
	sys.exit()
    if outdir is None or outdir.strip() == "":
	print "No value has been specified for the mandatory config param 'outputDir'. Can't proceed without it.\n"
	sys.exit()
    if cfgDict.has_key('attachmentsDir'):
	attachmentdir = cfgDict['attachmentsDir']
	if EmailBot.pathEndingWithSlashPattern.search(attachmentdir):
	    attachmentdir = outdir[:-1]
	if not os.path.isdir(attachmentdir):
	    os.makedirs(attachmentdir)
    else: # 'attachmentsDir' is not a mandatory config param. If not found, it is set to 'outdir'.
	attachmentdir = outdir
    if attachmentdir is None or attachmentdir.strip() == "":
	attachmentdir = outdir
    if not cfgDict.has_key("acctUserId") or not cfgDict.has_key("acctPasswd"):
	print "Username or password is not specified. Exiting..."
	return (None)
    # Set up default values for config params.
    outformat = "csv"
    logfile = "./Logs/YahooMailBot.log"
    numthreads = 1
    resumesupport = False
    # Override all default values of configurable params with value from config file, if available.
    if cfgDict.has_key("outputFormat"):
	outformat = cfgDict['outputFormat']
    if cfgDict.has_key("numThreads"):
	numthreads = cfgDict['numThreads']
    if cfgDict.has_key("canResume"):
	resumesupport = cfgDict['canResume']
    if cfgDict.has_key("Logfile"):
	logfile = cfgDict['Logfile']
    logger = Logger(logfile) # Created Logger object
    # Set up contextual filename for dumping inbox data
    outfile = Utils.getContextualFilename(cfgDict['acctUserId'], "Inbox")
    outfile = outdir + os.path.sep + outfile + ".csv"
    # Set up signal handler.
    Utils.setSignal()
    # Open output file...
    ofh = open(outfile, "w")
    if outformat.lower() == "csv": # If output format is CSV, print headers in the output file.
	ofh.write("DateTime, Subject, Sender, URL, Message, ReadFlag\n")
    # Start crawling...
    ybot = YahooMailBot()
    cloneCfg = Utils._cloneConfig(cfgDict)
    if ybot is not None:
    	logger.write("Successfully created 'YahooMailBot' object with following configuration:\n%s\n"%(cloneCfg.__str__()))
	print "YahooMailBot object successfully created....\n"
    loginStatus = ybot.doLogin(cfgDict['acctUserId'], cfgDict['acctPasswd'])
    if loginStatus:
	logger.write("Successfully logged in as %s\n"%cfgDict['acctUserId'])
    else:
	logger.write("Failed to login as %s... Exiting\n\n"%cfgDict['acctUserId'])
	sys.exit(-1)
    # First, go to the 'Inbox' emails listing page... This is the point where we discover our interface type.
    ybot.fetchInboxPage()
    contactCount = ybot.getContactsInfo()
    #print "Contacts List: \n", ybot.allContacts
    logger.write("Number of contacts: %s\n"%contactCount.__str__())
    if contactCount > 0:
	logger.write("Dumping contacts: %s\n\n"%ybot.allContacts.__str__())
    contactsOutfile = outdir + os.path.sep
    fcon = None # Initialize contacts file filehandle
    if outformat.lower() == "csv": # If output format is CSV, create CSV file, open it and print headers in it.
	contactsOutfile = contactsOutfile + "CONTACTS.csv"
	fcon = open(contactsOutfile, "w")
	fcon.write("EmailID, Name\n")
	for contact in ybot.allContacts.keys():
	    fcon.write('"%s", "%s"\n'%(contact, ybot.allContacts[contact]))
    elif outformat.lower() == "xml":
	contactsOutfile = contactsOutfile + "CONTACTS.xml"
	fcon = open(contactsOutfile, "w")
	# TODO: Do whatever is necessary for XML format.
    else:
	print "Unsupported format: Falling back on default format (which is CSV)"
	contactsOutfile = contactsOutfile + "CONTACTS.csv"
	fcon = open(contactsOutfile, "w")
	fcon.write("name, details\n")
	for contact in ybot.allContacts.keys():
	    fcon.write('"%s", "%s"\n'%(contact, ybot.allContacts[contact]))
    fcon.close() # Close "CONTACTS" file handle
    if contactCount > 0:
    	logger.write("Dumped %s contacts\n\n"%contactCount.__str__())
    # Get all custom and built-in folders
    folders = ybot.getCustomFolders()
    bfolders = ybot.getAvailableFolders()
    foldersCount = folders.keys().__len__() + bfolders.keys().__len__()
    allFolders = Utils.mergeDicts(folders, bfolders)
    logger.write("Found %s folders to scan through...\n"%(foldersCount.__str__()))
    # Now start iterating over all folders and fetch email messages from each of them. Start with 'Inbox' folder...
    count = ybot.getTotalMailsInCurrentFolder()
    logger.write("Scanning 'Inbox' folder... %s emails to be processed\n"%count.__str__())
    print "Inbox contains %s messages"%count
    emailsDict = ybot.listEmailsOnPage()
    pagesCount = int(count/emailsDict.keys().__len__()) + 1
    pageCtr = 0
    while pageCtr < pagesCount:
	logger.write("Processing page #%s...\n"%(pageCtr + 1).__str__())
	for msgUrl in emailsDict.keys():
	    sender = emailsDict[msgUrl][0]
	    subject = emailsDict[msgUrl][2]
	    recvdDate = emailsDict[msgUrl][3]
	    readFlag = emailsDict[msgUrl][4]
	    content = ybot.fetchEmailMessage(msgUrl)
	    message = ybot.extractEmailMessage(content)
	    subject = subject.encode("ascii", "ignore")
	    subject = Utils.decodeHtmlEntities(subject)
	    sender = sender.decode("ascii", "ignore")
	    sender = Utils.decodeHtmlEntities(sender)
	    # 'sender' contains curly braces and quotes which should be removed. HTML Entities should be converted to respective characters.
	    sender = Utils.cleanUp(sender)
	    sender = sender.replace("{", "")
	    sender = sender.replace("}", "")
	    msgUrl = msgUrl.decode("ascii", "ignore")
	    message = message.encode("ascii", "ignore")
	    message = Utils.decodeHtmlEntities(message)
	    message = Utils.cleanUp(message)
	    recvdDate = datetime.datetime.fromtimestamp(int(recvdDate)).strftime('%Y-%m-%d %H:%M:%S')
	    ofh.write('"%s", "%s", "%s", "%s", "%s", "%s"\n'%(recvdDate, subject, sender, msgUrl, message, readFlag.__str__()))
	pageCtr += 1
	logger.write("Fetching page #%s...\n"%(pageCtr + 1).__str__())
	ybot.getNextPage()
	emailsDict = {} # re-initialize 'emailsDict'
	emailsDict = ybot.listEmailsOnPage()
    logger.write("Completed processing 'Inbox'\n\n")
    ofh.close()
    # Iterate over all the folders and fetch all messages contained in them.
    for fkey in allFolders.keys():
	if fkey.lower() == "inbox":
	    continue
	folderContent = ybot.getFolderPage(fkey)
	if folderContent is None: # It is necessary to check the return value of 'getFolderPage()' method since it returns 'None' when it cannot fetch the requested folder's page.
	    print "Could not fetch folder '%s'"%fkey
	    logger.write("Could not fetch folder '%s'\n"%fkey)
	    continue
	print "Processing folder '%s' containing %s emails"%(ybot.currentFolderLabel, ybot._totalEmailsInCurrentFolder.__str__())
	logger.write("Processing folder '%s' containing %s emails\n\n"%(ybot.currentFolderLabel, ybot._totalEmailsInCurrentFolder.__str__()))
	if ybot._totalEmailsInCurrentFolder == 0:
	    logger.write("Skipping folder '%s' as there are no emails in it.\n\n"%ybot.currentFolderLabel)
	    print "Skipping folder '%s' as there are no emails in it."%ybot.currentFolderLabel
	    continue
	emailsDict = {}
	emailsDict = ybot.listEmailsOnPage()
	pagesCount = ybot.maxPageNumberCurrentFolder
	pageCtr = 0
	outfile = Utils.getContextualFilename(cfgDict['acctUserId'], ybot.currentFolderLabel)
    	outfile = outdir + os.path.sep + outfile + ".csv"
	print "Opening file '%s'"%outfile
	ffh = open(outfile, "w")
	if outformat.lower() == "csv": # If output format is CSV, print headers in the output file.
	    ffh.write("DateTime, Subject, Sender, URL, Message, ReadFlag\n")
	while pageCtr < pagesCount:
	    logger.write("Processing page #%s of '%s' folder...\n"%((pageCtr + 1).__str__(), ybot.currentFolderLabel))
	    print "Processing page #%s of '%s' folder...\n"%((pageCtr + 1).__str__(), ybot.currentFolderLabel)
	    for msgUrl in emailsDict.keys():
	    	sender = emailsDict[msgUrl][0]
	    	subject = emailsDict[msgUrl][2]
	    	recvdDate = emailsDict[msgUrl][3]
	    	readFlag = emailsDict[msgUrl][4]
	    	content = ybot.fetchEmailMessage(msgUrl)
	    	message = ybot.extractEmailMessage(content)
	    	subject = subject.encode("ascii", "ignore")
	     	subject = Utils.decodeHtmlEntities(subject)
	    	sender = sender.decode("ascii", "ignore")
	    	sender = Utils.decodeHtmlEntities(sender)
	    	# 'sender' contains curly braces and quotes which should be removed. HTML Entities should be converted to respective characters.
	    	sender = Utils.cleanUp(sender)
	    	sender = sender.replace("{", "")
	    	sender = sender.replace("}", "")
	    	msgUrl = msgUrl.decode("ascii", "ignore")
	    	message = message.encode("ascii", "ignore")
	    	message = Utils.decodeHtmlEntities(message)
	    	message = Utils.cleanUp(message)
	    	recvdDate = datetime.datetime.fromtimestamp(int(recvdDate)).strftime('%Y-%m-%d %H:%M:%S')
		if outformat.lower() == "csv": # If output format is CSV, print headers in the output file.
	    	    ffh.write('"%s", "%s", "%s", "%s", "%s", "%s"\n'%(recvdDate, subject, sender, msgUrl, message, readFlag.__str__()))
	    pageCtr += 1
	    logger.write("Fetching page #%s...\n"%(pageCtr + 1).__str__())
	    ybot.getNextPage()
	    emailsDict = {}
	    emailsDict = ybot.listEmailsOnPage()
	ffh.close()
    # Now, logout of the account.
    ybot.doLogout()
    #print " \n--------------------------------------------------------\n"
    #for fkey in bfolders.keys():
    #    print fkey, " ======= >> ", bfolders[fkey]
    #	content = ybot.openFolderPage(fkey)
    #	fw = open("./Yahoo/AvailableFolders/folderPage_" + fkey + ".html", "w")
    #	fw.write(content)
    #	fw.close()
    #count = ybot.getTotalMailsInCurrentFolder()
    #emailsDict = ybot.listEmailsOnPage()
    #msgUrl = ""
    #for msgUrl in ybot.currentPageEmailsDict2.keys():
    #    try: # Keep in mind that there might be unicode characters in the content or subject...
    #        sub = ybot.currentPageEmailsDict2[msgUrl][2]
    #        print "Message URL: " + msgUrl + " ====== Subject: " + ybot.currentPageEmailsDict2[msgUrl][2]
    #    except:
    #        continue
    ##print "Message URL: ", msgUrl
    #content = ybot.fetchEmailMessage(msgUrl)
    #if content is not None:
    #	f = open(r"./Yahoo/Message_ProfMoriarty_Page1.html", "w")
    #	f.write(content)
    #	f.close()
    #else:
    #	print "'ybot.currentPageContent' is None after 'fetchEmailMessage()' call."
    ## Note: Issue here is there is a need to check if there is a next page. If the number of messages is too few for a page, then the 'getNextPage' call fails with a 'HTTP Error 500'.
    #ybot.getNextPage()
    #if ybot.currentPageContent is not None:
    #	f = open(r"./Yahoo/MailsList_ProfMoriarty.html", "w")
    #	f.write(ybot.currentPageContent)
    #	f.close()
    #else:
    #	print "'ybot.currentPageContent' is None after 'getNextPage()' call."
    #emailsDict = ybot.listEmailsOnPage()
    #msgUrl = ""
    #for msgUrl in ybot.currentPageEmailsDict2.keys():
    #    try: # Keep in mind that there might be unicode characters in the content or subject...
    #        print "Message URL: " + msgUrl + " ====== URL: " + ybot.currentPageEmailsDict2[sub][2]
    #        sub = ybot.currentPageEmailsDict2[msgUrl][2]
    #    except:
    #        continue
    #content = ybot.fetchEmailMessage(msgUrl)
    #if content is not None:
    #	f = open(r"./Yahoo/Message_ProfMoriarty_Page2.html", "w")

    #	f.write(content)
    #	f.close()
    #else:
    #	print "'ybot.currentPageContent' is None after 2nd 'fetchEmailMessage()' call."
    #msgDict = {'Subject' : 'Script Test AAAAAAAAAAAA', 'Sender' : 'me@me.me', 'Recipients' : ['supmit@gmail.com', 'supmit@rediffmail.com', 'vns_smitra@yahoo.co.in' ], 'MessageBody' : 'This is a test mail sent from the script.... WHATS THIS KOLAVERI KOLAVERI SHIT....', 'CcRecipients' : [], 'BccRecipients' : [], 'Attachments' : ''}
    #ybot.sendEmailMessage(msgDict)
    #print "Message Sent"
    ##f = open(r"./Yahoo/SentMessage2k3.html", "w")
    ##f.write(ybot.currentPageContent)
    ##f.close()
    ##ybot.abracadabra



if __name__ == "__main__":
    #drvAccountCrawler()
    YahooMailBot.createNewAccount(None, None)
    


# supmit

