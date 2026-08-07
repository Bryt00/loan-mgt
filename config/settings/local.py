from .base import *

# Quick-start development settings
DEBUG = env.bool('DEBUG', default=True)

SECRET_KEY = env('SECRET_KEY', default='django-insecure-*#q%8v+b^goywn1(a=u9d&+0=lw!^qqst4u#vq$c50yzuvl8pv')

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}