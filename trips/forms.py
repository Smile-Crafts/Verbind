from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model

from .models import Profile, Trip, Message, Rating

User = get_user_model()


class StyledFormMixin:
    """
    Drops the colon Django adds after every label and gives each widget a
    placeholder where a hint helps. Keeps the styling in the stylesheet
    rather than scattered through the templates.
    """
    placeholders = {}

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('label_suffix', '')
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in self.placeholders:
                field.widget.attrs.setdefault('placeholder', self.placeholders[name])


class SignUpForm(StyledFormMixin, UserCreationForm):
    email = forms.EmailField(required=True, help_text="We send ride notifications here.")

    placeholders = {
        'username': 'e.g. smile_a',
        'email': 'you@example.com',
    }

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class LoginForm(StyledFormMixin, AuthenticationForm):
    placeholders = {'username': 'Your username'}


class ProfileForm(StyledFormMixin, forms.ModelForm):
    placeholders = {'phone_number': '0803 000 0000'}

    class Meta:
        model = Profile
        fields = ['picture', 'gender', 'phone_number']
        labels = {
            'picture': 'Profile photo',
            'gender': 'Gender',
            'phone_number': 'Phone number',
        }
        help_texts = {
            'picture': 'A clear face photo. Riders see this before they join.',
            'phone_number': 'Only shared with people on the same ride as you.',
        }


class IDVerificationForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['id_document']
        labels = {'id_document': 'Photo of your ID'}
        help_texts = {'id_document': 'NIN slip, driver\'s licence, voter\'s card or student ID.'}


class TripForm(StyledFormMixin, forms.ModelForm):
    placeholders = {
        'pickup_area': 'e.g. Berger, Lagos',
        'dropoff_area': 'e.g. Victoria Island, Lagos',
        'cost_estimate': 'e.g. 4500',
        'notes': 'Anything worth knowing — landmark to meet at, luggage, timing flexibility.',
    }

    class Meta:
        model = Trip
        fields = [
            'pickup_area', 'dropoff_area', 'departure_time',
            'max_companions', 'cost_estimate', 'gender_preference', 'notes',
        ]
        labels = {
            'pickup_area': 'Setting off from',
            'dropoff_area': 'Heading to',
            'departure_time': 'Leaving at',
            'max_companions': 'Seats you can share',
            'cost_estimate': 'Estimated total fare (₦)',
            'gender_preference': 'Who can join',
            'notes': 'Notes for riders',
        }
        help_texts = {
            'pickup_area': '',
            'dropoff_area': '',
            'cost_estimate': 'Roughly what the whole ride costs. Riders split it between them.',
        }
        widgets = {
            'departure_time': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'
            ),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['departure_time'].input_formats = ['%Y-%m-%dT%H:%M']


class TripFilterForm(StyledFormMixin, forms.Form):
    """Not tied to a model, just powers the search bar on the ride list."""
    dropoff_area = forms.CharField(required=False, label='Where are you heading?')
    gender_preference = forms.ChoiceField(
        required=False,
        label='Who can join',
        choices=[('', 'Anyone')] + Trip._meta.get_field('gender_preference').choices,
    )

    placeholders = {'dropoff_area': 'e.g. Ikeja'}


class MessageForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Message
        fields = ['body']
        labels = {'body': ''}
        widgets = {'body': forms.TextInput(attrs={'placeholder': 'Write a message…'})}


class RatingForm(StyledFormMixin, forms.ModelForm):
    placeholders = {'comment': 'Optional note'}

    class Meta:
        model = Rating
        fields = ['score', 'comment']
        labels = {'score': '', 'comment': ''}
        widgets = {
            'score': forms.Select(
                choices=[(i, f"{i} star{'s' if i != 1 else ''}") for i in range(1, 6)]
            )
        }
