from datetime import datetime
import click
import getpass

import pymongo
from ..extentions.database import mongo
from flask import Blueprint
from app.routes.backend import get_aposta,get_users,get_games,make_score_board,get_bet_results,get_score_results

configCommands = Blueprint('config',__name__)
ANO=22

#@bolaoCommands.cli.command("getOrdered")
#@click.argument("")
def get_ordered(ano=ANO):
    basehis = 'bolao' + ano + 'his'
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
    ano_jogos = get_games(int(ano))
    allUsers = getBolaoUsers(ano)

    for jogo in ano_jogos:
        id_jogo = jogo["Jogo"]
        data_jogo = datetime.strptime(jogo["Data"],"%d/%m/%Y %H:%M")
        aposta = get_aposta(id_jogo,'apostas'+ano)
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
        #ordered_total[i]["tipo"] = tipo
    
    return ordered_total

@configCommands.cli.command("setHistory")
@click.argument("ano",required=False)
def set_history(ano):
    if not ano:
        ano = str(ANO)
    basehis = 'bolao' + ano + 'his'
    # Em caso de duplo ranking, setar tipo 2x
    ordered_total_gk = get_ordered(ano)
    print(ordered_total_gk)
    print("Escrevendo placar de hoje na base")
    mongo.db[basehis].insert(ordered_total_gk)

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

@configCommands.cli.command("set_bolao_users")
@click.argument("ano")
@click.argument("users")
def set_bolao_users(ano,users):
    u_arr = users.split()
    mongoconfig = mongo.db.settings.find_one_and_update({"config": "bolao_u", "ano": int(ano)},{'$set': {"users": u_arr }})
    if mongoconfig:
        print("Valor atualizado.")
    else:
        print("Config não existe na base, definindo...")
        mongo.db.settings.insert({"config": "bolao_u","ano": int(ano),"users": u_arr })

def getBolaoUsers(ano):
    b_users = mongo.db.settings.find_one({"config": "bolao_u","ano": int(ano)})
    return b_users["users"]

@configCommands.cli.command("get_bolao_users")
@click.argument("ano")
def get_bolao_users(ano):
    print(getBolaoUsers(ano))

@configCommands.cli.command("migrate")
def migrate():
    print("- Apagando dados de tipo dos boloes")
    print("bolao2022his gk")
    outdb = mongo.db.bolao2022his.find_one_and_delete({"tipo":"gk"})
    while outdb:
        outdb = mongo.db.bolao2022his.find_one_and_delete({"tipo":"gk"})
    print("bolao21his cp")
    outdb = mongo.db.bolao21his.find_one_and_delete({"tipo":"cp"})
    while outdb:
        outdb = mongo.db.bolao21his.find_one_and_delete({"tipo":"cp"})
    print("- Setando grupos das gokopas 20-21 e wc 2022")
    wc_2022 = {
        'A': [0,2,17,18,32,33],
        'B': [1,3,16,19,34,35],
        'C': [4,6,21,23,38,39],
        'D': [5,7,20,22,36,37],
        'E': [9,10,24,27,42,43],
        'F': [8,11,25,26,40,41],
        'G': [12,15,28,30,46,47],
        'H': [13,14,29,31,44,45]
    }
    print("wc 2022 e gk21")
    for i in wc_2022:
        print(f"Grupo {i}")
        for j in wc_2022[i]:
            #print(f'Set jogo {j} grupo ')
            mongo.db.jogos.find_one_and_update({'Ano': 2022, 'Jogo': j+1},{'$set': {'Grupo': i}})
            mongo.db.jogos.find_one_and_update({'Ano': 21, 'Jogo': j+1},{'$set': {'Grupo': i}})
    print("gk20")
    gk20wc = ['A','A','B','B','C','D','C','D','E','F','E','F','G','G','H','H','A','B','A','B','C','C','D','E','D','E','G','F','F','G','H','H','A','A','B','B','C','C','D','D','F','F','E','E','H','H','G','G']
    gk20t = ['A-EUR','B-EUR','C-EUR','D-EUR','E-EUR','F-EUR','G-EUR','H-EUR','A-AFR','B-AFR','C-AFR','D-AFR','A-ASO','B-ASO','C-ASO','D-ASO','A-AME','B-AME','C-AME','D-AME','A-EUR','B-EUR','C-EUR','D-EUR','E-EUR','F-EUR','G-EUR','H-EUR','A-AFR','B-AFR','C-AFR','D-AFR','A-ASO','B-ASO','C-ASO','D-ASO','A-AME','B-AME','C-AME','D-AME','A-EUR','B-EUR','C-EUR','D-EUR','E-EUR','F-EUR','G-EUR','H-EUR','A-AFR','B-AFR','C-AFR','D-AFR','A-ASO','B-ASO','C-ASO','D-ASO','A-AME','B-AME','C-AME','D-AME']
    for i in range(len(gk20t)):
        mongo.db.jogos.find_one_and_update({'Ano': 20, 'Jogo': 21+i},{'$set': {'Grupo': gk20t[i]}})
    for i in range(len(gk20wc)):
        mongo.db.jogos.find_one_and_update({'Ano': 20, 'Jogo': 121+i},{'$set': {'Grupo': gk20wc[i]}})

    print("gk19")
    gk19wc = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P']
    for i in range(len(gk19wc)):
        mongo.db.jogos.find_one_and_update({'Ano': 19, 'Jogo': 79+i},{'$set': {'Grupo': gk19wc[i]}})

    print("-Ajuste de nomes de competição")
    oldn = ['Copa','Taça ÁSIAOCE','Taça AMÉRICA','Taça EUROPA','Taça ÁFRICA']
    newn = ['Copa do Mundo','Taça Ásia-Oceania','Taça América','Taça Europa','Taça África']
    for i in range(len(oldn)):
        outdb = True
        while outdb:
            outdb = mongo.db.jogos.find_one_and_update({'Competição': oldn[i]},{'$set': {'Competição': newn[i] }})
    


    print("Finalizado.")
