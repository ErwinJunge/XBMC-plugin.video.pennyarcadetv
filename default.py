import xbmcplugin,xbmcgui,xbmcaddon
import os,urllib2,re,urlparse
from cgi import parse_qs
from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup

__addonName__   = "Penny Arcade TV"
__addonID__     = "plugin.video.pennyarcadetv"
__addon__       = xbmcaddon.Addon(__addonID__)
__strings__     = __addon__.getLocalizedString
__version__     = __addon__.getAddonInfo("version")
__dbg__         = __addon__.getSetting("debug") == "true"
__latestInSub__ = __addon__.getSetting("latestInSub") == "true"
__baseURL__     = "http://www.penny-arcade.com"

def log(msg):
    if(__dbg__):
        print "[PLUGIN] '%s (%s)' " % (__addonName__, __version__) + str(msg)

log("Parameters: " + str(sys.argv))

pluginPath = sys.argv[0]
pluginHandle = int(sys.argv[1])
pluginQuery = sys.argv[2]

def getHeaders(referrer):
    headers = {}
    headers["User-Agent"] = "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3"
    if referrer:
        headers["Referrer"] = referrer
    return headers

def getHTML(forURL, withPOSTData=None, withReferrer=__baseURL__):
    log("Get HTML for URL: " + forURL)
    req = urllib2.Request(forURL, withPOSTData, getHeaders(withReferrer))
    response = urllib2.urlopen(req)
    data = response.read()
    response.close()
    return data
  
def getRedirectURL(forURL, withReferrer=None):
    log("Get redirect for URL: " + forURL)
    req = urllib2.Request(forURL, None, getHeaders(withReferrer))
    return urllib2.urlopen(req).url 
  
def listShowsAndLatest(showOnlyLatest):
    #Note: not sure if using set content is worth the effort since there isn"t much 
    #metadata available for these episodes other than title and image
    #xbmcplugin.setContent(pluginHandle, "tvshows")
    showsPage = BeautifulSoup(getHTML(forURL=__baseURL__ + "/patv"), convertEntities=BeautifulSoup.HTML_ENTITIES)
  
    titleRegex = re.compile("Season (?P<s>[0-9]): Episode (?P<ep>[0-9]+) - (?P<title>.+)")
    onlyNumberRegex = re.compile("Season (?P<s>[0-9]): Episode (?P<ep>[0-9]+)")
  
    #Parse the current ep and show links from the root page
    infoDivs = showsPage.findAll("div",attrs={"class":"info"})
    foundShows = []
    foundEps = []
  
    #Get a list of found shows and current episodes
    for div in infoDivs:
        try:
            links = div.findAll("a")
            
            if links[0]["title"] == "Watch Now":
                ep = {}
                #Show title
                ep["title"] = links[1]["title"]

                #Episode title
                titleParts = titleRegex.match(links[2]["title"]) or onlyNumberRegex.match(links[2]["title"])
                if(titleParts is not None): 
                    titleParts = titleParts.groupdict()
                    ep["title"] += " - %sx%s" % (titleParts["s"], titleParts["ep"])
                    if "title" in titleParts:
                        ep["title"] += " - " + titleParts["title"]
                else:
                    #Fallback if title isn't an expected format...
                    ep["title"] = links[2]["title"]

                #Image and url
                ep["imgurl"] = __baseURL__ + div.parent.img["src"]
                ep["url"] = __baseURL__ + links[0]["href"]

                foundEps.append(ep)
            else:
                #Todo - Get show infos to add as some info label? Doesn"t seem to be a good view
                #that shows the info without having other fields left empty..
                show = {}
                show["title"] = links[0]["title"]
                show["imgurl"] = __baseURL__ + div.parent.a.img["src"]
                show["url"] = __baseURL__ + links[0]["href"]
                foundShows.append(show)
        except:
            log("Issue with parsing show or ep div.")
            log(div)
            continue
          
    #Add the found shows
    if not __latestInSub__ or (__latestInSub__ and not showOnlyLatest) :
        for show in foundShows:
            li = xbmcgui.ListItem(show["title"], iconImage=show["imgurl"], thumbnailImage=show["imgurl"])
            li.setInfo(type="video", infoLabels={"Title": show["title"]})
            xbmcplugin.addDirectoryItem(
                handle=pluginHandle,
                isFolder=True,
                url=pluginPath + "?action=listshowepisodes&url=" + show["url"],
                listitem=li)
    
    #Add latest directory if necessary
    if __latestInSub__ and not showOnlyLatest :
        xbmcplugin.addDirectoryItem(
            handle=pluginHandle,
            isFolder=True,
            url=pluginPath + "?action=listlatestepisodes",
            listitem=xbmcgui.ListItem(__strings__(30051)))
    
    #Add latest episodes if necessary
    if not __latestInSub__ or showOnlyLatest :
        for ep in foundEps: 
            li = xbmcgui.ListItem(ep["title"], thumbnailImage=ep["imgurl"])
            li.setProperty("IsPlayable", "true")
            xbmcplugin.addDirectoryItem(
                handle=pluginHandle,
                url=pluginPath + "?action=playvideo&url=" + ep["url"],
                listitem=li)

    xbmcplugin.endOfDirectory(pluginHandle)

def addEpisodeItem(name, url, img):
    li = xbmcgui.ListItem(name, iconImage=img, thumbnailImage=img)
    li.setInfo(type="video", infoLabels={"Title": name})
    li.setProperty("IsPlayable","true")
    xbmcplugin.addDirectoryItem(
        handle=pluginHandle,
        url=pluginPath + "?action=playvideo&url=" + url,
        listitem=li)

def listShowEpisodes(url):
    #TODO - not sure if using set content is worth the effort since there isn"t much 
    #metadata available for these episodes other than title and image
    #xbmcplugin.setContent(pluginHandle, "episodes")
    urlRegex = re.compile("/.*/.*/(.*?)/")
    episodesPage = BeautifulSoup(getHTML(forURL=url), convertEntities=BeautifulSoup.HTML_ENTITIES)

    epLists = episodesPage.findAll(attrs={"class" : "episodes"})
    if not epLists:
        epLists = episodesPage.findAll(attrs={"id" : "episodes"})
  
    #passing counter into format ep name for non number episodes
    seasonCounter = len(epLists)
    for epList in epLists:
        for ep in epList.findAll("li"):
            aTags = ep.findAll("a")
            img = __baseURL__ + ep.img["src"]
            url = __baseURL__ + aTags[0]["href"]
            name = formatEpName(aTags[0]["href"], aTags[1].contents[2], urlRegex, seasonCounter)
            addEpisodeItem(name, url, img)
        seasonCounter -= 1

    xbmcplugin.endOfDirectory(pluginHandle)
  
def formatEpName(url, epName, urlRegex, seasonCt):
    #for urls that don"t have trailing / so they will work with regex
    if url[-1] != "/":
        url += "/"
  
    #some eps in penny arcade series have non-number episodes
    epPart = urlRegex.match(url).groups()[0]
    try: 
        test = int(epPart)
        finalName = epPart[0] + "x" + epPart[1:] + " - "
    except:
        finalName = "%sx00 - " % (seasonCt)
  
    idx = epName.find(":")
    if idx != -1:
        finalName += epName[idx+2:]
    else:
        finalName += epName
    
    return finalName
    
def playVideo(url):
    #Start at video page http://www.penny-arcade.com/patv/[show]/[episode]
    #Get the embed tag on the video page as the first step to get the final url
    videoPage = BeautifulSoup(getHTML(forURL=url))
    #Assuming a single embed tag works for now
    embedUrl = videoPage("embed")[0]["src"]

    #embedUrl redirects to another Url that has a QS param for a Url to the rss file for this specific video
    #4 is to get the query portion of the final url, not sure why the named attribute doesn"t work..
    redirectUrl = urlparse.urlparse(getRedirectURL(forURL=embedUrl))
    redirectQS = parse_qs(redirectUrl[4])
    rssFileUrl = redirectQS["file"][0]
    rssFile = BeautifulStoneSoup(getHTML(forURL=rssFileUrl))

    #assuming first is default, if not true for all will need to alter this.
    mediaTags = rssFile("media:content")
    
    #todo - should probably add a default choice, need to be sure what's all available first
    choices = []
    for mTag in mediaTags:
        size = float(mTag["filesize"]) / (1024*1024)
        choices.append("%s (%sx%s) (%.2f MB)" % (mTag["blip:role"],mTag["width"],mTag["height"], size))
        
    selected = xbmcgui.Dialog().select(__strings__(30052), choices)
    
    #todo - should figure out how to gracefully not play something if they back out of 
    #selection
    if selected == -1:
        selected = 0
        
    finalVideoUrl = mediaTags[selected]["url"]

    #set the final url as the resolved url
    resolvedItem = xbmcgui.ListItem(path=finalVideoUrl)
    xbmcplugin.setResolvedUrl(pluginHandle, True, resolvedItem)
  
#Set default action
action="listshowsandlatest"

#Parse parameters, slicing to remove leading ?
params = parse_qs(pluginQuery[1:])

if len(params) > 0:
  action = params["action"][0]
  
if action == "listshowsandlatest":
  listShowsAndLatest(showOnlyLatest=False)
elif action == "listlatestepisodes":
  listShowsAndLatest(showOnlyLatest=True)
elif action == "listshowepisodes":
  listShowEpisodes(params["url"][0])
elif action == "playvideo":
  playVideo(params["url"][0])