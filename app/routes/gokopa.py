import re
from app.routes.backend import get_next_jogos, get_user_name, progress_data,get_aposta,get_score_game,get_rank, make_score_board,read_config_ranking,probability,get_ranking
from array import array
from datetime import datetime, time
from typing import Collection
from flask import Blueprint, current_app, render_template, session, request, url_for, flash
import pymongo
from pymongo import collection
from werkzeug.utils import redirect
from werkzeug.security import check_password_hash
from ..extentions.database import mongo
from ..cache import cache

#current_app para carregar app.py

gokopa = Blueprint('gokopa',__name__)

ANO=24

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


@gokopa.route('/api/get_news<anon>')
#@cache.cached(timeout=2*60)
def getNews(anon=str(ANO)):
    news_do_ano = [u for u in mongo.db.news.find({'ano':int(anon)}).sort('nid',pymongo.DESCENDING)]
    if len(news_do_ano) < 6:
        newsold = [u for u in mongo.db.news.find({'ano':int(anon)-1}).sort('nid',pymongo.DESCENDING)]
        news = news_do_ano + newsold[0:6]
    else:
        news = news_do_ano
    for u in news:
        u.pop('_id',None)
        u['texto'] = u['texto'].replace('\\n','<br/>')
    return {'news': news}

@gokopa.route('/')
@cache.cached(timeout=2*60)
def index():
    past_jogos = [u for u in mongo.db.jogos.find({'Ano': ANO-1}).sort([('Jogo',pymongo.DESCENDING)])]
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
    
    return render_template("inicio.html",menu="Home",past_jogos=past_jogos[:21],next_jogos=next_jogos[:15],classificados=classificados,total=lista_bolao,progress_data=progress_data(),probabilidade=probability(),news=getNews()['news'][:6])

@gokopa.route('/noticias<anon>')
@cache.cached(timeout=2*60)
def noticias(anon):
    return render_template("news.html",menu="Gokopa",news=getNews(anon))

@cache.memoize(300)
def get_jogos_tab(ano,r1):
    return mongo.db.jogos.find({'Ano': ano, "Jogo": {'$gt': r1 }}).sort([("Jogo",pymongo.ASCENDING)])

# Alterar para 4 durante sorteio
@cache.memoize(3600*24*30)
def get_team_table(descx,desc,timex):
    return mongo.db.jogos.find_one({"Ano": ANO, descx: desc}).get(timex)

@cache.memoize(20)
def get_anoX_games(ano,indi,indf):
    if indf > 0:
        search_criteria = {'$gte': indi ,'$lte': indf}
    else:
        search_criteria = {'$gte': indi }
    anoX_games = [u for u in mongo.db.jogos.find({'Ano': ano, "Jogo": search_criteria}).sort("Jogo",pymongo.ASCENDING)]
    now = datetime.now()

    # Zera placares caso seja futuro
    for j in anoX_games:
        j.pop('_id')
        try:
            data_jogo = datetime.strptime(j.get("Data"),"%d/%m/%Y %H:%M")
        except:
            current_app.logger.error(f"Erro na leitura do jogo {j}")
        else:
            if data_jogo > now:
                j['p1'] = ""
                j['p2'] = ""
                j['tr1'] = ""
                j['tr2'] = ""
    
    return anoX_games

@gokopa.route('/api/get_tabela<ano>')
def gerar_tabela(ano):
    ano_jogos = get_anoX_games(int(ano),0,0)
    # Temporario copa do Qatar
    if ano == '2022':
        ano_jogos[0]['Time1'] = 'Qatar'
        ano_jogos[17]['Time1'] = 'Qatar'
        ano_jogos[32]['Time1'] = 'Qatar'
    descs = {
        '2022': 'Esta é a tabela da Copa do Mundo de 2022, no Qatar.',
        '24': 'O ano 24 será ao redor do Nilo, no Egito e no Sudão. A mesma tabela da temporada anterior, com taças regionais, taça mundial e a copa de 48 times.',
        '23': 'O ano 23 será no Caribe, com mesma sequência do ano anterior: taças regionais, classificando para as finais das taças e para a gokopa de 48 times. Mais um recorde de jogos, com 212 na temporada.',
        '22': 'O ano 22 terá taças regionais, classificando para as finais das taças e para a gokopa de 48 times. A maior gokopa de todos os tempos até aqui, com 104 jogos em 12 grupos de 4.',
        '21': 'O ano 21 é a Gokopa simulada em homenagem à Copa do Mundo de 2022, com a mesma tabela.',
        '20': 'Ano 20 com taças regionais e Copa do Mundo versão 32 times.',
        '19': 'Gokopa do Mundo com versão 48 times na América Central, em 4 países, maior número de sedes até então.',
        '18': 'Primeira Gokopa do Mundo com versão 48 times em 16 grupos de 3, na Alemanha.',
        '17': 'Edição especial na Rússia, com a tabela da Copa do Mundo 2018.',
        '16': 'Gokopa do Mundo 16, no Japão.',
        '15': 'Edição especial no Brasil, com a tabela da Copa do Mundo de 2014.',
        '14': 'Gokopa 14 na península ibérica, Portugal e Espanha.',
        '13': 'Gokopa no México, com primeiro evento de Taças Regionais e Taça Mundial em seguida.',
        '12': '12ª edição da copa, na Italia.',
        '11': 'Gokopa 11 na Venezuela, com Copa dos Reis. A partir dessa copa, é utilizado o jogo Fifa Copa do Mundo 2006 como simulador.',
        '10': 'Gokopa 10 na Noruega. Primeiro ano de Taça Mundial.',
        '9': 'Gokopa 9 na Nigéria, e Confederações.',
        '8': 'Gokopa 8 na Inglaterra, com Copa dos Reis.',
        '7': 'Gokopa 7 nos Estados Unidos.',
        '6': 'Gokopa 6 na Áustria, e Confederações.',
        '5': 'Gokopa 5 na Ucrânia, e Copa dos Reis com 10 times e quadrangular final.',
        '4': 'Gokopa 4 no Japão.',
        '3': 'Gokopa 3 na Austrália. A partir dessa edição a Copa passa a ter 32 times. Temos ainda a primeira edição das Confederações, com os melhores de cada uma.',
        '2': 'Gokopa 2 se expande para 24 times, no País de Gales. Temos ainda a primeira edição da Copa dos Reis com os top8 do ano.',
        '1': 'Gokopa 1 no Chile, a primeira de todas, com 16 times.'
    }
    # Lista de competições válidas para montar grupos
    comp_valida = ['Copa do Mundo','Taça Mundial','Taça Ásia-Oceania','Taça América','Taça Europa','Taça África','Confederações','Reis']
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
                    trank = get_rank(j['Time1'])
                    if trank:
                        time_rank = trank['posicao']
                    else:
                        time_rank = "-"
                    competicao[torneio]['grupos'][grupoj]['tabela']['pontos'][j['Time1']] = [0,0,0,time_rank]
                if j['Time2'] not in competicao[torneio]['grupos'][grupoj]['tabela']['times']:
                    competicao[torneio]['grupos'][grupoj]['tabela']['times'].append(j['Time2'])
                    trank = get_rank(j['Time2'])
                    if trank:
                        time_rank = trank['posicao']
                    else:
                        time_rank = "-"
                    competicao[torneio]['grupos'][grupoj]['tabela']['pontos'][j['Time2']] = [0,0,0,time_rank]
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
    if ano == str(ANO):
        last_game = progress_data()['last_game']
        for torneio in competicao:
            adicionar = False
            if torneio == 'Copa do Mundo' and last_game > 108 and last_game < 209:
                adicionar = True
            elif torneio != 'Copa do Mundo' and last_game > 1 and last_game < 91:
                adicionar = True
            if adicionar:
                classificados = {
                    'grupos': []
                }
                dono_casa = "Sudão"
                torneio_sede = "Taça África"
                for g in competicao[torneio]['grupos']:
                    #sorted(g, key=lambda k: k['pc'],reverse=True))
                    times = []
                    for i in range(len(competicao[torneio]['grupos'][g]['tabela']['times'])):
                        time = competicao[torneio]['grupos'][g]['tabela']['times'][i]
                        if time == dono_casa and last_game < 109:
                            cor_time = 'copa'
                        else:
                            cor_time = 'des'
                        newt = {
                            'time': time,
                            'pts': competicao[torneio]['grupos'][g]['tabela']['pontos'][time][0],
                            'sal': competicao[torneio]['grupos'][g]['tabela']['pontos'][time][1],
                            'gol': competicao[torneio]['grupos'][g]['tabela']['pontos'][time][2],
                            'rnk': get_rank(time)['posicao'],
                            'cor': cor_time
                        }
                        times.append(newt)
                    grupo = {
                        'nome': g,
                        'times': sorted(sorted(sorted(sorted(times, key=lambda k: k['rnk']), key=lambda k: k['gol'],reverse=True), key=lambda k: k['sal'],reverse=True), key=lambda k: k['pts'],reverse=True)
                    }
                    classificados['grupos'].append(grupo)
                if torneio == 'Copa do Mundo':
                    for g in classificados['grupos']:
                        g['times'][0]['cor'] = 'copa'
                        g['times'][1]['cor'] = 'copa'
                else:
                    for g in classificados['grupos']:
                        g['times'][0]['cor'] = 'taca'
                        #g['times'][1]['cor'] = 'copa'

                # Definiçao de melhores 2os e 3os
                if torneio == 'Copa do Mundo':
                    times_1 = []
                    times_2 = []
                    times_3 = []
                    times_4 = []
                    for g in classificados['grupos']:
                        times_1.append(g['times'][0])
                        times_2.append(g['times'][1])
                        times_3.append(g['times'][2])
                        times_4.append(g['times'][3])
                    grupo_1 = {
                        'nome': 'Primeiros',
                        'times': sorted(sorted(sorted(sorted(times_1, key=lambda k: k['rnk']), key=lambda k: k['gol'],reverse=True), key=lambda k: k['sal'],reverse=True), key=lambda k: k['pts'],reverse=True)
                    }
                    grupo_2 = {
                        'nome': 'Segundos',
                        'times': sorted(sorted(sorted(sorted(times_2, key=lambda k: k['rnk']), key=lambda k: k['gol'],reverse=True), key=lambda k: k['sal'],reverse=True), key=lambda k: k['pts'],reverse=True)
                    }
                    grupo_3 = {
                        'nome': 'Terceiros',
                        'times': sorted(sorted(sorted(sorted(times_3, key=lambda k: k['rnk']), key=lambda k: k['gol'],reverse=True), key=lambda k: k['sal'],reverse=True), key=lambda k: k['pts'],reverse=True)
                    }
                    grupo_4 = {
                        'nome': 'Quartos',
                        'times': sorted(sorted(sorted(sorted(times_4, key=lambda k: k['rnk']), key=lambda k: k['gol'],reverse=True), key=lambda k: k['sal'],reverse=True), key=lambda k: k['pts'],reverse=True)
                    }
                    # Colore de amarelo os melhores terceiros colocados
                    for i in range(8):
                       grupo_3['times'][i]['cor'] = 'copa'
                    # Adiciona a lista de 4 grupos na tabela de classificaçao
                    classificados['grupos'].append(grupo_1)
                    classificados['grupos'].append(grupo_2)
                    classificados['grupos'].append(grupo_3)
                    classificados['grupos'].append(grupo_4)
                elif torneio in ['Taça Ásia-Oceania','Taça América','Taça Europa','Taça África']:
                    if torneio == 'Taça África':
                        range_2o = 2
                    elif torneio == 'Taça Europa':
                        range_2o = 9
                    elif torneio == 'Taça América':
                        range_2o = 5
                    else:
                        range_2o = 3
                    times_1 = []
                    times_2 = []
                    for g in classificados['grupos']:
                        times_1.append(g['times'][0])
                        times_2.append(g['times'][1])
                        # Para expansao da vaga
                        if torneio == torneio_sede:
                            if g['times'][0]['time'] == dono_casa:
                                range_2o += 1
                    grupo_1 = {
                        'nome': 'Primeiros',
                        'times': sorted(sorted(sorted(sorted(times_1, key=lambda k: k['rnk']), key=lambda k: k['gol'],reverse=True), key=lambda k: k['sal'],reverse=True), key=lambda k: k['pts'],reverse=True)
                    }
                    grupo_2 = {
                        'nome': 'Segundos',
                        'times': sorted(sorted(sorted(sorted(times_2, key=lambda k: k['rnk']), key=lambda k: k['gol'],reverse=True), key=lambda k: k['sal'],reverse=True), key=lambda k: k['pts'],reverse=True)
                    }
                    if torneio == torneio_sede:
                        for t in grupo_2['times']:
                            if t['time'] == dono_casa:
                                t['cor'] = 'copa'
                    for i in range(range_2o):
                        if torneio == torneio_sede:
                            if grupo_2['times'][i]['cor'] == 'copa':
                                i -= 1
                        grupo_2['times'][i]['cor'] = 'copa'
                    classificados['grupos'].append(grupo_1)
                    classificados['grupos'].append(grupo_2)

                competicao[torneio]['classificados'] = classificados

    return {
        'ano': ano,
        'desc':  descs[ano],
        'competicao': competicao,
        'outros': outros
    }            

@gokopa.route('/tabela<ano>')
@cache.cached(timeout=60*2)
def tabelaano(ano):
    if ano not in ['2022'] and int(ano) not in range(1,ANO+1):
        flash(f'Tabela do ano {ano} não disponível.','danger')
        ano = str(ANO)
    dados = gerar_tabela(ano)
    return render_template('tabela.html',menu="Tabela",dados=dados)

@gokopa.route('/sorteio')
def sorteio():
    dados = gerar_tabela(str(ANO))
    potdata = [u for u in mongo.db.pot.find({'Ano': ANO})]
    pots = []
    for time in potdata:
        #pot = time['pot']
        time.pop('_id',None)
        time['rank'] = get_rank(time["nome"])['posicao']
    #print(potdata)
    last_game = progress_data()['last_game']
    if last_game < 80:
        list_pots = ["A-EUR","B-EUR","C-EUR","A-AME","B-AME","C-AME","A-ASO","B-ASO","C-ASO","A-AFR","B-AFR","C-AFR"]
    else:
        list_pots = ["Cabeças","ASO","AFR","AME","TopASOAFR","EUR"]
    for potname in list_pots:
        times_do_pot = []
        for time in potdata:
            if time['pot'] == potname:
                times_do_pot.append(time)
        pots.append(
            {'potname': potname,
            'times': times_do_pot}) 
    
    #print(pots)

    return render_template('sorteio.html',menu="Tabela",dados=dados,pots=pots)

@gokopa.route('/tabelahis')
@cache.memoize(3600*720)
def tabela_his():
    fase_final = []
    for i in range(ANO-1):
        jogos = [u for u in mongo.db.jogos.find({"Ano": i+1, "Competição": "Copa do Mundo", '$or': [{"Fase": "8vas-de-final"},{"Fase": "4as-de-final"},{"Fase": "Semi-final"},{"Fase": "D. 3º Lugar"},{"Fase": "Final"}]}).sort('Jogo',pymongo.ASCENDING)]
        if i == 0:
            jogos = [0,0,0,0,0,0,0,0] + jogos
        fase_final.append(jogos)
        #print(f'Add ano {i+1}: {jogos}')
    return render_template('tabelahis.html',menu="Tabela",lista_jogos=fase_final)

@cache.memoize(3600*24)
def get_historic_copa(comp):
    if comp == 'tacas':
        historia = [u for u in mongo.db.historico.find({"comp": { '$in': [ "Taça América", "Taça Europa", "Taça Ásia-Oceania", "Taça África" ] }}).sort('Ano',pymongo.DESCENDING)]
    elif comp == 'bet':
        historia = [u for u in mongo.db.historico.find({"comp": { '$in': [ "bet", "moedas" ] }}).sort('Ano',pymongo.DESCENDING)]
        for u in historia:
            if u['comp'] == 'moedas':
                u['Ano'] = "🪙"+str(u['Ano'])
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

@gokopa.route('/api/get_enquete<ano>')
def getEnquete(ano):
    enq = [u for u in mongo.db.enquete.find({"ano": int(ano)})]
    andamento = []
    finalizadas = []
    #last_game = progress_data()['last_game']
    for u in enq:
        u.pop('_id',None)
        u['optqtd'] = len(u['opcoes'])
        if u.get("andamento"):
            if session.get("username"):
                nome = get_user_name(session["username"])
                u['meuvoto'] = u['votos'].get(nome)
                if nome != 'rlins':
                    if u['votos'].get(nome):
                        u['votos'] = {
                            nome: u['votos'][nome]
                        }
                    else:
                        u['votos'] = {}
                elif u['votos']:
                    finalizadas.append(u)
            else:
                u['votos'] = {}
            andamento.append(u)
        else:
            finalizadas.append(u)

    for u in finalizadas:
        mapa_id = []
        resultado = {}
        # Gera pts para pontos de cada indice e ptadd com qtd a ser somada
        pts = []
        ptadd = []
        max_n = u['optqtd']
        for i in range(max_n):
            pts.append(0)
            ptadd.append(max_n-i-1)
        ptadd[0] += 2
        ptadd[1] += 1
        for votante in u['votos']:
            for i in range(len(u['votos'][votante])):
                pts[u['votos'][votante][i]] += ptadd[i]

        for i in range(max_n):
            mapa_id.append({
                'id': i,
                'votos': 0,
                'votantes': [],
                'pontos': pts[i]
            })
        for rodada in range(max_n - 1):
            rodadar = str(rodada+1)+"r"
            resultado[rodadar] = []
            for user in u['votos']:
                voto = True
                i = -1
                while voto:
                    i += 1
                    pref = u['votos'][user][i]
                    for candidato in mapa_id:
                        if candidato['id'] == pref:
                            candidato['votos'] += 1
                            candidato['votantes'].append(user)
                            voto = False
                            #print(f'{rodada}: Voto feito por {user} em {pref}')
            new_mapaid = []
            for item in sorted(sorted(sorted(mapa_id, key=lambda k: k['id']), key=lambda k: k['pontos'],reverse=True), key=lambda k: k['votos'],reverse=True):
                resultado[rodadar].append(item.copy())
                new_mapaid.append(item.copy())
            new_mapaid.pop(-1)
            for m in new_mapaid:
                m['votos'] = 0
                m['votantes'] = []
            mapa_id = new_mapaid


        u['resultado'] = resultado

    return {
        'andamento': andamento,
        'finalizadas': finalizadas
    }

@gokopa.route('/api/estadios/<ano>')
def getEstadios(ano):
    data = [u for u in mongo.db.estadiolist.find({'ano': int(ano)})]
    for item in data:
        item.pop("_id")
        estadios = []
        jogos = get_anoX_games(int(ano),item['games'][0],item['games'][1])
        for c in item['cidades']:
            edesc = mongo.db.estadios.find_one({"cidade": c})
            jogose = []
            for j in jogos:
                if j["Estadio"] == c:
                    jogose.append(j)
            edesc['jogos'] = jogose
            edesc.pop('_id')
            estadios.append(edesc)
        item['estadios'] = estadios
    #print(data)
    return {'dados': data}
    
@gokopa.route('/estadios<ano>')
#@cache.cached(timeout=2*60)
def estadios(ano):
    if int(ano) not in range(22,ANO+1):
        flash(f'Ano {ano} não válido.','danger')
        ano = str(ANO)
    dados = {
        'ano': ano,
        'data': getEstadios(ano)['dados']
    }
    return render_template("estadios.html",menu="Gokopa",dados = dados)

@gokopa.route('/enquete<ano>')
#@cache.cached(timeout=2*60)
def enquete(ano):
    return render_template("enquete.html",menu="Gokopa",dados=getEnquete(ano))

@gokopa.route('/enquete/votar',methods=["POST"])
def votar():
    anoenq=ANO
    if "username" in session:
        apostador = get_user_name(session["username"])
        opcoes = []
        for i in range(int(request.values.get("optqtd"))-1):
            campo = "opt" + str(i)
            print(f'campo {campo} valor {request.values.get(campo)}')
            opcoes.append(int(request.values.get(campo)))
        enquete = request.values.get("enquete")
        opcoesset = set(opcoes)
        
        #enqdb = mongo.db.enquete.find_one({'nome': enquete})
        if len(opcoes) == len(opcoesset):
            enqdb = mongo.db.enquete.find_one({'nome': enquete})
            votos = enqdb['votos']
            anoenq=enqdb["ano"]
            votos[apostador] = opcoes
            outdb = mongo.db.enquete.find_one_and_update({'nome': enquete},{'$set': {'votos': votos}})
            if outdb:
                flash(f'Votação realizada!','success')
                current_app.logger.info(f"Votação realizada por {apostador} na enquete: {enquete}")
            else:
                flash(f'Erro na atualização da enquete.','danger')
                current_app.logger.error(f"Erro na atualização da enquete: {enquete}")
        else:
            flash(f'Os valores precisam ser diferentes!','danger')
    else:
        flash(f'Usuário não logado.','danger')
    
    return redirect(url_for('gokopa.enquete',ano=str(anoenq)))

@gokopa.route('/ranking')
#@cache.cached(timeout=600)
def ranking():
    #rank_ed = read_config_ranking()
    #ranking = [u for u in mongo.db.ranking.find({"ed": rank_ed}).sort('pos',pymongo.ASCENDING)]
    ranking = get_ranking()
    #copas_list,copas_medal = get_historic_copa("Copa do Mundo")
    #taca_list,taca_medal = get_historic_copa("Taça Mundial")
    bet_list,bet_medals = get_historic_copa("bet")
    #tacas_list,tacas_medals = get_historic_copa("tacas")
    #moedas_list,moedas_med = get_historic_copa("moedas")
    list_and_medal = dict()
    for comp in ["Taça América", "Taça Europa", "Taça Ásia-Oceania", "Taça África", "Copa do Mundo", "Taça Mundial"]:
        comp_list, comp_medal = get_historic_copa(comp)
        list_and_medal[comp] = {
            "comp_list": comp_list,
            "comp_medal": comp_medal
        }
    return render_template("ranking.html",menu="Gokopa",ranking=ranking,bet_his=bet_list,bet_med=bet_medals,list_and_medal=list_and_medal)
    #copa_his=copas_list,copa_med=copas_medal,taca_his=taca_list,taca_med=taca_medal,tacas_his=tacas_list,tacas_med=tacas_medals)

@cache.memoize(3600*24)
def get_team_list():
    ranking = [u['Time'] for u in mongo.db.timehistory.find().sort('Time',pymongo.ASCENDING)]
    return ranking

@cache.memoize(3600*24*7)
def return_historic_duels(team1,team2):
    last_game = progress_data()['last_game']
    historico_antigo = [u for u in mongo.db.jogos.find({ '$or': [{'Time1': team1,'Time2': team2 },{'Time1': team2,'Time2': team1 }],"Ano": {'$lt':ANO} }).sort([("Ano",pymongo.DESCENDING),("Jogo",pymongo.DESCENDING)])]
    historico_atual = [u for u in mongo.db.jogos.find({ '$or': [{'Time1': team1,'Time2': team2 },{'Time1': team2,'Time2': team1 }],"Ano": ANO, "Jogo": {'$lt':last_game+1} }).sort([("Ano",pymongo.DESCENDING),("Jogo",pymongo.ASCENDING)])]
    historico_total = historico_atual + historico_antigo
    
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
    for i in range(1,ANO):
        copa = "c" + str(i)
        rank = "r" + str(i)
        pos_copa.append(historia[copa])
        if historia[rank] == "-":
            pos_rank.append('null')
        else:
            pos_rank.append(int(historia[rank]))
    # Add current rank
    pos_copa.append(historia['c'+str(ANO)])
    pos_rank.append(get_rank(team1)['posicao'])
    #print(pos_copa,pos_rank)
    return pos_copa,pos_rank

@cache.memoize(3600)
@gokopa.route('/historico',methods=["GET","POST"])
def historico():
    time_1 = dict()
    time_2 = dict()
    lista_times=get_team_list()
    #print(lista_times)
    lista_jogos = []
    vev=[]
    nextgameid = progress_data()['last_game']+1
    lastgames = get_anoX_games(ANO,nextgameid,nextgameid+19)
    if request.method == "POST":
        time_1["nome"] = request.values.get("time1")
        time_2["nome"] = request.values.get("time2")
        #times = [time1,time2]
        if time_1["nome"] in lista_times and time_2["nome"] in lista_times:
            lista_jogos,vev = return_historic_duels(time_1["nome"],time_2["nome"])
            time_1["hc"],time_1["hr"] = return_team_history(time_1["nome"])
            time_2["hc"],time_2["hr"] = return_team_history(time_2["nome"])
        else:
            flash(f'Times não encontrados na base.','danger')
    new_lastgames = []
    for jogo in lastgames:
        if jogo.get('Time1') and jogo.get('Time2'):
            listaj,jvev = return_historic_duels(jogo['Time1'],jogo['Time2'])
            jogo['vev'] = jvev
            new_lastgames.append(jogo)
    data2t = {
        'lista_jogos': lista_jogos,
        'vev': vev,
        'time1': time_1,
        'time2': time_2,
        'lista_times': lista_times
    }
    return render_template('historico.html',menu='Gokopa',data2t=data2t,lastgames=new_lastgames)

@cache.memoize(3600*2)
def getDossieTime(time):
    jogos_antigos = [u for u in mongo.db.jogos.find({ '$or': [{'Time1': time},{'Time2': time }],"Ano": {'$lt':ANO} }).sort([("Ano",pymongo.DESCENDING),("Jogo",pymongo.DESCENDING)])]
    last_game = progress_data()['last_game']
    jogos_atual = [u for u in mongo.db.jogos.find({ '$or': [{'Time1': time},{'Time2': time }],"Ano": ANO ,'Jogo': {'$lt': last_game+1}}).sort([("Ano",pymongo.DESCENDING),("Jogo",pymongo.DESCENDING)])]
    jogos = jogos_atual + jogos_antigos
    for j in jogos:
        j.pop('_id')
    posc,posr = return_team_history(time)
    ved = [0,0,0,len(jogos)]
    for j in jogos:
        if j['p1'] == j['p2']:
            ved[1] += 1
        elif (j['p1'] > j['p2']):
            if j['Time1'] == time:
                ved[0] += 1
            else:
                ved[2] += 1
        else:
            if j['Time2'] == time:
                ved[0] += 1
            else:
                ved[2] += 1
    aproveitamento = (ved[0]*2 + ved[1]) / (ved[3]*2)
    historico = [u for u in mongo.db.historico.find().sort("Ano",pymongo.ASCENDING)]
    titlist = []
    tittorneios = {}
    for h in historico:
        for medal in ['ouro','prata','bronze','quarto']:
            if h[medal] == time:
                if medal in [ "Taça América", "Taça Europa", "Taça Ásia-Oceania", "Taça África" ] or medal != 'quarto':
                    if medal == 'quarto':
                        medal = 'bronze'
                    if not tittorneios.get(h['comp']):
                        tittorneios[h['comp']] = {
                            'ouro': 0,
                            'prata': 0,
                            'bronze': 0,
                            'total': 0
                        }
                    titlist.append({
                        'ano': h['Ano'],
                        'comp': h['comp'],
                        'medal': medal
                    })
                    tittorneios[h['comp']][medal] += 1
                    tittorneios[h['comp']]['total'] += 1

    return {
        'time': time,
        'pos_c': posc,
        'pos_r': posr,
        'ved': ved,
        'ranking': get_rank(time),
        'aprov': "{:.2%}".format(aproveitamento),
        'jogos': jogos,
        'titulos': {
            'lista': titlist,
            'torneios': tittorneios
        }
    }


@gokopa.route('/api/get_dossie',methods=["GET","POST"])
def getDossie():
    time = request.values.get("time")
    return getDossieTime(time)

@gokopa.route('/dossie',methods=["GET","POST"])
def dossie():
    lista = [u['Time'] for u in mongo.db.timehistory.find().sort("Time",pymongo.ASCENDING)]
    if request.method == "POST":
        time = request.values.get("time")
        if time in lista:
            dados = getDossieTime(time)
        else:
            flash(f'Time {time} não encontrado.','danger')
            dados = {}
    else:
        dados = {}
    dados['lista_times'] = lista
    # print(lista)
    # for t in lista:
    #     dados['lista_times'].append(t['Time'])
    return render_template('dossie.html',menu='Gokopa',dados=dados)


# def get_tabela_pot():
#     tabela_pot = []
#     for i in range(4):
#         times = []
#         times_pot = [u for u in mongo.db.pot.find({"Ano": ANO,"pot": int(i+1)}).sort('nome',pymongo.ASCENDING)]
#         tabela_pot.append(times_pot)
#     #print(tabela_pot)

#     pot_trans = []
#     for i in range(10):
#         pot_trans.append([dict(),dict(),dict(),dict()])
#     #print(pot_trans)
#     for i in range(10):
#         for j in range(4):
#             #print("pegando",tabela_pot[i][j])
#             if len(tabela_pot[j]) > i:
#                 #print("pegando",tabela_pot[j][i])
#                 time = tabela_pot[j][i]
#                 time['rank'] = get_rank(time['nome'])
#                 pot_trans[i][j] = time
#     return pot_trans
