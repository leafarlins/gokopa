from flask import Flask
from .routes.usuario import usuario
from .routes.bolao import bolao
from .routes.gokopa import gokopa
from .extentions import database
from .commands.userCommands import userCommands
from .commands.jogosCommands import jogosCommands
from .commands.timeCommands import timeCommands

def create_app(config_object="app.settings"):
    # name: variavel especial com nome do script
    app = Flask(__name__) 
    app.config.from_object(config_object)
    app.register_blueprint(usuario)
    app.register_blueprint(bolao)
    app.register_blueprint(gokopa)
    app.register_blueprint(userCommands)
    app.register_blueprint(jogosCommands)
    app.register_blueprint(timeCommands)

    database.init_app(app)

    return app

