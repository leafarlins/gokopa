#import re
#from array import array
from datetime import datetime, time
#from typing import Collection
from flask import Blueprint, app, render_template, session, request, url_for, flash, jsonify, current_app
import pymongo
from pymongo import collection
from ..extentions.database import mongo
from ..cache import cache

ANO=22
APOSTADB='apostas2022'

# Para usar curl: WERKZEUG_DEBUG_PIN=off

backend = Blueprint('backend',__name__)

@cache.memoize(300)
def getBolaoUsers(ano):
    if int(ano) == ANO:
        b_users = get_users('gk')
        #print(b_users)
        return b_users
    else:
        b_users = mongo.db.settings.find_one({"config": "bolao_u","ano": int(ano)})
        return b_users["users"]

@cache.memoize(300)
def get_games(ano):
    ano_jogos = [u for u in mongo.db.jogos.find({'Ano': ano}).sort("Jogo",pymongo.ASCENDING)]
    return ano_jogos

@cache.memoize(3600*2)
def read_config_ranking():
    dbitem = mongo.db.settings.find_one({"config": "ranking"})
    return dbitem.get('edition')

@cache.memoize(600)
def get_ranking():
    historic = [u for u in mongo.db.timehistory.find() ]
    ranking = []
    last_game = progress_data()['last_game']
    if last_game >= 75:
        deb = (last_game-74)/129/2
    else:
        deb = 0
    for t in historic:
        time = t['Time']
        u_r = int(t['r21'])
        wcr = int(t['wcr'])
        pts_his = [t['p22'],t['p21'],t['p20'],t['p19'],t['p18'],t['ph']]
        pts_bruto = 5.5*pts_his[0] + (5-deb)*pts_his[1] + (4-deb)*pts_his[2] + (3-deb)*pts_his[3] + (2-deb)*pts_his[4] + (1-deb/2)*pts_his[5]
        wc_pts = int(250*(128-wcr)/127*(128-u_r)/127)
        if pts_bruto > wc_pts:
            pontos = int(pts_bruto+wc_pts)
        else:
            pontos = int(pts_bruto*2)
        ranking.append({
            'time': time,
            'u_pts': int(t['u_pts']),
            'u_r': u_r,
            'd_pts': pontos - int(t['u_pts']),
            'wcr': int(t['wcr']),
            'wc_pts': wc_pts,
            'pts': pts_his,
            'score': pontos
        })
        sorted_ranking = sorted(sorted(ranking,key=lambda k: k['wcr']),key=lambda k: k['score'],reverse=True)
        i = 1
        for item in sorted_ranking:
            item['posicao'] = i
            item['d_r'] = int(item['u_r']) - i
            i += 1
        #lista_users = sorted(lista_users, key=lambda k: k['total'],reverse=True)
    
    return {'ranking': sorted_ranking }

@cache.memoize(300)
def get_rank(time):
    #rank_ed = read_config_ranking()
    ranking = get_ranking()
    for t in ranking['ranking']:
        if t['time'] == time:
            return t
    return ""

@backend.route('/api/get_ranking')
@cache.cached(timeout=3600)
def get_rank_api():
    return get_ranking()

@backend.route('/api/get_ranking/<time>')
@cache.cached(timeout=600)
def get_rank_t_api(time):
    return get_rank(time)

@cache.memoize(3600)
def get_user_name(username):
    validUser = mongo.db.users.find_one_or_404({"username": username})
    return validUser["name"]

@cache.memoize(3600)
def get_last_pos(user,ano):
    basehis = 'bolao' + str(ano) + 'his'
    user_last = [u for u in mongo.db[basehis].find({"nome": user}).sort("Dia",pymongo.DESCENDING)]
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

@cache.memoize(600)
def get_bet_results2(users,aposta,jogo):
    peso=int(jogo['peso'])
    for user in users:
        b1 = aposta.get(str(user + "_p1"))
        b2 = aposta.get(str(user + "_p2"))
        bv = aposta.get(str(user + "_vit"))
        if b1 == None or b2 == None:
            aposta_str="-"
            score = 0
        else:
            aposta_str=str(b1)+"x"+str(b2)
            if b1 == b2:
                if bv == '0':
                    aposta_str='v'+aposta_str
                elif bv== '1':
                    aposta_str=aposta_str+'v'
            # Caso jogo esta sem resultado ainda
            if jogo['p1'] == "" or jogo['p1'] == None:
                score = 0
            else:
                score = get_score_game2(jogo,b1,b2,bv)
        # Score com valor de pontos e valor de pontos*peso
        jogo[user]=[aposta_str,score,score*peso]
    return jogo

@cache.memoize(300)
def get_score_results(users,resultados,ano):
        list_total=[]
        if int(ano) in [22,23]:
            score_full = 10
        else:
            score_full = 5
        for u in users:
            udict=dict()
            udict["nome"]=u
            udict["score"]=0
            udict["pc"]=0
            last_position_day,last_position_week = get_last_pos(u,ano)
            udict["last_day"] = last_position_day
            udict["last_week"] = last_position_week
            # sum score*peso foreach result
            for r in resultados:
                scores_user = r.get(u)
                if scores_user:
                    udict["score"]+=int(scores_user[2])
                    if scores_user[1] == score_full:
                        udict["pc"] += 1 
            list_total.append(udict)
        return list_total

@backend.route('/api/score_board', methods=['GET'])
#@cache.memoize(120)
def make_score_board(ano_score=ANO):
    db_apostas = 'apostas' + str(ano_score)
    now = datetime.now()
    ano_jogos = get_games(ano_score)
    allUsers = getBolaoUsers(ano_score)
    resultados = []
        
    # Calcula caso ano atual
    if ano_score == ANO:
        for jogo in ano_jogos:
            id_jogo = jogo["Jogo"]
            data_jogo = datetime.strptime(jogo["Data"],"%d/%m/%Y %H:%M")
            aposta = get_aposta(id_jogo,db_apostas)
            # If game is old and score not empty
            if data_jogo < now and jogo['p1'] != "":
                if int(ano_score) >= 22:
                    jogo_inc = get_bet_results2(allUsers,aposta,jogo)
                else:
                    jogo_inc = get_bet_results(allUsers,aposta,jogo)
                jogo_inc.pop('_id',None)
                resultados.append(jogo_inc)
        list_total=get_score_results(allUsers,resultados,ano_score)

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
    else:
        basedb = 'bolao' + str(ano_score) + 'his'
        outdb = [u for u in mongo.db[basedb].find().sort('Dia',pymongo.DESCENDING)]
        if outdb:
            ultimo_dia = outdb[0]['Dia']
            lista = [u for u in mongo.db[basedb].find({'Dia': ultimo_dia})]
            ordered_total = sorted(lista, key=lambda k: k['posicao'])
            for i in ordered_total:
                i.pop('_id',None)
        else:
            current_app.logger.error(f"Erro no acesso a base {basedb}")

    return ordered_total

@backend.route('/api/progress_data', methods=['GET'])
#@cache.cached(timeout=5*60)
def progress_data():
    ano_jogos = [u for u in mongo.db.jogos.find({'Ano': ANO}).sort("Jogo",pymongo.ASCENDING)]
    progress = dict()
    now = datetime.now()
    progress["last_game"]=0
    progress["current_game"]=0
    progress["total_games"]=ano_jogos[-1]['Jogo']
    progress["game_progress"]=0
    progress["score_progress"]=0
    progress["score_percent"]='0%'
    progress["last_weight"]=0
    progress["total_weight"]=int(ano_jogos[-1]['p_acu'])
    for jogo in ano_jogos:
        data_jogo = datetime.strptime(jogo["Data"],"%d/%m/%Y %H:%M")
        if data_jogo < now:
            progress["current_game"]=jogo['Jogo']
            if jogo["p1"] != "":
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
        allUsers = [u.get("name") for u in mongo.db.users.find({"active": True,"pago": True}).sort("name",pymongo.ASCENDING)]
    return allUsers

@cache.memoize(10)
def get_aposta(id_jogo,base):
    apostas = mongo.db[base]
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

@cache.memoize(3600*24*7)
def get_score_game2(jogo,b1,b2,bv):
    score=0
    p1 = jogo['p1']
    p2 = jogo['p2']
    #print(p1,p2,b1,b2,bv)
    
    if (p1 > p2 and b1 > b2) or (p1 == p2 and b1 == b2) or (p1 < p2 and b1 < b2):
        # Acertou vitoria/empate
        score = 2
        if jogo.get('Grupo'):
            score += 2
        else:
            if p1 == p2:
                if jogo['pe1'] > jogo['pe2'] and bv == '0':
                    score += 2
                elif jogo['pe1'] < jogo['pe2'] and bv == '1':
                    score += 2
            else:
                score += 2
        # Placar cheio
        if p1 == b1 and p2 == b2:
            score += 6
        # +3 Ponto extra se saldo igual
        if (p1-p2) == (b1-b2) and (abs(p1-b1) == 1):
            score += 3
        # +2 se placar vencedor
        elif (p1 > p2 and b1 == p1 and (abs(p2-b2) == 1)) or (p1 < p2 and b2 == p2 and (abs(p1-b1) == 1)):
            score += 2
        # +1 se saldo igual ou placar derrotado
        elif (p1-p2) == (b1-b2) and (abs(p1-b1) == 2):
            score += 1
        elif (p1 > p2 and b2 == p2 and (abs(p1-b1) == 1)) or (p1 < p2 and b1 == p1 and (abs(p2-b2) == 1)):
            score += 1
    elif not jogo.get('Grupo'):
        if b1 == b2:
            if p1 > p2 and bv == '0':
                score += 2
            elif p1 < p2 and bv == '1':
                score += 2
            elif p1 == p2:
                if jogo['pe1'] > jogo['pe2'] and bv == '0':
                    score += 2
                elif jogo['pe1'] < jogo['pe2'] and bv == '1':
                    score += 2
        elif p1 == p2:
            if jogo['pe1'] > jogo['pe2'] and b1 > b2:
                score += 2
            elif jogo['pe1'] < jogo['pe2'] and b1 < b2:
                score += 2

    #print(f'Calculando score para aposta {b1}x{b2} e placar {p1}x{p2}: {score}')
    return score

@backend.route('/api/frequency', methods=['GET'])
#@cache.cached(timeout=3600*24)
def frequency():
    # Setado para frequencia do ano 20
    lista_jogos = mongo.db.jogos.find({'Ano': 22}).sort("Jogo",pymongo.ASCENDING)
    # Array de frequencias de pontuações de 0 a 10
    freq = [0,0,0,0,0,0,0,0,0,0,0]
    totalb = 0
    # Comentar ate gk22
    freq = [294,0,17,0,57,48,17,34,0,0,28]
    totalb = 495
    # for jogo in lista_jogos:
    #     idjogo = jogo["Jogo"]
    #     aposta = mongo.db.apostas22.find_one_or_404({"Jogo": idjogo})
    #     for user in get_all_users():
    #         b1 = aposta.get(str(user + "_p1"))
    #         b2 = aposta.get(str(user + "_p2"))
    #         vit = aposta.get(str(user + "_vit"))
    #         if b1 != None and b2 != None:
    #             if jogo['p1'] != "" or jogo['p1'] != None:
    #                 score = get_score_game2(jogo,b1,b2,vit)
    #                 freq[score] += 1
    #                 totalb += 1
    freq1j = [u/totalb for u in freq]
    freq2j = [0 for i in range(21)]
    for i in range(11):
        for j in range(11):
            freq2j[i+j] += freq1j[i]*freq1j[j]
    freq3j = [0 for i in range(31)]
    for i in range(21):
        for j in range(11):
            freq3j[i+j] += freq2j[i]*freq1j[j]
    freq4j = [0 for i in range(41)]
    for i in range(31):
        for j in range(11):
            freq4j[i+j] += freq3j[i]*freq1j[j]
    freq5j = [0 for i in range(51)]
    for i in range(41):
        for j in range(11):
            freq5j[i+j] += freq4j[i]*freq1j[j]
    freq6j = [0 for i in range(61)]
    for i in range(51):
        for j in range(11):
            freq6j[i+j] += freq5j[i]*freq1j[j]
    freq7j = [0 for i in range(71)]
    for i in range(61):
        for j in range(11):
            freq7j[i+j] += freq6j[i]*freq1j[j]
    freq8j = [0 for i in range(81)]
    for i in range(71):
        for j in range(11):
            freq8j[i+j] += freq7j[i]*freq1j[j]

    freqs = {"Frequencias": freq,"Total": totalb, "Freq1j": freq1j, "Freq2j": freq2j, "Freq3j": freq3j, "Freq4j": freq4j, "Freq5j": freq5j, "Freq6j": freq6j, "Freq7j": freq7j, "Freq8j": freq8j}
    return freqs


@backend.route('/api/probability', methods=['GET'])
#@cache.cached(timeout=30*30)
def probability():
    frequencias = dict(frequency())
    progress = dict(progress_data())
    users = getBolaoUsers(ANO)
    jogos_restantes = progress["total_games"] - progress["last_game"]
    pontos_restantes = (progress["total_weight"] - progress["last_weight"])*10
    score_board = make_score_board(ANO)
    
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

@backend.route('/api/bet_report', methods=['GET'])
#@cache.cached(timeout=30*30)
def bet_report():
    progresso = progress_data()
    lista_jogos = []
    if progresso['current_game'] < 49 and progresso['current_game'] > 32:
        lista_jid = [progresso['current_game']-1,progresso['current_game']]
    else:
        lista_jid = [progresso['current_game']]
    for l_game in lista_jid:
        l_jogo = mongo.db.jogos.find_one_or_404({"Ano": ANO, "Jogo": l_game})
        bet_results = get_aposta(l_game,APOSTADB)
        apostas = []
        for user in getBolaoUsers(ANO):
            placar1 = str(user) + "_p1"
            placar2 = str(user) + "_p2"
            if bet_results.get(placar1) != None:
                apostas.append(dict({"Nome": user, "p1": bet_results.get(placar1),"p2": bet_results.get(placar2)}))
        lista_jogos.append({"Jogo": l_game, "Data": l_jogo["Data"], "Fase": l_jogo["Competição"] + " " + l_jogo["Fase"], "Time1": l_jogo['Time1'], "Time2": l_jogo['Time2'], "Apostas": apostas})
    return {'reports': lista_jogos}

@backend.route('/api/get_free_teams', methods=['GET'])
#@cache.cached(timeout=30*30)
def get_free_teams():
    lista = [u for u in mongo.db.patrocinio.find({"Patrocinador": "-"}).sort("Valor",pymongo.DESCENDING)]
    lista_livres = []
    for t in lista:
        lista_livres.append({'Time': t["Time"],'Valor': t["Valor"]})
    return {"Livres": lista_livres}

@backend.route('/api/moedas_board')
#@cache.cached(timeout=3*60)
def get_moedas_board():
    moedasDb = [u for u in mongo.db.moedas.find()]
    lista_users = []
    for item in moedasDb:
        saldo = item['saldo']+item['bloqueado']
        total = saldo + item['investido']
        getdb = mongo.db.users.find_one({'name': item['nome']})
        if getdb and getdb['active']:
            lista_users.append({'nome': item['nome'],'saldo': saldo, 'investido': item['investido'],'total': total})
    lista_users = sorted(lista_users, key=lambda k: k['total'],reverse=True)
    p = 1
    last_total = lista_users[0]['total']
    for i in range(len(lista_users)):
        if lista_users[i]['total'] != last_total:
            p = i+1
        lista_users[i]['pos'] = p
        last_total = lista_users[i]['total']


    return {'moedas_board': lista_users}

def moedas_log(nome,moedas,time,jid,msg):
    data = datetime.strftime(datetime.now(),"%d/%m")
    log_id = mongo.db.settings.find_one_and_update({'config':'logid'},{'$inc': {'lid': 1}})
    if log_id:
        lid = log_id['lid']+1
    else:
        current_app.logger.info(f"Iniciando base de Moedaslog")
        lid = 1
        mongo.db.settings.insert_one({'config':'logid','lid': 1})
    log = {
        'nome': nome,
        'moedas': moedas,
        'time': time,
        'msg': msg,
        'data': data,
        'lid': lid,
        'jid': jid
    }
    mongo.db.moedaslog.insert_one(log)
    current_app.logger.info(f"Moedaslog: {log}")


@backend.route('/api/get_next_jogos',methods=['GET'])
def get_next_jogos():
    ano_jogos = mongo.db.jogos.find({'Ano': ANO}).sort([("Jogo",pymongo.ASCENDING)])
    next_jogos = []
    past_jogos = []
    lista_pat = mongo.db.patrocinio
    now = datetime.now()
    for n in ano_jogos:
        if n["Time1"] and n["Time2"]:
            time1 = n['Time1']
            time2 = n['Time2']
            t1 = lista_pat.find_one({'Time': time1})
            t2 = lista_pat.find_one({'Time': time2})
            if t1 and t2:
                proporcao = t1['Valor'] / t2['Valor']
                t1v = t1['Valor']
                t2v = t2['Valor']
                if proporcao < 1:
                    proporcao = t2['Valor'] / t1['Valor']
                if proporcao > 4:
                    percent = 100
                else:
                    percent = int(20*proporcao+20)
                if t2['Valor'] > t1['Valor']:
                    moedas_em_jogo = int(t1['Valor']*percent/100)
                else:
                    moedas_em_jogo = int(t2['Valor']*percent/100)
                #print(t1,t2)
                patdb1 = lista_pat.find_one({'Time': time1})
                patdb2 = lista_pat.find_one({'Time': time2})
                pat1 = patdb1['Patrocinador']
                pat2 = patdb2['Patrocinador']
            else:
                pat1 = "-"
                pat2 = "-"
                moedas_em_jogo = 0
                percent=0
                t1v = 0
                t2v = 0
            jogo = {
                'data': n['Data'],
                'jid' :n['Jogo'],
                'time1': time1,
                'time2': time2,
                'time1_valor': t1v,
                'time2_valor': t2v,
                'percent': percent,
                'moedas_em_jogo': moedas_em_jogo,
                'pat1': pat1, 
                'pat2': pat2 }
            data_jogo = datetime.strptime(n["Data"],"%d/%m/%Y %H:%M")
            if data_jogo < now and n["p1"] != "" :
                if n['p1'] > n['p2']:
                    timevit = time1
                elif n['p1'] < n['p2']:
                    timevit = time2
                else:
                    timevit = 'empate'
                    if n.get("pe1"):
                        if n['pe1'] > n['pe2']:
                            timevit = time1
                        else:
                            timevit = time2
                jogo['p1'] = n['p1']
                jogo['p2'] = n['p2']
                jogo['vitoria'] = timevit
                jogo['processado'] = n.get('processado')
                if n.get('moedas_em_jogo'):
                    jogo['moedas_em_jogo']=n['moedas_em_jogo']
                past_jogos.insert(0,jogo)
            else:
                next_jogos.append(jogo)

    return {'next_jogos': next_jogos, 'past_jogos': past_jogos}

@backend.route('/api/get_pat_teams', methods=['GET'])
@cache.cached(timeout=2)
def get_pat_teams():
    lista = [u for u in mongo.db.patrocinio.find().sort("Valor",pymongo.DESCENDING)]
    lista_pat = []
    lista_livres = []
    lista_leilao = []
    lista_avenda = []
    next_jogos_list = get_next_jogos()
    jogos = next_jogos_list['next_jogos']
    past_jogos = next_jogos_list['past_jogos'][:6]
    for t in lista:
        if t['Patrocinador'] == "-" or t.get('avenda'):
            if t.get('avenda'):
                valor = t.get('avenda')
            else:
                valor = t["Valor"]
            procpatDb = mongo.db.tentarpat.find({'processar': True,'time':t['Time']})
            if procpatDb:
                for item in procpatDb:
                    lista_leilao.append({
                        'time': item['time'],
                        'nome': item['nome'],
                        'valor': item['valor']
                    })
                    valor = item['valor']
            lista_livres.append({'time': t["Time"],'valor': valor})
        if t['Patrocinador'] != "-":
            if jogos:
                busca = True
            else:
                busca = False
            j=0
            apoio_liberado = False
            moedas_do_jogo = 0
            t1 = "-"
            t2 = "-"
            while busca:
                jogo=jogos[j]
                now = datetime.now()
                if jogo['time1'] == t['Time'] or jogo['time2'] == t['Time']:
                    # Se o horario do jogo nao passou, libera apoio
                    if now < datetime.strptime(jogo['data'],"%d/%m/%Y %H:%M"):
                        apoio_liberado = True
                    # Busca em jogos recentes
                    for pastj in past_jogos:
                        if pastj['time1'] == t['Time'] or pastj['time2'] == t['Time']:
                            data = datetime.strptime(pastj['data'],"%d/%m/%Y %H:%M")
                            if datetime.strftime(now,"%d/%m") == datetime.strftime(data,"%d/%m") and now > data:
                                apoio_liberado = False
                                if pastj.get('processado'):
                                    apoio_liberado = True
                    t1 = jogo['time1']
                    t2 = jogo['time2']
                    moedas_do_jogo = jogo['moedas_em_jogo']
                    busca=False
                else:
                    j+=1
                    if j >= len(jogos):
                        busca = False
                        
            timepat = {
                'next_jogo': {'t1': t1,'t2':t2},
                'patrocinador': t['Patrocinador'],
                'time': t["Time"],
                'valor': t["Valor"],
                'avenda': t.get('avenda'),
                'apoiadores': t.get('Apoiadores'),
                'moedas_em_jogo': moedas_do_jogo,
                'apoio_liberado': apoio_liberado
            }
            if t.get('avenda'):
                lista_avenda.append(timepat)
            lista_pat.append(timepat)
        
    return {"livres": lista_livres, "patrocinados": lista_pat, 'lista_leilao': lista_leilao,'lista_avenda': lista_avenda}