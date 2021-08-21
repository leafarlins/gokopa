from flask import Flask
from .routes.usuario import usuario
from .routes.bolao import bolao
from .routes.gokopa import gokopa
from .extentions import database
from .commands.userCommands import userCommands
from .commands.jogosCommands import jogosCommands
from .commands.timeCommands import timeCommands
from .commands.bolaoCommands import bolaoCommands
from .cache import cache

def create_app(config_object="app.settings"):
    app = Flask(__name__)
    app.config.from_object(config_object)
    app.register_blueprint(usuario)
    app.register_blueprint(bolao)
    app.register_blueprint(gokopa)
    app.register_blueprint(userCommands)
    app.register_blueprint(jogosCommands)
    app.register_blueprint(timeCommands)
    app.register_blueprint(bolaoCommands)
    
    cache.init_app(app)
    database.init_app(app)

    return app