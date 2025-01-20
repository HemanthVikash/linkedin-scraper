from selenium import webdriver
from selenium.webdriver.chrome.service import Service

import chromedriver_autoinstaller
import tqdm
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup as bs

import yaml
import os
import pandas as pd
import numpy as np

import time
from getpass import getpass

from typing import Final, List

from common_methods import *

from pprint import pprint
import keyring
# To get out of testing mode and actually do scraping, 
# 1. Set TESTING to False


with open("./settings.yml") as stream:
    try:
        SETTINGS = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)

TEST_SEARCH_PATH: Final = os.path.join('data', SETTINGS['intermediate_files']['sample_search'])
TEST_PROFILE_PATH: Final = os.path.join('data', SETTINGS['intermediate_files']['sample_profile'])
TESTING = False


'''
LinkedIn Post Crawler
Login to LinkedIn and crawl posts

'''
class LinkedInPostCrawler:

    def __init__(self):
        # Automatically download and install ChromeDriver
        
        # chrome_driver_path = ChromeDriverManager._get_driver_binary_path()
        # driver_path =  chromedriver_autoinstaller.install()
        # print(f"{chrome_driver_path}, {driver_path}")
        # chrome_driver_path = '/Users/paramesh/.wdm/drivers/chromedriver/mac64/122.0.6261.69/chromedriver-mac-x64/chromedriver'
        
        self.url = 'https://www.linkedin.com'

        logger.info("Installing Chrome Driver")
        
        # ChromeDriver Way
        # chrome_driver_path = ChromeDriverManager().install()
        # cService = webdriver.ChromeService(executable_path=chrome_driver_path)
        
        # logger.info("Opening automated primary browser")
        # self.driver = webdriver.Chrome(service=cService)

        # Selenium Way
        service = Service()
        options = webdriver.ChromeOptions()
        
        logger.info("Opening automated primary browser")
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.get(self.url)

        logger.info("Opening automated secondary browser")
        secondary_service = Service()
        secondary_options = webdriver.ChromeOptions()
        self.secondary_driver = webdriver.Chrome(service=secondary_service, options=secondary_options)
        self.secondary_driver.get(self.url)
        
        logger.info("Initialized drivers")

        self.password_store = SETTINGS['authentication']['password_storage']
        self.username = SETTINGS['authentication']['username']

        if self.username is None:
            raise PermissionError("Username is not set")
        if self.password_store is None:
            raise PermissionError("Password store is not set")
        

        self.results: dict = None

    '''
    Can raise exceptions

    @param search_term search term
    @param filters filters dictionary object
    @return bool for success/failure
    '''
    def login(self):
        
        driver = self.driver
        endpoint = f"{self.url}/login"

        driver.get(endpoint)



        password: str = keyring.get_password(service_name=self.password_store, username=self.username)
        

        if password is None:
            logger.info("Authentication failed. Please enter username and password")
            username = input("Username: ")
            password = getpass("Password: ")

            if self.username != username:
                logger.warning("Username mismatch. Please ensure you provide this username in the settings file")
                self.username = username

            keyring.set_password(self.password_store, self.username, password)

            
        
        

        
        username_field = driver.find_element(By.ID, 'username')
        password_field = driver.find_element(By.ID, 'password')

        username_field.send_keys(self.username)
        password_field.send_keys(password)

        sign_in_btn = (
            driver
            .find_element(By.CLASS_NAME, 'login__form_action_container')
            .find_element(By.TAG_NAME, 'button')
        )
        
        sign_in_btn.click()
        
        logger.info(f"Logged in...")
        
        # Update the secondary driver with login cookies
        logger.info(f"Updating secondary driver cookies")
        cookies = driver.get_cookies()
        for cookie in cookies:
            self.secondary_driver.add_cookie(cookie)

        self.secondary_driver.refresh()

        
        
        input("Click any button after security check...")




        

    def __get_search_options(self):
        
        with open(os.path.join('code', 'search_options.yml')) as stream:
            try:
                return yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        return

    def search(self, keywords:str):
        logger.info(f"Navigating to search")
        endpoint = f"{self.url}/search/results/content/"
        
        filter_options = self.__get_search_options()
        search_terms = search_params(search_term=keywords, filter_options=filter_options)
        self.driver.get(endpoint + search_terms)


    def __get_post_details(self, post_object:bs):
        actor = post_object.find("div", {'class': 'update-components-actor__container'})
        if actor is None:
            return None
        text = None

        name = (
            actor
            .find('span', {'class': 'update-components-actor__title'})
            .find('span', {'class': 'visually-hidden'})
            .get_text(" ",strip=True)
            )
        
        
        subheading = (
            actor
            .find('span', {'class': 'update-components-actor__description'})
            .find('span', {'class': 'visually-hidden'})
            .get_text(" ",strip=True)
        )

        profile_link = (
            actor
            .find('a', {'class': 'update-components-actor__meta-link'})
            .get('href')

        )

        try:
            # description_container = post_object.find("div", {
            #     "class": "update-components-text"
            # })
            text = (
                post_object
                .find("div", {"class": "update-components-text"})
                .find("span", {"class": "break-words"})
                .get_text(" ", strip=True)
            )
        except Exception as err:
            logger.error(f"Error with {profile_link}")
            logger.exception(err)


        social_counts = post_object.find('div', {'class', 'social-details-social-counts'})
        likes = None
        comments = None
        reposts = None
        if social_counts is not None:
            # Extract likes (reactions)
            like_button = social_counts.find("button", {"aria-label": True})
            if like_button and "reaction" in like_button.get("aria-label", "").lower():
                likes = like_button.get("aria-label").split()[0]

            # Extract comments and reposts
            interaction_items = social_counts.find_all(
                "li", class_=lambda x: x and "social-details-social-counts__item" in x
            )
            for item in interaction_items:
                button = item.find("button", {"aria-label": True})
                if button:
                    aria_label = button.get("aria-label", "").lower()
                    if "comment" in aria_label:
                        comments = aria_label.split()[0]
                    elif "repost" in aria_label:
                        reposts = aria_label.split()[0]
        
        person_result = None
        profile_type = None
        # Get person detail
        ## If subheading is of the format "10,934 followers"
        ## it is a page. No need to scrape
        heading_split = subheading.split(' ')
        if len(heading_split) == 2:
            if heading_split[1] == 'followers' and '/company/' in profile_link:
                profile_type = 'Page'
        
        if("/company/" not in profile_link):
            # Else, it is a person. Should scrape
            person_result = self.get_person_details(profile_link)
            profile_type = 'Person'


        
        


        

        result = {
            "name": name,
            "profile_link": profile_link,
            "subheading": subheading,
            "profile_type": profile_type,
            "text": text,
            "likes": likes,
            "comments": comments,
            "reposts": reposts,
            
        }

        if person_result is not None:
            # merge both
            result.update(person_result)
            

        # logger.info(f"Keys: {result.keys()}, {person_result}, {profile_link}")
        return result

    def store_person_details(self, post_url: str):
        self.secondary_driver.get(post_url)
        time.sleep(5)
        page = self.secondary_driver.page_source

        soup = bs(page.encode('utf-8'), features='html.parser')
        with open(TEST_PROFILE_PATH, "w", encoding='utf-8') as file:
            file.write(str(soup))

    

        



    def __get_test_soup_profile(self):
        # Open and read the HTML file
        with open(TEST_PROFILE_PATH, 'r', encoding='utf-8') as file:
            html_content = file.read()

        # Parse HTML with Beautiful Soup
        soup = bs(html_content, 'html.parser')

        return soup
    
    def __get_test_soup_search(self):
        # Open and read the HTML file
        with open(TEST_SEARCH_PATH, 'r', encoding='utf-8') as file:
            html_content = file.read()

        # Parse HTML with Beautiful Soup
        soup = bs(html_content, 'html.parser')

        return soup

    '''
    TODO: Change location dependency on employer
    TODO: Add about me functionality
    '''
    def get_person_details(self, post_url: str):
        
        
        if TESTING:
            if os.path.exists(TEST_PROFILE_PATH):
                logger.info(f"File {TEST_PROFILE_PATH} exists. Using that")
                soup = self.__get_test_soup_profile()
        else:
            self.secondary_driver.get(post_url)
            time.sleep(2)
            page = self.secondary_driver.page_source
            soup = bs(page.encode('utf-8'), features='html.parser')
            if not os.path.exists(TEST_PROFILE_PATH):
                self.save_page(page_path=TEST_PROFILE_PATH, secondary=True)
        try:
            # location = (
            #     soup
            #     # .find('main', {'class', 'scaffold-layout__main'})
            #     .find('ul', {'class', 'pv-text-details__right-panel'})  # Right panel is the one with work places
            #     .find_parent('div', {'class', 'mt2 relative'})          # Find the parent container
            #     .find_all('div')[-1]                                    # Find the last container in the parent
            #     .find_next('span')                                      # Get the span
            #     .get_text(" ", strip=True)                              
            # )


            location = (
                soup
                .find(id='top-card-text-details-contact-info')
                .find_parent('span') # Find the contact info button
                .find_previous_sibling('span')
                .get_text(" ", strip=True)

            ) 
        except Exception as err:
            logger.warning(f"location not found because there is no company for {post_url}: {err}")
            location = None

        
        
        # about_me = (
        #     soup
        #     .find(id='ember34')         # Get name
        #     .find_parent('div')         # Get parent container
        #     .find_next_sibling('div')   # Next sibling is about me
        #     .get_text(" ", strip=True)
        # )
        about_me = None
        try:
            followers = (
                soup
                .find("ul", {'class', 'pv-top-card--list-bullet'})
                .find_next('li')
                .find('span', {'class', 't-bold'})
                .get_text(" ", strip=True)
                # .prettify()
                )
        except Exception as err:
            logger.warning(f"No follower count found for user {post_url}")
            followers = None
        
        try:
            company = (
                soup
                .find(id='top-card-text-details-contact-info')
                .find_parent('div')                # Find the contact info button
                .find_previous_sibling('ul')       # Find the previous sibling which is the work experience tab
                .find_all('li')[0]                 # Find the first work experience
                .get_text(" ", strip=True)

            )
        except Exception as err:
            logger.warning(f"No company found for user {post_url}")
            company = None

        result = {
            "location": location, 
            'followers': followers, 
            "about_me": about_me, 
            "company": company
        }

        
        # logger.info(f"{result}")
        return result
    
    def scroll_all(self):
        TIME_BETWEEN_SCROLLS = 4
        MAX_SCROLLS = 2              # For testing

        # Javascript scrolling
        scroll_command = "window.scrollTo(0, document.body.scrollHeight);"
        scroll_height_command = "return document.body.scrollHeight"

        # First scroll height
        last_height = self.driver.execute_script(scroll_height_command)
        scrolls = 3
        no_change = 0

        while True:
            # Scroll down
            self.driver.execute_script(scroll_command)

            # Hardcoded wait TODO: change to element based if possible
            time.sleep(TIME_BETWEEN_SCROLLS)

            # Get new height
            new_height = self.driver.execute_script(scroll_height_command)

            # No change update
            no_change += 1 if new_height == last_height else 0

            if no_change >= 3 or (scrolls >= MAX_SCROLLS and TESTING):
                break
            
            last_height = new_height
            scrolls += 1
        


            

    def store_search_details(self):
        self.login()
        self.search("Machine Learning Hiring")
        self.scroll_all()
        page = self.driver.page_source

        soup = bs(page.encode('utf-8'), features='html.parser')
        with open(TEST_SEARCH_PATH, "w", encoding='utf-8') as file:
            file.write(str(soup))
        

        

    def save_page(self, page_path:str=os.path.join('data', 'sample_page.html'), secondary: bool = False):
        
        driver = self.secondary_driver if secondary else self.driver
        
        
        page = driver.page_source
        soup = bs(page.encode('utf-8'), features='html.parser')
        
        with open(page_path, 'w', encoding='utf-8') as file:
            file.write(str(soup))
        

    def scrape(self):
        # if else method just for testing purposes.
        # This is just to avoid parsing every time 
        try:
            if not TESTING:
                # Scroll all to load all
                logger.info(f"Scrolling till the end")
                self.scroll_all()
                time.sleep(5)
                
                logger.info(f"Saving page to file {TEST_SEARCH_PATH}")
                self.save_page(page_path=TEST_SEARCH_PATH)
                # Get container (list)
                page = self.driver.page_source
                soup = bs(page.encode('utf-8'), features='html.parser')
            else:
                if os.path.exists(TEST_SEARCH_PATH):
                    logger.info(f"File {TEST_SEARCH_PATH} exists. Using that")
                    soup = self.__get_test_soup_search()
                else:
                    logger.info(f"File {TEST_SEARCH_PATH} does not exist.")
            
            logger.info(f"Getting post and recruiter details")
            search_results = soup.find("div", {'class':"search-results-container"})
            
            # Get all posts
            posts = search_results.find_all('div', {'class': 'feed-shared-update-v2'})
            posts = posts if len(posts) > 0 else search_results.find_all('li', {'class': 'artdeco-card'})
            logger.info(f"Posts count: {len(posts)}")

            # Each post call __get_post_details
            
            post_details = [] 
            for post in tqdm.tqdm(posts):
                details = self.__get_post_details(post_object=post)
                if details is not None:
                    post_details.append(details)
                else:
                    logger.warning("No actor found")
            
                


            logger.info(f"posts details for {len(post_details)} posts")
            # Each post link __get_person_details
            if TESTING:

                return self.__save(post_details, SETTINGS['results']['test_posts_file'])
            
            return self.__save(post_details, SETTINGS['results']['posts_file'])
        
        except KeyboardInterrupt as err:
            logger.info(f"Code attempted to stop. Exiting after writing results")
            return self.__save(post_details, SETTINGS['results']['posts_file'])
        
    
    def __save(self, dictionary, filename):
        try: 
            # Convert to pandas
            df = pd.DataFrame(dictionary).fillna(np.nan)
            
            # Create directory if it does not exist
            dir_path = os.path.dirname(filename)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

            # Save to csv
            df.to_csv(filename, index=False)
        except Exception as ex:    
            logger.error(f"{ex}")
            return False
        # return true/false for success/failure
        return True




if __name__ == '__main__':

    logger.info(f"Results to be saved in {SETTINGS['results']['posts_file']}")

    crawler = LinkedInPostCrawler()
    # if not os.path.exists(TEST_SEARCH_PATH):
    #     logger.info(f"File {TEST_SEARCH_PATH} does not exist. Scraping for test file")
    #     crawler.login()
    #     crawler.search("Machine Learning Hiring")
    # crawler.scrape()
    # crawler.login(secondary=True)
    # crawler.store_person_details('https://www.linkedin.com/in/sheth/')
    
    crawler.login()
    # TESTING = True
    # person = crawler.get_person_details('https://www.linkedin.com/in/venali/')
    # pprint(person)
    # TESTING = False

    crawler.search("Machine Learning Hiring")
    

    if crawler.scrape() == True:
        logger.info("Success")

    input("Type anything to end code....")
    # time.sleep(5)


    
    