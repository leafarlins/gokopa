from app.routes.bolao import get_rank, make_score_board, read_config_ranking
from array import array
from datetime import datetime, time
from typing import Collection
from flask import Blueprint, app, render_template, session, request, url_for, flash
import pymongo
from pymongo import collection
from werkzeug.utils import redirect
from werkzeug.security import check_password_hash
from ..extentions.database import mongo
from ..cache import cache

#current_app para carregar app.py

gokopa = Blueprint('gokopa',__name__)

ANO=20

@cache.memoize(600)
def get_classificados():
    lista = [u for u in mongo.db.pot.find({'Ano': ANO})]
    #print("lista",lista)
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
    #print(lista_final)
    return lista_final

# Rota / associada a função index
@gokopa.route('/')
@cache.cached(timeout=60*60)
def index():
    #past_jogos = [u for u in mongo.db.jogos.find({'Ano': 19}).sort([('Jogo',pymongo.DESCENDING)])]
    past_jogos=[]
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

    lista_bolao = make_score_board()
    #pot_table = get_tabela_pot()

    tabelas_label = ['A','B','C','D','E','F','G','H']
    tabelas = get_tabelas_copa()
    return render_template("inicio.html",menu="Home",past_jogos=past_jogos[:20],next_jogos=next_jogos[:20],classificados=classificados,total=lista_bolao,tabelas=tabelas,labels=tabelas_label)


@cache.memoize(300)
def get_jogos_tab(ano,r1):
    return mongo.db.jogos.find({'Ano': ano, "Jogo": {'$gt': r1 }}).sort([("Jogo",pymongo.ASCENDING)])

# Alterar para 4 durante sorteio
@cache.memoize(3600*24*30)
def get_team_table(descx,desc,timex):
    return mongo.db.jogos.find_one({"Ano": 20, descx: desc}).get(timex)

@cache.memoize(300)
def get_ano20_games():
    ano20_games = [u for u in mongo.db.jogos.find({'Ano': 20, "Jogo": {'$gt': 20 }}).sort("Jogo",pymongo.ASCENDING)]
    now = datetime.now()

    # Zera placares caso seja futuro
    for j in ano20_games:
        data_jogo = datetime.strptime(j.get("Data"),"%d/%m/%Y %H:%M")
        if data_jogo > now:
            j['p1'] = ""
            j['p2'] = ""
    
    return ano20_games

@gokopa.route('/tabela')
@cache.cached(timeout=180)
def tabela():
    ano20_jogos = get_ano20_games()
    tabelas_label = ['A-EUR','B-EUR','C-EUR','D-EUR','E-EUR','F-EUR','G-EUR','H-EUR','A-AFR','B-AFR','C-AFR','D-AFR','A-ASO','B-ASO','C-ASO','D-ASO','A-AME','B-AME','C-AME','D-AME','A','B','C','D','E','F','G','H']
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
    # Add games id for copa
    jogos_id.append([100,101,116,118,132,133])
    jogos_id.append([102,103,117,119,134,135])
    jogos_id.append([104,106,120,121,136,137])
    jogos_id.append([105,107,122,124,138,139])
    jogos_id.append([108,110,123,125,142,143])
    jogos_id.append([109,111,127,128,140,141])
    jogos_id.append([112,113,126,129,146,147])
    jogos_id.append([114,115,130,131,144,145])

    # Tabelas para campeonatos regionais
    for i in range(28):
        desc1 = "p" + str(1) + tabelas_label[i]
        desc2 = "p" + str(2) + tabelas_label[i]
        desc3 = "p" + str(3) + tabelas_label[i]
        time1 = get_team_table('desc1',desc1,'Time1')
        time2 = get_team_table('desc1',desc2,'Time1')
        time3 = get_team_table('desc2',desc3,'Time2')
        times = [time1,time2,time3]
        descs = [desc1,desc2,desc3]
        # If i>20, tables for copa
        if i >= 20:
            desc4 = "p" + str(4) + tabelas_label[i]
            time4 = get_team_table('desc2',desc4,'Time2')
            descs.append(desc4)
            times.append(time4)
        for j in range(len(times)):
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
                            #print("Calculando para jogo ",ano20_jogos[jid])
                            if p1 == p2:
                                if linha['nome'] == ano20_jogos[jid].get('Time1') or linha['nome'] == ano20_jogos[jid].get('Time2'):
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
                linha['nome'] = descs[j]
                #tab.update({'nome': desc})
            tabelas.append(linha)

    return render_template('tabela20reg.html',menu="Tabela",tabelas=tabelas,labels=tabelas_label,lista_jogos=ano20_jogos,jogos_id=jogos_id)

@cache.memoize(3600*24*7)
def get_historic_copa(comp):
    if comp == 'tacas':
        historia = [u for u in mongo.db.historico.find({"comp": { '$in': [ "tacaame", "tacaeur", "tacaaso", "tacaafr" ] }}).sort('Ano',pymongo.DESCENDING)]
    else:
        historia = [u for u in mongo.db.historico.find({"comp": comp}).sort('Ano',pymongo.DESCENDING)]
    times = set()
    medal_count = []
    for h in historia:
        times.add(h['ouro'])
        times.add(h['prata'])
        times.add(h['bronze'])
    for t in times:
        time = dict()
        time['nome'] = t
        time['ouro'] = 0
        time['prata'] = 0
        time['bronze'] = 0
        for l in historia:
            if t == l['ouro']:
                time['ouro'] += 1
            if t == l['prata']:
                time['prata'] += 1
            if t == l['bronze']:
                time['bronze'] += 1
        time['total'] = time['ouro'] + time['prata'] + time['bronze']
        medal_count.append(time)

    #print(medal_count)
    return historia,medal_count

@gokopa.route('/ranking')
@cache.cached(timeout=3600*24)
def ranking():
    rank_ed = read_config_ranking()
    ranking = [u for u in mongo.db.ranking.find({"ed": rank_ed}).sort('pos',pymongo.ASCENDING)]
    copas_list,copas_medal = get_historic_copa("copa")
    taca_list,taca_medal = get_historic_copa("taca")
    bet_list,bet_medals = get_historic_copa("bet")
    tacas_list,tacas_medals = get_historic_copa("tacas")
    return render_template("ranking.html",menu="Ranking",ranking=ranking,rank_ed=rank_ed,copa_his=copas_list,copa_med=copas_medal,bet_his=bet_list,bet_med=bet_medals,taca_his=taca_list,taca_med=taca_medal,tacas_his=tacas_list,tacas_med=tacas_medals)

@cache.memoize(3600*24)
def get_team_list():
    rank_ed = read_config_ranking()
    ranking = [u['time'] for u in mongo.db.ranking.find({"ed": rank_ed}).sort('pos',pymongo.ASCENDING)]
    return ranking

@cache.memoize(3600*24*7)
def return_historic_duels(team1,team2):
    ano_max_game = 134
    historico_total = [u for u in mongo.db.jogos.find({ '$or': [{'Time1': team1,'Time2': team2 },{'Time1': team2,'Time2': team1 }],"Ano": {'$lt':20} }).sort([("Ano",pymongo.DESCENDING),("Jogo",pymongo.DESCENDING)])]
    historico_a20 = [u for u in mongo.db.jogos.find({ '$or': [{'Time1': team1,'Time2': team2 },{'Time1': team2,'Time2': team1 }],"Ano": 20, "Jogo": {'$lt':ano_max_game} }).sort([("Ano",pymongo.DESCENDING),("Jogo",pymongo.ASCENDING)])]
    for obj in historico_a20:
        historico_total.insert(0,obj)

    print(historico_total)
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

def get_tabela_pot():
    tabela_pot = []
    for i in range(4):
        times = []
        times_pot = [u for u in mongo.db.pot.find({"Ano": ANO,"pot": int(i+1)}).sort('nome',pymongo.ASCENDING)]
        tabela_pot.append(times_pot)
    #print(tabela_pot)

    pot_trans = []
    for i in range(10):
        pot_trans.append([dict(),dict(),dict(),dict()])
    #print(pot_trans)
    for i in range(10):
        for j in range(4):
            #print("pegando",tabela_pot[i][j])
            if len(tabela_pot[j]) > i:
                #print("pegando",tabela_pot[j][i])
                time = tabela_pot[j][i]
                time['rank'] = get_rank(time['nome'])
                pot_trans[i][j] = time
    return pot_trans

def get_tabelas_copa():
    tabelas_label = ['A','B','C','D','E','F','G','H']
    tabelas = []
    # Tabelas para campeonatos regionais
    for i in range(8):
        desc1 = "p" + str(1) + tabelas_label[i]
        desc2 = "p" + str(2) + tabelas_label[i]
        desc3 = "p" + str(3) + tabelas_label[i]
        time1 = get_team_table('desc1',desc1,'Time1')
        time2 = get_team_table('desc1',desc2,'Time1')
        time3 = get_team_table('desc2',desc3,'Time2')
        desc4 = "p" + str(4) + tabelas_label[i]
        time4 = get_team_table('desc2',desc4,'Time2')
        times = [time1,time2,time3,time4]
        descs = [desc1,desc2,desc3,desc4]
        for j in range(len(times)):
            linha = dict()
            if times[j]:
                linha['nome'] = times[j]
                linha['rank'] = get_rank(times[j])
            else:
                linha['nome'] = descs[j]
                #tab.update({'nome': desc})
            tabelas.append(linha)

    return tabelas


@gokopa.route('/sorteio')
@cache.cached(timeout=3600*24*30)
def sorteio_page():
    tabelas_label = ['A','B','C','D','E','F','G','H']
    tabelas = get_tabelas_copa()
    
    # Tabela de pots
    pot_table = get_tabela_pot()
    #print(pot_trans)

    highlightdb = mongo.db.settings.find_one({"config":"highlight"})
    if highlightdb:
        highlight = highlightdb['time']
    else:
        highlight = "nenhum"

    return render_template('sorteio.html',menu='Home',labels=tabelas_label,tabelas=tabelas,tabela_pot=pot_table,hlt=highlight)