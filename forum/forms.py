from django import forms
from .models import Thread, Post


class ThreadForm(forms.ModelForm):
    """Form to create a new thread."""
    class Meta:
        model = Thread
        fields = ['title', 'category', 'content', 'tags']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'What\'s your question or topic?',
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'Describe your question in detail. You can use Markdown for formatting.',
            }),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., python, neural-networks, pytorch (comma separated)',
            }),
        }


class PostForm(forms.ModelForm):
    """Form to create a reply/post."""
    class Meta:
        model = Post
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Write your reply...',
            }),
        }
