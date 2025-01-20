[![Last commit](https://img.shields.io/github/last-commit/HemanthVikash/linkedin-scraper)](https://github.com/parameshv/linkedin-scraper/commits/master)
[![Python Version](https://img.shields.io/badge/python-3.12.2-blue.svg)](https://github.com/HemanthVikash/linkedin-scraper/blob/master/environment.yml)

# LinkedIn Post Scraper     
Simple post scraper for LinkedIn. 
Stores scraped posts in a csv file

## Setup

After installing the virtual environment through the provided environment.yml file, follow the steps to set up and run your project

### Changing the Settings

Search parameters can be changed in the code/search_options.yml file. Potential options are provided in the file as comments

Other settings (where to save, filename, etc.) can be changed in the **settings.yml file**. 

HIGHLY RECOMMEND CHANGING settings.yml before running the application. 


### Running the project (Terminal Mac)

```
git clone https://github.com/HemanthVikash/linkedin-scraper.git
cd scraper
conda env create --file=environment.yml
conda activate scraper
python code/main.py
```




## Functionality


### Login
- Credentials read from file/input

### Search
- Navigate to search page. 
- Enter search term with filter options

### Scrape

Data scraped by the scraper would include

**LinkedIn profile** \
Name, Link to Profile, Position at company, 

Inside link: \
Hiring for roles (bool), About section (not that useful), Company name

**LinkedIn post** \
Post Link, Post Type, Post text, comments count, likes count, other popularity metrics


### Scroll
Infinite scroll functionality


## Contribution

### Updating environment
`conda env export --no-builds | grep -v "^prefix: " > environment.yml`

