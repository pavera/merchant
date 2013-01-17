import requests
import datetime

from django.conf import settings
from django.template.loader import render_to_string

from billing import Gateway, GatewayNotConfigured
from billing.signals import *
from billing.utils.credit_card import InvalidCard, Visa,\
    MasterCard, Discover, AmericanExpress
from billing.utils.xml_parser import parseString, nodeToDic

API_VERSION = "XWeb3.3"
TRANS_TYPES = {
    'purchase': 'CreditSaleTransaction',
    'authorize': 'CreditAuthTranscation',
    'capture': 'CreditCaptureTransaction',
    'credit': 'CreditReturnTransaction',
    'void': 'CreditVoidTransaction',
    'store': 'AliasCreateTransaction',
    'unstore': 'AliasDeleteTransaction',
    'recurring': 'RecurringCreateTransaction',
}

class APTGateway(Gateway):
    test_url = 'https://test.t3secure.net/x-chargeweb.dll'
    prod_url = 'https://gw.t3secure.net/x-chargeweb.dll'

    supported_countries = ["US"]
    default_currency = "USD"

    supported_cardtypes = [Visa, MasterCard, AmericanExpress, Discover]
    homepage_url = "http://www.acceleratedpay.com/"
    display_name = "APT"

    def __init__(self, options=None, *args, **kwargs):
        merchant_settings = getattr(settings, "MERCHANT_SETTINGS")
        if not merchant_settings or not (merchant_settings.get("apt") or options):
            raise GatewayNotConfigured("The '%s' gateway is not correctly "
                                       "configured." % self.display_name)

        apt_settings = options or merchant_settings["apt"]
        self.login = apt_settings["MERCHANT_ID"]
        self.password = apt_settings["AUTH_KEY"]
        self.terminal_id = apt_settings['TERMINAL_ID']

    def _request(self, data, transaction_type):
        data['TransactionType'] = TRANS_TYPES[transaction_type]
        r = requests.get(self.service_url, params=data)
        status = "SUCCESS"
        if r.response_code != 1:
            status = "FAILURE"
            transaction_was_unsuccessful.send(sender=self,
                type=transaction_type,
                response=r)
        else:
            transaction_was_successful.send(sender=self,
                type=transaction_type,
                response=r)
        return {"status": status, "response": r}

    def _header_data(self):
        post = dict()

        post['SpecVersion'] = API_VERSION
        post['XWebID'] = self.login
        post['AuthKey'] = self.password
        post['TerminalID'] = self.terminal_id
        post['Industry'] = "ECOMMERCE"
        post['TrackCapabilities'] = "NONE"
        post['PinCapabilities'] = "FALSE"
        post['POSType'] = "ECR"
        return post

    @property
    def service_url(self):
        if self.test_mode:
            return self.test_url
        return self.prod_url


    def purchase(self, money, credit_card, options=None):
        """One go authorize and capture transaction"""
        data = self._header_data()
        data['CustomerPresent'] = "FALSE"
        data['CardPresent'] = "FALSE"
        data['Amount'] = money
        data['ECI'] = 7
        if options and options.get('alias', None):
            data['Alias'] = options.get('alias')
        else:
            data['AcctNum'] = credit_card.number
            data['ExpDate'] = credit_card.expire_date_mmyy

        if options:
            if options.get('cvv2', None):
                data['CardCode'] = options.get('cvv2')

        return self._request(data, 'purchase')

    def authorize(self, money, credit_card, options=None):
        """Authorization for a future capture transaction"""
        data = self._header_data()
        data['CustomerPresent'] = "FALSE"
        data['CardPresent'] = "FALSE"
        data['Amount'] = money
        data['ECI'] = 7
        if options and options.get('alias', None):
            data['Alias'] = options.get('alias')
        else:
            data['AcctNum'] = credit_card.number
            data['ExpDate'] = credit_card.expire_date_mmyy

        if options:
            if options.get('cvv2', None):
                data['CardCode'] = options.get('cvv2')

        return self._request(data, 'authorize')

    def capture(self, money, authorization, options=None):
        """Capture funds from a previously authorized transaction"""
        data = self._header_data()
        data['TransactionID'] = authorization

    def void(self, identification, options=None):
        """Null/Blank/Delete a previous transaction"""
        data = self._header_data()
        data['TransactionID'] = identification

    def credit(self, money, identification, options=None):
        """Refund a previously 'settled' transaction"""
        data = self._header_data()
        data['TransactionID'] = identification

    def recurring(self, money, credit_card, options=None):
        """Setup a recurring transaction"""
        data = self._header_data()

    def cancel_recurring(self, identification, options=None):
        data = self._header_data()
        data['RecurringPlanID'] = identification

    def store(self, credit_card, options=None):
        """Store the credit card and user profile information
        on the gateway for future use"""
        data = self._header_data()
        data['AcctNum'] = credit_card.number
        data['ExpDate'] = credit_card.expire_date_mmyy

        if options:
            if options.get('cvv2', None):
                data['CardCode'] = options.get('cvv2')

        return self._request(data, 'store')

    def unstore(self, identification, options=None):
        """Delete the previously stored credit card and user
        profile information on the gateway"""
        data = self._header_data()
        data['Alias'] = identification
        return self._request(data, 'unstore')