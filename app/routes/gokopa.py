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

ANO=20


def get_classificados():
    lista = [u for u in mongo.db.pot.find({'Ano': ANO})]
    print("lista",lista)
    class_eur = []
    class_afr = []
    class_aso = []
    class_ame = []
    for time in lista:
        if time['conf'] == 'EUR':
            class_eur.append(time)
        elif time['conf'] == 'AFR':
            class_afr.append(time)
        elif time['conf'] == 'ASO':
            class_aso.append(time)
        elif time['conf'] == 'AME':
            class_ame.append(time)
    lista_final = []
    # Vagas: 14 6 4 8
    for i in range(14-len(class_eur)):
        class_eur.append(dict({'nome:': 'x'}))
    for i in range(6-len(class_afr)):
        class_afr.append(dict({'nome:': 'x'}))
    for i in range(4-len(class_aso)):
        class_aso.append(dict({'nome:': 'x'}))
    for i in range(8-len(class_ame)):
        class_ame.append(dict({'nome:': 'x'}))
    lista_final.append(class_eur)
    lista_final.append(class_afr)
    lista_final.append(class_aso)
    lista_final.append(class_ame)
    print(lista_final)
    return lista_final



# Rota / associada a função index
@gokopa.route('/')
@cache.cached(timeout=120)
def index():
    past_jogos = [u for u in mongo.db.jogos.find({'Ano': 19}).sort([('Jogo',pymongo.DESCENDING)])]
    ano20_jogos = mongo.db.jogos.find({'Ano': ANO}).sort([("Jogo",pymongo.ASCENDING)])
    next_jogos = []
    classificados = get_classificados()
    now = datetime.now()
    for n in ano20_jogos:
        if n["Time1"] and n["Time2"]:
            data_jogo = datetime.strptime(n["Data"],"%d/%m/%Y %H:%M")
            if data_jogo < now and n["p1"] != "" :
                past_jogos.insert(0,n)
            else:
                next_jogos.append(n)

    return render_template("inicio.html",menu="Home",past_jogos=past_jogos[:20],next_jogos=next_jogos[:20],classificados=classificados)


@cache.memoize(300)
def get_jogos_tab(ano,r1):
    return mongo.db.jogos.find({'Ano': ano, "Jogo": {'$gt': r1 }}).sort([("Jogo",pymongo.ASCENDING)])

@cache.memoize(300)
def get_team_table(descx,desc,timex):
    return mongo.db.jogos.find_one({"Ano": 20, descx: desc}).get(timex)

@gokopa.route('/tabela')
@cache.cached(timeout=120)
def tabela():
    ano20_jogos = [u for u in mongo.db.jogos.find({'Ano': 20, "Jogo": {'$gt': 20 }}).sort("Jogo",pymongo.ASCENDING)]
    tabelas_label = ['A-EUR','B-EUR','C-EUR','D-EUR','E-EUR','F-EUR','G-EUR','H-EUR','A-AFR','B-AFR','C-AFR','D-AFR','A-ASO','B-ASO','C-ASO','D-ASO','A-AME','B-AME','C-AME','D-AME']
    tabelas = []
    now = datetime.now()
    # id of each game based on groups
    jogos_id = []
    for i in range(20):
        array_ids = []
        for j in range(3):
            j_id = i+j*20
            array_ids.append(j_id)
            
        # add ids [i,20+i,40+i]
        jogos_id.append(array_ids)
    #print(jogos_id)
    #print(ano20_jogos)

    for i in range(20):
        desc1 = "p" + str(1) + tabelas_label[i]
        desc2 = "p" + str(2) + tabelas_label[i]
        desc3 = "p" + str(3) + tabelas_label[i]
        time1 = get_team_table('desc1',desc1,'Time1')
        time2 = get_team_table('desc1',desc2,'Time1')
        time3 = get_team_table('desc2',desc3,'Time2')
        times = [time1,time2,time3]
        descs = [desc1,desc2,desc3]
        for j in range(3):
            linha = dict()
            if times[j]:
                linha['nome'] = times[j]
                linha['P'] = 0
                linha['S'] = 0
                linha['G'] = 0
                # Calculo de pontos para cada linha do grupo
                for jid in jogos_id[i]:
                    p1 = ano20_jogos[jid].get('p1')
                    data_jogo = datetime.strptime(ano20_jogos[jid].get("Data"),"%d/%m/%Y %H:%M")
                    if data_jogo < now:
                        if p1 != None:
                            p2 = ano20_jogos[jid].get('p2')
                            print("Calculando para jogo ",ano20_jogos[jid])
                            if p1 == p2:
                                linha['P'] += 1
                                linha['G'] = p1
                            elif p1 > p2: # Time1 ganha
                                if linha['nome'] == ano20_jogos[jid].get('Time1'):
                                    linha['P'] += 3
                                    linha['S'] += p1 - p2
                                    linha['G'] += p1
                                elif linha['nome'] == ano20_jogos[jid].get('Time2'):
                                    linha['S'] -= p1 - p2
                                    linha['G'] += p2
                            else: # Time2 ganha
                                if linha['nome'] == ano20_jogos[jid].get('Time2'):
                                    linha['P'] += 3
                                    linha['S'] += p2 - p1
                                    linha['G'] += p2
                                elif linha['nome'] == ano20_jogos[jid].get('Time1'):
                                    linha['S'] -= p2 - p1
                                    linha['G'] += p1
                    else:
                        if ano20_jogos[jid].get('p1'):
                            # Zera placares por ser placar futuro
                            ano20_jogos[jid]['p1'] = ""
                            ano20_jogos[jid]['p2'] = ""
            else:
                linha['nome'] = descs[j]
                #tab.update({'nome': desc})
            tabelas.append(linha)

    return render_template('tabela20reg.html',menu="Tabela",tabelas=tabelas,labels=tabelas_label,lista_jogos=ano20_jogos,jogos_id=jogos_id)


@gokopa.route('/ranking')
@cache.cached(timeout=3600*24)
def ranking():
    ranking = [u for u in mongo.db.ranking.find({"ed": "19-3"}).sort('pos',pymongo.ASCENDING)]
    return render_template("ranking.html",menu="Ranking",ranking=ranking)

@cache.memoize(3600*24)
def get_team_list():
    ranking = [u['time'] for u in mongo.db.ranking.find({"ed": "19-3"}).sort('pos',pymongo.ASCENDING)]
    return ranking

@cache.memoize(3600*24)
def return_historic_duels(team1,team2):
    historico_total = [u for u in mongo.db.jogos.find({ '$or': [{'Time1': team1,'Time2': team2 },{'Time1': team2,'Time2': team1 }],"Ano": {'$lt':20} }).sort([("Ano",pymongo.DESCENDING),("Jogo",pymongo.DESCENDING)])]
    vev = [0,0,0,len(historico_total)]
    for j in historico_total:
        if j['p1'] == j['p2']:
            vev[1] += 1
        elif (j['p1'] > j['p2']):
            if j['Time1'] == team1:
                vev[0] += 1
            else:
                vev[2] += 1
        else:
            if j['Time2'] == team1:
                vev[0] += 1
            else:
                vev[2] += 1

    return historico_total,vev

@gokopa.route('/historico',methods=["GET","POST"])
def historico():
    if request.method == "POST":
        time1 = request.values.get("time1")
        time2 = request.values.get("time2")
        times = [time1,time2]
        lista_jogos,vev = return_historic_duels(time1,time2)
    else:
        lista_jogos = []
        vev=[]
        times=[]
    return render_template('historico.html',menu='Historico',lista_jogos=lista_jogos,vev=vev,times=times,lista_times=get_team_list())
    