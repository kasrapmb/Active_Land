import jdatetime
from django import forms
from django.utils import timezone
from .authentication import normalize_phone
from .models import Child, ParentProfile

class PhoneForm(forms.Form):
    phone = forms.CharField(label='شماره همراه',max_length=16,widget=forms.TextInput(attrs={'inputmode':'tel','autocomplete':'tel','placeholder':'۰۹۱۲۳۴۵۶۷۸۹'}))
    def clean_phone(self):
        return normalize_phone(self.cleaned_data['phone'])

class CodeForm(forms.Form):
    code = forms.CharField(label='کد پیامکی',min_length=6,max_length=6,widget=forms.TextInput(attrs={'inputmode':'numeric','autocomplete':'one-time-code'}))

class ProfileForm(forms.ModelForm):
    class Meta:
        model = ParentProfile
        fields = ['full_name','emergency_phone']
    def clean_full_name(self):
        value = self.cleaned_data['full_name'].strip()
        if not value:
            raise forms.ValidationError('نام والد الزامی است.')
        return value
    def clean_emergency_phone(self):
        return normalize_phone(self.cleaned_data['emergency_phone'])

class ChildForm(forms.ModelForm):
    birth_jalali = forms.CharField(label='تاریخ تولد شمسی',help_text='مثال: ۱۴۰۳/۰۸/۲۴',widget=forms.TextInput(attrs={'placeholder':'۱۴۰۳/۰۸/۲۴','inputmode':'numeric'}))
    class Meta:
        model = Child
        fields = ['full_name','birth_jalali','gender','attended_before','notes']
        widgets = {'notes':forms.Textarea(attrs={'rows':3})}
    def clean_birth_jalali(self):
        try:
            value = self.cleaned_data['birth_jalali'].translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹','0123456789'))
            year,month,day = map(int,value.split('/'))
            birth = jdatetime.date(year,month,day).togregorian()
            if birth > timezone.localdate() or year < 1300:
                raise ValueError()
            return birth
        except (ValueError,TypeError):
            raise forms.ValidationError('تاریخ تولد شمسی معتبر وارد کنید.')
    def save(self,commit=True):
        self.instance.birth_date = self.cleaned_data['birth_jalali']
        return super().save(commit)
