from datetime import datetime
import click
import getpass

import pymongo
from ..extentions.database import mongo
from flask import Blueprint
from app.routes.backend import get_aposta,get_users,get_games,make_score_board,get_bet_results2,get_score_results,getBolaoUsers

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
            jogo_inc = get_bet_results2(allUsers,aposta,jogo)
            resultados.append(jogo_inc)

    list_total=get_score_results(allUsers,resultados,ano)

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

# def getBolaoUsers(ano):
#     b_users = mongo.db.settings.find_one({"config": "bolao_u","ano": int(ano)})
#     return b_users["users"]

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
    paises19 = ["Panamá","Honduras","Honduras","Honduras","Nicarágua","Nicarágua","Costa Rica","Costa Rica","Honduras","Honduras","Honduras","Panamá","Costa Rica","Costa Rica","Nicarágua","Nicarágua","Panamá","Honduras","Honduras","Honduras","Nicarágua","Nicarágua","Costa Rica","Costa Rica","Honduras","Honduras","Honduras","Panamá","Costa Rica","Costa Rica","Nicarágua","Nicarágua","Panamá","Honduras","Honduras","Honduras","Nicarágua","Nicarágua","Costa Rica","Costa Rica","Honduras","Honduras","Honduras","Panamá","Costa Rica","Costa Rica","Nicarágua","Nicarágua","Panamá","Honduras","Honduras","Honduras","Nicarágua","Nicarágua","Costa Rica","Costa Rica","Honduras","Honduras","Honduras","Panamá","Costa Rica","Costa Rica","Nicarágua","Nicarágua","Panamá","Honduras","Nicarágua","Honduras","Honduras","Honduras","Costa Rica","Panamá","Panamá","Nicarágua","Honduras","Costa Rica","Honduras","Costa Rica","Honduras","Panamá"]
    estadios19 = ["Panama City","Juticalpa","Tegucigalpa","San Pedro Sula","Managua","Estelí","Alanjuela","San José","San Pedro Sula","Tegucigalpa","Juticalpa","Panama City","San José","Alanjuela","Estelí","Managua","Panama City","Juticalpa","Tegucigalpa","San Pedro Sula","Managua","Estelí","Alanjuela","San José","San Pedro Sula","Tegucigalpa","Juticalpa","Panama City","San José","Alanjuela","Estelí","Managua","Panama City","Juticalpa","Tegucigalpa","San Pedro Sula","Managua","Estelí","Alanjuela","San José","San Pedro Sula","Tegucigalpa","Juticalpa","Panama City","San José","Alanjuela","Estelí","Managua","Panama City","Juticalpa","Tegucigalpa","San Pedro Sula","Managua","Estelí","Alanjuela","San José","San Pedro Sula","Tegucigalpa","Juticalpa","Panama City","San José","Alanjuela","Estelí","Managua","Panama City","San Pedro Sula","Managua","Juticalpa","San Pedro Sula","Tegucigalpa","San José","Panama City","Panama City","Managua","San Pedro Sula","San José","San Pedro Sula","San José","Tegucigalpa","Panama City"]
    for i in range(79,159):
        mongo.db.jogos.find_one_and_update({'Ano': 19, 'Jogo': i},{'$set': {'Pais': paises19[i-79],'Estadio': estadios19[i-79]}})

    print("-Ajuste de nomes de competição")
    oldn = ['Copa','Taça ÁSIAOCE','Taça AMÉRICA','Taça EUROPA','Taça ÁFRICA']
    newn = ['Copa do Mundo','Taça Ásia-Oceania','Taça América','Taça Europa','Taça África']
    for i in range(len(oldn)):
        outdb = True
        while outdb:
            outdb = mongo.db.jogos.find_one_and_update({'Competição': oldn[i]},{'$set': {'Competição': newn[i] }})
    
    print("gk18")
    gk18wc = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P']
    for i in range(len(gk18wc)):
        mongo.db.jogos.find_one_and_update({'Ano': 18, 'Jogo': 93+i},{'$set': {'Grupo': gk18wc[i],'Estadio': 'Alemanha','Pais': 'Alemanha'}})
    for i in range(65,81):
        outdb = mongo.db.jogos.find_one_and_update({'Ano': 18, 'Jogo': i},{'$set': {'Estadio': 'Alemanha','Pais': 'Alemanha'}})
    for i in range(141,173):
        outdb = mongo.db.jogos.find_one_and_update({'Ano': 18, 'Jogo': i},{'$set': {'Estadio': 'Alemanha','Pais': 'Alemanha'}})
    conf18a = [65,66,69,70,73,74]
    conf18b = [67,68,71,72,75,76]
    for i in conf18a:
        mongo.db.jogos.find_one_and_update({'Ano': 18, 'Jogo': i},{'$set': {'Grupo': 'A-CONF'}})
    for i in conf18b:
        mongo.db.jogos.find_one_and_update({'Ano': 18, 'Jogo': i},{'$set': {'Grupo': 'B-CONF'}})
    datas18 = ["11/08/2018 10:00","11/08/2018 10:00","11/08/2018 10:00","11/08/2018 10:00","11/08/2018 10:00","11/08/2018 10:00","11/08/2018 10:00","11/08/2018 10:00","12/08/2018 10:00","12/08/2018 10:00","12/08/2018 10:00","12/08/2018 10:00","12/08/2018 10:00","12/08/2018 10:00","12/08/2018 10:00","12/08/2018 10:00","14/08/2018 10:00","14/08/2018 10:00","14/08/2018 10:00","14/08/2018 10:00","14/08/2018 10:00","15/08/2018 10:00","15/08/2018 10:00","15/08/2018 10:00","15/08/2018 10:00","15/08/2018 10:00","15/08/2018 10:00","15/08/2018 10:00","16/08/2018 15:00","16/08/2018 15:00","16/08/2018 15:00","16/08/2018 15:00","16/08/2018 15:00","16/08/2018 15:00","16/08/2018 15:00","17/08/2018 10:00","17/08/2018 10:00","17/08/2018 10:00","17/08/2018 10:00","17/08/2018 10:00","17/08/2018 10:00","17/08/2018 10:00","17/08/2018 10:00","17/08/2018 10:00","17/08/2018 10:00","17/08/2018 10:00","17/08/2018 10:00","18/08/2018 10:00","18/08/2018 10:00","18/08/2018 10:00","18/08/2018 10:00","18/08/2018 10:00","19/08/2018 10:00","19/08/2018 10:00","19/08/2018 10:00","19/08/2018 10:00","19/08/2018 10:00","19/08/2018 10:00","21/08/2018 15:00","21/08/2018 15:00","21/08/2018 15:00","22/08/2018 15:00","22/08/2018 15:00","22/08/2018 15:00","25/08/2018 15:00","26/08/2018 15:00","26/08/2018 15:00","27/08/2018 15:00","29/08/2018 15:00","29/08/2018 15:00","30/08/2018 15:00","30/08/2018 15:00","01/09/2018 15:00","01/09/2018 15:00","02/09/2018 15:00","02/09/2018 15:00","05/09/2018 15:00","06/09/2018 15:00","09/09/2018 15:00","09/09/2018 15:00","11/09/2018 15:00","11/09/2018 15:00","11/09/2018 15:00","11/09/2018 15:00","11/09/2018 15:00","12/09/2018 15:00","12/09/2018 15:00","14/09/2018 15:00","14/09/2018 15:00","14/09/2018 15:00","14/09/2018 15:00","14/09/2018 15:00","19/09/2018 15:00","20/09/2018 11:00","20/09/2018 13:00","20/09/2018 15:00","20/09/2018 09:00","20/09/2018 11:00","20/09/2018 13:00","20/09/2018 15:00","21/09/2018 09:00","21/09/2018 11:00","21/09/2018 13:00","21/09/2018 15:00","22/09/2018 09:00","22/09/2018 11:00","22/09/2018 13:00","22/09/2018 15:00","23/09/2018 09:00","23/09/2018 11:00","23/09/2018 13:00","23/09/2018 15:00","24/09/2018 09:00","24/09/2018 11:00","24/09/2018 13:00","24/09/2018 15:00","25/09/2018 09:00","25/09/2018 11:00","25/09/2018 13:00","25/09/2018 15:00","26/09/2018 09:00","26/09/2018 11:00","26/09/2018 13:00","26/09/2018 15:00","27/09/2018 09:00","27/09/2018 11:00","27/09/2018 13:00","27/09/2018 15:00","28/09/2018 09:00","28/09/2018 11:00","28/09/2018 13:00","28/09/2018 15:00","29/09/2018 09:00","29/09/2018 11:00","29/09/2018 13:00","29/09/2018 15:00","30/09/2018 09:00","30/09/2018 11:00","30/09/2018 13:00","30/09/2018 15:00","01/10/2018 09:00","01/10/2018 11:00","01/10/2018 13:00","01/10/2018 15:00","02/10/2018 09:00","02/10/2018 11:00","02/10/2018 13:00","02/10/2018 15:00","03/10/2018 09:00","03/10/2018 11:00","03/10/2018 13:00","03/10/2018 15:00","04/10/2018 09:00","04/10/2018 11:00","04/10/2018 13:00","04/10/2018 15:00","05/10/2018 11:00","05/10/2018 15:00","06/10/2018 11:00","06/10/2018 15:00","07/10/2018 11:00","07/10/2018 15:00","08/10/2018 11:00","08/10/2018 15:00","11/10/2018 11:00","11/10/2018 15:00","12/10/2018 11:00","12/10/2018 15:00","15/10/2018 15:00","16/10/2018 15:00","19/10/2018 15:00","20/10/2018 15:00"]
    for i in range(172):
        mongo.db.jogos.find_one_and_update({'Ano': 18, 'Jogo': i+1},{'$set': {'Data': datas18[i]}})

    print("gk17")
    datas17 = ["10/05/2018 12:00","11/05/2018 09:00","11/05/2018 12:00","11/05/2018 15:00","12/05/2018 07:00","12/05/2018 10:00","12/05/2018 13:00","12/05/2018 16:00","13/05/2018 09:00","13/05/2018 12:00","13/05/2018 15:00","14/05/2018 09:00","14/05/2018 12:00","14/05/2018 15:00","15/05/2018 09:00","15/05/2018 12:00","15/05/2018 15:00","16/05/2018 09:00","16/05/2018 12:00","16/05/2018 15:00","17/05/2018 09:00","17/05/2018 12:00","17/05/2018 15:00","18/05/2018 09:00","18/05/2018 12:00","18/05/2018 15:00","19/05/2018 09:00","19/05/2018 12:00","19/05/2018 15:00","20/05/2018 09:00","20/05/2018 12:00","20/05/2018 15:00","21/05/2018 11:00","21/05/2018 11:00","21/05/2018 15:00","21/05/2018 15:00","22/05/2018 11:00","22/05/2018 11:00","22/05/2018 15:00","22/05/2018 15:00","23/05/2018 11:00","23/05/2018 11:00","23/05/2018 15:00","23/05/2018 15:00","24/05/2018 11:00","24/05/2018 11:00","24/05/2018 15:00","24/05/2018 15:00","26/05/2018 11:00","26/05/2018 15:00","27/05/2018 11:00","27/05/2018 15:00","28/05/2018 11:00","28/05/2018 15:00","29/05/2018 11:00","29/05/2018 15:00","01/06/2018 11:00","01/06/2018 15:00","02/06/2018 11:00","02/06/2018 15:00","05/06/2018 15:00","06/06/2018 15:00","09/06/2018 11:00","10/06/2018 12:00"]
    for i in range(1,65):
        mongo.db.jogos.find_one_and_update({'Ano': 17, 'Jogo': i},{'$set': {'Data': datas17[i-1],'Estadio': 'Rússia','Pais': 'Rússia'}})
    gk17g = ["A","A","B","B","C","D","C","D","E","F","E","F","G","G","H","H","A","B","A","B","C","C","D","E","D","E","G","F","F","G","H","H","A","A","B","B","C","C","D","D","F","F","E","E","H","H","G","G"]
    for i in range(1,49):
        mongo.db.jogos.find_one_and_update({'Ano': 17, 'Jogo': i},{'$set': {'Grupo': gk17g[i-1]}})

    print("gk16")
    datas16 = ["10/09/2016 10:00","10/09/2016 10:00","10/09/2016 10:00","10/09/2016 10:00","11/09/2016 10:00","11/09/2016 10:00","11/09/2016 10:00","11/09/2016 10:00","13/09/2016 10:00","13/09/2016 10:00","13/09/2016 10:00","13/09/2016 10:00","14/09/2016 10:00","14/09/2016 10:00","14/09/2016 10:00","14/09/2016 10:00","17/09/2016 10:00","17/09/2016 10:00","17/09/2016 10:00","18/09/2016 10:00","18/09/2016 10:00","18/09/2016 10:00","20/09/2016 10:00","20/09/2016 10:00","21/09/2016 10:00","21/09/2016 10:00","21/09/2016 10:00","22/09/2016 10:00","22/09/2016 10:00","24/09/2016 10:00","24/09/2016 10:00","24/09/2016 10:00","24/09/2016 10:00","25/09/2016 10:00","25/09/2016 10:00","25/09/2016 10:00","25/09/2016 10:00","25/09/2016 10:00","01/10/2016 10:00","01/10/2016 10:00","01/10/2016 10:00","01/10/2016 10:00","02/10/2016 10:00","02/10/2016 10:00","02/10/2016 10:00","02/10/2016 10:00","04/10/2016 10:00","04/10/2016 10:00","04/10/2016 10:00","04/10/2016 10:00","05/10/2016 10:00","05/10/2016 10:00","05/10/2016 10:00","05/10/2016 10:00","08/10/2016 10:00","08/10/2016 10:00","08/10/2016 10:00","09/10/2016 10:00","09/10/2016 10:00","09/10/2016 10:00","11/10/2016 10:00","11/10/2016 10:00","12/10/2016 10:00","12/10/2016 10:00","12/10/2016 10:00","13/10/2016 10:00","15/10/2016 10:00","15/10/2016 10:00","15/10/2016 10:00","15/10/2016 10:00","16/10/2016 10:00","16/10/2016 10:00","16/10/2016 10:00","16/10/2016 10:00","16/10/2016 10:00","08/11/2016 00:00","08/11/2016 00:00","08/11/2016 00:00","08/11/2016 00:00","09/11/2016 00:00","09/11/2016 00:00","09/11/2016 00:00","09/11/2016 00:00","10/11/2016 00:00","10/11/2016 00:00","10/11/2016 00:00","11/11/2016 00:00","11/11/2016 00:00","11/11/2016 00:00","12/11/2016 00:00","12/11/2016 00:00","12/11/2016 00:00","12/11/2016 00:00","12/11/2016 00:00","12/11/2016 00:00","13/11/2016 00:00","13/11/2016 00:00","13/11/2016 00:00","13/11/2016 00:00","13/11/2016 00:00","13/11/2016 00:00","15/11/2016 00:00","15/11/2016 00:00","22/10/2016 08:00","23/10/2016 08:00","23/10/2016 08:00","24/10/2016 08:00","26/10/2016 08:00","26/10/2016 08:00","27/10/2016 08:00","27/10/2016 08:00","29/10/2016 08:00","29/10/2016 08:00","30/10/2016 08:00","30/10/2016 08:00","02/11/2016 08:00","03/11/2016 08:00","06/11/2016 08:00","06/11/2016 08:00","25/11/2016 07:00","26/11/2016 01:00","26/11/2016 04:00","26/11/2016 07:00","26/11/2016 10:00","27/11/2016 01:00","27/11/2016 04:00","27/11/2016 07:00","28/11/2016 01:00","28/11/2016 04:00","28/11/2016 07:00","29/11/2016 01:00","29/11/2016 04:00","29/11/2016 07:00","30/11/2016 01:00","30/11/2016 04:00","30/11/2016 07:00","01/12/2016 01:00","01/12/2016 04:00","01/12/2016 07:00","02/12/2016 01:00","02/12/2016 04:00","02/12/2016 07:00","03/12/2016 01:00","03/12/2016 04:00","03/12/2016 07:00","04/12/2016 01:00","04/12/2016 04:00","04/12/2016 07:00","05/12/2016 01:00","05/12/2016 04:00","05/12/2016 07:00","13/12/2016 01:00","13/12/2016 01:00","13/12/2016 05:00","13/12/2016 05:00","14/12/2016 01:00","14/12/2016 01:00","14/12/2016 05:00","14/12/2016 05:00","15/12/2016 01:00","15/12/2016 01:00","15/12/2016 05:00","15/12/2016 05:00","16/12/2016 01:00","16/12/2016 01:00","16/12/2016 05:00","16/12/2016 05:00","17/12/2016 01:00","17/12/2016 05:00","18/12/2016 01:00","18/12/2016 05:00","19/12/2016 01:00","19/12/2016 05:00","20/12/2016 01:00","20/12/2016 05:00","23/12/2016 01:00","23/12/2016 05:00","24/12/2016 01:00","24/12/2016 05:00","27/12/2016 05:00","28/12/2016 05:00","31/12/2016 05:00","01/01/2017 05:00"]
    for i in range(1,104):
        mongo.db.jogos.find_one_and_update({'Ano': 16, 'Jogo': i},{'$set': {'Data': datas16[i-1]}})
    for i in range(104,184):
        mongo.db.jogos.find_one_and_update({'Ano': 16, 'Jogo': i},{'$set': {'Data': datas16[i-1],'Estadio': 'Japão','Pais': 'Japão'}})
    for i in [104,105,108,109,112,113]:
        mongo.db.jogos.find_one_and_update({'Ano': 16, 'Jogo': i},{'$set': {'Grupo': 'A-CONF'}})
    for i in [106,107,110,111,114,115]:
        mongo.db.jogos.find_one_and_update({'Ano': 16, 'Jogo': i},{'$set': {'Grupo': 'B-CONF'}})
    grupos = ["A","A","B","B","C","C","D","D","E","E","F","F","G","G","H","H"]
    i = 120
    for g in grupos+grupos+grupos:
        mongo.db.jogos.find_one_and_update({'Ano': 16, 'Jogo': i},{'$set': {'Grupo': g}})
        i += 1
    
    print("- Limpando base de moedas")
    mongo.db.moedas.drop()
    mongo.db.moedaslog.drop()
    mongo.db.patrocinio.drop()

    print("Finalizado.")

@configCommands.cli.command("migratet")
def migratet():



    print("Finalizado.")