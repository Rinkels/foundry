from django import forms

class WebsiteDownloadForm(forms.Form):
    url = forms.URLField(label="Website URL", max_length=200, required=True)