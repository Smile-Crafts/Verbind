import json
import secrets
import urllib.parse
import urllib.request
from datetime import date
from functools import wraps

from django import forms as django_forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.db.models import Q, Max
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView

from .forms import (
    SignUpForm, LoginForm, NameForm, ProfileForm, IDVerificationForm, TripForm,
    TripFilterForm, MessageForm, RatingForm, RideRequestForm,
)
from .models import Trip, JoinRequest, Message, Rating, Profile


def verified_required(view_func):
    """
    Blocks posting or joining a ride unless both email and ID verification
    are done. Staff/superuser accounts are exempt — this protects against a
    bug in this gate locking the app owner out of the admin panel.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_staff or request.user.profile.fully_verified:
            return view_func(request, *args, **kwargs)
        messages.error(request, "Verify your email and identity before posting or joining a ride.")
        return redirect('verification-gate')
    return wrapper


# ---------- Accounts ----------

class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = 'registration/signup.html'
    success_url = reverse_lazy('verification-gate')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


class VerbindLoginView(LoginView):
    """Same as Django's built-in login, but unverified accounts land on the
    verification gate instead of the ride list, and staff always go to the
    ride list (skipping the gate) so admin access never depends on it."""
    form_class = LoginForm

    def get_success_url(self):
        user = self.request.user
        if user.is_staff or user.profile.fully_verified:
            return reverse_lazy('trip-list')
        return reverse_lazy('verification-gate')


@login_required
def verification_gate(request):
    """Landing page for anyone who isn't fully verified yet — explains what's
    missing and links straight to whichever step isn't done."""
    if request.user.is_staff or request.user.profile.fully_verified:
        return redirect('trip-list')
    return render(request, 'trips/verification_gate.html')


@login_required
def resend_verification_email(request):
    profile = request.user.profile
    if not profile.email_verification_token:
        profile.email_verification_token = secrets.token_urlsafe(24)
        profile.save(update_fields=['email_verification_token'])
    if request.user.email:
        from django.urls import reverse
        verify_url = f"{settings.SITE_URL}{reverse('verify-email', args=[profile.email_verification_token])}"
        send_mail(
            subject='Verify your Verbind email',
            message=f"Open this link to verify your email:\n\n{verify_url}",
            from_email=None,
            recipient_list=[request.user.email],
            fail_silently=True,
        )
        messages.success(request, f"Verification email sent to {request.user.email}.")
    else:
        messages.error(request, "Your account has no email on file — add one from Profile first.")
    return redirect('verification-gate')


def verify_email(request, token):
    """No @login_required: the link is clicked from an email client, which
    may not carry the session cookie, so we look the person up by token
    instead of relying on them already being logged in."""
    from .models import Profile
    profile = get_object_or_404(Profile, email_verification_token=token)
    if not profile.email_verified:
        profile.email_verified = True
        profile.save(update_fields=['email_verified'])
        messages.success(request, "Email verified.")
    else:
        messages.success(request, "Already verified — you're good.")
    if request.user.is_authenticated and request.user == profile.user:
        return redirect('verification-gate')
    return redirect('login')


@login_required
def edit_profile(request):
    profile = request.user.profile
    if request.method == 'POST':
        name_form = NameForm(request.POST, instance=request.user)
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        # Both forms submit together — save only if both are valid, so a
        # mistake in one field doesn't half-save the other.
        if name_form.is_valid() and form.is_valid():
            name_form.save()
            form.save()
            messages.success(request, "Profile updated.")
            return redirect('trip-list')
    else:
        name_form = NameForm(instance=request.user)
        form = ProfileForm(instance=profile)
    return render(request, 'trips/edit_profile.html', {'form': form, 'name_form': name_form})


@login_required
def verify_identity(request):
    """
    PROTOTYPE ONLY: accepts an uploaded document and marks the user verified.
    No real identity check happens here yet, this is a placeholder for a
    future integration with a real ID-verification provider.
    """
    profile = request.user.profile
    if request.method == 'POST':
        form = IDVerificationForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.is_verified = True  # mocked: real check happens in a later phase
            profile.save()
            messages.success(request, "Document received. Your account is now marked verified (prototype check).")
            if profile.fully_verified:
                return redirect('trip-list')
            return redirect('verification-gate')
    else:
        form = IDVerificationForm(instance=profile)
    return render(request, 'trips/verify_identity.html', {'form': form})


# ---------- Passenger-first ride request ----------

@login_required
def request_ride(request):
    """Passenger creates a real ride request that partners can browse."""

    if request.method == 'POST':
        form = RideRequestForm(request.POST)

        if form.is_valid():
            data = form.cleaned_data

            # Create a real Trip in the database.
            # This makes the request visible to other Verbind users.
            trip = Trip.objects.create(
                traveler=request.user,
                pickup_area=data['pickup_area'],
                pickup_lat=data.get('pickup_lat'),
                pickup_lng=data.get('pickup_lng'),
                dropoff_area=data['dropoff_area'],
                dropoff_lat=data.get('dropoff_lat'),
                dropoff_lng=data.get('dropoff_lng'),
                departure_time=data['departure_time'],
                max_companions=data['passengers'],
                status='not_started',
            )

            # Keep the request in session so the passenger
            # can return to the matching/waiting page.
            request.session['ride_request'] = {
                'trip_id': trip.id,
                'pickup_area': trip.pickup_area,
                'dropoff_area': trip.dropoff_area,
                'departure_time': trip.departure_time.isoformat(),
                'passengers': trip.max_companions,
            }

            messages.success(
                request,
                "Your ride request has been posted. We're waiting for a partner to join."
            )

            return redirect('ride-matching')

    else:
        form = RideRequestForm(initial={'when': 'now'})

    return render(
        request,
        'trips/request_ride.html',
        {'form': form}
    )


@login_required
def ride_matching(request):
    """
    Passenger waiting screen.

    The request is now a real Trip in the database.
    Partners can discover and join it instead of
    Verbind immediately showing a fake driver.
    """

    ride_request = request.session.get('ride_request')

    if not ride_request:
        return redirect('request-ride')

    trip_id = ride_request.get('trip_id')

    if not trip_id:
        return redirect('request-ride')

    trip = get_object_or_404(
        Trip,
        pk=trip_id,
        traveler=request.user
    )

    join_requests = trip.join_requests.select_related(
        'requester'
    ).all()

    return render(
        request,
        'trips/ride_matching.html',
        {
            'trip': trip,
            'ride_request': ride_request,
            'join_requests': join_requests,
            'partner_count': join_requests.count(),
        }
    )

# ---------- Trips ----------

class TripListView(ListView):
    model = Trip
    template_name = 'trips/trip_list.html'
    context_object_name = 'trips'

    def get_queryset(self):
        qs = super().get_queryset()
        dropoff = self.request.GET.get('dropoff_area')
        gender_pref = self.request.GET.get('gender_preference')
        if dropoff:
            qs = qs.filter(dropoff_area__icontains=dropoff)
        if gender_pref:
            qs = qs.filter(gender_preference=gender_pref)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = TripFilterForm(self.request.GET or None)
        return context


class TripCreateView(LoginRequiredMixin, CreateView):
    model = Trip
    form_class = TripForm
    template_name = 'trips/trip_form.html'
    success_url = reverse_lazy('trip-list')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_staff and not request.user.profile.fully_verified:
            messages.error(request, "Verify your email and identity before posting a ride.")
            return redirect('verification-gate')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.traveler = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, "Ride posted.")
        return response


class TripUpdateView(LoginRequiredMixin, UpdateView):
    """Editing a ride is restricted to the person who posted it — get_queryset
    below is what enforces that: anyone else gets a 404, not a peek."""
    model = Trip
    form_class = TripForm
    template_name = 'trips/trip_form.html'
    success_url = reverse_lazy('my-trips')

    def get_queryset(self):
        return Trip.objects.filter(traveler=self.request.user)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Ride updated.")
        return response


@login_required
def trip_delete(request, pk):
    """POST-only, and only the trip's own poster can delete it."""
    trip = get_object_or_404(Trip, pk=pk, traveler=request.user)
    if request.method == 'POST':
        trip.delete()
        messages.success(request, "Ride deleted.")
    return redirect('my-trips')


@login_required
def my_trips(request):
    trips = Trip.objects.filter(traveler=request.user)
    return render(request, 'trips/my_trips.html', {'trips': trips})


def trip_detail(request, pk):
    """
    Works logged out too, deliberately: anonymous visitors can see that
    real rides are posted (builds trust before signup), but never see who
    posted them, and get a "Join ride" prompt that sends them to log in
    rather than the full chat/status view logged-in riders get.
    """
    trip = get_object_or_404(Trip, pk=pk)

    if not request.user.is_authenticated:
        return render(request, 'trips/trip_detail.html', {
            'trip': trip, 'is_participant': False, 'anonymous': True,
        })

    is_participant = (
        trip.traveler == request.user
        or trip.join_requests.filter(requester=request.user).exists()
    )

    # Everyone else sharing this ride, so the participant can pick who to
    # message — chat is a private thread per pair, not one shared room.
    companions = [u for u in trip.participants() if u != request.user] if is_participant else []

    rating_form = RatingForm()
    already_rated_ids = list(
        Rating.objects.filter(trip=trip, rater=request.user).values_list('ratee_id', flat=True)
    )
    other_participants = [u for u in trip.participants() if u != request.user and u.id not in already_rated_ids]
    needs_rating = trip.status == 'completed' and bool(other_participants)

    return render(request, 'trips/trip_detail.html', {
        'trip': trip,
        'is_participant': is_participant,
        'anonymous': False,
        'companions': companions,
        'rating_form': rating_form,
        'other_participants': other_participants,
        'needs_rating': needs_rating,
        'is_own_join': trip.traveler != request.user and trip.join_requests.filter(requester=request.user).exists(),
    })


@login_required
def trip_chat(request, pk, user_id):
    """
    A private 1-on-1 thread between the current user and one other rider on
    this specific trip. Messages sent before threads existed (recipient is
    null) only show up here if this trip only ever had two participants —
    otherwise there's no way to know which pair an old group message
    belonged to, so it's left out rather than guessed at.
    """
    trip = get_object_or_404(Trip, pk=pk)
    is_participant = (
        trip.traveler == request.user or trip.join_requests.filter(requester=request.user).exists()
    )
    if not is_participant:
        messages.error(request, "Join this ride to message riders on it.")
        return redirect('trip-detail', pk=pk)

    other = get_object_or_404(trip.participants(), pk=user_id)
    if other == request.user:
        return redirect('trip-detail', pk=pk)

    if request.method == 'POST':
        msg_form = MessageForm(request.POST)
        if msg_form.is_valid():
            Message.objects.create(
                trip=trip, sender=request.user, recipient=other,
                body=msg_form.cleaned_data['body'],
            )
            return redirect('trip-chat', pk=pk, user_id=user_id)
    else:
        msg_form = MessageForm()

    thread = Q(sender=request.user, recipient=other) | Q(sender=other, recipient=request.user)
    if trip.participants().count() == 2:
        thread |= Q(recipient__isnull=True)  # legacy group messages, only unambiguous for a 2-person trip
    chat_messages = trip.messages.filter(thread).select_related('sender')

    # Opening the thread is what marks their messages as read — no
    # separate "mark as read" click needed.
    trip.messages.filter(trip=trip, sender=other, recipient=request.user, read=False).update(read=True)

    return render(request, 'trips/trip_chat.html', {
        'trip': trip,
        'other': other,
        'chat_messages': chat_messages,
        'msg_form': msg_form,
    })


@login_required
def set_trip_status(request, pk, new_status):
    """
    Lets a participant tell the app the ride has started / finished.
    This is what stands in for real GPS tracking in this prototype: it's
    manual status reporting, not live location monitoring.
    """
    trip = get_object_or_404(Trip, pk=pk)
    is_participant = (
        trip.traveler == request.user or trip.join_requests.filter(requester=request.user).exists()
    )
    if not is_participant:
        messages.error(request, "Only trip participants can update the ride status.")
    elif new_status not in dict(Trip._meta.get_field('status').choices):
        messages.error(request, "Unknown status.")
    else:
        trip.status = new_status
        trip.save()
        messages.success(request, f"Ride marked as {trip.get_status_display()}.")
    return redirect('trip-detail', pk=pk)


@login_required
def rate_participant(request, pk, user_id):
    trip = get_object_or_404(Trip, pk=pk)
    ratee = get_object_or_404(trip.participants(), pk=user_id)
    if request.method == 'POST':
        form = RatingForm(request.POST)
        if form.is_valid():
            Rating.objects.update_or_create(
                trip=trip, rater=request.user, ratee=ratee,
                defaults={'score': form.cleaned_data['score'], 'comment': form.cleaned_data['comment']},
            )
            messages.success(request, f"Rated {ratee.get_full_name() or ratee.username}.")
    return redirect('trip-detail', pk=pk)


@login_required
@verified_required
def request_to_join(request, pk):
    trip = get_object_or_404(Trip, pk=pk)

    if trip.traveler == request.user:
        messages.error(request, "You can't join your own ride.")
        return redirect('trip-list')

    if trip.is_full:
        messages.error(request, "This ride is already full.")
        return redirect('trip-list')

    profile = request.user.profile
    if not profile.is_pro:
        joins_this_month = JoinRequest.objects.filter(
            requester=request.user,
            created_at__year=date.today().year,
            created_at__month=date.today().month,
        ).count()
        if joins_this_month >= settings.FREE_JOINS_PER_MONTH:
            messages.error(
                request,
                f"You've used your {settings.FREE_JOINS_PER_MONTH} free rides this month. "
                "Upgrade to Pro for unlimited rides."
            )
            return redirect('trip-list')

    JoinRequest.objects.get_or_create(trip=trip, requester=request.user)
    messages.success(request, f"Request sent to join the ride to {trip.dropoff_area}.")

    if trip.traveler.email:
        requester_name = request.user.get_full_name() or request.user.username
        send_mail(
            subject='Someone wants to share your ride',
            message=(
                f"Hi {trip.traveler.get_full_name() or trip.traveler.username},\n\n"
                f"{requester_name} wants to join your ride to {trip.dropoff_area} "
                f"on {trip.departure_time:%d %b, %H:%M}. Open Verbind to chat with them."
            ),
            from_email=None,
            recipient_list=[trip.traveler.email],
            fail_silently=True,
        )

    return redirect('trip-list')


@login_required
def leave_trip(request, pk):
    """Lets someone who joined by mistake back out — deletes their own
    JoinRequest only, never anyone else's, and never the trip itself."""
    trip = get_object_or_404(Trip, pk=pk)
    if request.method == 'POST':
        deleted, _ = JoinRequest.objects.filter(trip=trip, requester=request.user).delete()
        if deleted:
            messages.success(request, "You've left this ride.")
        else:
            messages.error(request, "You hadn't joined this ride.")
    return redirect('trip-list')


# ---------- Small JSON endpoints (username check, address search) ----------

def check_username(request):
    """Called from the signup form as someone types, so they find out a
    username is taken before submitting the whole form, not after."""
    username = request.GET.get('username', '').strip()
    if not username:
        return JsonResponse({'available': None})
    taken = Profile._meta.get_field('user').related_model.objects.filter(
        username__iexact=username
    ).exists()
    return JsonResponse({'available': not taken})


def location_search(request):
    """
    Proxies address search to OpenStreetMap's free Nominatim service.
    Done server-side (not called directly from the browser) so we can set a
    proper identifying User-Agent, which Nominatim's usage policy requires,
    and so the API key/quota story never has to involve the frontend.
    """
    query = request.GET.get('q', '').strip()
    if len(query) < 3:
        return JsonResponse({'results': []})

    params = urllib.parse.urlencode({
        'q': query,
        'format': 'jsonv2',
        'countrycodes': 'ng',
        'limit': 5,
        'addressdetails': 0,
    })
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Verbind-Lagos-RideShare/1.0 (prototype; contact via app)',
    })
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode())
    except Exception:
        # Nominatim being slow/down shouldn't break posting a ride — the
        # text field still works as a normal free-typed input either way.
        return JsonResponse({'results': []})

    results = [
        {'label': item.get('display_name', ''), 'lat': item.get('lat'), 'lng': item.get('lon')}
        for item in data
    ]
    return JsonResponse({'results': results})


# ---------- Messages inbox ----------

@login_required
def messages_inbox(request):
    """
    One row per conversation (a trip + the other person), newest first,
    instead of making someone hunt through every trip they're part of to
    find where a reply landed.
    """
    mine = Message.objects.filter(
        Q(sender=request.user) | Q(recipient=request.user)
    ).select_related('trip', 'sender', 'recipient')

    threads = {}
    for m in mine:
        other = m.recipient if m.sender == request.user else m.sender
        if other is None:
            continue  # legacy group message with no single recipient
        key = (m.trip_id, other.id)
        entry = threads.get(key)
        if entry is None or m.created_at > entry['last_message'].created_at:
            threads[key] = {
                'trip': m.trip, 'other': other, 'last_message': m,
                'unread': 0,
            }

    # Count unread separately so it reflects ALL unread messages in the
    # thread, not just whether the single latest one is unread.
    for key, entry in threads.items():
        trip_id, other_id = key
        entry['unread'] = Message.objects.filter(
            trip_id=trip_id, sender_id=other_id, recipient=request.user, read=False
        ).count()

    thread_list = sorted(threads.values(), key=lambda e: e['last_message'].created_at, reverse=True)
    return render(request, 'trips/messages_inbox.html', {'threads': thread_list})
@login_required
def partner_dashboard(request):
    available_rides = Trip.objects.filter(
        status='not_started'
    ).exclude(
        traveler=request.user
    ).order_by('departure_time')

    return render(
        request,
        'trips/partner_dashboard.html',
        {
            'available_rides': available_rides,
        }
    )