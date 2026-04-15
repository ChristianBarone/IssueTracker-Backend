from django import forms
from django.utils.text import slugify
from .models import Profile, Status, Priority, IssueType, Severity, Tag, DueDate


class ColorInput(forms.TextInput):
    input_type = 'color'


_COLOR_WIDGET  = ColorInput()
_NAME_WIDGET   = forms.TextInput(attrs={'autocomplete': 'off'})


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


class StatusForm(forms.ModelForm):
    class Meta:
        model = Status
        fields = ['name', 'color', 'is_default', 'is_closed']
        widgets = {'name': _NAME_WIDGET, 'color': _COLOR_WIDGET}

    def save(self, commit=True):
        obj = super().save(commit=False)
        base_slug = slugify(obj.name)
        slug = base_slug
        qs = Status.objects.filter(slug=slug)
        if obj.pk:
            qs = qs.exclude(pk=obj.pk)
        if qs.exists():
            slug = f"{base_slug}-{obj.pk or 'new'}"
        obj.slug = slug
        if commit:
            obj.save()
        return obj


class PriorityForm(forms.ModelForm):
    class Meta:
        model = Priority
        fields = ['name', 'color', 'is_default']
        widgets = {'name': _NAME_WIDGET, 'color': _COLOR_WIDGET}


class IssueTypeForm(forms.ModelForm):
    class Meta:
        model = IssueType
        fields = ['name', 'color', 'is_default']
        widgets = {'name': _NAME_WIDGET, 'color': _COLOR_WIDGET}


class SeverityForm(forms.ModelForm):
    class Meta:
        model = Severity
        fields = ['name', 'color', 'is_default']
        widgets = {'name': _NAME_WIDGET, 'color': _COLOR_WIDGET}


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ['name', 'color']
        widgets = {'name': _NAME_WIDGET, 'color': _COLOR_WIDGET}


class DueDateForm(forms.ModelForm):
    class Meta:
        model = DueDate
        fields = ['name', 'color', 'days_offset', 'before_or_after']
        widgets = {
            'name': _NAME_WIDGET,
            'color': _COLOR_WIDGET,
            'days_offset': forms.NumberInput(attrs={
                'min': '0', 'placeholder': 'Leave empty for "always applies"'
            }),
        }
