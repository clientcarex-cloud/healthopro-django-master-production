"""Django settings for healtho_pro project."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY = '2QjIpEzxxFqcoaBbb69peyQYxpVWpd-Aks4m7-q1sk_1fcETL6jw29tFaOmvk7nIbtU'
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

HEALTHO_SECRET_KEY = os.environ.get('HEALTHO_SECRET_KEY')
# HEALTHO_SECRET_KEY = '17d55f99-dec1-4b7f-ac56-20cf7624896a'

generated_access_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwianRpIjoiMTdkNTVmOTktZGVjMS00YjdmLWFjNTYtMjBjZjc2MjQ4OTZhIiwiZXhwIjoxNzQ5MDk3OTY5LCJ1c2VyX2lkIjoxfQ.EX5FyMZ725-OR2EeMQOGVt6Tx2rSAYrsywL5Ns-grew'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
# DEBUG = True


#FOR MEDIA STORAGE
# AZURE_CONTAINER = 'healthopro'
# DEFAULT_FILE_STORAGE = 'storages.backends.azure_storage.AzureStorage'
# STATICFILES_STORAGE = 'storages.backends.azure_storage.AzureStorage'
# AZURE_STATIC_LOCATION = "static"


ALLOWED_HOSTS = ['*']

# Application definition
SHARED_APPS = [
    'daphne',
    'channels',
    'django_tenants',
    'django_filters',
    'corsheaders',
    'healtho_pro_user',
    'pro_universal_data',
    'interoperability',
    'mobile_app',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'django_extensions',
    'cloud_messaging',
    'super_admin',
]


TENANT_APPS = [
    'pro_prescription',
    'accounts',
    'pro_laboratory',
    'pro_pharmacy',
    'pro_hospital',
    'business_messaging'
]

INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

# CHANNEL_LAYERS = {
#     'default': {
#         'BACKEND': 'channels.layers.InMemoryChannelLayer',
#         'CONFIG': {},
#     },
# }

TENANT_MODEL = "healtho_pro_user.Client"  # app.Model

TENANT_DOMAIN_MODEL = "healtho_pro_user.Domain"  # app.Model

REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),

    'DEFAULT_PAGINATION_CLASS': 'healtho_pro.pagination.CustomPagination',
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated'
    ]
}

from datetime import timedelta, datetime

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': False,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}


MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'logging_middleware.LoggingMiddleware',
    'healtho_pro_user.middlewares.jwt_authentication_middleware',
    'healtho_pro_user.middlewares.TenantContextMiddleware'
]


# Paths that don't require tenant schema logic
UNPROTECTED_PATHS = [
    '/user/otp-login/',
    'user/password_login/'
    '/user/token/refresh/',
    'user/usertypes'
    '/user/login/',
    'user/resend-otp'
    '/user/country/',
    '/user/state/',
    '/user/city/',
    '/inter/lab_tpa_integrated_secret_keys/',
    '/lab/tpa_ultrasound_integration/',
    '/lab/download_test_report/',
    '/lab/otp_for_report/',
    '/lab/download_patient_receipt/'

    # Add other paths as needed
]

'''
For these, permission_classes = [permissions.AllowAny] or [permissions.IsAuthenticatedOrReadOnly] is kept in the api view
 'user/create',
  'user/login',
 'user/otp-login',
 'user/password_login'
 'user/resend-otp',
 'user/usertypes',
 'user/login_sliders',
 'user/city',
 'user/state',
 'user/country', 
 'user/healthcare_registry_types',
 'inter/lab_tpa_integrated_secret_keys',
 'lab/tpa_ultrasound_integration/',
 'lab/tpa_machine_integration',
 '/lab/download_test_report/',
 'lab/otp_for_report/',
 '/lab/download_patient_receipt/'
'''

CORS_ALLOW_ALL_ORIGINS = True

CORS_ALLOWED_ORIGINS = [
    "http://localhost:4200",
]

ROOT_URLCONF = 'healtho_pro.urls'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],  # Include your templates directory here
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


# WSGI_APPLICATION = "healtho_pro.wsgi.application"

ASGI_APPLICATION = "healtho_pro.asgi.application"

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT')
    },
}

DATABASE_ROUTERS = (
    'django_tenants.routers.TenantSyncRouter',
)

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Kolkata'

USE_TZ = False  # This is set to False to get the times in IST

USE_I18N = True

USE_L10N = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = '/static/'

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'healtho_pro_user.HealthOProUser'

STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}

SENDINBLUE_API_KEY =os.environ.get('SENDINBLUE_API_KEY')
