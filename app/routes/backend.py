#import re
#from app.routes.bolao import get_rank, make_score_board, read_config_ranking
#from array import array
from datetime import datetime, time
#from typing import Collection
from flask import Blueprint, app, render_template, session, request, url_for, flash, jsonify
import pymongo
from pymongo import collection
from ..extentions.database import mongo
from ..cache import cache

ANO=21

# Para usar curl: WERKZEUG_DEBUG_PIN=off

backend = Blueprint('backend',__name__)

@cache.memoize(300)
def get_games():
    ano_jogos = [u for u in mongo.db.jogos.find({'Ano': ANO}).sort("Jogo",pymongo.ASCENDING)]
    return ano_jogos

@cache.memoize(3600*2)
def read_config_ranking():
    dbitem = mongo.db.settings.find_one({"config": "ranking"})
    return dbitem.get('edition')

@cache.memoize(3600*24)
def get_rank(time):
    rank_ed = read_config_ranking()
    ranking = mongo.db.ranking.find_one({"ed": rank_ed,"time": time})
    if ranking:
        return ranking['pos']
    else:
        return ""

@cache.memoize(3600)
def get_user_name(username):
    validUser = mongo.db.users.find_one_or_404({"username": username})
    return validUser["name"]

@cache.memoize(3600)
def get_last_pos(user):
    user_last = [u for u in mongo.db.bolao21his.find({"nome": user}).sort("Dia",pymongo.DESCENDING)]
    if user_last:
        last_day = user_last[0].get("posicao")
        if len(user_last) >= 7:
            last_week = user_last[6].get("posicao")
        else:
            last_week = user_last[-1].get("posicao")
        return last_day,last_week
    else:
        return 0,0

# Insert in jogo bets and results foreach user
@cache.memoize(600)
def get_bet_results(users,aposta,jogo):
    peso=int(jogo['peso'])
    for user in users:
        b1 = aposta.get(str(user + "_p1"))
        b2 = aposta.get(str(user + "_p2"))
        if b1 == None or b2 == None:
            aposta_str="-"
            score = 0
        else:
            aposta_str=str(b1)+"x"+str(b2)
            # Caso jogo esta sem resultado ainda
            if jogo['p1'] == "" or jogo['p1'] == None:
                score = 0
            else:
                score = get_score_game(jogo['p1'],jogo['p2'],b1,b2)
        # Score com valor de pontos e valor de pontos*peso
        jogo[user]=[aposta_str,score,score*peso]
    return jogo

@cache.memoize(300)
def get_score_results(users,resultados):
        list_total=[]
        for u in users:
            udict=dict()
            udict["nome"]=u
            udict["score"]=0
            udict["pc"]=0
            last_position_day,last_position_week = get_last_pos(u)
            udict["last_day"] = last_position_day
            udict["last_week"] = last_position_week
            # sum score*peso foreach result
            for r in resultados:
                scores_user = r.get(u)
                if scores_user:
                    udict["score"]+=int(scores_user[2])
                    if scores_user[1] == 5:
                        udict["pc"] += 1 
            list_total.append(udict)
        return list_total

#@backend.route('/api/score_board/<tipo>', methods=['GET'])
@cache.memoize(600)
def make_score_board(tipo):
    now = datetime.now()
    ano_jogos = get_games()
    allUsers = get_users(tipo)
    resultados = []
        
    for jogo in ano_jogos:
        id_jogo = jogo["Jogo"]
        data_jogo = datetime.strptime(jogo["Data"],"%d/%m/%Y %H:%M")
        aposta = get_aposta(id_jogo)
        # If game is old and score not empty
        if data_jogo < now and jogo['p1'] != "":
            jogo_inc = get_bet_results(allUsers,aposta,jogo)
            resultados.append(jogo_inc)
    
    list_total=get_score_results(allUsers,resultados)

    ordered_total = sorted(sorted(list_total, key=lambda k: k['pc'],reverse=True), key=lambda k: k['score'],reverse=True)
    last_score = 0
    last_pc = 0
    last_pos = 1
    #scoreboard = dict()
    for i in range(len(ordered_total)):
        if ordered_total[i]["score"] == last_score and ordered_total[i]["pc"] == last_pc:
            ordered_total[i]["posicao"] = last_pos
        else:
            ordered_total[i]["posicao"] = i+1
            last_score = ordered_total[i]["score"]
            last_pc = ordered_total[i]["pc"]
            last_pos = i+1
    
    return ordered_total

@backend.route('/api/progress_data', methods=['GET'])
@cache.cached(timeout=5*60)
def progress_data():
    ano_jogos = [u for u in mongo.db.jogos.find({'Ano': ANO}).sort("Jogo",pymongo.ASCENDING)]
    progress = dict()
    now = datetime.now()
    progress["last_game"]=0
    progress["total_games"]=64
    progress["game_progress"]=0
    progress["score_progress"]=0
    progress["score_percent"]='0%'
    progress["last_weight"]=0
    progress["total_weight"]=272
    for jogo in ano_jogos:
        data_jogo = datetime.strptime(jogo["Data"],"%d/%m/%Y %H:%M")
        if data_jogo < now and jogo["p1"] != "":
            progress["last_game"]=jogo['Jogo']
            progress["last_weight"]=int(jogo['p_acu'])
        else:
            break
    if progress["last_game"] > 0:
        last_game = ano_jogos[progress["last_game"] - 1]
        p_acu = int(last_game['p_acu'])
        p_acu_total = int(ano_jogos[-1]['p_acu'])
        progress["game_progress"]=int(progress["last_game"]*100/progress["total_games"])
        progress["score_percent"]=last_game['percent']
        progress["score_progress"]=int(p_acu*100/p_acu_total)
    return progress

@cache.memoize(7200)
def get_all_users():
    allUsers = [u.get("name") for u in mongo.db.users.find().sort("name",pymongo.ASCENDING)]
    return allUsers

@cache.memoize(600)
def get_users(tipo):
    if tipo == 'gk':
        allUsers = [u.get("name") for u in mongo.db.users.find({"active": True,"gokopa": True}).sort("name",pymongo.ASCENDING)]
    else:
        allUsers = [u.get("name") for u in mongo.db.users.find({"active": True}).sort("name",pymongo.ASCENDING)]
    return allUsers

@cache.memoize(10)
def get_aposta(id_jogo):
    apostas = mongo.db.apostas21
    return apostas.find_one_or_404({"Jogo": id_jogo})

@cache.memoize(3600*24*7)
def get_score_game(p1,p2,b1,b2):
    score=0
    if p1 == b1 and p2 == b2:
        # Placar cheio
        score = 5
    elif (p1 > p2 and b1 > b2) or (p1 == p2 and b1 == b2) or (p1 < p2 and b1 < b2):
        # Acertou vitoria/empate
        score = 2
        # Ponto extra se saldo igual
        if (p1-p2) == (b1-b2) and (abs(p1-b1) == 1):
            score += 1 
    #print(f'Calculando score para aposta {b1}x{b2} e placar {p1}x{p2}: {score}')
    return score

@backend.route('/api/frequency', methods=['GET'])
#@cache.cached(timeout=3600*24)
def frequency():
    # Setado para frequencia do ano 20
    lista_jogos = mongo.db.jogos.find({'Ano': 20}).sort("Jogo",pymongo.ASCENDING)
    # Array de frequencias de pontuações de 0 a 5
    freq = [0,0,0,0,0,0]
    totalb = 0
    for jogo in lista_jogos:
        idjogo = jogo["Jogo"]
        aposta = mongo.db.apostas20.find_one_or_404({"Jogo": idjogo})
        for user in get_all_users():
            b1 = aposta.get(str(user + "_p1"))
            b2 = aposta.get(str(user + "_p2"))
            if b1 != None and b2 != None:
                if jogo['p1'] != "" or jogo['p1'] != None:
                    score = get_score_game(jogo['p1'],jogo['p2'],b1,b2)
                    freq[score] += 1
                    totalb += 1
    freq1j = [u/totalb for u in freq]
    freq2j = [0 for i in range(11)]
    for i in range(6):
        for j in range(6):
            freq2j[i+j] += freq1j[i]*freq1j[j]
    freq3j = [0 for i in range(16)]
    for i in range(11):
        for j in range(6):
            freq3j[i+j] += freq2j[i]*freq1j[j]
    freq4j = [0 for i in range(21)]
    for i in range(16):
        for j in range(6):
            freq4j[i+j] += freq3j[i]*freq1j[j]
    freq5j = [0 for i in range(26)]
    for i in range(21):
        for j in range(6):
            freq5j[i+j] += freq4j[i]*freq1j[j]
    freq6j = [0 for i in range(31)]
    for i in range(26):
        for j in range(6):
            freq6j[i+j] += freq5j[i]*freq1j[j]
    freq7j = [0 for i in range(36)]
    for i in range(31):
        for j in range(6):
            freq7j[i+j] += freq6j[i]*freq1j[j]
    freq8j = [0 for i in range(41)]
    for i in range(36):
        for j in range(6):
            freq8j[i+j] += freq7j[i]*freq1j[j]

    freqs = {"Frequencias": freq,"Total": totalb, "Freq1j": freq1j, "Freq2j": freq2j, "Freq3j": freq3j, "Freq4j": freq4j, "Freq5j": freq5j, "Freq6j": freq6j, "Freq7j": freq7j, "Freq8j": freq8j}
    return freqs


@backend.route('/api/probability/<tipo>', methods=['GET'])
#@cache.cached(timeout=30*30)
def probability(tipo):
    frequencias = dict(frequency())
    progress = dict(progress_data())
    users = get_users(tipo)
    jogos_restantes = progress["total_games"] - progress["last_game"]
    pontos_restantes = (progress["total_weight"] - progress["last_weight"])*5
    score_board = make_score_board(tipo)
    
    if jogos_restantes > 3:
        freq_array_name = "Freq" + "4" + "j"
    elif jogos_restantes == 0:
        return {"jogos_restantes": jogos_restantes}
    else:
        freq_array_name = "Freq" + str(jogos_restantes) + "j"
    prob_array = frequencias[freq_array_name]

    array_user_prob = []
    parcelas = len(prob_array)-1
    p_acu = []
    p_acu.append(prob_array[0])
    for i in range(1,len(prob_array)):
        p_acu.append(p_acu[i-1]+prob_array[i])
    #for user in users:
    for i in score_board:
        parcelas_u = []
        u_score = i['score']
        user = i['nome']
        #for item in score_board:
        #    if item["nome"] == user:
        #        u_score = item["score"]
        #        break
        for i in range(parcelas+1):
            parcelas_u.append(u_score + i*pontos_restantes/parcelas)
        array_user_prob.append({"user": user,"parcelas": parcelas_u,"score_range": str(int(parcelas_u[0]))+" - "+str(int(parcelas_u[-1]))})
    # Calculo de probs para cada user
    total_users = len(array_user_prob)
    for u in range(total_users):
        prob_vit = 0
        prob_parcela = []
        for i in range(parcelas+1):
            valor_i = array_user_prob[u]["parcelas"][i]
            # Busca cada outro usuario apra calcular prob parcela
            prob_p_i = prob_array[i]
            for uj in range(total_users):
                if uj != u:
                    p_acu_u = 0
                    for j in range(parcelas+1):
                        valor_j = array_user_prob[uj]["parcelas"][j]
                        if valor_i > valor_j:
                            p_acu_u = p_acu[j]
                        elif valor_i == valor_j:
                            p_acu_u += prob_array[j]/2

                    prob_p_i *= p_acu_u
            prob_parcela.append(prob_p_i)
            prob_vit += prob_p_i
        #array_user_prob[u]["prob_parcela"]=prob_parcela
        array_user_prob[u]['prob_vitoria']=round(prob_vit*100,4)

    #prob_vit["users"] = array_user_prob
    now = datetime.strftime(datetime.now(),"%H:%M de %d/%m/%Y")
    return {"jogos_restantes": jogos_restantes, "pontos_restantes": pontos_restantes, "prob_array": prob_array, "users": array_user_prob, "p_acu": p_acu,"atualizado": now}