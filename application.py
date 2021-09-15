import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from flask import Flask

from app import create_app

sentry_sdk.init(
    integrations=[FlaskIntegration()],
    traces_sample_rate=1.0
)

application = Flask('app')

create_app(application)
