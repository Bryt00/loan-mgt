from .base import *

DEBUG = False

SECRET_KEY = env('SECRET_KEY')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

# Database (Example using PostgreSQL via dj-database-url / django-environ)
DATABASES = {
    'default': env.db('DATABASE_URL')
}