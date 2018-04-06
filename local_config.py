import logging
LOG_LEVEL = 30 # To be deprecated when all microservices use ADSFlask
LOGGING_LEVEL = "INFO"
BIBLIB_ADSWS_API_DB_URI = ''
BIBLIB_CLASSIC_SERVICE_URL = ''
BIBLIB_CLIENT_ADSWS_API_TOKEN = ''
BIBLIB_SOLR_BIG_QUERY_URL = ''
BIBLIB_TWOPOINTOH_SERVICE_URL = ''
BIBLIB_USER_EMAIL_ADSWS_API_URL = ''
DISCOVERER_SELF_PUBLISH = True
SQLALCHEMY_BINDS = {"": ""}
SQLALCHEMY_DATABASE_URI = ''
SQLALCHEMY_ECHO = False
SQLALCHEMY_POOL_SIZE = 1
SQLALCHEMY_MAX_OVERFLOW = 1 # allow to exceptionally grow the pool by N
SQLALCHEMY_POOL_TIMEOUT = 1 # Specifies the connection timeout in seconds for the pool
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_RECORD_QUERIES = False


# added by eb-deploy (over-write config values) from environment
try:
    import os, json, ast
    G = globals()
    for k, v in os.environ.items():
        if k == k.upper() and k in G:
            logging.info("Overwriting constant '%s' old value '%s' with new value '%s'", k, G[k], v)
            try:
                w = json.loads(v)
                G[k] = w
            except:
                try:
                    # Interpret numbers, booleans, etc...
                    G[k] = ast.literal_eval(v)
                except:
                    # String
                    G[k] = v
except:
    pass
