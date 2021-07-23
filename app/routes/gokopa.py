from array import array
from datetime import datetime
from typing import Collection
from flask import Blueprint, render_template, session, request, url_for, flash
import pymongo
from pymongo import collection
from werkzeug.utils import redirect
from werkzeug.security import check_password_hash
from ..extentions.database import mongo
from ..cache import cache

#current_app para carregar app.py

gokopa = Blueprint('gokopa',__name__)

# Rota / associada a função index
@gokopa.route('/')
@cache.cached(timeout=120)
def index():
    ANO=20
    past_jogos = [u for u in mongo.db.jogos.find({'Ano': 19}).sort([('Jogo',pymongo.DESCENDING)])]
    ano20_jogos = mongo.db.jogos.find({'Ano': ANO}).sort([("Jogo",pymongo.ASCENDING)])
    next_jogos = []
    now = datetime.now()
    for n in ano20_jogos:
        if n["Time1"] and n["Time2"]:
            data_jogo = datetime.strptime(n["Data"],"%d/%m/%Y %H:%M")
            if data_jogo < now and n["p1"] != "" :
                past_jogos.insert(0,n)
            else:
                next_jogos.append(n)

    return render_template("inicio.html",menu="Home",past_jogos=past_jogos[:20],next_jogos=next_jogos[:20])


@cache.memoize(300)
def get_jogos_tab(ano,r1):
    return mongo.db.jogos.find({'Ano': ano, "Jogo": {'$gt': r1 }}).sort([("Jogo",pymongo.ASCENDING)])

@cache.memoize(300)
def get_team_table(descx,desc,timex):
    return mongo.db.jogos.find_one({"Ano": 20, descx: desc}).get(timex)

@gokopa.route('/tabela')
def tabela():
    ano20_jogos = [u for u in mongo.db.jogos.find({'Ano': 20, "Jogo": {'$gt': 20 }}).sort([("Jogo",pymongo.ASCENDING)])]
    tabelas_label = ['A-EUR','B-EUR','C-EUR','D-EUR','E-EUR','F-EUR','G-EUR','H-EUR','A-AFR','B-AFR','C-AFR','D-AFR','A-ASO','B-ASO','C-ASO','D-ASO','A-AME','B-AME','C-AME','D-AME']
    tabelas = []
    # id of each game based on groups
    jogos_id = []
    for i in range(20):
        jogos_id.append([i,20+i,40+i])
        print("Jogosid",jogos_id)

    for i in range(20):
        desc1 = "p" + str(1) + tabelas_label[i]
        desc2 = "p" + str(2) + tabelas_label[i]
        desc3 = "p" + str(3) + tabelas_label[i]
        time1 = get_team_table('desc1',desc1,'Time1')
        time2 = get_team_table('desc1',desc2,'Time1')
        time3 = get_team_table('desc2',desc3,'Time2')
        times = [time1,time2,time3]
        descs = [desc1,desc2,desc3]
        for i in range(3):
            linha = dict()
            if times[i]:
                linha['nome'] = times[i]
                linha['P'] = 0
                linha['S'] = 0
                linha['G'] = 0
            else:
                linha['nome'] = descs[i]
                #tab.update({'nome': desc})
            tabelas.append(linha)
    #print(tabelas)

    return render_template('tabela20reg.html',menu="Tabela",tabelas=tabelas,labels=tabelas_label,lista_jogos=ano20_jogos,jogos_id=jogos_id)


@gokopa.route('/ranking')
@cache.cached(timeout=6000)
def ranking():
    ranking = [u for u in mongo.db.ranking.find({"ed": "19-3"}).sort('pos',pymongo.ASCENDING)]
    return render_template("ranking.html",menu="Ranking",ranking=ranking)

    