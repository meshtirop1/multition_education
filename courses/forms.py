from django import forms
from .models import Course, Module, Exercise, ExerciseSubmission


class CourseForm(forms.ModelForm):
    """Admin course creation/edit form."""
    class Meta:
        model = Course
        fields = ['title', 'description', 'short_description', 'category', 'level',
                  'thumbnail', 'mentor', 'duration_hours', 'is_published', 'is_featured', 'max_students',
                  'is_free', 'price', 'price_kes']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'short_description': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'level': forms.Select(attrs={'class': 'form-select'}),
            'thumbnail': forms.FileInput(attrs={'class': 'form-control'}),
            'mentor': forms.Select(attrs={'class': 'form-select'}),
            'duration_hours': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_students': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_free': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'isFreeToggle'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'id': 'priceField'}),
            'price_kes': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0', 'placeholder': 'Auto-converts from USD if left at 0'}),
        }


class ModuleForm(forms.ModelForm):
    """Module creation/edit form."""
    class Meta:
        model = Module
        fields = ['title', 'description', 'content', 'order', 'video_url', 'resources']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 10}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
            'video_url': forms.URLInput(attrs={'class': 'form-control'}),
            'resources': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ExerciseForm(forms.ModelForm):
    """Exercise creation/edit form."""
    class Meta:
        model = Exercise
        fields = ['title', 'description', 'exercise_type', 'points', 'order',
                  'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'exercise_type': forms.Select(attrs={'class': 'form-select'}),
            'points': forms.NumberInput(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
            'option_a': forms.TextInput(attrs={'class': 'form-control'}),
            'option_b': forms.TextInput(attrs={'class': 'form-control'}),
            'option_c': forms.TextInput(attrs={'class': 'form-control'}),
            'option_d': forms.TextInput(attrs={'class': 'form-control'}),
            'correct_answer': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 1}),
        }


class ExerciseSubmissionForm(forms.ModelForm):
    """Student exercise submission form."""
    selected_option = forms.CharField(max_length=1, required=False, widget=forms.HiddenInput())

    class Meta:
        model = ExerciseSubmission
        fields = ['answer', 'file_upload']
        widgets = {
            'answer': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Type your answer here...'}),
            'file_upload': forms.FileInput(attrs={'class': 'form-control'}),
        }


class GradeSubmissionForm(forms.Form):
    """Mentor grading form."""
    score = forms.IntegerField(min_value=0, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    feedback = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    is_completed = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
