from django.conf import settings
from django.db import models
from django.db.models import Avg


GENDER_CHOICES = [
    ('male', 'Male'),
    ('female', 'Female'),
    ('other', 'Other'),
    ('prefer_not_to_say', 'Prefer not to say'),
]

RIDE_GENDER_PREFERENCE_CHOICES = [
    ('any', 'Any gender'),
    ('male_only', 'Male only'),
    ('female_only', 'Female only'),
]

TRIP_STATUS_CHOICES = [
    ('not_started', 'Not started'),
    ('in_progress', 'In progress'),
    ('completed', 'Completed'),
]


class Profile(models.Model):
    """Extra info attached to every user account, on top of Django's built-in User."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)

    # --- Identity verification (PROTOTYPE ONLY) ---
    # This does NOT perform a real NIN or face-verification check. It stores
    # whatever document the user uploads and marks them "verified" once they
    # submit one. Wiring this to a real ID-verification provider (e.g. an
    # NIN verification API) is a follow-up phase, not part of this build.
    id_document = models.ImageField(upload_to='id_documents/', blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    is_pro = models.BooleanField(default=False, help_text="Unlocks unlimited ride joins")

    def __str__(self):
        return self.user.username

    @property
    def trust_score(self):
        """Average of all ratings this user has received, or None if no ratings yet."""
        result = Rating.objects.filter(ratee=self.user).aggregate(avg=Avg('score'))
        return result['avg']


class Trip(models.Model):
    """A ride someone is planning within the city and is open to sharing."""

    traveler = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posted_trips'
    )
    pickup_area = models.CharField(max_length=120, help_text="e.g. 'Berger, Lagos'")
    dropoff_area = models.CharField(max_length=120, help_text="e.g. 'Victoria Island, Lagos'")
    departure_time = models.DateTimeField()
    max_companions = models.PositiveIntegerField(default=1)
    cost_estimate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    gender_preference = models.CharField(
        max_length=20, choices=RIDE_GENDER_PREFERENCE_CHOICES, default='any'
    )
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=TRIP_STATUS_CHOICES, default='not_started')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['departure_time']

    def __str__(self):
        return f"{self.pickup_area} -> {self.dropoff_area} on {self.departure_time:%d %b, %H:%M}"

    @property
    def spots_filled(self):
        return self.join_requests.count()

    @property
    def is_full(self):
        return self.spots_filled >= self.max_companions

    @property
    def seat_states(self):
        """
        One entry per seat, True if taken. Lets the template draw seat pips
        without needing a range/loop tag Django templates don't have.
        """
        filled = self.spots_filled
        return [i < filled for i in range(self.max_companions)]

    def participants(self):
        """Everyone involved in this trip: the poster plus everyone who joined."""
        from django.contrib.auth import get_user_model
        ids = [self.traveler_id] + list(self.join_requests.values_list('requester_id', flat=True))
        return get_user_model().objects.filter(id__in=ids)


class JoinRequest(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='join_requests')
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='join_requests')
    message = models.CharField(max_length=280, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('trip', 'requester')

    def __str__(self):
        return f"{self.requester} wants to join {self.trip}"


class Message(models.Model):
    """A single in-app chat message tied to a trip (visible to everyone on that trip)."""

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.CharField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender}: {self.body[:30]}"


class Rating(models.Model):
    """A rating one participant leaves for another after a completed trip."""

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='ratings')
    rater = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ratings_given')
    ratee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ratings_received')
    score = models.PositiveSmallIntegerField(help_text="1 to 5")
    comment = models.CharField(max_length=280, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('trip', 'rater', 'ratee')

    def __str__(self):
        return f"{self.rater} rated {self.ratee}: {self.score}/5"
