from selenium import webdriver
from selenium.webdriver.chrome.service import Service


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


TESTING = True


with open('./settings.yml') as stream:
    try:
        SETTINGS = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        logger.error(exc)


'''
LinkedIn Easy Apply Crawler
- Login to LinkedIn
- Navigate to next page
- Scrape Job postings with hiring manager information
'''
class LinkedInEasyApplyCrawler:

    def __init__(self) -> None:
        pass


    '''
    May login using different chrome sessions
    '''
    def __login(self, driver:webdriver.Chrome):
        pass
    

    '''

    '''
    def login(self, secondary: False):
        pass


