# Procfile
web: python manage.py migrate --no-input && python manage.py collectstatic --no-input && gunicorn core.wsgi