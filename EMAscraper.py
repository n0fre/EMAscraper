#! python3
# EMAscraper v1.1
# Downloads all PDFs from European Medicines Agency search results to ./output

# Define the URL of the EMA search action here
url = 'https://www.ema.europa.eu/en/medicines/field_ema_web_categories%253Aname_field/Human'
#url2 = 'https://www.ema.europa.eu/en/medicines/human/paediatric-investigation-plans/emea-002503-pip01-18'

# Load the libraries
import requests, re, sys, os, math, threading
from pathlib import Path
from bs4 import BeautifulSoup

os.makedirs('output', exist_ok=True)  # Makes the ./output directory

# Sets some variables
directory = '.' if not sys.argv[1:] else sys.argv[1]
links = []
downloadThreads = []
maxThreads = 100
sema = threading.Semaphore(value=maxThreads)
screenLock = threading.Semaphore(value=1)

# Defines the function to request the page from a url and parse it
def getPageAndParse(url):
    global soup
    res = requests.get(url)
    try:
        res.raise_for_status()
    except Exception as exc:
        print('There was a problem: %s' % (exc))
    soup = BeautifulSoup(res.text, 'html.parser')

# Gets the search hit links from the current page
def getLinksFromPage(url):
    global links
    getPageAndParse(url)
    for link in soup.select('.ecl-list-item__link'):
        links.append(link.get('href'))

# Gets the total number of search hits and calculates the total number of pages required to loop through
getPageAndParse(url)
numResults = int(''.join(filter(str.isdigit, soup.select('.ecl-u-mr-xl')[0].text)))
numPages = math.ceil(numResults / 25)

# Loops through all available pages (like clicking the 'load more' button until the end)
for i in range(0, numPages):
    urlPage = url + '?page=' + str(i)
    getLinksFromPage(urlPage)

# Downloads all PDFs from the search hit
def downloadPDFs(url):
    getPageAndParse(url)

    links = soup.findAll('a', href=re.compile("\.pdf$"))

    pdfNumber = 0

    if links != []:
        for el in links:
            pdfNumber = pdfNumber + 1
            headerElem = soup.select('h1')[0].text

            screenLock.acquire()
            print('This is page: ' + url + ' (%s)' % (headerElem))
            if r"/" in headerElem:  # Replaces slashes with dashes in header element
                headerElem = headerElem.replace("/", "-")

            print("Downloading pdf: " + el['href'])
            screenLock.release()

            pdfURL = el['href']

            res = requests.get(pdfURL)
            try:
                res.raise_for_status()
            except Exception as exc:
                print('There was a problem: %s' % (exc))

            pdfFile = open(Path(directory, 'output', headerElem + '_' + str(pdfNumber).zfill(2) + '.pdf'), 'wb')
            for chunk in res.iter_content(100000):
                pdfFile.write(chunk)
        pdfFile.close()
    else:
        print('No PDFs found.')

# Downloads the PDFs from the list of search hits
def processSearchHits(SearchHit):
    global links
    sema.acquire()
    link = links[SearchHit]
    urlSearchHit = 'https://www.ema.europa.eu' + link
    downloadPDFs(urlSearchHit)
    sema.release()

# Create and start the thread objects
for i in range(numResults):
    downloadThread = threading.Thread(target=processSearchHits, args=(i,))
    downloadThreads.append(downloadThread)
    downloadThread.start()
