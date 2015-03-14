**Note** : Ideally, all service provider's class implementations should call
```
super(<ServiceProviderClass>, self).__init__(username, passwd)
```
> in their `__`init`__` methods. This class is not supposed to be used directly in scripts implementing bots.


---


> ## EmailBot.NoRedirectHandler ##

This is a class derived from urllib2.HTTPRedirectHandler. This class is used by EmailBot.EmailBot (<EmailBot.EmailBot Object>.no\_redirect\_opener) and all classes derived from it to prevent automatic redirections. Need not be used externally in scripts using  any of the service provider's classes.


---


> ## GmailBot.GmailBot ##

  * This class  handles all functionalities for Gmail.

  * This is derived from 'EmailBot.EmailBot' class and it overrides some of the methods mentioned in 'EmailBot.EmailBot'.

  * This class has the following methods:

> _`__`init`__`(self, username="", passwd="")_  :  Calls EmailBot.EmailBot's `__`init`__`, and then defines some attributes of its own. The object attributes defined in this class are listed later.

> _`_`pingUserRequest(self)_  :  Method used internally in GmailBot.GmailBot. Need not be used by users importing GmailBot.GmailBot.

> _doLogin(self, username="", password="")_  :  This method completes the login process for the user specified by _username_ (and whose password is specified in _password_)

> _`_`handlePaidDomainServiceLogin(self)_  :  Handle login related functionality for paid domains in Gmail. Need not be used directly by users importing from GmailBot.GmailBot.

> _isLoginSuccessful(self)_  :  This method checks to see if the user has been able to login successfully or not. It returns a boolean 'True' if login was successful and a boolean value  of 'False' if not.

> _`_`checkInterfaceFormat(self)_  :  Checks if the format of the page is javascript/ajax or basic HTML. This method is specific to GmailBot only.

> _setBasicHTMLView(self)_  :  This method first checks to see the format of the interface. Gmail, by default, displays content as ajax/javascript. Such content is difficult to parse since the data is in the form of list variables. If the content received is in such  ajax/javascript) format, then this method tries to set the UI format to plain HTML (which is much easier to parse). This method is specific to GmailBot only. It returns a boolean value of 'True' if it successfully changes the format to HTML and 'False' if it can't. As a side effect, it also sets the attribute 'currentInterfaceFormat' to the appropriate value.

> _listEmailsOnPage(self)_  :  This method retrieves the emails on a the page specified by the 'currentPageContent' attribute of the 'GmailBot' object. The result is returned as a dict object. The dictionary keys are the subject lines while the values would be lists comprising of the following items: i) Sender's name or email Id, ii) URL of the actual email message, iii) Part of the content that is normally listed with the emails list in gmail, iv) Date and Time at which the message was received.

> _getMaxPageNumberInCurrentFolder(self)_  :  Finds the maximum page number of the email listing in the folder specified by the object attribute 'currentFolderLabel'. It computes the value on the basis of the values of the attributes  `<GmailBot_Object>._totalEmailsInCurrentFolder` and `<GmailBot_Object>.perPageEmailsCount`.

> _getAccountActivity(self)_  :  Fetches the account activity detail displayed by Gmail accounts at the bottom right corner of email listings pages.

> _getNextPageUrl(self)_  :  This method gets the URL to the next page for the current Folder/Label being accessed.

> _getNextPage(self)_  :  Gets the contents of the next page for the folder/label in which the user is currently browsing. This enables the user to sequentially access pages in the account.

> _getTotalMailsInCurrentFolder(self)_  :  This method returns the count of emails in the folder currently being accessed. The current folder is specified by the obj.currentFolderLabel variable. This method returns None if it fails to find the count, and returns the count if it succeeds. Also, as a side effect, this method also populates the perPageEmailsCount' attribute of the 'GmailBot' object.

> _fetchEmailMessage(self, msgUrl)_  :  This method will fetch the HTML content of the specified email message. The email should be specified by its URL. Thus, you need to call the 'listEmailsOnPage' method prior to calling this method. Note that there is also a method named 'fetchEmailMessage2' defined in GmailBot.GmailBot. Please ignore that method as it is only a deprecated version of 'fetchEmailMessage()' method.

> _extractEmailMessage(self, htmlContent)_  :  This method extracts the textual content of the email message passed to it as an argument. It strips the message of all HTML tags and returns only the textual content of the email message.

> _getAvailableFolders(self)_  :  This method retrieves the folders that the logged in user has in her/his account. The return value is a dictionary, with folder names are the keys and their URLs are values.

> _getAvailableLabels(self)_  :  This method retrieves the labels that the logged in user has in her/his account. The return value is a dictionary, with label names are the keys and their URLs are values.

> _getContactsInfo(self)_  :  Gets all available contacts information, and populates the 'self.allContacts' dictionary (inherited from 'EmailBot.EmailBot') with the collected contacts information. This method may be called any time after 'setBasicHTMLView()' method has been called. The return value is the count of keys in 'self.allContacts' dictionary. If something fails while operation, the method returns 'None'.

> _searchEmails(self, searchString, firstFlag=False, containerScope=None)_  :  Not yet implemented.

> _getAttachmentsFromMessage(self, msgHTML, localDir, msgUrl)_  :  This method will try to retrieve the attachment contained in the 'msgHTML' parameter. If the message HTML doesn't have any attachment, the method will return None. Otherwise, it returns the path to the file in which the attachment contents has been dumped. The msgUrl parameter is not necessary here but we pass it to populate the 'referer' header while fetching the attachment contents. All arguments are compulsory.

> _doLogout(self, logoutUrl=None)_  :  Method to logout of the account. This method sends the HTTP requests for logging out of a Gmail account and finally sets the 'self.httpHeaders' attribute to 'None' so that the 'GmailBot.GmailBot' object cannot be used anymore to access resources from the account.

> _getAccountSettings(self, dumpFile=None)_  :  This method retrieves all the account settings and loads the dictionary 'accountSettings' (inherited from 'EmailBot'). It also dumps the data structure as an XML file if 'dumpFile' argument is specified as a path to a file in a writable dir. By default, however, it doesn't dump the account settings.

> _getFolderPage(self, folderPageURL, folderName)_  :  Fetch the page listing emails from the specified folderName and  folderPageURL.


  * Object Attributes of GmailBot.GmailBot are **'requestUrl'** (a string containing the entire URL that would be requested in the next (or current) HTTP request) , '**pageRequest**' (an urllib2.Request object that is going to be dispatched), **httpHeaders**' (a dictionary containing the header field names as keys and their corresponding values as values for those keys), '**pageResponse**' (a HTTP response object), '**currentPageContent**' (the HTML content string retrieved from the last HTTP response), '**baseUrl**' (the string value of the base URL of the website being scraped), '**domainUrl**' (string variable specifying the domain and subdomain), '**sessionCookies**' (a dictionary with cookie names as keys and their corresponding values as values for that dict), '**gmail\_login\_cookie**' (Login cookie string specific to Gmail. This should not be used by the importer of this module directly), '**gmail\_rtt\_cookie**' (another Gmail specific cookie string, not to be used directly by the importer of this module), '**ping\_cookie**' (Gmail specific cookie string, not to be used directly by the importer of this module), '**currentInterfaceFormat**' (interface format of Gmail, normally we use the basic HTML interface), '**perPageEmailsCount**' (number of emails listed per page), '**accountActivity**' (list containing the last login time of the user of the Gmail account being scraped), '**isPrivateDomain**' (boolean value specifying whether the domain is a private one under Gmail or a basic gmail.com domain), '**myContacts**' (dictionary with the email Ids listed in the contacts section of the account as keys and the names of those contacts as values), '**isLoggedIn**' (a boolean value specifying whether the bot is in logged in state (True) or not (False)), '**username**' (username as which the bot is going to login), '**password**' (password for the user as which the bot will log in), '**lastChecked**' (unused variable, can't remember right now why I defined it), '**currentPageEmailsDict**' (a dict containing the emails listed in the current emails listing page with subject as the key and a list containing sender, url, content, datetime as the value), '**currentFolderLabel**' (name of the current folder or label being processed), '**currentPageNumber**' (self explanatory), '**maxPageNumberCurrentFolder**' (int value computed as the `int(int(self._totalEmailsInCurrentFolder) / int(self.perPageEmailsCount)) + 1`), '**`_`totalEmailsInCurrentFolder**' (self explanatory), '**currentInterfaceFormat**' (self explanatory), '**accountSettings**' (not yet used), and '**no\_redirect\_opener'** (the opener object used by the GmailBot.GmailBot object).

**Note:**
For GmailBot to work, you might need to change the value of GMAIL\_RTT variable in the GmailBot.py file. You will find this value by following the steps mentioned below:

  * Open Gmail in Google-Chrome browser
  * Go to 'Tools' menu of the browser and click on the "Developer tools" submenu.
  * Click on the "Network" panel of the sub-window that opens at the bottom of the browser.
  * Type in your username in the google login page that had opened in the main browser window. Press 'Tab' to move the cursor from the username field to the password field. This action sends a request to google.
  * In the 'Network' panel, you would be able to see this request. Click on the request to see the headers. Search for 'GMAIL\_RTT='. Copy the value (integer) on the right side of the '=' sign and substitute it with the 'GMAIL\_RTT' value set in the GmailBot.py file.


---


> ## YahooMailBot.YahooMailBot ##

  * This class handles functionalities of Yahoo Mail. Like GmailBot.GmailBot, this class is also derived from EmailBot.EmailBot.


  * It supports all yahoo domains (like yahoo.com, yahoo.co.in, ymail.in, rocketmail.com, yahoo.co.uk, etc).


  * The following methods are defined for YahooMailBot.YahooMailBot class:

> _`__`init`__`(self, username="", passwd="")_  :  Calls EmailBot.EmailBot's `__`init`__`, and then defines some attributes of its own. The object attributes defined in this class are listed later.


> _doLogin(self, username="", passwd="")_  :  Method to perform the login into the user account. It parses the login form to retrieve all the form variables that might be needed, builds the 'postData' and then submits the form to the appropriate URL.


> _`_`getCookieFromResponse(cls, lastHttpResponse)_  :  Extracts the session cookies from the current page response object (`<YahooMailBot_Obj>.pageResponse`)


> _`_`assertLogin(self)_  :  This method looks for the string 'You are signed in as'. If that is found in the page content, the method returns True. Otherwise this method will return False.  Note: Calling this also sets the 'signoutURL' attribute of the 'YahooMailBot' object.

> _`_`getLogoutUrl(self)_  :  This method gets the logout (or signout) URL and sets `<YahooMailBot_obj>.signoutUrl` with it.

> _fetchInboxPage(self)_  :  This method looks for the "Check Mail" button on the page and emulates the click event on it. Hence this method would be successful only if the page content has the "Check Mail" button somewhere. TO DO: This method cannot fetch the login page when the user has changed the skin to some value other than the default.

> _fetchSpamPageJSON(self, page\_num=1, num\_emails=20)_  :  This method fetches the spam emails listing page (bulk folder). The contents of the page are returned as is, Since we request the result in JSON format, Yahoo sends a JSON output and the return value from this method is a JSON data structure. The page fetches the start page by default and contains 20 email messages by default. User may override these values by passing a value for the second and third parameters. This method may be called anytime after logging in.

> _getCustomFolders(self)_  :  This method returns a dictionary comprising of all the folders that the user has created. The folder names are the keys and their URLs are the values. The count of unread messages in each of these folders appear as a bracketted ("(\d)") entry with the folder names.

> _getAvailableFolders(self)_  :  This method returns a dictionary with the built-in folder names as keys and their URLs as values. The count of unread messages in each folder also appears alongwith the names in the keys.

> _getAccountActivity(self)_  :  This won't be implemented for Yahoo mail as there is no straight forward method to find the date and time at which the current user logged in previously. (In fact, I am not sure if yahoo provides that sort of info in any way in their mail service interface. Any idea if they do ????)

> _listEmailsOnPage(self, folder="Inbox", page=1)_  :  This method fetches the list of emails on the page currently being processed. (The current page content will be in 'currentPageContent' attribute.) This method populates the 'currentPageEmailsDict' attribute of the caller object. The keys of the dictionary are subjects of the listed emails while the values are lists containing the following information in the order specified: sender, msgUrl, partialContent, dateReceived. Note: Please call this method in a try/except block so that unicode characters existing as part of subject lines or message contents do not throw an error. TODO: Add unicode support.

> _getNextPageUrl(self)_  :  Fetch the URL of the next page of emails listing in a folder.

> _getNextPage(self)_  :  This method calls the 'getNextPageUrl()' method and fetches the next page of listing for the folder being processed currently. The current folder can be obtained from `<ybotObj>.currentFolderLabel`

> _openFolderPage(self, foldername)_  :  The following 2 methods 'openFolderPage' and 'getFolderPage' perform the same function: they both navigate to the Folder page whose name is passed in as an argument. However, they are different in terms of the state of the object at the end of the method. 'openFolderPage' doesn not modify the caller object much, whereas the 'getFolderPage' method sets the caller objects attributes like 'currentPageContent', 'requestUrl', 'pageRequest', 'pageResponse', 'maxPageNumberCurrentFolder', '`_`totalEmailsInCurrentFolder' and 'newInterfaceMessagesList'.  The attributes 'currentFolderLabel' and 'currentPageNumber' are set by both methods.

> _getFolderPage(self, foldername)_  :  Please refer to the explanation for 'openFolderPage()' method above.

> _`_`listEmailsInCurrentFolderPage(self)_  :  This method extracts the list of emails from the json data structure returned as the contents of the folder. It is relevant for all folders except 'Inbox', which is taken care of by the method 'listEmailsOnPage()'. Actually, this method is called from within 'listEmailsOnPage()', so calling listEmailsOnPage()' handles all folders. Like 'listEmailsOnPage()', it populates the attributes 'currentPageEmailsDict' and currentPageEmailsDict2', and returns 'currentPageEmailsDict2' of the YahooMailBot object. Please note that this method handles only the new interface case. The older interface with HTML content is not handled by this method (and trying to use it in such cases raises an exception).

> _getTotalMailsInCurrentFolder(self)_  :  This method fetches the total emails in the folder value from the contents of the 'self.currentPageConetnt' attribute in case of the older interface (consisting of HTML). For new interface cases (interface containing javascript and json data), the following value is returned: ` int(self._totalEmailsInCurrentFolder) ` The '`_`totalEmailsInCurrentFolder' value is populated during execution of 'getFolderPage()' method. (Normally you would only call this method after calling 'getFolderPage()' since that method sets the 'currentFolderLabel' attribute which identifies the folder your object is processing currently).

> _fetchEmailMessage(self, msgUrl)_  :  Fetches the message content whose URL (or 'mid' for new interface) has been passed in as argument. Returns the message content. **Note**: For the older interface (HTML interface), the content is returned as well as the 'currentPageContent' attribute is modified. However, for the newer version, the 'currentPageContent' attribute is not affected since the response is a json data structure and assigning that to 'currentPageContent' would not be appropriate. So it would be safer if you use the returned value from this method rather than trying to figure what 'currentPageContent'  contains after calling it. TO DO: Handle unicode.

> _sendEmailMessage(self, msgDict)_  :  This method enables the user to send emails through the account currently being probed. 'msgDict' is a dictionary with the following keys: 'Subject', 'Sender', 'Recipients', 'CcRecipients', 'BccRecipients', 'MessageBody', 'Attachments'. The keys are mostly self explanatory. 'Subject' specifies the subject line string, 'Sender' specifies the sender's email Id, 'Recipients', 'CcRecipients' and 'BccRecipients' are lists of strings for specifying recipients, cc and bcc fields, 'MessageBody' specifies the actual message content and 'Attachments' specify the attached filename and its path (if any). Status: Needs a lot of testing. Doesn't work always as expected. Needs to be fine-tuned.

> _`_`assertMessageSent(self, pageContent)_  :  Internal method used by 'sendEmailMessage()' method to ascertain whether the message has been sent or not. It does this by checking the content of the page that comes up after an email has been sent.

> _getAttachmentsFromMessage(self, msgUrl, localDir)_  :  This method will try to retrieve the message pointed to by the 'msgUrl' parameter, and then try to get any attachments that might exist in the email. The 'localDir' parameter specifies the directory in which the attachment will be stored. Status: Yet to be implemented

> _getAttachmentsPage(self, page=1)_  :  This method retrieves the list of all the attachments in your emails. By default, it takes you to the first page, but specifying a page number will take you to the specified page. It returns the HTML of the page which is retrieved. Status: Yet to be implemented.

> _doLogout(self)_  :  Method to logout of the account. Depends on whether the 'signoutUrl' had been extracted while asserting the success of 'doLogin()' method. Thus, this will not be able to perform successfully if '`_`assertLogin()' was never called.

> _extractEmailMessage(self, htmlContent)_  :  Method to extract the email message from the HTML content of the message page. Handling of old interface cases is still not perfect. The new interface is handled successfully. The method strips all HTML tags that are part of the message and returns only the unformatted text content of the message.

> _getAccountSettings(self, dumpFile=None)_  :  This method retrieves all the account settings and loads the dictionary 'accountSettings' (inherited from 'EmailBot'). It also dumps the data structure as an XML file if 'dumpFile' argument is specified as a path to a file in a writable dir. By default, however, it doesn't dump the account settings.

> _getContactsInfo(self)_  :  Get all available contacts information. This method populates the 'self.allContacts' dictionary (inherited from 'EmailBot') with the collected contacts information. This method should be called before navigating to any of the folders or inbox page. The return value is the count of keys in 'self.allContacts' dictionary. If something fails while operation, the method returns 'None'. Note: Best time to call this method is immediately after 'doLogin()'.

  * Object Attributes of YahooMailBot.YahooMailBot are '**requestUrl**' (same as in GmailBot), '**pageRequest**' (same as in GmailBot), '**httpHeaders**' (same as in GmailBot), '**pageResponse**' (same as in GmailBot), '**currentPageContent**' (same as in GmailBot), '**baseUrl**' (same as in GmailBot), '**domainUrl**' (same as in GmailBot), '**sessionCookies**' (same as in GmailBot), '**currentInterfaceFormat**' (same as in GmailBot), '**perPageEmailsCount**' (same as in GmailBot), '**accountActivity**' (same as in GmailBot, but not yet used in YahooMailBot), '**myContacts**'  (same as in GmailBot), '**isLoggedIn**' (same as in GmailBot), '**username**' (same as in GmailBot), '**password**' (same as in GmailBot), '**lastChecked**' (same as in GmailBot), '**currentPageEmailsDict**' (same as in GmailBot), '**currentFolderLabel**' (same as in GmailBot), '**currentPageNumber**' (same as in GmailBot), '**maxPageNumberCurrentFolder**' (same as in GmailBot), '**`_`totalEmailsInCurrentFolder**' (same as in GmailBot), '**currentInterfaceFormat**' (same as in GmailBot), '**accountSettings**' (same as in GmailBot), '**wssid**' (a value used specifically in Yahoo emails listing pages after logging in, not to be used by users importing YahooMailBot), '**newInterface**' (Boolean value specifying whether the account uses the new json based interface or the old HTML based one), '**newInterfaceMessagesList**' (list containing messages from the new interface, please see implementation for a clear idea), '**attachmentLocalStorage**'  (same as in GmailBot) and '**no\_redirect\_opener**' (same as in GmailBot).


---


> ## Tools`.`Utils Module ##

  * This is an utility module that consists of various functions that do not fit anywhere in the bot classes.

  * It consists of the following functions:

> _getUrlDirPathFromUrl(url)_  :  This function retrieves the URL path from the URL passed to it as argument.

> _getCountryNameFromIP(ipaddr)_  :  Retrieve the name of the country in which the IP passed in as argument is based in. It uses the GeoIP module and database to extract the information.

> _getIPAddrFromUrl(urlStr)_  :  Retrieve the IP address of the server from an URL.

> _readBasicConfig(cfgfile)_  :  Read a configuration file with the following basic format: Each line contains a config parameter and its value of the form 'param=value'. Parameter names may not contain spaces. Values may contain spaces and should always be terminated by newline character or '#' character (comment character). Parameter names and values are separated by a '=' sign. Whitespaces around the '=' sign are trimmed when the line is processed by this function. Whitespace characters may also be present at the start and end of a line. These are also trimmed while processing the line. Lines may also contain comments. Comments always start with '#'. Everything succeeding a '#' character is ignored by this function. Lines may also be empty (containing 0 or more spaces). Comments lines and empty lines are ignored during processing.

> _`_`cloneConfig(cfgDict)_  :  Clone a config dict with the passwd info blanked out.

> _getContextualFilename(acctId, contextString=None)_  :  Create a valid filename from a string passed as argument.

> _cleanNonFilenameCharacters(s)_  :  Removes characters from the given string that cannot be used in a filename.

> _fileIsBinary(filename)_  :  Function to check if a file is a binary file or not (ASCII text file). Return true if the given filename appears to be binary. File is considered to be binary if it contains a NULL byte. TODO: This approach incorrectly reports UTF-16 as binary. Need to fix this. (This function was taken from a post in stackoverflow.com)

> _dataIsBinary(data)_  :  Function to check if a file is a binary file or not (ASCII text file). Return true if the given data appears to be binary. Data is considered to be binary if it contains a NULL byte. TODO: This approach incorrectly reports UTF-16 as binary. Need to fix this. (This function was taken from a post in stackoverflow.com)

> _mergeDicts(dict1, dict2)_  :  Function to merge 2 dicts to form a 3rd dict. If dict1 has one or more keys common to dict2, then the values for those keys in dict3 will be the ones specified for dict2.

> _decodeHtmlEntities(content)_  :  This is self explanatory.

> _cleanUp(content)_  :  Removes multiple whitespace characters with single whitespace character, and also removes double quotes from the content.

> _sortCsv(filename, indices, datatypes)_  :  Method to sort CSV file on one or more fields. This is not yet implemented. More will be specified here one implementation is complete.

> _setSignal()_  :  Signal handler implementation. Not yet implemented. More will be specified here one implementation is complete.

  * This module also has a variable defined  in it: **urlPattern**. It holds the regular expression pattern of a URL.