import os

MONGO_URI = os.getenv('MONGO_URI')
SECRET_KEY = os.getenv('SECRET_KEY')
WERKZEUG_DEBUG_PIN = os.getenv('WERKZEUG_DEBUG_PIN')
LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
#ANO = 21
#RANKING = os.getenv('RANKING','19-3')
