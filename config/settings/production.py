from .base import *  # noqa: F403,F401

DEBUG = False

SECURE_SSL_REDIRECT = env("DJANGO_SECURE_SSL_REDIRECT", default="True", cast=bool)  # noqa: F405
SESSION_COOKIE_SECURE = env("DJANGO_SESSION_COOKIE_SECURE", default="True", cast=bool)  # noqa: F405
CSRF_COOKIE_SECURE = env("DJANGO_CSRF_COOKIE_SECURE", default="True", cast=bool)  # noqa: F405
USE_X_FORWARDED_HOST = env("DJANGO_USE_X_FORWARDED_HOST", default="True", cast=bool)  # noqa: F405
