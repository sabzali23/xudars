from django import forms

from .models import Child


class ChildForm(forms.ModelForm):
    class Meta:
        model = Child
        fields = ["name", "grade", "target_school"]
        widgets = {"target_school": forms.TextInput(attrs={"placeholder": "Название школы в Хороге"})}
