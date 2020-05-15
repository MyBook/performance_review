Performance review
==================

Инструмент для performance review с BSD-лицензией.
Python 3.7.3, Django 2.2, на основе https://cookiecutter-django.readthedocs.io
Деплоится на Heroku + AWS (статика), мониторинг ошибок в Sentry, Sendgrid для писем, Redis для кэша.


Фичи
~~~~

* авторизация через google account
* выбор и модерация респондентов review
* написание и модерация self-review
* написание и модерация review
* уведомления на почту (см. perf/templates/email)
* статистика прохождения ревью, агрегация обратной связи
* постановка квартальных целей


Development
~~~~~~~~~~~

::

    # Docker
    https://cookiecutter-django.readthedocs.io/en/latest/developing-locally-docker.html
    docker-compose -f local.yml build
    docker-compose -f local.yml up
    docker-compose -f local.yml run --rm django py.test

    # No docker
    https://cookiecutter-django.readthedocs.io/en/latest/developing-locally.html


Deployment
~~~~~~~~~~

::

    https://cookiecutter-django.readthedocs.io/en/latest/deployment-on-heroku.html


Environment variables
---------------------

::

    CONTENT_DESCRIPTION_PAGE:       wiki page where perf review process is described
    CONTENT_EMAIL_SIGNATURE:        email signature in some letters (welcome, self-review started)
    CONTENT_FREE_FEEDBACK_URL:      google docs form URL in top menu
    CONTENT_SUPPORT_EMAIL:          email address of support
    CONTENT_TIPS_PAGE:              URL to wiki pages for welcome email
    CONTENT_SELFREVIEW_EXAMPLE:     URL for selfreview example
    DATABASE_URL:                   Database connection URL, parsed with https://github.com/jacobian/dj-database-url
    DJANGO_ADMIN_URL:               secret slug to avoid admin password bruteforcing
    DJANGO_ALLOWED_HOSTS:           https://docs.djangoproject.com/en/3.0/ref/settings/#allowed-hosts
    DJANGO_AWS_ACCESS_KEY_ID:       https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
    DJANGO_AWS_SECRET_ACCESS_KEY:
    DJANGO_AWS_STORAGE_BUCKET_NAME:
    DJANGO_DEFAULT_FROM_EMAIL:      https://docs.djangoproject.com/en/3.0/ref/settings/#default-from-email
    DJANGO_SECRET_KEY:              https://docs.djangoproject.com/en/3.0/ref/settings/#secret-key
    DJANGO_SENTRY_DSN:              Sentry connection URL
    DJANGO_SETTINGS_MODULE:         config.settings.production
    MENU_FREE_FEEDBACK_URL:         google docs form URL
    REDIS_URL:                      Redis connection URL
    SENDGRID_API_KEY:
    SENDGRID_PASSWORD:
    SENDGRID_USERNAME:
    SOCIALACCOUNT_DOMAINS_ALLOWED:  domains separated with colon (no whitespaces)
