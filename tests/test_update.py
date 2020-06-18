#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import logging
import sys
sys.path.append('../')
from backend.update import Update
from cleep.exception import InvalidParameter, MissingParameter, CommandError, Unauthorized
from cleep.libs.tests import session

class TestUpdate(unittest.TestCase):

    def setUp(self):
        self.session = session.Session(logging.CRITICAL)
        #next line instanciates your module, overwriting all useful stuff to isolate your module for tests
        self.module = self.session.setup(Update)

    def tearDown(self):
        #clean session
        self.session.clean()

    #write your tests here defining functions starting with test_
    #see official documentation https://docs.python.org/2.7/library/unittest.html
    #def test_my_test(self):
    #   ...

#do not remove code below, otherwise test won't run
if __name__ == '__main__':
    unittest.main()
    
