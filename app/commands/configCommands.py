from datetime import datetime
import click
import getpass

import pymongo
from ..extentions.database import mongo
from flask import Blueprint
from app.routes.backend import get_aposta,get_users,get_games,make_score_board,get_bet_results,get_score_results

configCommands = Blueprint('config',__name__)
ANO=2022

#@bolaoCommands.cli.command("getOrdered")
#@click.argument("")
def get_ordered(tipo):
    basehis = 'bolao' + str(ANO) + 'his'
    collection = mongo.db[basehis]
    bolao_his = [u for u in collection.find().sort("Dia",pymongo.DESCENDING)]
    last_day = ""
    now = datetime.now()
    resultados=[]
    hoje = datetime.strftime(now,"%d/%m/%Y")
    #print(bolao_his)
    
    if not len(bolao_his) > 0:
        print("Nao existe base historica de bolao")
        last_day = 0
    else:
        last_day = bolao_his[0].get("Dia")
        last_date = bolao_his[0].get("Data")
        #print(f'Ultima dia: {last_day} - {last_date}')
    ano_jogos = get_games()
    allUsers = get_users(tipo)

    for jogo in ano_jogos:
        id_jogo = jogo["Jogo"]
        data_jogo = datetime.strptime(jogo["Data"],"%d/%m/%Y %H:%M")
        aposta = get_aposta(id_jogo)
        # If game is old and score not empty
        if data_jogo < now and jogo['p1'] != "":
            jogo_inc = get_bet_results(allUsers,aposta,jogo)
            resultados.append(jogo_inc)

    list_total=get_score_results(allUsers,resultados)

    #print(allUsers)
    #print(list_total)
    ordered_total = sorted(sorted(list_total, key=lambda k: k['pc'],reverse=True), key=lambda k: k['score'],reverse=True)

    dia_id = last_day + 1
    last_score = 0
    last_pc = 0
    last_pos = 1
    for i in range(len(ordered_total)):
        ordered_total[i]["Dia"] = dia_id
        ordered_total[i]["Data"] = hoje
        if ordered_total[i]["score"] == last_score and ordered_total[i]["pc"] == last_pc:
            ordered_total[i]["posicao"] = last_pos
        else:
            ordered_total[i]["posicao"] = i+1
            last_score = ordered_total[i]["score"]
            last_pc = ordered_total[i]["pc"]
            last_pos = i+1
        # Define tipo gk ou cp
        ordered_total[i]["tipo"] = tipo
    
    return ordered_total

@configCommands.cli.command("setHistory")
def set_history():
    basehis = 'bolao' + str(ANO) + 'his'
    # Em caso de duplo ranking, setar tipo 2x
    ordered_total_gk = get_ordered('gk')
    print(ordered_total_gk)
    ordered_total_cp = get_ordered('cp')
    print(ordered_total_cp)
    print("Escrevendo placar de hoje na base")
    mongo.db[basehis].insert(ordered_total_gk)
    mongo.db[basehis].insert(ordered_total_cp)

@configCommands.cli.command("setRank")
@click.argument("edition")
def set_history(edition):
    mongoconfig = mongo.db.settings.find_one_and_update({"config": "ranking"},{'$set': {'edition': edition }})
    if mongoconfig:
        print("Valor atualizado.")
    else:
        print("Config não existe na base, definindo...")
        mongo.db.settings.insert({"config": "ranking", "edition": edition})

@configCommands.cli.command("setHl")
@click.argument("team")
def set_hl(team):
    mongoconfig = mongo.db.settings.find_one_and_update({"config": "highlight"},{'$set': {'time': team }})
    if mongoconfig:
        print("Valor atualizado.")
    else:
        print("Config não existe na base, definindo...")
        mongo.db.settings.insert({"config": "highlight", "time": team})