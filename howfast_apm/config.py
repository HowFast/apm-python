import os

# Where to send the performance data
HOWFAST_APM_COLLECTOR_URL = os.environ.get(
    'HOWFAST_APM_COLLECTOR_URL',
    "https://api.howfast.tech/v1.1/apm-collector/store",
)

# Record interactions of the API with external sources (HTTP requests, etc)
HOWFAST_APM_RECORD_INTERACTIONS = os.environ.get(
    'HOWFAST_APM_RECORD_INTERACTIONS',
    False,
)
