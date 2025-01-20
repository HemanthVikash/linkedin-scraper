import unittest
from main import *


class TestLinkedInScraper(unittest.TestCase):

    def test_search_params(self):

        fo = {
            'datePosted': 'past-24h', 
            'datePosted': 'past-36h'
        }
        params = search_params('Haas Team', fo)

        assert(' ' not in params)
        assert(params[0] == '?')
    
    






if __name__ == "__main__":
    unittest.main()