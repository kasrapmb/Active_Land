"""Server-to-server gateway adapter. Never trusts callback success flags."""
import json
from urllib.request import Request,urlopen
from django.conf import settings
from django.utils.module_loading import import_string

class GatewayUnavailable(Exception): pass

class Zarinpal:
    api = 'https://payment.zarinpal.com/pg/v4/payment/'
    def _post(self,action,payload):
        if not settings.PAYMENT_MERCHANT_ID: raise GatewayUnavailable()
        payload['merchant_id']=settings.PAYMENT_MERCHANT_ID
        try:
            response=urlopen(Request(self.api+action+'.json',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'}),timeout=15)
            with response:
                return json.load(response)['data']
        except Exception as exc:
            raise GatewayUnavailable('Gateway request could not be completed') from None
    def request(self,booking,callback_url):
        data=self._post('request',{'amount':booking.amount*10,'description':'ثبت‌نام کلاس اکتیولند','callback_url':callback_url})
        if data.get('code')!=100 or not data.get('authority'): raise GatewayUnavailable()
        return str(data['authority'])
    def url(self,authority):
        from urllib.parse import quote
        return 'https://payment.zarinpal.com/pg/StartPay/'+quote(authority,safe='')
    def verify(self,booking):
        data=self._post('verify',{'amount':booking.amount*10,'authority':booking.gateway_authority})
        if data.get('code') in (100,101) and data.get('ref_id'):
            return str(data['ref_id'])
        # Unknown provider outcomes remain pending; they must not free a charged seat.
        raise GatewayUnavailable('Payment is not verified')

def backend():
    if not settings.PAYMENT_BACKEND: raise GatewayUnavailable('Payment is not configured')
    return import_string(settings.PAYMENT_BACKEND)()
