from django import forms
from portal.models import Child
from catalog.models import Session

class RegistrationForm(forms.Form):
    child = forms.ModelChoiceField(label='انتخاب فرزند',queryset=Child.objects.none())
    accept_rules = forms.BooleanField(label='قوانین سن، شهریه، غیبت و اعتبار یک‌ماهه را خوانده‌ام و می‌پذیرم.')
    def __init__(self,*args,user,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['child'].queryset = Child.objects.filter(parent=user)

class OfflinePaymentForm(forms.Form):
    reference = forms.CharField(label='شناسه یکتای رسید پرداخت تأییدشده',max_length=120)

class TransferForm(forms.Form):
    target = forms.ModelChoiceField(label='سانس مقصد',queryset=Session.objects.filter(active=True))
    note = forms.CharField(label='توضیح هماهنگی تسویه شهریه با پشتیبانی',widget=forms.Textarea,max_length=1000)

class ManualRegistrationForm(forms.Form):
    child = forms.ModelChoiceField(label='کودک',queryset=Child.objects.select_related('parent').all())
    session = forms.ModelChoiceField(label='سانس',queryset=Session.objects.filter(active=True))
    reference = forms.CharField(label='شناسه رسید پرداخت کامل تأییدشده',max_length=120)
    age_override_reason = forms.CharField(label='دلیل استثنای سن (فقط مدیر سایت)',max_length=1000,required=False,widget=forms.Textarea)
