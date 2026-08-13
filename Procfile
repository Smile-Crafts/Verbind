web: python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn travelbuddy.wsgi --bind 0.0.0.0:$PORT --log-file -
