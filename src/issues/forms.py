from django import forms
from .models import Profile


class UploadFileForm(forms.Form):
    files = forms.FileField(label="Upload Attachment")


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio', 'avatar']
        widgets = {
            'bio': forms.Textarea(attrs={
                'rows': 6,
                'placeholder': 'Write a short bio about yourself...'
            }),
        }
