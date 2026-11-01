from django import forms
from portal.models import Child

class RegistrationForm(forms.Form):
    child = forms.ModelChoiceField(label='انتخاب فرزند',queryset=Child.objects.none())
    accept_rules = forms.BooleanField(label='قوانین سن، شهریه، غیبت و اعتبار یک‌ماهه را خوانده‌ام و می‌پذیرم.')
    def __init__(self,*args,user,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['child'].queryset = Child.objects.filter(parent=user)

class OfflinePaymentForm(forms.Form):
    reference = forms.CharField(label='شناسه یکتای رسید پرداخت تأییدشده',max_length=120)
