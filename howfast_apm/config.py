import os

# Constants
HOWFAST_APM_COLLECTOR_URL = os.environ.get(
    'HOWFAST_APM_COLLECTOR_URL',
    "https://api.howfast.tech/v1.1/apm-collector/store",
)
