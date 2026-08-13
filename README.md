# Verbind — updated project

This is your app rebuilt with the new features: signup with profile
pictures, gender field, location-filtered ride matching, in-app chat,
trust score / ratings, a free-ride cap, and a mock (prototype-only)
identity verification flow.

## Important: this replaces your code, not your setup

Your existing `venv` folder does NOT need to be recreated. You're just
swapping out the project files inside it.

## Exact steps

1. **Close VS Code and stop the running server** (Ctrl+C in the terminal)
   if it's still running.
2. **Unzip this** into a new folder, e.g. `Desktop/verbind`.
3. **Copy your existing `venv` folder** from your old `travelbuddy` project
   into this new `verbind` folder (drag and drop it in). This saves you
   from reinstalling Django from scratch.
4. **Delete the old database**: if there's a `db.sqlite3` file anywhere in
   your old project, don't copy it over. This project has new/changed
   models (Profile, Message, Rating, etc.), so we need a fresh database.
5. **Open the `verbind` folder in VS Code**: File → Open Folder.
6. **Open a terminal** in VS Code and activate the venv:
   - Windows: `.\venv\Scripts\Activate.ps1`
   - Mac/Linux: `source venv/bin/activate`

   You should see `(venv)` appear.
7. **Install the one new dependency** (Pillow, needed for image uploads):
   ```
   pip install -r requirements.txt
   ```
8. **Build the database fresh**:
   ```
   python manage.py makemigrations trips
   python manage.py migrate
   ```
9. **Create yourself an account**:
   ```
   python manage.py createsuperuser
   ```
10. **Run it**:
    ```
    python manage.py runserver
    ```
11. Visit `http://127.0.0.1:8000`, log in, click **Profile** in the top
    nav to add a picture/gender, then **Post a Ride** to try the new form
    (now has a gender preference field), then open a ride and try the
    chat box.

## What's real vs. what's mocked in this version

**Real and working:**
- Sign up / log in / profile with picture and gender
- Posting and browsing rides, filtered by drop-off area and gender preference
- In-app chat per ride (refresh-based, not instant/live)
- Ratings after a completed ride, shown as a trust score (★) on profiles
- Free-ride cap (2 joins/month unless `is_pro` is set on a Profile, toggle
  it manually in the Django admin at `/admin` for now, there's no real
  payment flow yet)
- Emails print to your terminal for now (see the comment block in
  `travelbuddy/settings.py` for how to switch to real Gmail sending
  before your demo)

**Mocked for the prototype, clearly labeled in the UI as such:**
- Identity verification: accepts any uploaded image, marks the account
  "Verified" immediately. No real NIN or face-matching check happens.
- Ride status ("started" / "completed"): manually toggled by
  participants, not live GPS tracking. This stands in for what would
  eventually be real location monitoring like Uber/Bolt use.

**Not built yet, roadmap only:**
- Real in-app voice calling (needs a Twilio account you'll need to set up)
- AI-assisted multi-stop route matching
- Native mobile app
- Real payment/Pro subscription flow

## If something errors

Paste me the exact error text and which step you were on, same as before.
