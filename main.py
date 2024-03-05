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



from common_methods import *
# To get out of testing mode and actually do scraping, 
# 1. Remove TEST_SEARCH_PATH file in your folder
# 2. Remove TEST_PROFILE_PATH in your folder
# 3. Set TESTING to False

TEST_SEARCH_PATH = './sample_search.html'
TEST_PROFILE_PATH = './sample_profile.html'
TESTING = False

with open("./settings.yml") as stream:
    try:
        SETTINGS = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)


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
        chrome_driver_path = ChromeDriverManager().install()

        

        cService = webdriver.ChromeService(executable_path=chrome_driver_path)
        

        logger.info("Opening automated primary browser")
        self.driver = webdriver.Chrome(service=cService)

        logger.info("Opening automated secondary browser")
        self.secondary_driver = webdriver.Chrome(service=cService)
        logger.info("Initialized drivers")
        

    '''
    Can raise exceptions

    @param search_term search term
    @param filters filters dictionary object
    @return bool for success/failure
    '''
    def login(self, secondary:bool = False):
        
        driver = self.secondary_driver if secondary else self.driver
        logger.info(f"Logging in on {"primary" if not secondary else "secondary"}")
        endpoint = f"{self.url}/login"

        driver.get(endpoint)

        username = input("Username: ")
        password = getpass("Password: ")
        
        username_field = driver.find_element(By.ID, 'username')
        password_field = driver.find_element(By.ID, 'password')

        username_field.send_keys(username)
        password_field.send_keys(password)

        sign_in_btn = (
            driver
            .find_element(By.CLASS_NAME, 'login__form_action_container')
            .find_element(By.TAG_NAME, 'button')
        )
        # sign_in_btn = driver.find_element(By.XPATH, '//*[@id="organic-div"]/form/div[3]/button')
        logger.debug(f"Button retreived: {sign_in_btn.text}")
        sign_in_btn.click()
        
        # wait_until(driver, By.ID, 'ember19')

        logger.info(f"Logged in on {"primary" if not secondary else "secondary"}")
        
        input("Click any button after security check...")




        

    def __get_search_options(self):
        with open("./search_options.yml") as stream:
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
        actor = post_object.find("div", {'class': 'update-components-actor'})
        if actor is None:
            return None
        text = None

        name = (
            actor
            .find('span', {'class': 'update-components-actor__name'})
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
            .find('a', {'class': 'update-components-actor__sub-description-link'})
            .get('href')

        )

        try:
            text = (
                post_object
                .find('div', {'class', "feed-shared-update-v2__description-wrapper mr2"})
                .find('span', {'class', 'break-words'})
                .get_text(" ",strip=True)
            )
        except Exception as err:
            logger.error(f"Error with {profile_link}")
            logger.exception(err)


        social_counts = post_object.find('div', {'class', 'social-details-social-counts'})
        likes = None
        comments = None
        reposts = None
        if social_counts is not None:
            like_container = (
                social_counts
                    .find('span', {'class', 'social-details-social-counts__reactions-count'})
                )
            if like_container:
                likes = like_container.get_text(" ", strip=True)

            # for reposts and comments
            containers = social_counts.find_all('li')

            for container in containers:
                # like containers have buttons 
                # comments and reposts containers have spans with text: 
                # x comments, y reposts
                
                # check if container span text has comments or reposts
                if container.find('span') is not None:
                    span_text = container.find('span').get_text(' ', strip=True)
                    
                    # assign values accordingly
                    if "comment" in span_text:
                        comments = span_text.split(' ')[0]
                    elif "repost" in span_text:
                        reposts = span_text.split(' ')[0]
        
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
            soup = self.__get_test_soup_profile()
        else:
            self.secondary_driver.get(post_url)
            time.sleep(2)
            page = self.secondary_driver.page_source
            soup = bs(page.encode('utf-8'), features='html.parser')
        
        try:
            location = (
                soup
                # .find('main', {'class', 'scaffold-layout__main'})
                .find('ul', {'class', 'pv-text-details__right-panel'})  # Right panel is the one with work places
                .find_parent('div', {'class', 'mt2 relative'})          # Find the parent container
                .find_all('div')[-1]                                    # Find the last container in the parent
                .find_next('span')                                      # Get the span
                .get_text(" ", strip=True)                              
            )
        except Exception as err:
            logger.warning(f"location not found because there is no company for {post_url}")
            location = None

        
        
        # about_me = (
        #     soup
        #     .find('div', {'id', 'about'})    # This might be deprecated soon
        #     # .find_parent('div', {'class', 'pv-profile-card'})
        #     # .find('div', {'class', 'pv-shared-text-with-see-more'})
        #     # .find('span', {'class', 'visually-hidden'})
        #     # .get_text(" ", strip=True)
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
                .find('ul', {'class', 'pv-text-details__right-panel'})
                .find_all('li')[0]
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
    
    def __scroll_all(self):
        TIME_BETWEEN_SCROLLS = 4
        MAX_SCROLLS = 2              # For testing

        # Javascript scrolling
        scroll_command = "window.scrollTo(0, document.body.scrollHeight);"
        scroll_height_command = "return document.body.scrollHeight"

        # First scroll height
        last_height = self.driver.execute_script(scroll_height_command)
        scrolls = 0
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
        self.__scroll_all()
        page = self.driver.page_source

        soup = bs(page.encode('utf-8'), features='html.parser')
        with open(TEST_SEARCH_PATH, "w", encoding='utf-8') as file:
            file.write(str(soup))
        

        



    def scrape(self):
        # if else method just for testing purposes.
        # This is just to avoid parsing every time 
        if not TESTING:
            # Scroll all to load all
            logger.info(f"Scrolling till the end")
            self.__scroll_all()
            time.sleep(5)
            # Get container (list)
            page = self.driver.page_source
            soup = bs(page.encode('utf-8'), features='html.parser')
        else:
            soup = self.__get_test_soup_search()
        
        logger.info(f"Getting post and recruiter details")
        search_results = soup.find("div", {'class':"search-results-container"})
        
        # Get all posts
        posts = search_results.find_all('div', {'class': 'feed-shared-update-v2'})
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
        
    
    def __save(self, dictionary, filename):
        try: 
            # Convert to pandas
            df = pd.DataFrame(dictionary).fillna(np.nan)
            
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
    crawler.login(secondary=True)

    crawler.search("Machine Learning Hiring")
    if crawler.scrape() == True:
        logger.info("Success")


    # time.sleep(5)


    
    