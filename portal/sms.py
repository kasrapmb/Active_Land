"""Optional Kavenegar adapter; activation requires a purchased, configured account."""
import json
from urllib.parse import urlencode,quote
from urllib.request import Request,urlopen
from django.conf import settings
from .authentication import DeliveryUnavailable

def _request(method,payload):
    key=settings.SMS_API_KEY
    if not key: raise DeliveryUnavailable()
    url='https://api.kavenegar.com/v1/'+quote(key,safe='')+'/'+method+'.json'
    try:
        with urlopen(Request(url,data=urlencode(payload).encode()),timeout=15) as response:
            result=json.load(response)
        if result.get('return',{}).get('status')!=200:
            raise DeliveryUnavailable()
    except Exception:
        # Never propagate the provider URL, API key or response body into logs/UI.
        raise DeliveryUnavailable('SMS delivery was not accepted') from None

def send_otp(phone,code):
    if not settings.SMS_OTP_TEMPLATE: raise DeliveryUnavailable()
    _request('verify/lookup',{'receptor':phone,'token':code,'template':settings.SMS_OTP_TEMPLATE})

def send_message(phone,message):
    if not settings.SMS_SENDER: raise DeliveryUnavailable()
    _request('sms/send',{'receptor':phone,'sender':settings.SMS_SENDER,'message':message})
