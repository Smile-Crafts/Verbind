from datetime import date

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView

from .forms import (
    SignUpForm, ProfileForm, IDVerificationForm, TripForm,
    TripFilterForm, MessageForm, RatingForm,
)
from .models import Trip, JoinRequest, Message, Rating


# ---------- Accounts ----------

class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = 'registration/signup.html'
    success_url = reverse_lazy('edit-profile')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


@login_required
def edit_profile(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect('trip-list')
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'trips/edit_profile.html', {'form': form})


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
            return redirect('trip-list')
    else:
        form = IDVerificationForm(instance=profile)
    return render(request, 'trips/verify_identity.html', {'form': form})


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

    def form_valid(self, form):
        form.instance.traveler = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, "Ride posted.")
        return response


@login_required
def trip_detail(request, pk):
    trip = get_object_or_404(Trip, pk=pk)
    is_participant = (
        trip.traveler == request.user
        or trip.join_requests.filter(requester=request.user).exists()
    )

    if request.method == 'POST' and 'send_message' in request.POST and is_participant:
        msg_form = MessageForm(request.POST)
        if msg_form.is_valid():
            Message.objects.create(trip=trip, sender=request.user, body=msg_form.cleaned_data['body'])
            return redirect('trip-detail', pk=pk)
    else:
        msg_form = MessageForm()

    rating_form = RatingForm()
    already_rated_ids = list(
        Rating.objects.filter(trip=trip, rater=request.user).values_list('ratee_id', flat=True)
    )
    other_participants = [u for u in trip.participants() if u != request.user and u.id not in already_rated_ids]

    return render(request, 'trips/trip_detail.html', {
        'trip': trip,
        'is_participant': is_participant,
        'chat_messages': trip.messages.select_related('sender'),
        'msg_form': msg_form,
        'rating_form': rating_form,
        'other_participants': other_participants,
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
            messages.success(request, f"Rated {ratee.username}.")
    return redirect('trip-detail', pk=pk)


@login_required
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
        send_mail(
            subject='Someone wants to share your ride',
            message=(
                f"Hi {trip.traveler.username},\n\n"
                f"{request.user.username} wants to join your ride to {trip.dropoff_area} "
                f"on {trip.departure_time:%d %b, %H:%M}. Open Verbind to chat with them."
            ),
            from_email=None,
            recipient_list=[trip.traveler.email],
            fail_silently=True,
        )

    return redirect('trip-list')
