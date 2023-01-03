import re
from app.routes.backend import progress_data,get_aposta,get_score_game,get_rank, make_score_board,read_config_ranking,probability,get_ranking
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

ANO=22

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

# @gokopa.route('/')
# @cache.cached(timeout=5*60)
# def home():
#     if re.match('.*gokopa.leafarlins',request.url_root):
#         return redirect(url_for('gokopa.index',tipo='gk'))
#     else:
#         return redirect(url_for('gokopa.index',tipo='cp'))

# Rota / associada a função index
@gokopa.route('/')
@cache.cached(timeout=2*60)
def index():
    past_jogos = [u for u in mongo.db.jogos.find({'Ano': 21}).sort([('Jogo',pymongo.DESCENDING)])]
    #past_jogos=[]
    ano_jogos = mongo.db.jogos.find({'Ano': ANO}).sort([("Jogo",pymongo.ASCENDING)])
    next_jogos = []

    classificados = get_classificados()
    
    now = datetime.now()
    for n in ano_jogos:
        if n["Time1"] and n["Time2"]:

            data_jogo = datetime.strptime(n["Data"],"%d/%m/%Y %H:%M")
            if data_jogo < now and n["p1"] != "" :
                past_jogos.insert(0,n)
            else:
                next_jogos.append(n)

    lista_bolao = make_score_board(ANO)
    #pot_table = get_tabela_pot()


    #tabelas_label = ['A','B','C','D','E','F','G','H']
    #tabelas = get_tabelas_copa()
    return render_template("inicio.html",menu="Home",past_jogos=past_jogos[:20],next_jogos=next_jogos[:20],classificados=classificados,total=lista_bolao,progress_data=progress_data(),probabilidade=probability())


@cache.memoize(300)
def get_jogos_tab(ano,r1):
    return mongo.db.jogos.find({'Ano': ano, "Jogo": {'$gt': r1 }}).sort([("Jogo",pymongo.ASCENDING)])

# Alterar para 4 durante sorteio
@cache.memoize(3600*24*30)
def get_team_table(descx,desc,timex):
    return mongo.db.jogos.find_one({"Ano": ANO, descx: desc}).get(timex)

@cache.memoize(20)
def get_anoX_games(ano,indx):
    anoX_games = [u for u in mongo.db.jogos.find({'Ano': ano, "Jogo": {'$gt': indx }}).sort("Jogo",pymongo.ASCENDING)]
    now = datetime.now()

    # Zera placares caso seja futuro
    for j in anoX_games:
        data_jogo = datetime.strptime(j.get("Data"),"%d/%m/%Y %H:%M")
        if data_jogo > now:
            j['p1'] = ""
            j['p2'] = ""
    
    return anoX_games

@gokopa.route('/api/get_tabela<ano>')
def gerar_tabela(ano):
    ano_jogos = get_anoX_games(int(ano),0)
    # Temporario copa do Qatar
    if ano == '2022':
        ano_jogos[0]['Time1'] = 'Qatar'
        ano_jogos[17]['Time1'] = 'Qatar'
        ano_jogos[32]['Time1'] = 'Qatar'
    descs = {
        '2022': 'Este é a tabela da Copa do Mundo de 2022, no Qatar.',
        '22': 'O ano 22 terá taças regionais, classificando para as finais das taças e para a gokopa de 48 times. A maior gokopa de todos os tempos até aqui, com 104 jogos em 12 grupos de 4.',
        '21': 'O ano 21 é a Gokopa simulada em homenagem à Copa do Mundo de 2022, com a mesma tabela.',
        '20': 'Ano 20 com taças regionais e Copa do Mundo versão 32 times.',
        '19': 'Gokopa do Mundo com versão 48 times na América Central, 4 países, maior número de sedes até então.',
        '18': 'Primeira Gokopa do Mundo com versão 48 times em 16 grupos de 3, na Alemanha.',
        '17': 'Edição especial na Rússia, com a tabela da Copa do Mundo 2018.',
        '16': 'Gokopa do Mundo 16, no Japão.'
    }
    # Lista de competições válidas para montar grupos
    comp_valida = ['Copa do Mundo','Taça Mundial','Taça Ásia-Oceania','Taça América','Taça Europa','Taça África','Confederações']
    fase_valida = ['16-avos-de-final','8vas-de-final','4as-de-final','Semi-final','D. 3º Lugar','Final']
    # Lista inicial de competição para formar grupos
    competicao = {
        'Copa do Mundo': {
            'grupos': {},
            'eliminatorias': {}
        }
    }
    outros = []

    for j in ano_jogos:
        j.pop('_id',None)
        if not j['Time1']:
            j['Time1'] = j['desc1']
        if not j['Time2']:
            j['Time2'] = j['desc2']
        if j['Competição'] in comp_valida:
            torneio = j['Competição']
            if not competicao.get(torneio):
                competicao[torneio] = {
                    'grupos': {},
                    'eliminatorias': {}
                }
            if j.get('Grupo'):
                grupoj = j.get('Grupo')
                if not competicao[torneio]['grupos'].get(grupoj):
                    competicao[torneio]['grupos'][grupoj] = {}
                    competicao[torneio]['grupos'][grupoj]['jogos'] = []
                    competicao[torneio]['grupos'][grupoj]['tabela'] = {}
                    competicao[torneio]['grupos'][grupoj]['tabela']['times'] = []
                    competicao[torneio]['grupos'][grupoj]['tabela']['pontos'] = {}
                competicao[torneio]['grupos'][grupoj]['jogos'].append(j)
                if j['Time1'] not in competicao[torneio]['grupos'][grupoj]['tabela']['times']:
                    competicao[torneio]['grupos'][grupoj]['tabela']['times'].append(j['Time1'])
                    competicao[torneio]['grupos'][grupoj]['tabela']['pontos'][j['Time1']] = [0,0,0]
                if j['Time2'] not in competicao[torneio]['grupos'][grupoj]['tabela']['times']:
                    competicao[torneio]['grupos'][grupoj]['tabela']['times'].append(j['Time2'])
                    competicao[torneio]['grupos'][grupoj]['tabela']['pontos'][j['Time2']] = [0,0,0]
                if j['p1'] == 0 or (j['p1'] != None and j['p1']):
                    p1 = int(j['p1'])
                    p2 = int(j['p2'])
                    competicao[torneio]['grupos'][grupoj]['tabela']['pontos'][j['Time1']][1] += p1 - p2
                    competicao[torneio]['grupos'][grupoj]['tabela']['pontos'][j['Time1']][2] += p1
                    competicao[torneio]['grupos'][grupoj]['tabela']['pontos'][j['Time2']][1] += p2 - p1
                    competicao[torneio]['grupos'][grupoj]['tabela']['pontos'][j['Time2']][2] += p2
                    if p1 > p2:
                        competicao[torneio]['grupos'][grupoj]['tabela']['pontos'][j['Time1']][0] += 3
                    elif p1 == p2:
                        competicao[torneio]['grupos'][grupoj]['tabela']['pontos'][j['Time1']][0] += 1
                        competicao[torneio]['grupos'][grupoj]['tabela']['pontos'][j['Time2']][0] += 1
                    else:
                        competicao[torneio]['grupos'][grupoj]['tabela']['pontos'][j['Time2']][0] += 3
            else:
                fase = j['Fase']
                if fase not in fase_valida:
                    fase = 'outros'
                if not competicao[torneio]['eliminatorias'].get(fase):
                    competicao[torneio]['eliminatorias'][fase] = {}
                    competicao[torneio]['eliminatorias'][fase]['jogos'] = []
                competicao[torneio]['eliminatorias'][fase]['jogos'].append(j)
        else:
            outros.append(j)

    return {
        'ano': ano,
        'desc':  descs[ano],
        'competicao': competicao,
        'tacas': "",
        'outros': outros
    }            

@gokopa.route('/tabela<ano>')
#@cache.cached(timeout=60*2)
def tabelaano(ano):
    if ano not in ['2022'] and int(ano) not in range(16,23):
        flash(f'Tabela do ano {ano} não disponível.','danger')
        ano = '22'
    dados = gerar_tabela(ano)
    return render_template('tabela.html',menu="Tabela",dados=dados)

@gokopa.route('/tabelahis')
@cache.memoize(3600*720)
def tabela_his():
    fase_final = []
    for i in range(21):
        jogos = [u for u in mongo.db.jogos.find({"Ano": i+1, "Competição": "Copa do Mundo", '$or': [{"Fase": "8vas-de-final"},{"Fase": "4as-de-final"},{"Fase": "Semi-final"},{"Fase": "D. 3º Lugar"},{"Fase": "Final"}]}).sort('Jogo',pymongo.ASCENDING)]
        if i == 0:
            jogos = [0,0,0,0,0,0,0,0] + jogos
        fase_final.append(jogos)
        #print(f'Add ano {i+1}: {jogos}')
    return render_template('tabelahis.html',menu="Tabela",lista_jogos=fase_final)

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
        if comp == 'tacas':
            times.add(h['quarto'])
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
            if comp == 'tacas':
                if t == l['quarto']:
                    time['bronze'] += 1
        time['total'] = time['ouro'] + time['prata'] + time['bronze']
        medal_count.append(time)

    #print(medal_count)
    return historia,medal_count

@gokopa.route('/ranking')
#@cache.cached(timeout=600)
def ranking():
    #rank_ed = read_config_ranking()
    #ranking = [u for u in mongo.db.ranking.find({"ed": rank_ed}).sort('pos',pymongo.ASCENDING)]
    ranking = get_ranking()
    copas_list,copas_medal = get_historic_copa("copa")
    taca_list,taca_medal = get_historic_copa("taca")
    bet_list,bet_medals = get_historic_copa("bet")
    tacas_list,tacas_medals = get_historic_copa("tacas")
    return render_template("ranking.html",menu="Ranking",ranking=ranking,copa_his=copas_list,copa_med=copas_medal,bet_his=bet_list,bet_med=bet_medals,taca_his=taca_list,taca_med=taca_medal,tacas_his=tacas_list,tacas_med=tacas_medals)

@cache.memoize(3600*24)
def get_team_list():
    rank_ed = read_config_ranking()
    ranking = [u['time'] for u in mongo.db.ranking.find({"ed": rank_ed}).sort('pos',pymongo.ASCENDING)]
    return ranking

@cache.memoize(3600*24*7)
def return_historic_duels(team1,team2):
    ano_max_game = 134
    historico_total = [u for u in mongo.db.jogos.find({ '$or': [{'Time1': team1,'Time2': team2 },{'Time1': team2,'Time2': team1 }],"Ano": {'$lt':22} }).sort([("Ano",pymongo.DESCENDING),("Jogo",pymongo.DESCENDING)])]
    #historico_a20 = [u for u in mongo.db.jogos.find({ '$or': [{'Time1': team1,'Time2': team2 },{'Time1': team2,'Time2': team1 }],"Ano": 20, "Jogo": {'$lt':ano_max_game} }).sort([("Ano",pymongo.DESCENDING),("Jogo",pymongo.ASCENDING)])]
    #for obj in historico_a20:
    #    historico_total.insert(0,obj)

    #print(historico_total)
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

@cache.memoize(3600*2)
def return_team_history(team1):
    historia = mongo.db.timehistory.find_one({'Time': team1})
    pos_copa = []
    pos_rank = []
    for i in range(21):
        copa = "c" + str(i+1)
        rank = "r" + str(i+1)
        pos_copa.append(historia[copa])
        if historia[rank] == "-":
            pos_rank.append('null')
        else:
            pos_rank.append(int(historia[rank]))
    # Add current rank
    pos_copa.append('?')
    pos_rank.append(get_rank(team1)['posicao'])
    print(pos_copa,pos_rank)
    return pos_copa,pos_rank

@gokopa.route('/historico',methods=["GET","POST"])
def historico():
    time_1 = dict()
    time_2 = dict()
    if request.method == "POST":
        time_1["nome"] = request.values.get("time1")
        time_2["nome"] = request.values.get("time2")
        #times = [time1,time2]
        lista_jogos,vev = return_historic_duels(time_1["nome"],time_2["nome"])
        time_1["hc"],time_1["hr"] = return_team_history(time_1["nome"])
        time_2["hc"],time_2["hr"] = return_team_history(time_2["nome"])
    else:
        lista_jogos = []
        vev=[]
        #time1=""
    print(f"lista_jogos={lista_jogos},vev={vev},time1={time_1},time2={time_2},lista_times=get_team_list()")
    return render_template('historico.html',menu='Historico',lista_jogos=lista_jogos,vev=vev,time1=time_1,time2=time_2,lista_times=get_team_list())

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
