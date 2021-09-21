#!/usr/bin/python3
#Dependencies: Selenium, BeautifulSoup, urllib.parse

"""scrape.py: Scrapes the top google results from a given keyword to see 
if a given link is present on the results"""

#WEBSITES TO PERSONALIZE: 
__author__  = "Ronak Pai"
 
from flask import Flask, render_template, request, redirect, Response
import random, json
import logging
#Output file
fileWrite = open('./output/result.txt','w')
#The path for the logs
LOG_FILENAME = 'logs/logging.log'
#Set up the logger
logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG)
#All the flagged Websites
flagged = []
#Set up the app path
app = Flask(__name__)
#Render the starting website
@app.route('/')
def start():
	return render_template("index.html")
#Get the data from the website
@app.route('/recieve', methods = ['POST'])
def getData():
	#Clear the array of flagged websites
	flagged.clear()
	#Log that the script is being used
	logging.info("Scraper has been called")
	#Get the data from AJAX
	data = request.get_json(force = True)
	try:
		#URL, SEARCH_TERM, and the number of pages to be searched
		URL = str(data[0])
		SEARCH_TERM = str(data[1])
		maxPages = int(data[2])
		#Run with the given parameters
		run(URL, SEARCH_TERM, maxPages)
	#If something goes wrong, print that something went wrong on the result page as log the error
	except Exception as exc:
		logging.critical(exc)
		flagged.append("Something went wrong. Try running it again or changing your parameters")
		pass 
	#Return success to the website once we're done
	return "success"
#Run the scraper for the parameters
def run(URL, SEARCH_TERM, maxPages):
	from selenium import webdriver
	from selenium.webdriver.common.keys import Keys
	from selenium.webdriver.common.by import By
	from selenium.webdriver.support.ui import WebDriverWait
	from selenium.webdriver.support import expected_conditions as EC
	from selenium.webdriver import ActionChains
	from urllib.parse import urlparse
	from selenium.common.exceptions import TimeoutException
	from datetime import datetime
	from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
	from bs4 import BeautifulSoup
	import time
	
	#Banned websites (Websites that will never have the URL)
	banned = ["facebook.com", "twitter.com", "instagram.com", "youtube.com", "linkedin.com", "trivago.com", "mapquest.com", "booking.com", "expedia.com", "pinterest.com", "kayak.com", "google.com", "en.wikipedia.org", "imdb.com"]

	#Incognito mode and don't load images
	chrome_options = webdriver.ChromeOptions()
	prefs = {"profile.managed_default_content_settings.images":2, 'disk-cache-size': 4096}
	chrome_options.add_experimental_option("prefs",prefs)
	chrome_options.add_argument("--incognito")
	chrome_options.add_argument("--no-sandbox")
	#chrome_options.add_argument('load-extension=./gmlafnjffcblkipjaelgjdgdpmgmjbfp/1.0.0_0')
	#Run without bringing up a window
	#chrome_options.add_argument("--headless")  

	#The number of pages visited
	numPages = 0
	#Uncomment to run against remote server (Must start server first)
	#driver = webdriver.Remote(
	#   command_executor='http://127.0.0.1:4444/wd/hub',
	#   desired_capabilities=DesiredCapabilities.CHROME)

	#Create the browser
	driver = webdriver.Chrome(chrome_options=chrome_options)
	#Search up the term on Google
	driver.get("https://www.google.com")
	time.sleep(.5)
	driver.find_element_by_id("lst-ib").send_keys(SEARCH_TERM + Keys.RETURN)

	#Second driver that's only for redirects
	capabilites = DesiredCapabilities.CHROME
	#Don't load the page to save time
	capabilites["pageLoadStrategy"] = "none"
	#Create the second driver
	redirectDriver = webdriver.Chrome(chrome_options=chrome_options, desired_capabilities=capabilites)
	#Open a couple windows to make sure the program doesn't run out of windows
	redirectDriver.execute_script("window.open('');")
	redirectDriver.execute_script("window.open('');")
	#Get the time before the program in order to print out the total time
	start = datetime.now()

	#Upon exit, print the total number of pages visited and flagged websites (For debugging)
	def exit():
		logging.debug("Number of pages: " + str(numPages))
		logging.debug("Took " + str((datetime.now() - start).total_seconds()) + " seconds")
		logging.info("Flagged Websites: ")
		for p in set(flagged):
			fileWrite.write(p + "\n")
			logging.info(p)

	#Removes the http:// or https:// and www. before URLs, along with the / after them
	def strip(url):
		#Check if the URL starts with anything that we want to remove, and if so remove it
		if url.startswith('https'):
			url = url.replace("https://", "")
		elif url.startswith('http'):
			url = url.replace("http://", "")
		if url.startswith('www'):
			url = url.replace("www.", "")
		#Remove the last backlash to ensure no matching errors
		if url.endswith('/'):
			url = url[:-1]
		return url

	#Parse the given URL
	URL = strip(URL)

	#Follows a redirect link to see if it leads to the domain
	def redirect(link):
		try:
			#Open a window and switch to it
			redirectDriver.execute_script("window.open('');")
			redirectDriver.switch_to.window(redirectDriver.window_handles[-1])
			#Go to the link that was passes to the method
			redirectDriver.get(link)
			#Wait for the redirect to finish
			WebDriverWait(redirectDriver, 10).until( EC.presence_of_element_located((By.TAG_NAME, "script")) )
			time.sleep(2)
			#Gets the parsed url of the new domain
			parsed_uri = urlparse(redirectDriver.current_url)
			domain = strip('{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri))

			redirectDriver.execute_script("window.close('');")

			#If it's the same website, return True
			if domain == URL:
				return True
		#If the website doesn't exsist, we have to ignore it and move past it
		except TimeoutException:
			pass
		except:
			#Log that we ran out of windows
			logging.warning("Ran out of windows")
			#If the program runs out of windows, switch to the first window
			redirectDriver.switch_to.window(redirectDriver.window_handles[0])
			#Open a new tab
			actions = ActionChains(redirectDriver)
			actions.send_keys(Keys.COMMAND + "t").perform()
			#Try again
			return redirect(link)
			pass
	#Checks a link to see if it's a backlink
	def check(link, domain):
		#If it links to the URL or if it's text has the URL, return nothing because it links back to the URL
		if URL in strip('{uri.scheme}://{uri.netloc}/'.format(uri=urlparse(link['href']))):
			return True

		#If it might be a redirect link, follow the path to see if it links back to the website
		elif ("redir" in link['href'].lower() or "url=" in link['href'].lower() or "bit.ly" in link['href'].lower() or URL in link['href'].lower()) and (not strip('{uri.scheme}://{uri.netloc}/'.format(uri=urlparse(link['href']))) in banned):
			#If it links to an independent website, follow that href
			if bool(urlparse(link['href']).netloc) and redirect(link['href']):
				return True
			#If it redirects within the same website, go to that page in the same domain
			elif (not bool(urlparse(link['href']).netloc)) and redirect("https://www." + domain + link['href']):
				return True
		#If it finds the URL return True, otherwise if nothing is found return False
		return False

	#Searches a site for the URL
	def search(web):
		#Get the url of the Google result
		site = web.get_attribute("href")
		#Opens a new tab
		driver.execute_script("window.open('');")
		driver.switch_to.window(driver.window_handles[-1])
		#Goes to the website of the Google result
		driver.get(site)

		#Gets the parsed url
		parsed_uri = urlparse(site)
		domain = strip('{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri))

		#If it's the same website, return nothing to add to the list
		if domain == URL:
			#Close the browser and focus on the first tab
			driver.execute_script("window.close('');")
			driver.switch_to.window(driver.window_handles[0])
			return ''
		#If it's banned, do nothing
		if domain in banned:
			driver.execute_script("window.close('');")
			driver.switch_to.window(driver.window_handles[0])
			return ''
		#Checks if it's an article, if so do nothing
		if len(driver.find_elements(By.XPATH, "//a[contains(@rel, 'author')]")) > 0:
			driver.execute_script("window.close('');")
			driver.switch_to.window(driver.window_handles[0])
			return ''
		#Specialized searches for some websites
		#For tripadvisor
		if domain == "tripadvisor.com":
			cards = driver.find_elements(By.XPATH, "//span[contains(., 'Hotel website')]/parent::div")
			#Check all the "card" for the hotel website
			if len(cards) > 0:
				driver.execute_script("arguments[0].click();", cards[len(cards) - 1])
				#Click on the link and see if it links back to the website
				WebDriverWait(driver, 10).until( EC.presence_of_element_located((By.TAG_NAME, "script")))
				driver.switch_to.window(driver.window_handles[-1])
				#If it does, end your search
				if strip('{uri.scheme}://{uri.netloc}/'.format(uri=urlparse(driver.current_url))) == URL:
					#Close all the tabs you opened
					driver.close()
					driver.switch_to.window(driver.window_handles[-1])
					driver.close()
					driver.switch_to.window(driver.window_handles[0])
					return ''
				else:
					#Close the new tab before returning to the search
					driver.close()
					driver.switch_to.window(driver.window_handles[-1])
		#Default search
		bs = BeautifulSoup(driver.page_source, 'html.parser')
		#Go through every link in the page
		#If the link is present, return nothing
		for link in bs.findAll('a', href=True):
			if check(link, domain):
				driver.execute_script("window.close('');")
				driver.switch_to.window(driver.window_handles[0])
				return ''
		for link in bs.findAll('img', href=True):
			if check(link, domain):
				driver.execute_script("window.close('');")
				driver.switch_to.window(driver.window_handles[0])
				return ''
		#If nothing is found, return the name of the website to be flagged
		driver.execute_script("window.close('');")
		driver.switch_to.window(driver.window_handles[0])
		return site

	try:
		#Iterate over the pages of Google (150 is the max)
		for googlePage in range(2, 150):

			#Wait for google to load, then get the links for all the pages
		    element = WebDriverWait(driver, 10).until(
		 EC.presence_of_element_located((By.ID, "resultStats"))
		    )
		    pages = driver.find_elements_by_xpath("//*[@id='ires']//h3/a")

		    #For each of the pages, see if the URL backlink is present 
		    for result in pages:
		    	flag = search(result)
		    	if(flag != ''):
		    		#If the URL backlink isn't present, add the name of the site to the flagged websites
		    		flagged.append(flag)
		    	numPages += 1

		    	#If we've visited all the pages we wanted to, close the program
		    	if(numPages == maxPages):
		    		raise KeyboardInterrupt

		    #At the end of the page, go to the next page of results
		    driver.find_element_by_link_text(str(googlePage)).click()

	#Print out any errors we get
	except Exception as exc:
		logging.critical(exc)
	finally:
		#Quit the browsers
		exit()
		driver.quit()
		redirectDriver.quit()
		fileWrite.close()
		return
#Renders the results page with the results		
@app.route("/results")
def result():
	return render_template("done.html", results = set(flagged))

#Run the app!
if __name__ == "__main__":
	app.run(debug = False)




