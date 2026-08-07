from .base import *

DEBUG = False

SECRET_KEY = env('SECRET_KEY')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

# Database (Example using PostgreSQL via dj-database-url / django-environ)
DATABASES = {
    'default': env.db('DATABASE_URL')
}

# Security settings for production (HTTPS via Cloudflare/Nginx)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS if host not in ('127.0.0.1', 'localhost')]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True