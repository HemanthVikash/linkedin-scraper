from selenium.common.exceptions import NoSuchElementException      
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import logging



def wait_until(webdriver, selector:By, name:str): 
    try:
        wait = WebDriverWait(webdriver, 10)
        element = wait.until(EC.visibility_of_element_located((selector, name)))
        return element
    except:
        return None

def check_exists_by_xpath(webdriver, xpath):
    try:
        webdriver.find_element_by_xpath(xpath)
    except NoSuchElementException:
        return False
    return True


def check_exists_by_class(webdriver, classname):
    try:
        webdriver.find_element_by_class_name(classname)
    except NoSuchElementException:
        return False
    return True


'''
LinkedIn handles bad parameters. We don't need a parameter check yet.

'''
def search_params(search_term: str, filter_options: str = None):

    search_keyword = f"keywords={search_term.replace(' ', '%20')}"
    
    # possibilities
    # datePosted - past-24h
    #            - past-week
    #            - past-month

    search_filter = ''
    if filter_options is not None:
        for key, value in filter_options.items():
            search_filter += f"{key}=%22{value}%22&"
    

    search_parameters = f"?{search_filter}{search_keyword}"

    return search_parameters


def __create_logger():
    # Create a custom logger
    logger = logging.getLogger(f"{__name__}")
    logger.setLevel(logging.DEBUG)

    # Create handlers
    c_handler = logging.StreamHandler()
    f_handler = logging.FileHandler('logfile.txt')
    c_handler.setLevel(logging.INFO)
    f_handler.setLevel(logging.DEBUG)

    # Create formatters and add it to handlers
    c_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    c_handler.setFormatter(c_format)
    f_handler.setFormatter(f_format)

    # Add handlers to the logger
    logger.addHandler(c_handler)
    logger.addHandler(f_handler)

    return logger

logger = __create_logger()