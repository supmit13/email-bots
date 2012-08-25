import os, sys, re
import urllib, urllib2, htmllib
from urlparse import urlparse
import httplib
from BeautifulSoup import BeautifulSoup
import StringIO
import gzip
import time
from EmailBot import EmailBot, NoRedirectHandler
from Tools import Utils
from LogHandler import Logger
import struct



class GmailBot(EmailBot):
    
    GMAIL_RTT = 4396
    startUrl=r"http://mail.google.com/mail/"
    logoutUrl = r"https://mail.google.com/mail/?logout&hl=en"
    privateDomainUsernamePattern = re.compile(r"@(\w+)\.(\w+)$")
    attachmentsPattern1 = re.compile(r"Scan\s+and\s+download", re.IGNORECASE | re.MULTILINE | re.DOTALL)
    attachmentsPattern2 = re.compile(r"download", re.IGNORECASE | re.MULTILINE | re.DOTALL)
    # Attachments to ignore if the filename contains the following regular expression patterns:
    ignorableAttachmentFilenamesList = [ \
	re.compile(r"External\s+images\s+are\s+not\s+displayed", re.IGNORECASE), \
	re.compile(r"Sponsored\s+by\s+IBM", re.IGNORECASE), \
	re.compile(r"Sponsored\s+by\s+Oracle", re.IGNORECASE), \
    ]
    
    def __init__(self, username="", passwd=""):
	super(GmailBot, self).__init__(username, passwd) # Call parent's __init__() method.
        # Initialize object properties that need to be initialized differently from 'EmailBot'.
        self.httpHeaders = { 'User-Agent' : r'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.2.10) Gecko/20111103 Firefox/3.6.24',  'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Accept-Language' : 'en-us,en;q=0.5', 'Accept-Encoding' : 'gzip,deflate', 'Accept-Charset' : 'ISO-8859-1,utf-8;q=0.7,*;q=0.7', 'Keep-Alive' : '115', 'Connection' : 'keep-alive', }
        self.requestUrl = self.__class__.startUrl
        parsedUrl = urlparse(self.requestUrl)
        self.baseUrl = r"https://mail.google.com/mail/"
	self.domainUrl = r"https://mail.google.com/"
        # First, get the Gmail login page.
        self.pageRequest = urllib2.Request(self.requestUrl, None, self.httpHeaders)
        try:
            self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
            headers = self.pageResponse.info()
            if headers.has_key("Location"):
                self.requestUrl = headers["Location"]
                self.pageRequest = urllib2.Request(self.requestUrl, None, self.httpHeaders)
                try:
                    self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
                except:
                    print "Couldn't fetch page.... terminating!\n"
                    sys.exit()
        except:
            print "Could not fetch page.... terminating!\n"
            sys.exit()
        self.httpHeaders["Referer"] = self.requestUrl
        self.sessionCookies = self.__class__._getCookieFromResponse(self.pageResponse)
        self.httpHeaders["Cookie"] = self.sessionCookies
        # Initialize the account related variables...
        self.currentPageContent = GmailBot._decodeGzippedContent(self.getPageContent())
        # 2 Special cookies we need to remember throughout a session.
        self.gmail_login_cookie = ""
        self.gmail_rtt_cookie = ""
        self.ping_cookie = ""
        self.currentInterfaceFormat = "ajax" # The value would be "html" if the page is in HTML format, and "ajax" if it is in javascript. The default is "ajax"
        self.perPageEmailsCount = 50 # By default Gmail displays 50 emails per page.
        self.accountActivity = [] # This will be a list of the memory usage line and the 'Last Account Activity' line.
	self.isPrivateDomain = False # This value is set to true if the account is associated with a private domain under mail.google.com (e.g. whishworks.com, indiamart.com, etc). By default, it is false.
	self.myContacts = {} # Data structure to hold 'My Contacts' info. Contact email Id is the key and a list containing contact name and other contact info is the value. The list elements will be in the following order: name, address, alternate email Ids (as a list), sex.
	# Note: The contact information listed a 'Other Contacts' in a Gmail account will be stored in the EmailBot attribute named 'allContacts'.
                
 
    def _pingUserRequest(self):
        curtime = int(time.time())
        self.requestUrl = "https://mail.google.com/mail?gxlu=" + self.username + "&zx=" + curtime.__str__() + "000"
        self.ping_cookie = None
        tmpHttpHeaders = {}
        for hkey in self.httpHeaders.keys():
            tmpHttpHeaders[hkey] = self.httpHeaders.get(hkey)
        tmpHttpHeaders['Cookie'] += " GMAIL_RTT=" + self.__class__.GMAIL_RTT.__str__()
        tmpHttpHeaders['Accept'] = "image/png,image/*;q=0.8,*/*;q=0.5"
        self.pageRequest = urllib2.Request(self.requestUrl, None, tmpHttpHeaders)
        try:
            self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
	    response_headers = self.pageResponse.info()
	    cookies = response_headers.get('Set-Cookie')
        except urllib2.HTTPError, e: # This will be HTTP Error 204 (possibly)
            response_headers = e.info()
            # Get the 'Set-Cookie' header from response
            cookies = response_headers.get('Set-Cookie')
        if not cookies:
            print "Could not get the cookie values correctly. Please check your internet connection and try again"
            return self.ping_cookie
        cookieparts = cookies.split("Path=/")
        self.ping_cookie = cookieparts[0]
        # Before returning we must change the Referer header to suit the POST request. The POST request expects the Referer url to be sans arguments.
	if not self.isPrivateDomain:
            urlparts = self.httpHeaders['Referer'].split("?")
            self.httpHeaders['Referer'] = urlparts[0]
	self.lastRequestUrl = self.requestUrl
        return self.ping_cookie

    """
    This method completes the login process for the user specified by self.username (and whose password is specified in self.password)
    """
    def doLogin(self, username="", password=""):
        if username != "":
            self.username = username
        if password != "":
            self.password = password
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
                tagname = tag["name"]
                self.postData[tagname] = ""
                if tagname == "Email":
		    unamePatternSearch = self.__class__.privateDomainUsernamePattern.search(self.username)
		    if not unamePatternSearch:
                    	self.postData[tagname] = self.username + r"@gmail.com"
		    else:
			self.postData[tagname] = self.username # Possibly a private domain under google mail
			grp1, grp2 = unamePatternSearch.groups()
			if grp1.lower() + "." + grp2.lower() != "gmail.com":
			    self.isPrivateDomain = True
                elif tagname == "Passwd":
                    self.postData[tagname] = self.password
                elif tagname == "dnConn":
                    self.postData['dnConn'] = "https://accounts.youtube.com/"
                elif tagname == "pstMsg" or tagname == "scc" or tagname == "rmShown":
                    self.postData[tagname] = "1"
                elif tag.has_key("value"):
                    self.postData[tagname] = tag["value"]
                else:
                    self.postData[tagname] = ""
	if self.isPrivateDomain is True:
	    self.postData['checkConnection'] = "youtube:236:1"
	    self.postData['dnConn'] = ""
	    self.postData['ss'] = 1
	    self.httpHeaders['Keep-Alive'] = "300"
        urlencodedData = urllib.urlencode(self.postData)
        # Before POSTing the form data, gmail sends a ping request to the user. The cookie returned will be stored as self.ping_cookie.
        retval = self._pingUserRequest()
        if not retval:
            print "Could not login probably due to some transient problem"
            return None
        if form.has_key("action"):
            self.requestUrl = form["action"]
        if form.has_key("method"):
            self.requestMethod = form["method"].upper()
        else:
            self.requestMethod = "GET"
        if self.postData.has_key("GALX"):
            self.httpHeaders['Cookie'] += "; GALX=" + self.postData['GALX']
        jsnow = int(time.time())
        jsstart_time = jsnow - GmailBot.GMAIL_RTT
        # The following cookies are usually set by javascript in the page. Here, we need to set them manually.
        self.httpHeaders['Cookie'] += "GMAIL_LOGIN=T" + str(jsstart_time) + "/" + str(jsstart_time) + "/" + str(jsnow)
        self.gmail_login_cookie = "GMAIL_LOGIN=T" + str(jsstart_time) + "/" + str(jsstart_time) + "/" + str(jsnow)
        jsend = int(time.time())
        self.httpHeaders['Cookie'] += "; GMAIL_RTT=" + str(jsend - jsstart_time)
        self.gmail_rtt_cookie = "; GMAIL_RTT=" + str(jsend - jsstart_time)
        self.pageRequest = urllib2.Request(self.requestUrl, urlencodedData, self.httpHeaders)
        try:
            self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
        except:
            print "Couldn't Login.... - Error: " + sys.exc_info()[1].__str__()
	    self.lastRequestUrl = self.requestUrl
            return None
        self.httpHeaders['Referer'] = self.requestUrl
        self.sessionCookies = self.__class__._getCookieFromResponse(self.pageResponse)
        self.sessionCookies.rstrip(" ").rstrip(";")
        self.sessionCookies += self.ping_cookie + self.gmail_login_cookie + self.gmail_rtt_cookie
        self.httpHeaders["Cookie"] = self.sessionCookies
        pageContent = GmailBot._decodeGzippedContent(self.getPageContent())
        # The pageContent will have a "<meta http_equiv='refresh'..." tag. We need to follow
        # the URL therein to complete the login operation.
        lsoup = BeautifulSoup(pageContent)
	if self.isPrivateDomain is True: # if this is a paid domain under google mail, we need to look for the one and only anchor tag.
	    anchorTag = lsoup.find("a")
	    if anchorTag.has_key('href'):
		self.requestUrl = anchorTag['href']
		if not self.__class__._isAbsoluteUrl(self.requestUrl):
		    self.requestUrl = self.baseUrl + self.requestUrl
		self.lastRequestUrl = self.requestUrl
        else:
	    metaTag = lsoup.find("meta")
            if metaTag.has_key("content"):
            	metaContentParts = metaTag['content'].split("url=")
            	self.requestUrl = metaContentParts[1]
            else:
            	print "Couldn't find the 'meta' tag in the POST response. Possibly one or more of our login params are incorrect"
	    	self.lastRequestUrl = self.requestUrl
            	return None
        # ==== Eliminate the GAPS=1:... cookie, 'rememberme...' cookie and LSID cookie ========
        cookiesList = self.httpHeaders['Cookie'].split(";")[2:]
        self.httpHeaders['Cookie'] = ""
        for cookie in cookiesList:
            if re.search(r"^\s*$", cookie) or cookie is None:
                continue
            cookieParts = cookie.split("=")
            cookieName, cookieVal = cookieParts[0], cookieParts[1]
            if cookieParts.__len__() > 2:
                cookieName, cookieVal = cookieParts[0], "=".join(cookieParts[1:])
            if cookieName == "LSID" or cookieName == "GAUSR":
                continue
            self.httpHeaders['Cookie'] += cookieName + "=" + cookieVal + "; "
        # ===== GAPS=1:... cookie, 'rememberme...' cookie and LSID cookie eliminated ==========
        self.pageRequest = urllib2.Request(self.requestUrl, None, self.httpHeaders)
        try:
            self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
        except:
            print "Something went wrong in the GET request subsequent to the login POST request - Error: " + sys.exc_info()[1].__str__()
	    self.lastRequestUrl = self.requestUrl
            return None
        pageContent = self.__class__._decodeGzippedContent(self.getPageContent())
        self.sessionCookies = self.__class__._getCookieFromResponse(self.pageResponse)
        # We expect a HTTP Error 302 (temporary redirect). The redirect URL will be contained in the 'Location' header of the response.
        self.requestUrl = self.pageResponse.info().getheader("Location")
        self.sessionCookies = self.__class__._getCookieFromResponse(self.pageResponse)
        # Now we need to eliminate the expired GMAIL_RTT cookie and add the GMAIL_AT and GX cookies from the last response headers.
        cookiesList = self.httpHeaders['Cookie'].split(";")
        for cookie in cookiesList:
            if re.search(r"^\s*$", cookie) or cookie is None:
                continue
            cookieParts = cookie.split("=")
            cookieName, cookieVal = cookieParts[0], cookieParts[1]
            if cookieParts.__len__() > 2:
                cookieName, cookieVal = cookieParts[0], "=".join(cookieParts[1:])
            if cookieName == "GMAIL_RTT":
                continue
            self.httpHeaders['Cookie'] += cookieName + "=" + cookieVal + "; "
	self.lastRequestUrl = self.requestUrl
        if not self.sessionCookies or self.sessionCookies == "":
            print "Could not get the cookies correctly. Please ensure you are connected to the internet before trying again"
            return (None)
        sessionCookiesList = self.sessionCookies.split(";")
        for sessCookie in sessionCookiesList:
            if re.search(r"^\s*$", sessCookie) or sessCookie is None:
                continue
            sessCookieParts = sessCookie.split("=")
            sessCookieName, sessCookieValue = sessCookieParts[0], sessCookieParts[1]
            if sessCookieParts.__len__() > 2:
                sessCookieName, sessCookieValue = sessCookieParts[0], "=".join(sessCookieParts[1:])
            if sessCookieName == "GMAIL_RTT":
                continue
            self.httpHeaders['Cookie'] += sessCookieName + "=" + sessCookieValue + "; "
        self.pageRequest = urllib2.Request(self.requestUrl, None, self.httpHeaders)
        try:
            self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
        except:
	    if self.isPrivateDomain is False:
            	print "Something went wrong while fetching the inbox emails list page - Error: " + sys.exc_info()[1].__str__()
	    else:
		print "Couldn't complete the login procedure - " + sys.exc_info()[1].__str__()
	    self.lastRequestUrl = self.requestUrl
            return None
        self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
        self.lastRequestUrl = self.requestUrl
	if self.isPrivateDomain is False:
            if self.isLoginSuccessful():
            	self.currentFolderLabel = "inbox"
            	self.currentPageNumber = 1
            return(self.isLoggedIn)
	else: # For paid domains there are a few more steps to follow...
	    self._handlePaidDomainServiceLogin()
	    if self.isLoginSuccessful():
            	self.currentFolderLabel = "inbox"
            	self.currentPageNumber = 1
            return(self.isLoggedIn)


    def _handlePaidDomainServiceLogin(self):
	paidSoup = BeautifulSoup(self.currentPageContent)
	paidAnchor = paidSoup.find("a")
	if paidAnchor.has_key("href"):
	    self.requestUrl = paidAnchor["href"]
	else:
	    self.requestUrl = None
	    print "Couldn't fetch the last URL to follow for logging in. "
	    return(None)
	self.sessionCookies = self.__class__._getCookieFromResponse(self.pageResponse)
	self.httpHeaders['Cookie'] += self.sessionCookies
	self.pageRequest = urllib2.Request(self.requestUrl, None, self.httpHeaders)
	try:
            self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
        except:
	    print "Something went wrong while fetching the inbox emails list page - Error: " + sys.exc_info()[1].__str__()
	    self.lastRequestUrl = self.requestUrl
            return None
        self.lastRequestUrl = self.requestUrl
	responseHeaders = self.pageResponse.info()
	if responseHeaders.has_key("Location"):
	    self.requestUrl = responseHeaders["Location"]
	else:
	    print "Couldn't find the redirection URL during logging in. "
	    return (None)
	self.pageRequest = urllib2.Request(self.requestUrl, None, self.httpHeaders)
	try:
            self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
        except:
	    print "Could not fetch URL %s - Error: "%(self.requestUrl, sys.exc_info()[1].__str__())
	    self.lastRequestUrl = self.requestUrl
            return None
	self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
        self.lastRequestUrl = self.requestUrl


    #################### **** NOT IN USE **** ####################
    """
    Method to repair bad HTML in content. Such content causes 'Malformed start tag' errors. 
    Since such HTML normally occurs inside javascript '<script>' tags, we try to remove all
    'script' tags from the content.
    """
    def _repairHtmlContent(self, htmlContent):
	if htmlContent is None:
	    return None
	# Remove script tags
	scriptSplitParts = htmlContent.split("<script>")
	htmlContent = ""
	for htmlPart in scriptSplitParts:
	    if re.compile(r"</script>", re.IGNORECASE | re.DOTALL | re.MULTILINE).search(htmlPart):
	    	scriptAndHtmlParts = htmlPart.split('</script>')
	    	htmlContent += scriptAndHtmlParts[1]
	    else:
		htmlContent += htmlPart
	# TODO: Remove style tags
	styleSplitParts = htmlContent.split("<style>")
	return (htmlContent)
    #################### **** NOT IN USE **** ####################

    """
    The following method checks to see if the user has been able to login successfully or not.
    It returns a boolean 'True' if login was successful and a boolean value  of 'False' if not.
    """
    def isLoginSuccessful(self):
	userEmailIdPattern = re.compile(self.username + r"@gmail.com", re.IGNORECASE)
	if self.currentPageContent is None or self.currentPageContent == "":
	    print "Login failed as page HTML is empty!"
	    return False
	if self.isPrivateDomain is not True:
	    userEmailIdPattern = re.compile(self.username + r"@gmail.com", re.IGNORECASE)
	    usernameSearch = userEmailIdPattern.search(self.currentPageContent)
	    if usernameSearch is not None:
	    	print "Logged in as %s\n"%self.username
		self.isLoggedIn = True
	    	return True
	    print "Login failed for user specified as '%s'"%(self.username + r"@gmail.com")
	    return False
	else:
	    usernameParts = self.username.split("@")
	    userEmailIdPattern = re.compile(usernameParts[0])
	    usernameSearch = userEmailIdPattern.search(self.currentPageContent)
	    if usernameSearch is not None:
	    	print "Logged in as %s\n"%(usernameParts[0] + r"@" + usernameParts[1])
		self.isLoggedIn = True
	    	return True
	    print "Login failed for user specified as '%s'"%(usernameParts[0] + r"@" + usernameParts[1])
	    return False


    """
    Checks if the format of the page is javascript/ajax or basic HTML.
    This method is specific to GmailBot only. 
    """
    def _checkInterfaceFormat(self):
	targetPattern = re.compile(r"<a\s+href=[\"\']([^\"\']+)[\"\']>\s*Load\s+basic\s+HTML\s*<\/a>", re.IGNORECASE | re.MULTILINE | re.DOTALL)
	targetSearch = targetPattern.search(self.currentPageContent)
	ahref = ""
	if targetSearch is not None:
	    self.currentInterfaceFormat = 'ajax'
	    ahref = targetSearch.groups()[0]
	else:
	    self.currentInterfaceFormat = 'html'
	return(ahref)

    """
    This method first checks to see what format the interface is in. Gmail, by default, displays content
    as ajax/javascript. Such content is difficult to parse since the data is in the form of list variables.
    If the content received is in such (ajax/javascript) format, then this method tries to set the UI format
    to plain HTML (which is much easier to parse). This method is specific to GmailBot only. It returns a
    boolean value of 'True' if it successfully changes the format to HTML and 'False' if it can't. As a side
    effect, it also sets the attribute 'currentInterfaceFormat' to the appropriate value.
    """
    def setBasicHTMLView(self):
        uiUrl = self._checkInterfaceFormat()
        screenReaderUrl = ""
        if not self.__class__._isAbsoluteUrl(uiUrl):
            urlparts = self.lastRequestUrl.split("?")
            uiUrl = urlparts[0] + uiUrl
        screenReaderUrl = uiUrl[:-1] + "s"
        if self.currentInterfaceFormat == "ajax":
            self.requestUrl = screenReaderUrl
            self.pageRequest = urllib2.Request(self.requestUrl, None, self.httpHeaders)
            try:
                self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
            except:
                print "Could not set the interface to basic HTML"
                return False
            responseHeaders = self.pageResponse.info()
            if responseHeaders.has_key("Location"):
                self.httpHeaders['Referer'] = self.requestUrl
                self.requestUrl = responseHeaders.get("Location")
                self.pageRequest = urllib2.Request(self.requestUrl, None, self.httpHeaders)
                try:
                    self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
                    self.httpHeaders['Referer'] = self.requestUrl
                except:
                    print "Could not set the interface to basic HTML"
                    return False
            self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
            self.currentInterfaceFormat = "html"
            self.lastRequestUrl = self.requestUrl
            return True
        else:
            return True


    # TODO: Rectify the documentation below.
    """
    The following method lists the emails on a specific page for the folder specified. By default,
    it lists the emails in the Inbox folder's first page. If you would like to list out all emails
    on the 3rd page of your sent items folder, then your call would look something like the following:
    listOfEmailsSent = gm.listEmail("SentItems"). It populates a dictionary 'currentPageEmailsDict' 
    with the list of emails fetched from the targetted page. The dictionary keys are the subject lines
    while the values would be lists comprising of the following items: i) Sender's name or email Id, ii)
    URL of the actual email message, iii) Part of the content that is normally listed with the emails
    list in gmail, iv) Date and Time at which the message was received.
    """
    def listEmailsOnPage(self):
        pageBaseUrl = self.__class__._getPageBaseURL(self.currentPageContent)
        soup = BeautifulSoup(self.currentPageContent)
	self.currentPageEmailsDict = {}
        tableTag = soup.find("table", {'class' : 'th'})
        if not tableTag:
            print "Doesn't find any email on the current page."
            return(None)
        else:
            tableContents = tableTag.renderContents()
            tsoup = BeautifulSoup(tableContents)
            allTrs = tsoup.findAll("tr")
            # Every email has attributes specified in 4 tds. The first one contains a checkbox and we need to skip it.
            for tr in allTrs:
                tdsoup = BeautifulSoup(tr.renderContents())
                allTds = tdsoup.findAll("td")
                tdctr = 1
                sender, subject, contents, datetime, url = ("", "", "", "", "")
                for td in allTds:
                    if tdctr == 1:
                        tdctr = 2
                        continue
                    elif tdctr == 2:
                        sender = td.renderContents()
			sender = re.sub(re.compile(r"\s+", re.MULTILINE), " ", sender)
			sender = self.__class__.stripHTML(sender)
                        tdctr += 1
                        continue
                    elif tdctr == 3:
                        contentsoup = BeautifulSoup(td.renderContents())
                        aTag = contentsoup.find("a")
                        if aTag and aTag.has_key("href"):
                            url = aTag.get("href")
                            if not self.__class__._isAbsoluteUrl(url):
                                url = pageBaseUrl + url
                        bTag = contentsoup.find("b")
                        if bTag:
                            subject = bTag.renderContents()
			else: # Sometimes, the subject is not enclosed in "<b>" tags (read messages). In such cases, it will be inside the "a" tag as normal text.
			    subject = aTag.renderContents() # However, the 'subject' value will also have other tags around it, so we need to clean up...
			subject = self.__class__.stripHTML(subject) # In this case, the subject may contain a part of message.
			subject = re.sub(re.compile("\s+", re.MULTILINE), " ", subject)
                        content = aTag.renderContents()
                        fontTag = contentsoup.find("font", {'color' : '#7777CC'})
                        if fontTag:
                            content = fontTag.renderContents()
			content = self.__class__.stripHTML(content)
			content = re.sub(re.compile("\s+", re.MULTILINE), " ", content)
                        tdctr += 1
                        continue
                    elif tdctr == 4:
                        datetime = td.renderContents()
                        datetime = re.sub(re.compile("\s+", re.MULTILINE), " ", datetime)
			datetime = self.__class__.stripHTML(datetime)
                        tdctr += 1
                        continue
                self.currentPageEmailsDict[subject] = [ sender, url, content, datetime ]
        return(self.currentPageEmailsDict)
    

    def getMaxPageNumberInCurrentFolder(self):
        if self._totalEmailsInCurrentFolder == 0:
            self.getTotalMailsInCurrentFolder()
        pagesCount = int(int(self._totalEmailsInCurrentFolder) / int(self.perPageEmailsCount)) + 1
	if int(self._totalEmailsInCurrentFolder) == int(self.perPageEmailsCount):
	    pagesCount -= 1
        self.maxPageNumberCurrentFolder = pagesCount
        return(pagesCount)
        
    def getAccountActivity(self):
        soup = BeautifulSoup(self.currentPageContent)
        table = soup.find("table", {'class' : 'ft'})
        ssoup = BeautifulSoup(table.renderContents())
        span = ssoup.find("span")
        self.accountActivity.append(span.renderContents())
        div = ssoup.find("div")
        self.accountActivity.append(div.renderContents())
        return (self.accountActivity)


    """
    This method gets the URL to the next page for the current Folder/Label being accessed.
    """
    def getNextPageUrl(self):
        soup = BeautifulSoup(self.currentPageContent)
        pageBaseUrl = self.__class__._getPageBaseURL(self.currentPageContent)
        inputTag = soup.find("input", {'name' : 'nvp_tbu_go'})
        if not inputTag:
            return None
        else:
	    olderPattern = re.compile(r"Older\s+&#8250;", re.IGNORECASE | re.MULTILINE | re.DOTALL)
            tdTag = inputTag.findNext("td")
            tdContents = tdTag.renderContents()
            tdSoup = BeautifulSoup(tdContents)
	    if not tdSoup:
		return (None)
	    allAnchors = tdSoup.findAll("a")
	    for nexta in allAnchors:
	    	nextaContents = nexta.renderContents()
		if not olderPattern.search(nextaContents):
		    continue
            	if nexta.has_key("href"):
                    nextPageUrl = nexta.get("href")
                    if not self.__class__._isAbsoluteUrl(nextPageUrl):
                    	nextPageUrl = pageBaseUrl + nextPageUrl
                    return(nextPageUrl)
            	else:
                    return ("")


    """
    Gets the contents of the next page for the folder/label in which the user is currently browsing.
    This enables the user to sequentially access pages in the account.
    """
    def getNextPage(self):
        self.requestUrl = self.getNextPageUrl()
        if not self.requestUrl:
            print "There are no more pages in this folder"
            return(self.currentPageContent)
        self.httpHeaders['Referer'] = self.lastRequestUrl
        self.pageRequest = urllib2.Request(self.requestUrl, None, self.httpHeaders)
        try:
            self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
            self.currentPageNumber += 1
        except:
            print "Could not fetch the next page (Page number %s)"%(self.currentPageNumber + 1).__str__()
            return None
        self.currentPageEmailsDict = {}
        self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
        self.lastRequestUrl = self.requestUrl
        return (self.currentPageContent)
    

    """
    This method returns the count of emails in the folder currently being accessed. The current folder is
    specified by the obj.currentFolderLabel variable. This method returns None if it fails to find the count,
    and returns the count if it succeeds. Also, as a side effect, this method also populates the 'perPageEmailsCount'
    attribute of the 'GmailBot' object.
    """
    def getTotalMailsInCurrentFolder(self):
        soup = BeautifulSoup(self.currentPageContent)
        inputTag = soup.find("input", {'name' : 'nvp_tbu_go'})
        if not inputTag:
            return None
        else:
            tdTag = inputTag.findNext("td")
            tdText = tdTag.renderContents()
	    if not tdText:
		tdText = ""
	    tdText = tdText.lower()
            tdText = tdText.replace("&nbsp;", "")
	    tdText = tdText.replace("<b>", "")
	    tdText = tdText.replace("</b>", "")
            expectedPattern = re.compile(r"(\d+)\-(\d+)\s*of\s*(\d+)\D", re.IGNORECASE)
            expectedPatternSearch = expectedPattern.search(tdText)
            if expectedPatternSearch:
                emailsCount = expectedPatternSearch.groups()[2]
                self._totalEmailsInCurrentFolder = emailsCount
                lowerCount = expectedPatternSearch.groups()[0]
                higherCount = expectedPatternSearch.groups()[1]
                self.perPageEmailsCount = int(higherCount) - int(lowerCount) + 1
                return (emailsCount)
            else:
                return None

    """
    This method will enable the user to go to a page randomly. 
    """
    def getPage(self, url):
        pass


    """
    This method will fetch the textual content of the specified email message. The email should be
    specified by its URL. Thus, you need to call the 'listEmailsOnPage' method prior to calling this
    method.
    """
    def fetchEmailMessage2(self, msgUrl):
        self.requestUrl = msgUrl
        self.httpHeaders['Referer'] = self.lastRequestUrl
        self.pageRequest = urllib2.Request(self.requestUrl, None, self.httpHeaders)
        try:
            self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
        except:
            print "Could not fetch the message. Error: " + sys.exc_info()[1].__str__()
	    print "REQUEST URL: " + self.requestUrl
            return None
        self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
        self.lastRequestUrl = self.requestUrl
        return (self.currentPageContent)



    """
    This method will fetch the textual content of the specified email message. The email should be
    specified by its URL. Thus, you need to call the 'listEmailsOnPage' method prior to calling this
    method.
    """
    def fetchEmailMessage(self, msgUrl):
        httpHeaders = {}
	for reqHdr in self.httpHeaders.keys():
	    if reqHdr == 'Referer':
		httpHeaders[reqHdr] = self.lastRequestUrl # This would be the URL to the page listing the emails.
	    else:
	    	httpHeaders[reqHdr] = self.httpHeaders[reqHdr]
        pageRequest = urllib2.Request(msgUrl, None, httpHeaders)
        try:
            pageResponse = self.no_redirect_opener.open(pageRequest)
        except:
            print "Could not fetch message from '%s'. Error: %s"%(msgUrl, sys.exc_info()[1].__str__())
            return None
        pageContent = self.__class__._decodeGzippedContent(pageResponse.read())
        return (pageContent)


    def extractEmailMessage(self, htmlContent):
	message = htmlContent
	divMsgPattern = re.compile(r"<\s*div\s+class[\s\"\']*=msg[\s\"\']*>", re.IGNORECASE | re.MULTILINE | re.DOTALL)
	quickReplyPattern = re.compile(r"<b>Quick\s+Reply</b>", re.IGNORECASE | re.MULTILINE | re.DOTALL)
	htmlParts = divMsgPattern.split(message)
	if htmlParts.__len__() > 1:
	    message = htmlParts[1]
	htmlParts2 = quickReplyPattern.split(message)
	if htmlParts2.__len__() > 1:
	    message = htmlParts2[0]
	message = re.sub(EmailBot.htmlTagPattern, " ", message)
	return(message)


    """
    This method retrieves the folders that the logged in user has in her/his account.
    The return value is a dictionary, with folder names are the keys and their URLs are values.
    """
    def getAvailableFolders(self):
        pageBaseUrl = self.__class__._getPageBaseURL(self.currentPageContent)
	folderNamePattern = re.compile(r"([\w\s]+)", re.MULTILINE | re.DOTALL)
        uiUrl = self._checkInterfaceFormat()
        foldersDict = {}
        if self.currentInterfaceFormat == "ajax":
            print "The current interface is 'ajax'. In order for this function to work, you need to set the UI to 'html'."
            print "You can do that by calling 'setBasicHTMLView' method on the object that made this call."
            return None
        elif self.currentInterfaceFormat == "html":
            soup = BeautifulSoup(self.currentPageContent)
            tableM = soup.find("table", {'class' : 'm'})
            if not tableM:
                return None
            tableContents = tableM.renderContents()
            fsoup = BeautifulSoup(tableContents)
            h2tag = fsoup.find("h2", {'class' : 'hdn'})
            anchors = fsoup.findAll("a")
            for atag in anchors:
                if not atag.has_key("href"):
                    continue
                ahref = atag.get("href")
                atext = atag.renderContents()
		if not atext:
		    continue
                atext = atext.replace("&nbsp;", "")
                if not self.__class__._isAbsoluteUrl(ahref):
                    ahref = pageBaseUrl + ahref
		folderNamePatternSearch = folderNamePattern.search(atext)
		if folderNamePatternSearch:
		    atext = folderNamePatternSearch.groups()[0]
                foldersDict[atext] = ahref
            return (foldersDict)
        else:
            print "Unsupported interface format."
            return None
    

    """
    This method retrieves the labels that the logged in user has in her/his account.
    The return value is a dictionary, with label names are the keys and their URLs are values.
    """
    def getAvailableLabels(self):
        pageBaseUrl = self.__class__._getPageBaseURL(self.currentPageContent)
	labelNamePattern = re.compile(r"([\w\s]+)", re.MULTILINE | re.DOTALL)
        uiUrl = self._checkInterfaceFormat()
        labelsDict = {}
        if self.currentInterfaceFormat == "ajax":
            print "The current interface is 'ajax'. In order for this function to work, you need to set the UI to 'html'."
            print "You can do that by calling 'setBasicHTMLView' method on the object that made this call."
            return None
        elif self.currentInterfaceFormat == "html":
            soup = BeautifulSoup(self.currentPageContent)
            labelsTD = soup.find("td", {'class' : 'lb'})
            if not labelsTD:
                return labelsDict
            labelsTDContent = labelsTD.renderContents()
            lsoup = BeautifulSoup(labelsTDContent)
            anchors = lsoup.findAll("a")
            labelUrlPattern = re.compile(r"l=(\w+)$")
            for atag in anchors:
                if atag.has_key("href"):
                    ahref = atag.get("href")
                    ahref.strip()
                    labelSearch = labelUrlPattern.search(ahref)
                    if labelSearch:
                        labelName = labelSearch.groups()[0]
                        if not self.__class__._isAbsoluteUrl(ahref):
                            ahref = pageBaseUrl + ahref
			labelNamePatternSearch = labelNamePattern.search(labelName)
			if labelNamePatternSearch:
			    labelName = labelNamePatternSearch.groups()[0]
                        labelsDict[labelName] = ahref
                    else:
                        continue
                else:
                    continue
            return(labelsDict)
        else:
            return (None)


    # Get all available contacts information. This method populates the 
    # 'self.allContacts' dictionary (inherited from 'EmailBot') with the 
    # collected contacts information. It also populates the 'self.myContacts' 
    # attribute of 'GmailBot' object. This method may be called any time
    # after 'setBasicHTMLView()' method has been called. The return value
    # is the count of keys in 'self.allContacts' dictionary. If something
    # fails while operation, the method returns 'None'.
    # TODO: Implement extraction of 'MyContacts'.
    def getContactsInfo(self):
	pageBaseUrl = self.__class__._getPageBaseURL(self.currentPageContent)
	soup = BeautifulSoup(self.currentPageContent)
	allTables = soup.findAll("table", {'class' : 'm'})
	contactsPageUrl = ""
	contactUrlFoundFlag = False
	for table in allTables:
	    allAnchors = table.findAll("a")
	    for anchor in allAnchors:
		anchorContents = anchor.renderContents()
		anchorContents = anchorContents.strip()
		if anchorContents == "Contacts" and anchor.has_key('href'):
		    contactsPageUrl = pageBaseUrl + anchor['href']
		    contactUrlFoundFlag = True
		    break
		else:
		    continue
	    if contactUrlFoundFlag is True:
		break
	contactsPageUrl += "&pnl=a" # We need to get to the 'All Contacts' page.
	pageRequest = urllib2.Request(contactsPageUrl, None, self.httpHeaders)
	try:
	    pageResponse = self.no_redirect_opener.open(pageRequest)
	except:
	    print "Could not fetch contacts information page from '%s': %s\n"%(contactsPageUrl, sys.exc_info()[1].__str__())
	    return(None)
	pageContent = self.__class__._decodeGzippedContent(pageResponse.read())
	# Now pageContent contains the page listing all the contacts.
	contactSoup = BeautifulSoup(pageContent)
	inputTag = contactSoup.find("input", {'name' : 'nvp_bu_sc'})
	contactTable = inputTag.findNext("table", {'class' : 'th'})
	allTrs = contactTable.findAll("tr")
	# Skip the first 'tr'
	for trnum in range(1, allTrs.__len__()):
	    tr = allTrs[trnum]
	    allTds = tr.findAll("td")
	    name = allTds[1].renderContents()
	    emailId = allTds[2].renderContents()
	    name = name.replace("&nbsp;", "")
	    emailId = emailId.replace("&nbsp;", "")
	    name = re.sub(self.__class__.htmlTagPattern, "", name)
	    name = re.sub(self.__class__.newlinePattern, " ", name)
	    name = name.strip()
	    emailId = re.sub(self.__class__.htmlTagPattern, "", emailId)
	    emailId = re.sub(self.__class__.newlinePattern, " ", emailId)
	    emailId = emailId.strip()
	    self.allContacts[emailId] = name
	return(self.allContacts.__len__())


    # Search emails for a specific string in the content or subject.
    # The string to be searched is specified by the argument 'searchString'.
    # The third argument 'firstFlag', if True, specifies that the search
    # should return as soon as the first instance of the string is found.
    # The default value of 'firstFlag' is False, so by default all instances
    # of the 'searchString' argument are returned. The returned value from 
    # this method is a dictionary of messages that contain the searched string.
    # The keys of this dict are the URLs of the messages containing the 
    # search string, while the values are lists comprising of the date,
    # subject, sender and message. This method also accepts a fourth argument
    # that specifies the scope of the search. By default, this is 'None', 
    # meaning that the search should be conducted on all available folders 
    # and labels. However, the user may specify a list of strings as value
    # of this argument to specify the list of folders/labels in which the
    # the search is to be conducted. The strings specified in this list would
    # be case-insensitive and a regular expression match is conducted on all
    # available folder/label names to identify which folders/labels are to
    # be searched. The 'searchString' argument should follow the syntax
    # of the built-in Gmail search facility, as the search actually is 
    # conducted using Gmail's built-in search functionality.
    def searchEmails(self, searchString, firstFlag=False, containerScope=None):
        pass

    """
    This method will try to retrieve the attachment contained in the 'msgHTML' parameter. 
    If the message HTML doesn't have any attachment, the method will return None. Other-
    wise, it returns the path to the file in which the attachment contents has been dumped.
    The msgUrl parameter is not necessary here but we pass it to populate the 'referer'
    header while fetching the attachment contents. All arguments are compulsory.
    """
    def getAttachmentsFromMessage(self, msgHTML, localDir, msgUrl):
        self.attachmentLocalStorage = localDir
	messageContent = msgHTML
	soup = BeautifulSoup(messageContent)
	allAttachments = soup.findAll("a", {'target' : '_blank' })
	attachmentUrlsDict = {}
	attachmentCount = 0
	for anchor in allAttachments:
	    anchorContents = anchor.renderContents()
	    anchorContents = anchorContents.strip()
	    anchorSearch1 = self.__class__.attachmentsPattern1.search(anchorContents)
	    anchorSearch2 = self.__class__.attachmentsPattern2.search(anchorContents)
	    if not anchorSearch1 and not anchorSearch2:
		continue
	    if anchor.has_key("href"):
		downloadUrl = anchor.get("href")
	 	if not self.__class__._isAbsoluteUrl(downloadUrl):
		    downloadUrl = self.domainUrl[:-1] + downloadUrl
		prevBoldTag = anchor.findPrevious("b")
		if prevBoldTag is not None:
		    attachmentFilename = prevBoldTag.renderContents()
		else:
		    print "Couldn't find attachment filename for attachment at '%s'... Generating a timestamped filename\n"%downloadUrl
		    attachmentFilename = int(time.time()).__str__()
		attachmentFilename = attachmentFilename.strip()
		attachmentUrlsDict[downloadUrl] = attachmentFilename
	    else:
		continue
	# Set up the 'Referer' header to make the request look legitimate. (This is not necessary, but we don't want to raise anyone's eyebrows)
	httpHeaders = {}
	for hdr in self.httpHeaders.keys():
	    if hdr.lower() == 'referer':
		httpHeaders[hdr] = msgUrl
	    else:
	    	httpHeaders[hdr] = self.httpHeaders[hdr]
	ignoreAttachmentFlag = False
	# Now fetch the attachments from the URLs
	for attachmentUrl in attachmentUrlsDict.keys():
	    httpRequest = urllib2.Request(attachmentUrl, None, httpHeaders)
	    attachmentFilename = attachmentUrlsDict[attachmentUrl]
	    for filenamePattern in self.__class__.ignorableAttachmentFilenamesList:
		if filenamePattern.search(attachmentFilename) is not None:
		    ignoreAttachmentFlag = True
		    break
	    if ignoreAttachmentFlag is True:
		ignoreAttachmentFlag = False # Reset flag value
		continue # We will ignore the attachment that is being processed in this iteration. The attachment filename matches one of the ignorable filename patterns.
	    localfilename = localDir + os.path.sep + attachmentFilename
	    try:
		httpResponse = self.no_redirect_opener.open(httpRequest)
	    except:
            	print "Could not fetch redirect URL to retrieve attachments"
            	continue
	    # Now, the response headers will specify a redirect path that leads to the actual attachment.
	    responseHeaders = httpResponse.info()
	    redirectUrl = responseHeaders.getheader('Location')
	    httpRequest = urllib2.Request(redirectUrl, None, httpHeaders)
	    try:
		httpResponse = self.no_redirect_opener.open(httpRequest)
	    except:
            	print "Could not fetch attachment file '%s' from '%s'. Error: %s"%(attachmentFilename, attachmentUrl, sys.exc_info()[1].__str__())
            	continue
	    attachmentContent = httpResponse.read()
	    attachmentLength = attachmentContent.__len__()
	    if attachmentLength > 0 and (not os.path.exists(localDir) or not os.path.isdir(localDir)):
	    	os.makedirs(localDir)
	    else:
		continue
	    dataIsBin = Utils.dataIsBinary(attachmentContent)
	    fb = None
	    try:
		if dataIsBin is True:
	    	    fb = open(localfilename, "wb") # Open file in binary mode
		else:
		    fb = open(localfilename, "w")  # Open file in text mode
	    except IOError:
		attachmentFilenameParts = attachmentFilename.split(".")
		sanitizedAttachmentFilename = Utils.cleanNonFilenameCharacters(attachmentFilenameParts[0])
		localfilename = localDir + os.path.sep + sanitizedAttachmentFilename
		if attachmentFilenameParts.__len__() > 1:
		    attachmentFilenameLastPart = Utils.cleanNonFilenameCharacters(attachmentFilenameParts[1])
		    if attachmentFilenameLastPart is not None and attachmentFilenameLastPart != "":
		    	localfilename += "." + attachmentFilenameLastPart
		if dataIsBin is True:
		    fb = open(localfilename, "wb") # Open file in binary mode
		else:
		    fb = open(localfilename, "w")  # Open file in text mode
	    attachmentString = attachmentContent
	    if dataIsBin is True:
	    	packFormat = attachmentLength.__str__() + 's'
	    	attachmentString = struct.pack(packFormat, attachmentContent)
	    if fb is not None:
	    	fb.write(attachmentString)
	    	fb.close()
	    	attachmentCount += 1
	    	print "Dumped file '%s' at '%s'\n"%(attachmentFilename, localfilename)
	    else:
		#fb.close()
		print "Couldn't dump file '%s' at '%s' as filehandle is 'None'\n"%(attachmentFilename, localfilename)
	return(attachmentCount)


    # Method to logout of the account. This method sends the HTTP requests for logging out 
    # of a Gmail account and finally sets the 'self.httpHeaders' attribute to 'None' so that
    # the 'GmailBot' object cannot be used anymore to access resources from the account.
    def doLogout(self, logoutUrl=None):
	if logoutUrl is not None:
	    self.__class__.logoutUrl = logoutUrl
	print "Logging out of the account..."
	if not self.__class__.logoutUrl:
	    print "Logout URL ('%s') is not available or is invalid. Clearing cookies only to destroy the session locally."%self.__class__.logoutUrl
	    self.httpHeaders['Cookie'] = None
	    self.sessionCookies = None
	    print "Done!\n"
	    return (None)
	self.requestUrl = self.__class__.logoutUrl
	self.pageRequest = urllib2.Request(self.requestUrl, None, self.httpHeaders)
	try:
	    self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
        except:
            print "Logout request #1 failed. Error: " + sys.exc_info()[1].__str__()
	    print "Clearing cookies to make this 'GmailBot' object unusable."
	    self.httpHeaders['Cookie'] = None
	    self.sessionCookies = None
            return None
	responseHeaders = self.pageResponse.info()
        if responseHeaders.has_key("Location"):
            self.requestUrl = responseHeaders["Location"]
            self.pageRequest = urllib2.Request(self.requestUrl, None, self.httpHeaders)
	else:
	    print "Couldn't find the expected redirection URL from the response headers."
	    print "Clearing cookies to make this 'GmailBot' object unusable."
	    self.httpHeaders['Cookie'] = None
	    self.sessionCookies = None
            return None
	try:
	    self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
        except:
            print "Logout request #2 failed. Error: " + sys.exc_info()[1].__str__()
	    print "Clearing cookies to make this 'GmailBot' object unusable."
	    self.httpHeaders['Cookie'] = None
	    self.sessionCookies = None
            return None
	responseHeaders = self.pageResponse.info()
        if responseHeaders.has_key("Location"):
            self.requestUrl = responseHeaders["Location"]
            self.pageRequest = urllib2.Request(self.requestUrl, None, self.httpHeaders)
	else:
	    print "Couldn't find the expected redirection URL from the response headers."
	    print "Clearing cookies to make this 'GmailBot' object unusable."
	    self.httpHeaders['Cookie'] = None
	    self.sessionCookies = None
            return None
	try:
	    self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
	    self.httpHeaders['Cookie'] = None
	    self.sessionCookies = None
        except:
            print "Logout request #3 failed. Error: " + sys.exc_info()[1].__str__()
	    print "Clearing cookies to make this 'GmailBot' object unusable."
	    self.httpHeaders['Cookie'] = None
	    self.sessionCookies = None
            return None
	print "Successfully logged out."
	return (0)

    # This method retrieves all the account settings and loads
    # the dictionary 'accountSettings' (inherited from 'EmailBot').
    # It also dumps the data structure as an XML file if 'dumpFile'
    # argument is specified as a path to a file in a writable dir.
    # By default, however, it doesn't dump the account settings.
    def getAccountSettings(self, dumpFile=None):
	pass


    def getFolderPage(self, folderPageURL, folderName):
	self.requestUrl = folderPageURL
	self.pageRequest = urllib2.Request(self.requestUrl, None, self.httpHeaders)
	try:
	    self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
	    self.httpHeaders['Referer'] = self.requestUrl
	except:
	    print "Could not fetch page for %s folder from '%s' - Error: %s\n"%(folderName, folderPageURL, sys.exc_info()[1].__str__())
	    return(None)
	self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
	self.lastRequestUrl = self.requestUrl
	self.currentFolderLabel = folderName
        return (self.currentPageContent)



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
def drvAccountCrawler(configFile="./config/GmailBot.cfg"):
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
	sys.exit()
    # Set up default values for config params.
    outformat = "csv"
    logfile = "./Logs/GmailBot.log"
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
	ofh.write("DateTime, Subject, Sender, URL, Message\n")
    # Start crawling...
    gbot = GmailBot()
    cloneCfg = Utils._cloneConfig(cfgDict)
    logger.write("Successfully created 'GmailBot' object with following configuration:\n%s\n"%(cloneCfg.__str__()))
    html = gbot.getPageContent()
    loginStatus = gbot.doLogin(cfgDict['acctUserId'], cfgDict['acctPasswd'])
    if not loginStatus:
	print "Failed to login. Exiting..."
	logger.write("Login failed for user '%s'. Exiting...\n"%(cfgDict['acctUserId']))
	sys.exit()
    logger.write("Successfully logged in as %s\n"%(cfgDict['acctUserId']))
    gbot.setBasicHTMLView() # easier to parse
    logger.write("HTML (basic) view successfully set.\n")
    contactCount = gbot.getContactsInfo()
    logger.write("Number of contacts: %s\n"%contactCount.__str__())
    if contactCount > 0:
	logger.write("Dumping contacts: %s\n\n"%gbot.allContacts.__str__())
    contactsOutfile = outdir + os.path.sep
    fcon = None # Initialize contacts file filehandle
    if outformat.lower() == "csv": # If output format is CSV, create CSV file, open it and print headers in it.
	contactsOutfile = contactsOutfile + "CONTACTS.csv"
	fcon = open(contactsOutfile, "w")
	fcon.write("EmailID, Name\n")
	for contact in gbot.allContacts.keys():
	    fcon.write('"%s", "%s"\n'%(contact, gbot.allContacts[contact]))
    elif outformat.lower() == "xml":
	contactsOutfile = contactsOutfile + "CONTACTS.xml"
	fcon = open(contactsOutfile, "w")
	# TODO: Do whatever is necessary for XML format.
    else:
	print "Unsupported format: Falling back on default format (which is CSV)"
	contactsOutfile = contactsOutfile + "CONTACTS.csv"
	fcon = open(contactsOutfile, "w")
	fcon.write("name, details\n")
	for contact in gbot.allContacts.keys():
	    fcon.write('"%s", "%s"\n'%(contact, gbot.allContacts[contact]))
    fcon.close() # Close "CONTACTS" file handle
    if contactCount > 0:
    	logger.write("Dumped %s contacts\n\n"%contactCount.__str__())
    # Get last account activity info.
    gbot.getAccountActivity()
    print gbot.accountActivity[0]
    print gbot.accountActivity[1]
    logger.write("Account activity: %s: %s"%(gbot.accountActivity[0], gbot.accountActivity[1]))
    # Get folders and labels list and their corresponding URLs.
    labels = gbot.getAvailableLabels()
    folders = gbot.getAvailableFolders()
    logger.write("Fetched all labels and folders...\n")
    print "FOLDERS LIST: "
    logger.write("Folders List:\n")
    for fkey in folders.keys():
	logger.write("%s (URL: %s)\n"%(fkey,folders[fkey]))
        print fkey, " =========== ", folders[fkey]
    print "LABELS LIST: "
    logger.write("Labels List:\n")
    for lkey in labels.keys():
	logger.write("%s (URL: %s)\n"%(lkey,labels[lkey]))
        print lkey, " =========== ", labels[lkey]
    # Now we have got the paths to all labels and folders, so we will start iterating over them. 
    # First we iterate over folders - 'Inbox' first. 
    gbot.currentFolderLabel = 'Inbox'
    print "Processing '%s' folder...\n"%(gbot.currentFolderLabel)
    logger.write("Processing '%s' folder...\n"%(gbot.currentFolderLabel))
    count = gbot.getTotalMailsInCurrentFolder() # We are currently in 'Inbox' folder now.
    print "Total Emails In Current Folder: ", count
    logger.write("Total Emails In '%s' Folder: %s\n"%(gbot.currentFolderLabel, count.__str__()))
    print "Emails Listed Per Page: ", gbot.perPageEmailsCount
    logger.write("Emails Listed Per Page in '%s' folder: %s\n"%(gbot.currentFolderLabel, gbot.perPageEmailsCount.__str__()))
    pagesCount = gbot.getMaxPageNumberInCurrentFolder()
    print "Total Number of pages: ", pagesCount
    logger.write("Total Number of pages in '%s' folder: %s\n"%(gbot.currentFolderLabel, pagesCount.__str__()))
    for pageNum in range(1, int(pagesCount) + 1): # 'range' computes upto the preceeding integer of the second parameter.
	logger.write("Processing page #%s...\n"%pageNum.__str__())
	# Each time 'emailDict' is used, it should be re-initialized. Alternatively, one may also use 'gbot.currentPageEmailsDict' directly.
	emailDict = {}
	emailDict = gbot.listEmailsOnPage()
	logger.write("Extracted emails from page #%s\n"%pageNum.__str__())
    	for sub in emailDict.keys():
	    message = gbot.fetchEmailMessage(emailDict[sub][1])
	    if not message:
		continue
	    message = re.sub(EmailBot.newlinePattern, " ", message)
	    message = re.sub(EmailBot.multipleWhitespacePattern, " ", message)
	    message = message.decode("ascii", "ignore")
	    datetime = emailDict[sub][3].strip()
	    sender = emailDict[sub][0]
	    msgUrl = emailDict[sub][1]
	    # 'attachmentDirectory' name formula: str(datetime)/first 15 chars of subject. Whitespace characters in datetime are substituted with '_'.
	    subnameDirectory = sub[:15].strip()
	    subnameDirectory = Utils.cleanNonFilenameCharacters(subnameDirectory)
	    localdir = attachmentdir + os.path.sep + datetime.replace(" ", "_") + os.path.sep + subnameDirectory
	    logger.write("Attachment directory path: %s\n"%localdir)
	    attachmentCount = gbot.getAttachmentsFromMessage(message, localdir, msgUrl)
	    if attachmentCount > 0:
	    	logger.write("Retrieved attachment from '%s' and dumped into '%s'\n"%(msgUrl, localdir))
		print "Retrieved attachment from '%s' and dumped into '%s'\n"%(msgUrl, localdir)
	    message = gbot.extractEmailMessage(message)
	    sub = sub.decode("ascii", "ignore")
	    sender = sender.decode("ascii", "ignore")
	    msgUrl = msgUrl.decode("ascii", "ignore")
	    datetime = datetime.strip()
	    sender = sender.strip()
	    message = message.strip()
	    sub = sub.strip()
	    ofh.write('"%s", "%s", "%s", "%s", "%s"\n'%(datetime, sub, sender, msgUrl, message))
    	nextPageUrl = gbot.getNextPageUrl()
	if nextPageUrl is not None and nextPageUrl != "":
    	    print "Next Page URL: ", nextPageUrl
	    logger.write("Next page URL: '%s'\n"%nextPageUrl)
	    gbot.getNextPage()
	    logger.write("Successfully fetched next page\n")
	else:
	    print "Couldn't retrieve next page URL; possibly reached the last page for this folder."
	    logger.write("Couldn't retrieve next page URL; current page number is %s.\n"%pageNum.__str__())
	    break
    ofh.close() # close the output file where we dumped all inbox emails.
    # Now iterate over all folders - get the number of emails in each of them, list emails, and get the messages from each of them.
    inboxPattern = re.compile(r"inbox", re.IGNORECASE)
    composePattern = re.compile(r"composemail", re.IGNORECASE)
    allmailPattern = re.compile(r"all\s+mail", re.IGNORECASE)
    labelsAndFolders = Utils.mergeDicts(labels, folders) # Merge the dictionaries of labels and folders.
    for folderName in labelsAndFolders.keys():
	folderSearch = inboxPattern.search(folderName)
	if folderSearch is not None: # We have already iterated over 'inbox' folder, so we will skip processing it here.
	    continue
	folderSearch = composePattern.search(folderName)
	if folderSearch is not None: # We need to skip 'Compose Mail' folder too.
	    continue
	# TODO: Should we really skip this 'All Mail' folder? Need to analyze further.
	folderSearch = allmailPattern.search(folderName)
	if folderSearch is not None: # We need to skip 'All Mail' folder too, since we will be handling all other folders.
	    continue
	logger.write("Processing '%s' folder from '%s'...\n"%(folderName, labelsAndFolders[folderName]))
	print "Processing %s folder from '%s'..."%(folderName, labelsAndFolders[folderName])
	folderPageURL = labelsAndFolders[folderName]
	pageContent = gbot.getFolderPage(folderPageURL, folderName)
	emailsCount = gbot.getTotalMailsInCurrentFolder()
	if emailsCount is None:
	    emailsCount = 0
	logger.write("Folder '%s' contains %s emails.\n"%(folderName, emailsCount.__str__()))
	print "Folder '%s' contains %s emails.\n"%(folderName, emailsCount.__str__())
	# If there are no emails in a folder, we need not do any further processing for it. Data files will not be created for such folders.
	if emailsCount == 0:
	    continue
	pagesCount = gbot.getMaxPageNumberInCurrentFolder()
    	print "Total Number of pages: ", pagesCount
    	logger.write("Total Number of pages in '%s' folder: %s\n"%(gbot.currentFolderLabel, pagesCount.__str__()))
	# Open file where the email information for the currently processing folder will be dumped.
	contextualOutfile = Utils.getContextualFilename(cfgDict['acctUserId'], folderName)
	contextualOutfile = outdir + os.path.sep + contextualOutfile + ".csv"
	ofw = open(contextualOutfile, "w")
	if outformat.lower() == "csv": # If output format is CSV, print headers in the output file.
	    ofw.write("DateTime, Subject, Sender, URL, Message\n")
	for pageNum in range(1, int(pagesCount) + 1): # 'range' computes upto the preceeding integer of the second parameter.
	    logger.write("Processing page #%s...\n"%pageNum.__str__())
	    # Each time 'emailDict' is used, it should be re-initialized. Alternatively, one may also use 'gbot.currentPageEmailsDict' directly.
	    emailDict = {}
	    emailDict = gbot.listEmailsOnPage()
	    logger.write("Extracted emails from page #%s\n"%pageNum.__str__())
	    for subject in emailDict.keys():
		messageUrl = emailDict[subject][1]
		message = gbot.fetchEmailMessage(messageUrl)
	    	if not message:
		    continue
	    	message = re.sub(EmailBot.newlinePattern, " ", message)
	    	message = re.sub(EmailBot.multipleWhitespacePattern, " ", message)
	    	message = message.decode("ascii", "ignore")
		message = gbot.extractEmailMessage(message)
		sender = emailDict[subject][0]
		datetime = emailDict[subject][3]
		subject = subject.decode("ascii", "ignore")
		sender = sender.decode("ascii", "ignore")
		datetime = datetime.strip()
	    	sender = sender.strip()
	    	message = message.strip()
	    	subject = subject.strip()
	    	ofw.write('"%s", "%s", "%s", "%s", "%s"\n'%(datetime, subject, sender, messageUrl, message))
	    nextPageUrl = gbot.getNextPageUrl()
	    if nextPageUrl is not None and nextPageUrl != "":
    	    	print "Next Page URL: ", nextPageUrl
	    	logger.write("Next page URL: '%s'\n"%nextPageUrl)
	    	gbot.getNextPage()
	    	logger.write("Successfully fetched next page\n")
	    else:
	    	print "Couldn't retrieve next page URL; possibly reached the last page for this folder."
	    	logger.write("Couldn't retrieve next page URL; current page number is %s.\n"%pageNum.__str__())
	    	break
	ofw.close()
    gbot.doLogout()




# Gmail Scraper Program
if __name__ == "__main__":
    drvAccountCrawler()    

# supmit


