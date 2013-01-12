import urllib
import urllib2
import datetime

from django.conf import settings
from django.template.loader import render_to_string

from billing import Gateway, GatewayNotConfigured
from billing.signals import *
from billing.utils.credit_card import InvalidCard, Visa,\
    MasterCard, Discover, AmericanExpress
from billing.utils.xml_parser import parseString, nodeToDic

class APTGateway(Gateway):
    test_url = 'https://test.t3secure.net/x-chargeweb.dll'
    prod_url = 'https://gw.t3secure.net/x-chargeweb.dll'

    def purchase(self, money, credit_card, options=None):
        """One go authorize and capture transaction"""
        raise NotImplementedError

    def authorize(self, money, credit_card, options=None):
        """Authorization for a future capture transaction"""
        raise NotImplementedError

    def capture(self, money, authorization, options=None):
        """Capture funds from a previously authorized transaction"""
        raise NotImplementedError

    def void(self, identification, options=None):
        """Null/Blank/Delete a previous transaction"""
        raise NotImplementedError

    def credit(self, money, identification, options=None):
        """Refund a previously 'settled' transaction"""
        raise NotImplementedError

    def recurring(self, money, creditcard, options=None):
        """Setup a recurring transaction"""
        raise NotImplementedError

    def store(self, creditcard, options=None):
        """Store the credit card and user profile information
        on the gateway for future use"""
        raise NotImplementedError

    def unstore(self, identification, options=None):
        """Delete the previously stored credit card and user
        profile information on the gateway"""
        raise NotImplementedError