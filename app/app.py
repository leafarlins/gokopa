from flask import Flask
from .routes.usuario import usuario
from .routes.bolao import bolao
from .routes.gokopa import gokopa
from .routes.backend import backend
from .extentions import database
from .commands.userCommands import userCommands
from .commands.jogosCommands import jogosCommands
from .commands.timeCommands import timeCommands
from .commands.configCommands import configCommands
from .commands.email import emailCommands
from .cache import cache

def create_app(config_object="app.settings"):
    app = Flask(__name__)
    app.config.from_object(config_object)
    app.register_blueprint(usuario)
    app.register_blueprint(bolao)
    app.register_blueprint(gokopa)
    app.register_blueprint(backend)
    app.register_blueprint(userCommands)
    app.register_blueprint(jogosCommands)
    app.register_blueprint(timeCommands)
    app.register_blueprint(configCommands)
    app.register_blueprint(emailCommands)
    
    cache.init_app(app)
    database.init_app(app)

    
    return app