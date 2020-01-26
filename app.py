import os
from flask import Flask, render_template, request, redirect
from datetime import datetime
#from time import TimeG

class TimeG:
  def __init__(self, nome, conf, rank, link="no-image"):
    self.nome = nome
    self.confed = conf
    #self.console = console
    self.rf = rank
    self.ilink = link

class Partida:
  def __init__(self, ano, jogo, time1, pl1, pl2, time2,comp, fase, tr1, tr2, p1, p2, data, grupo,img1,img2):
      self.ano = int(ano)
      self.jogo = int(jogo)
      self.time1 = time1
      self.time2 = time2
      self.pl1 = int(pl1)
      self.pl2 = int(pl2)
      self.time2 = time2
      self.comp = comp
      self.fase = fase
      self.tr1 = tr1
      self.tr2 = tr2
      self.p1 = p1
      self.p2 = p2
      self.data = datetime.strptime(data,'%d/%m/%Y %H:%M')
      self.grupo = grupo
      self.img1 = img1
      self.img2 = img2
      self.r1 = time_rank[time1]
      self.r2 = time_rank[time2]

class Ranking:
  def __init__(self, pos, nome, ilink, pontos, sobdes, conf, titulos):
      self.pos = int(pos)
      self.nome = nome
      self.ilink = ilink
      self.pontos = int(pontos)
      self.sobdes = int(sobdes)
      self.conf = conf
      self.titulos = titulos
      if (self.sobdes > 0):
        self.irank = "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b0/Increase2.svg/11px-Increase2.svg.png"
      elif (self.sobdes < 0):
        self.irank = "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ed/Decrease2.svg/11px-Decrease2.svg.png"
      else:
        self.irank = "https://upload.wikimedia.org/wikipedia/commons/thumb/9/96/Steady2.svg/11px-Steady2.svg.png"


app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])
lista_time = []
l_partidas_futuras = []
l_partidas_passadas = []
l_ranking = []
time_img = {}
time_rank = {}

@app.route('/')
def home():
    lista_new = sorted(l_partidas_futuras,key=lambda x: x.data, reverse=False)
    lista_old = sorted(l_partidas_passadas,key=lambda x: x.data, reverse=True)
    return render_template('inicio.html', titulo='Início', menu="Home", listat=lista_time, lista_partidas_old=lista_old[:10], lista_partidas_new=lista_new[:10], lista_ranking=l_ranking[:20])

@app.route('/jogos')
def jogos():
  lista_new = sorted(l_partidas_futuras,key=lambda x: x.data, reverse=False)
  lista_old = sorted(l_partidas_passadas,key=lambda x: x.data, reverse=True)
  return render_template('jogos.html', titulo='Jogos', menu="Jogos", lista_partidas_old=lista_old, lista_partidas_new=lista_new)

@app.route('/hello-<name>')
def hello_name(name):
  return "Hello {}!".format(name)

@app.route('/gokopa18')
def gokopa(nrg):
  grupos = carrega_grupo(18)
  return render_template('gokopa16g.html', menu="Tabela",lista_grupos=grupos)

@app.route('/ranking')
def ranking():
  return render_template('ranking.html', menu="Ranking")

def carrega_historico(ano):
    arquivo = open("./files/historico.csv", "r")
    for linha in arquivo:
        jogol = linha.strip().split(",")
        if (int(jogol[0]) == ano):
            partida = Partida(jogol[0],jogol[1],jogol[2],jogol[4],jogol[6],jogol[8],jogol[9],jogol[10],jogol[11],jogol[12],jogol[13],jogol[14],jogol[15],jogol[16],time_img[jogol[2]],time_img[jogol[8]])
            if (agora > partida.data):
                l_partidas_passadas.append(partida)
            else:
                l_partidas_futuras.append(partida)
    arquivo.close()

def carrega_ranking():
    arquivo = open("./files/ranking.csv", "r")
    for linha in arquivo:
        rl = linha.strip().split(",")
        rank = Ranking(rl[0],rl[2],time_img[rl[2]],rl[3],rl[5],rl[9],[rl[10],rl[11],rl[12]])
        l_ranking.append(rank)
        time_rank.update({rl[2]:rl[0]})
    arquivo.close()

def carrega_grupo():
    arquivo = open("./files/grupo18.txt", "r")
    dic_grupo = {}
    for linha in arquivo:
        rl = linha.strip().split(",")
        dic_grupo.update({rl[0]:rl[1]})
    arquivo.close()
    return dic_grupo

if __name__ == '__main__':
    print(os.environ['APP_SETTINGS'])
    agora = datetime.now()
    # le arquivo de times e gokopa atual
    arquivo = open("files/times.txt", "r")
    for linha in arquivo:
        timel = linha.strip().split(",")
        time = TimeG(timel[0],timel[1],timel[2],timel[3])
        time_img.update( {timel[0]:timel[3]} )
        lista_time.append(time)
    arquivo.close()

    carrega_ranking()
    carrega_historico(18)
    carrega_historico(19)
    app.run()
