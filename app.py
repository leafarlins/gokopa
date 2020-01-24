import os
from flask import Flask, render_template, request, redirect
#from time import TimeG

class TimeG:
  def __init__(self, nome, conf, rank):
    self.nome = nome
    self.confed = conf
    #self.console = console
    self.rf = rank
    #self.ilink = ilink

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])
lista_time = []

@app.route('/')
def hello():
    return render_template('inicio.html', titulo='Início', menu="Home", listat=lista_time)

@app.route('/<name>')
def hello_name(name):
    return "Hello {}!".format(name)

if __name__ == '__main__':
    print(os.environ['APP_SETTINGS'])
    # le arquivo de times
    arquivo = open("times.txt", "r")
    for linha in arquivo:
        timel = linha.strip().split()
        time = TimeG(timel[0],timel[1],timel[2])
        lista_time.append(time)
    arquivo.close()

    app.run()
