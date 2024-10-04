from asyncio import sleep
import time
import json
import random
from re import T
import sys
from bson.objectid import ObjectId
import click
import getpass
import os
import requests
from bson.objectid import ObjectId
from flask_pymongo import BSONObjectIdConverter
import pymongo
from pymongo.collection import ReturnDocument

from app.routes.backend import get_moedas_board, get_next_jogos, get_pat_teams, moedas_log, get_ranking, progress_data
from ..extentions.database import mongo
from flask import Blueprint,current_app

SEPARADOR_CSV="\t"
ANO=24
#RANKING='20-4'
TELEGRAM_TOKEN=os.getenv('TELEGRAM_TKN')
TELEGRAM_CHAT_ID=os.getenv('TELEGRAM_CHAT_ID')
TELEGRAM=os.getenv('TELEGRAM')

timeCommands = Blueprint('time',__name__)

@timeCommands.cli.command("loadRanking")
@click.argument("csv_file")
def load_csv(csv_file):
    data = []
    with open(csv_file) as arq:
        headers = next(arq, None)
        # Caso valor default None, retorna []
        if headers is None:
            return []

        cabecalho = headers.strip().split(SEPARADOR_CSV)
        #print(cabecalho)

        for linha in arq:
            #print("linha:",linha)
            colunas = linha.strip().split(SEPARADOR_CSV)
            documento = zip(cabecalho,colunas)
            documento = dict(documento)
            documento["pos"]=int(documento["pos"])
            documento["pontos"]=int(documento["pontos"])
            documento["u_rank"]=int(documento["u_rank"])
            documento["u_pts"]=int(documento["u_pts"])
            documento["u_ano"]=int(documento["u_ano"])
            data.append(documento)

        if not data:
            print("Sem dados.")
            return None
        
        print(data)
    
    
    timeCollection = mongo.db.ranking
    timeCollection.insert_many(data)
    print("Dados inseridos")
    # question = input(f'Deseja inserir os dados impressos? (S/N) ')
    # if question.upper() == "S":
    #     timeCollection = mongo.db.ranking
    #     timeCollection.insert(data)
    #     print("Dados inseridos")
    # else:
    #     exit()

@timeCommands.cli.command("loadTimeHistory")
@click.argument("csv_file")
def load_csv(csv_file):
    data = []
    with open(csv_file) as arq:
        headers = next(arq, None)
        # Caso valor default None, retorna []
        if headers is None:
            return []

        cabecalho = headers.strip().split(SEPARADOR_CSV)
        #print(cabecalho)

        for linha in arq:
            #print("linha:",linha)
            colunas = linha.strip().split(SEPARADOR_CSV)
            documento = zip(cabecalho,colunas)
            documento = dict(documento)
            documento['p21'] = int(documento['p21'])
            documento['p20'] = int(documento['p20'])
            documento['p19'] = int(documento['p19'])
            documento['p18'] = int(documento['p18'])
            documento['ph'] = int(documento['ph'])
            data.append(documento)

        if not data:
            print("Sem dados.")
            return None
        
        #print(data)
    
    
    # question = input(f'Deseja inserir os dados impressos? (S/N) ')
    # if question.upper() == "S":
    timeCollection = mongo.db.timehistory
    outdb = timeCollection.find()
    if outdb:
        print("Base já existe, reescrevendo.")
        timeCollection.drop()
    timeCollection.insert_many(data)
    print("Dados inseridos")
    # else:
    #     exit()

@timeCommands.cli.command("set_copa_pos")
@click.argument("ano")
@click.argument("time")
@click.argument("status")
def set_copa_pos(ano,time,status):
    ca = "c" + ano
    outdb = mongo.db.timehistory.find_one_and_update({"Time": time},{'$set': {ca: status}})
    if outdb:
        print(f"Setado {ca} para time {time}")
    else:
        print("Erro")

@timeCommands.cli.command("set_rank_upts")
@click.argument("ano")
def set_rank_upts(ano):
    ranking = get_ranking()
    newr = "r" + ano
    for t in ranking["ranking"]:
        #print(f"{t['time']}: u_pts: {t['u_pts']} -> {t['score']} u_r/{newr}: {t['u_r']} -> {t['posicao']}")
        mongo.db.timehistory.update_one({"Time": t['time']},{'$set': {newr: t['posicao'],'u_pts':t['score']}})

@timeCommands.cli.command("zera_rank_pts")
@click.argument("ano")
def zera_rank_pts(ano):
    rank = "p" + ano
    print(f"Zerando dados {rank}")
    mongo.db.timehistory.update_many({},{'$set':{rank: 0}})

@timeCommands.cli.command("calc_ranking")
@click.argument("j_i")
@click.argument("j_f")
def calc_ranking(j_i,j_f):
    ft1 = 1
    ft2 = 4
    ranking = get_ranking()
    times = {}
    for t in ranking['ranking']:
        times[t['time']] = {
            'pts': 0,
            'posicao': float(t['posicao'])
        }
    print(f'Avaliando jogos de {j_i} a {j_f}')
    for i in range(int(j_i),int(j_f)+1):
        jogo = mongo.db.jogos.find_one({'Ano': ANO, 'Jogo': i})
        ptsg1 = 0
        ptsg2 = 0
        pts1 = 0
        pts2 = 0
        if jogo['p1'] > jogo['p2']:
            if not jogo.get('Grupo') and type(jogo.get('tr1')) == int:
                pts1 = 2.5
                pts2 = 0.5
            else:
                pts1 = 3
        elif jogo['p2'] > jogo['p1']:
            if not jogo.get('Grupo') and type(jogo.get('tr1')) == int:
                pts2 = 2.5
                pts1 = 0.5
            else:
                pts2 = 3
        else:
            if jogo.get('Grupo'):
                pts1 = 1.5
                pts2 = 1.5
            elif jogo['pe1'] > jogo['pe2']:
                pts1 = 2
                pts2 = 1
            else:
                pts1 = 1
                pts2 = 2
        #print(f'Jogo: {jogo}')
        pesojogo = float((int(jogo['peso'])+1)/2) 
        if pts1 > 0:
            ptsg1 = int( (ft1 + ft2*(127-times[jogo['Time2']]['posicao'])/126) * pts1 * pesojogo ) + 1
        if pts2 > 0:
            ptsg2 = int( (ft1 + ft2*(127-times[jogo['Time1']]['posicao'])/126) * pts2 * pesojogo ) + 1
        times[jogo['Time1']]['pts'] += ptsg1
        times[jogo['Time2']]['pts'] += ptsg2
        #print(f'ptsg1: {ptsg1} ptsg2: {ptsg2}')
    
    pontosano = "p"+str(ANO)
    for t in times:
        pts = times[t]['pts']
        if pts > 0:
            print(f'Time {t} = +{pts}')
            mongo.db.timehistory.find_one_and_update({'Time': t},{'$inc': {pontosano: pts}})
    
@timeCommands.cli.command("loadEmojis")
@click.argument("csv_file")
def load_emoji(csv_file):
    data = []
    with open(csv_file) as arq:
        headers = next(arq, None)
        # Caso valor default None, retorna []
        if headers is None:
            return []

        cabecalho = headers.strip().split(SEPARADOR_CSV)
        #print(cabecalho)

        for linha in arq:
            #print("linha:",linha)
            colunas = linha.strip().split(SEPARADOR_CSV)
            documento = zip(cabecalho,colunas)
            documento = dict(documento)
            data.append(documento)

        if not data:
            print("Sem dados.")
            return None
        
        print(data)
    
    timeCollection = mongo.db.emoji
    timeCollection.insert_many(data)


@timeCommands.cli.command("getRank")
@click.argument("rank")
def get_rank(rank):
    timeCollection = mongo.db.ranking
    print(f'Buscando ranking {rank}')
    busca = [u for u in timeCollection.find({"ed": rank})]
    if busca:
        print("Ranking encontrado\n",busca)
    else:
        print("Nada encontrado.")

@timeCommands.cli.command("editTime")
@click.argument("desc")
@click.argument("time")
def editTime(desc,time):
    edit_time(desc,time)

def edit_time(desc,time):
    timeValid = mongo.db.timehistory.find_one({'Time': time})
    if timeValid:
        print(f'Definindo time {time} em {desc}')
    elif time == "zera":
        print(f'Zerando posicao {desc}')
        time = ""
    else:
        print(f'Time {time} nao valido.')
        exit()

    ano20_jogos = mongo.db.jogos.find({'Ano': ANO}).sort("Jogo",pymongo.ASCENDING)
    for j in ano20_jogos:
        if j['desc1'] == desc:
            novo_jogo = mongo.db.jogos.find_one_and_update(
                {"_id": ObjectId(j['_id'])},
                {'$set': {'Time1': time}},return_document=ReturnDocument.AFTER)
            #print(novo_jogo)
        elif j['desc2'] == desc:
            novo_jogo = mongo.db.jogos.find_one_and_update(
                {"_id": ObjectId(j['_id'])},
                {'$set': {'Time2': time}},return_document=ReturnDocument.AFTER)
            #print(novo_jogo)
    print("Finalizado.")

# Para classificação da copa de acordo com confederação
@timeCommands.cli.command("classificaTime")
@click.argument("conf")
@click.argument("time")
def classifica_time(conf,time):
    timeValid = mongo.db.timehistory.find_one({'Time': time})
    if timeValid:
        print(f'Classificando time {time} em {conf}')
    else:
        print(f'Time {time} nao valido.')
        exit()

    classificado = dict()
    classificado['Ano'] = ANO
    classificado['nome'] = time
    classificado['conf'] = conf
    classificado['pot'] = conf

    mongo.db.pot.insert_one(classificado)
    copaname = "c" + str(ANO)
    mongo.db.timehistory.find_one_and_update({"Time": time},{'$set': {copaname: 'c'}})
    print("Finalizado.")

# Seta time no pot de sorteio
@timeCommands.cli.command("setPot")
@click.argument("potname")
@click.argument("time")
def set_pot(potname,time):
    timeValid = mongo.db.timehistory.find_one({'Time': time})
    if timeValid:
        print(f'Setando time {time} como pot {potname}:',end=" ")
    else:
        print(f'Time {time} nao valido.')
        exit()

    outdb = mongo.db.pot.find_one_and_update({"nome": time, 'Ano': ANO},{'$set': {'pot': potname,'sorteado': False}})
    if outdb:
        print("Time atualizado na base")
    else:
        print("Inserindo time novo na base")
        classificado = dict()
        classificado['Ano'] = ANO
        classificado['nome'] = time
        classificado['conf'] = "-"
        classificado['pot'] = potname
        mongo.db.pot.insert_one(classificado)

# Realiza sorteio dos times das tacas
@timeCommands.cli.command("sorteiaTaca")
@click.argument("teste",required=False)
def sorteia_taca(teste=""):
    sleeptime=3
    if teste:
        APLICA = False
    else:
        APLICA = True
    print("Iniciando sorteio das Taças")
    std_group_ori = ['A','B','C','D','E','F','G','H','I','J','K','L']
    std_groups = {
        "EUR": std_group_ori,
        "AFR": std_group_ori[:5],
        "AME": std_group_ori[:6],
        "ASO": std_group_ori[:4]
    }
    ordemg = {}
    
    for conf_name in ["EUR","AFR","AME","ASO"]:
        print(f"Iniciando sorteio da Taça {conf_name}")
        input("")
        tsede = mongo.db.pot.find_one({"Ano": ANO, 'pot': "S-"+conf_name})["nome"]
        #gr_cabecas = std_groups.copy()
        posic = "p1A-"+conf_name
        #gr_cabecas.remove("A")
        print(f"flask time editTime {posic} '{tsede}'")
        if APLICA:
            time.sleep(sleeptime)
            edit_time(posic,tsede)
            mongo.db.pot.find_one_and_update({"Ano": ANO, "nome": tsede},{'$set': {'sorteado': True}})
        times_c = [u['nome'] for u in mongo.db.pot.find({"Ano": ANO, 'pot': 'A-'+conf_name})]
        random.shuffle(times_c)
        # Para o restante dos grupos de cabeças, exceto A
        for g in std_groups[conf_name][1:]:
            posic = "p1" + g + "-" + conf_name
            t = times_c.pop()
            print(f"flask time editTime {posic} '{t}'")
            if APLICA:
                time.sleep(sleeptime)
                edit_time(posic,t)
                mongo.db.pot.find_one_and_update({"Ano": ANO, "nome": t},{'$set': {'sorteado': True}})
        
        for g in std_groups[conf_name]:
            ordemg[g] = [2,3]
        times_2r = [u['nome'] for u in mongo.db.pot.find({"Ano": ANO, 'pot': 'B-'+conf_name})]
        times_3r = [u['nome'] for u in mongo.db.pot.find({"Ano": ANO, 'pot': 'C-'+conf_name})]
        for times_r in [times_2r,times_3r]:
            random.shuffle(times_r)
            for g in std_groups[conf_name]:
                random.shuffle(ordemg[g])
                posic = "p" + str(ordemg.get(g).pop()) + g + "-" + conf_name
                t = times_r.pop()
                print(f"flask time editTime {posic} '{t}'")
                if APLICA:
                    time.sleep(sleeptime)
                    edit_time(posic,t)
                    mongo.db.pot.find_one_and_update({"Ano": ANO, "nome": t},{'$set': {'sorteado': True}})


# Realiza sorteio dos times da copa
@timeCommands.cli.command("sorteiaCopa")
@click.argument("teste",required=False)
def sorteia_copa(teste=""):
    if teste:
        sleeptime=2
        APLICA = False
    else:
        sleeptime=15
        APLICA = True
    print("Iniciando sorteio da Copa do Mundo")
    std_groups = ['A','B','C','D','E','F','G','H','I','J','K','L']
    # Inicia com cabeças de chave
    times_c = [u['nome'] for u in mongo.db.pot.find({"Ano": ANO, 'pot': 'Cabeças'})]
    cabeca_group = std_groups.copy()
    gr_ceur = []
    gr_came = []
    gr_aso = []
    gr_cafr = []
    gr_casa = ["A","G"]
    for t in ['Sudão','Egito']:
        g = gr_casa.pop()
        posic = "p1" + g
        print(f"flask time editTime {posic} {t}")
        cabeca_group.remove(g)
        times_c.remove(t)
        gr_cafr.append(g)
        if APLICA:
            time.sleep(sleeptime)
            edit_time(posic,t)
            mongo.db.pot.find_one_and_update({"Ano": ANO, "nome": t},{'$set': {'sorteado': True}})
    #print(cabeca_group)
    random.shuffle(times_c)
    #print(times_c)
    for g in cabeca_group:
        posic = "p1" + g
        t = times_c.pop()
        print(f"flask time editTime {posic} {t}")
        conf = mongo.db.pot.find_one({"Ano": ANO, "nome": t})['conf']
        if conf == "AME":
            gr_came.append(g)
        else:
            gr_ceur.append(g)
        if APLICA:
            time.sleep(sleeptime)
            edit_time(posic,t)
            mongo.db.pot.find_one_and_update({"Ano": ANO, "nome": t},{'$set': {'sorteado': True}})

    ordemg = {
        'A': [2,3,4],
        'B': [2,3,4],
        'C': [2,3,4],
        'D': [2,3,4],
        'E': [2,3,4],
        'F': [2,3,4],
        'G': [2,3,4],
        'H': [2,3,4],
        'I': [2,3,4],
        'J': [2,3,4],
        'K': [2,3,4],
        'L': [2,3,4]
    }

    # Sorteio dos grupos ASO e AFR
    times_aso = [u['nome'] for u in mongo.db.pot.find({"Ano": ANO, 'pot': 'ASO'})]
    times_afr = [u['nome'] for u in mongo.db.pot.find({"Ano": ANO, 'pot': 'AFR'})]
    r2_groups = std_groups.copy()
    random.shuffle(times_aso)
    random.shuffle(times_afr)
    input("Iniciando segunda rodada do sorteio...")

    for g in ['A','G']:
        random.shuffle(ordemg[g])
        posic = "p" + str(ordemg.get(g).pop()) + g
        t = times_aso.pop()
        print(f"flask time editTime {posic} {t}")
        conf = mongo.db.pot.find_one({"Ano": ANO, "nome": t})['conf']
        gr_aso.append(g)
        r2_groups.remove(g)
        if APLICA:
            time.sleep(sleeptime)
            edit_time(posic,t)
            mongo.db.pot.find_one_and_update({"Ano": ANO, "nome": t},{'$set': {'sorteado': True}})
    times_2r = times_aso + times_afr
    random.shuffle(times_2r)

    for g in r2_groups:
        random.shuffle(ordemg[g])
        posic = "p" + str(ordemg.get(g).pop()) + g
        t = times_2r.pop()
        print(f"flask time editTime {posic} {t}")
        conf = mongo.db.pot.find_one({"Ano": ANO, "nome": t})['conf']
        #print(f'conf: {conf}')
        if conf == 'ASO':
            gr_aso.append(g)
        if APLICA:
            time.sleep(sleeptime)
            edit_time(posic,t)
            mongo.db.pot.find_one_and_update({"Ano": ANO, "nome": t},{'$set': {'sorteado': True}})
    #print(ordemg)
    #print(gr_ceur)
    #print(gr_came)

    # Sorteio dos grupos AME + EUR
    input("Iniciando terceira rodada do sorteio...")
    times_ame = [u['nome'] for u in mongo.db.pot.find({"Ano": ANO, 'pot': 'AME'})]
    times_eur = [u['nome'] for u in mongo.db.pot.find({"Ano": ANO, 'pot': 'EUR'})]
    times_tasoafr = [u['nome'] for u in mongo.db.pot.find({"Ano": ANO, 'pot': 'TopASOAFR'})]
    random.shuffle(times_ame)
    random.shuffle(times_eur)
    random.shuffle(times_tasoafr)
    gr_came.sort()
    r3_groups = std_groups.copy()
    random.shuffle(gr_cafr)
    for g in gr_came + [gr_cafr.pop()]:
        posic = "p" + str(ordemg.get(g).pop()) + g
        t = times_eur.pop()
        print(f"flask time editTime {posic} {t}")
        r3_groups.remove(g)
        if APLICA:
            time.sleep(sleeptime)
            edit_time(posic,t)
            mongo.db.pot.find_one_and_update({"Ano": ANO, "nome": t},{'$set': {'sorteado': True}})
    for g in r3_groups:
        posic = "p" + str(ordemg.get(g).pop()) + g
        t = times_ame.pop()
        print(f"flask time editTime {posic} {t}")
        if APLICA:
            time.sleep(sleeptime)
            edit_time(posic,t)
            mongo.db.pot.find_one_and_update({"Ano": ANO, "nome": t},{'$set': {'sorteado': True}})

    #print(times_eur)
    #print(times_tasoafr)
    #print(ordemg)
    
    # Sorteio dos grupos TopASOSFR + EUR
    input("Iniciando quarta e última rodada do sorteio...")
    r4_aso = []
    r4_eur = []
    print(gr_aso)
    for g in std_groups:
        if g in gr_aso:
            r4_eur.append(g)
        else:
            r4_aso.append(g)
    print(r4_aso)
    print(r4_eur)
    random.shuffle(r4_aso)
    r4_groups = r4_aso[0:2] + sorted(r4_aso[2:] + r4_eur)
    r4_times = times_eur + times_tasoafr
    for g in r4_groups:
        posic = "p" + str(ordemg.get(g).pop()) + g
        t = r4_times.pop()
        print(f"flask time editTime {posic} {t}")
        if APLICA:
            time.sleep(sleeptime)
            edit_time(posic,t)
            mongo.db.pot.find_one_and_update({"Ano": ANO, "nome": t},{'$set': {'sorteado': True}})
 
    print("Sorteio finalizado.")


@timeCommands.cli.command("limpaPots")
def limpa_pots():
    mongo.db.pot.delete_many({'Ano': ANO})

@timeCommands.cli.command("zeraGrupos")
def zera_grupos():
    std_groups = ['A','B','C','D','E','F','G','H','I','J','K','L']
    for g in std_groups:
        for i in range(1,5):
            posic = "p" + str(i) + g
            edit_time(posic,"zera")
    mongo.db.pot.update_many({"Ano": ANO},{'$set': {'sorteado': False}})

@timeCommands.cli.command("defHist")
@click.argument("comp")
@click.argument("ano")
@click.argument("ouro")
@click.argument("prata")
@click.argument("bronze")
@click.argument("quarto")
@click.argument("sedes")
def def_historico(comp,ano,ouro,prata,bronze,quarto,sedes):
    # for t in comp,ano,ouro,prata,bronze,quarto:
    #     timeValid = mongo.db.ranking.find_one({"ed": RANKING,'time': t})
    # if not timeValid:
    #     print(f'Time {t} nao valido.')
    #     exit()
    base = "his_" + comp
    ano_hist = dict()
    ano_hist['Ano'] = int(ano)
    ano_hist['ouro'] = ouro
    ano_hist['prata'] = prata
    ano_hist['bronze'] = bronze
    ano_hist['quarto'] = quarto
    ano_hist['sedes'] = sedes
    ano_hist['comp'] = comp
    print(f'Inserindo histórico para {comp} ano {ano}: {ouro},{prata},{bronze},{quarto} em {sedes}')
    mongo.db.historico.insert_one(ano_hist)

@timeCommands.cli.command("defPot")
@click.argument("time")
@click.argument("pot")
def classifica_time(time,pot):
    timeValid = mongo.db.timehistory.find_one({'Time': time})
    if timeValid:
        print(f'Definindo para time {time} pot {pot}')
    else:
        print(f'Time {time} nao valido.')
        exit()

    itemdb = mongo.db.pot.find_one_and_update({"Ano": ANO, "nome": time},{'$set': {"pot": pot,"sorteado": False}})
    if itemdb:
        print("Atualizado.")
    else:
        print("Item",time,"nao encontrado!")

@timeCommands.cli.command("sorteia")
@click.argument("time")
def sorteia(time):
    itemdb = mongo.db.pot.find_one_and_update({"Ano": ANO, "nome": time},{'$set': {"sorteado": True}})
    if itemdb:
        print("Atualizado.")
    else:
        print("Item",time,"nao encontrado!")


@timeCommands.cli.command("loadPatrocinio")
@click.argument("csv_file")
def load_patrocinio(csv_file):
    data = []
    with open(csv_file) as arq:
        headers = next(arq, None)
        # Caso valor default None, retorna []
        if headers is None:
            return []

        cabecalho = headers.strip().split(SEPARADOR_CSV)
        #print(cabecalho)

        for linha in arq:
            colunas = linha.strip().split(SEPARADOR_CSV)
            documento = zip(cabecalho,colunas)
            documento = dict(documento)
            documento["Valor"]=int(documento["Valor"])
            documento["Patrocinador"]="-"
            #documento["Apoiadores"]=[]
            data.append(documento)

        if not data:
            return None
        
        print(data)
    
    
    jogosCollection = mongo.db.patrocinio
    jogosCollection.insert_many(data)
    print("Dados inseridos")

@timeCommands.cli.command("exec")
def exec():
    #mongo.db.moedas.find_one_and_update({'nome': 'ze1'},{'$set': {'saldo': 0, 'bloqueado': 0, 'investido': 1000}})
    #mongo.db.patrocinio.find_one_and_update({'Time': 'Holanda'},{'$set': {"Patrocinador" : "-"}})
    #mongo.db.tentarpat.find_one_and_update({'valor':500},{'$set': {'valor':0}})
    #mongo.db.patrocinio.find_and_modify({'Time': 'Holanda'},{'$set': {'Patrocinador': "-"}})
    #mongo.db.jogos.find_one_and_update({'Ano': 22, 'Jogo': 94},{'$set': {'desc1':'s1-EUR','desc2':'s2-EUR'}})
    #mongo.db.jogos.find_one_and_update({'Ano': 22, 'Jogo': 95},{'$set': {'desc1':'s1-AME','desc2':'s2-AME'}})
    for t in [u for u in mongo.db.patrocinio.find()]:
        print(t['Time'])
    # for t in ['Brasil','Argentina']:
    #     mongo.db.pot.find_one_and_delete({'Ano': 24, 'nome': t, 'pot': 'AME'})
    # for t in ['França','Alemanha','Tcheca','Portugal','Espanha','Sérvia','Bélgica','Suécia']:
    #     mongo.db.pot.find_one_and_delete({'Ano': 24, 'nome': t, 'pot': 'EUR'})


    # users = [u for u in mongo.db.moedas.find()]
    # for u in users:
    #     mongo.db.moedas.find_one_and_update({'nome': u['nome']},{'$inc':{'divida': 0}})
    # nome = "ernani"
    # mongo.db.moedas.find_one_and_update({'nome': nome},{'$inc':{'investido': -valor}})
    # moedas_log(nome,str(-valor),t,70,"Ajuste da derrota do time")

#def processa_jogos():


@timeCommands.cli.command("desclassifica")
@click.argument("time")
def desclassifica(time):
    patDb = mongo.db.patrocinio.find_one({'Time': time})
    patrocinador = patDb['Patrocinador']
    if  patrocinador != "-":
        # Retorna investimentos
        moedas = mongo.db.moedas
        valor = patDb['Valor']
        moedas.find_one_and_update({'nome':patrocinador},{'$inc': {'saldo': valor,'investido': -valor}})
        moedas_log(patrocinador,"x "+str(valor),time,0,"Retorno de patrocínio")
        if patDb.get('Apoiadores'):
            for a in patDb.get('Apoiadores'):
                apoiador = a['nome']
                avalor = a['valor']
                moedas.find_one_and_update({'nome':apoiador},{'$inc': {'saldo': avalor,'investido': -avalor}})
                moedas_log(apoiador,"x "+str(avalor),time,0,"Retorno de apoio")
    mongo.db.patrocinio.find_one_and_delete({'Time': time})
    print(f"Removido time {time}")

@timeCommands.cli.command("verificaInvest")
def verifica_invest():
    moedas = [u for u in mongo.db.moedas.find()]
    patrocinios = [u for u in mongo.db.patrocinio.find()]
    for u in moedas:
        valor_verificado = 0
        for t in patrocinios:
            if t['Patrocinador'] == u['nome']:
                valor_verificado += t['Valor']
            if t.get('Apoiadores'):
                for a in t['Apoiadores']:
                    if a['nome'] == u['nome']:
                        valor_verificado += a['valor']
        if valor_verificado == u['investido']:
            print(f"Usuário {u['nome']} OK - tem investimento de {u['investido']}.")
        else:
            print(f"Usuário {u['nome']} XX - investimento incompatível, {u['investido']} x {valor_verificado} ({valor_verificado-u['investido']})")


@timeCommands.cli.command("setaCartas")
def setaCartas():
    cartas = [{
        "id": 0,
        "freq": 40,
        "card": "Dia de folga",
        "desc": "Nenhuma ação por hoje, use outras cartas ou descanse.",
        "uso": "Esta carta não realiza nenhuma ação. Ao comprar cartas, caso tenha mais de 5 em mãos, a mais antiga será descartada. O acúmulo dessa carta fará com que cartas mais antigas sejam descartadas. Não há ações para realizar nessa rodada."
    },{
        "id": 1,
        "freq": 30,
        "card": "Ganhe 10",
        "saldo": 10,
        "desc": "Ganhe imediatamente 10 moedas em seu saldo.",
        "uso": "Use essa carta para adicionar imediatamente esta quantidade de moedas em seu saldo livre."
    },{
        "id": 9,
        "freq": 10,
        "card": "Ganhe 15",
        "saldo": 15,
        "desc": "Ganhe imediatamente 15 moedas em seu saldo.",
        "uso": "Use essa carta para adicionar imediatamente esta quantidade de moedas em seu saldo livre."
    },{
        "id": 2,
        "freq": 8,
        "card": "Peça 50",
        "desc": "Faça um pedido por 50 moedas que chegará em até dois dias.",
        "uso": "Use essa carta para realizar um pedido de moedas que chegara em até 4 rodadas e será incluída em seu saldo livre. A ação será adicionada à lista de cards processando."
    },{
        "id": 10,
        "freq": 2,
        "saldo": 500,
        "card": "Empréstimo longo",
        "desc": 'Peça um empréstimo de 500 moedas, pague 550 entre 30 e 50 dias.',
        "uso": "Use essa carta para realizar um empréstimo longo. Você receberá imediatamente moedas em seu saldo livre e deverá pagar no prazo estabelecido e adicionado à lista de cards processando. No início do jogo, cada jogador começa com uma mão inicial com essas cartas. Seu uso é opcional, e caso não utilise todas, as cartas retornarão ao deck no começo do jogo por causa do efeito do remix inicial."
    },{
        "id": 3,
        "freq": 8,
        "card": "Empréstimo a jato",
        "saldo": 200,
        "desc": "Peça por 200 moedas agora, que serão debitadas em 3 dias.",
        "uso": "Receba imediatamente o valor de moedas em seu saldo livre. O card irá gerar uma ação em processamento de débito, de mesmo valor, na quantidade indicada de turnos."
    },{
        "id": 4,
        "freq": 7,
        "card": "All-in",
        "desc": "Adicione a carta a um dos jogos apoiados ou patrocinados para dobrar ganhos, mas dobrar perdas caso haja derrota.",
        "uso": "Escolha um dos próximos jogos, que você apoie ou patrocine algum time, e use esta carta. No processamento do jogo, os ganhos serão dobrados, mas as perdas também serão dobradas. Use em jogos em que esteja mais confiante do resultado."
    },{
        "id": 5,
        "freq": 3,
        "card": "Depreciar time",
        "desc": "Deprecia valor do time em até 50 moedas.",
        "uso": "Essa carta diminui o valor do time alvo. É considerado um ataque ao patrocinador do time, uma vez que ele perderá valor em investimento por causa da perda de valor do time."
    },{
        "id": 6,
        "freq": 3,
        "card": "Processa jogador",
        "desc": "Multa jogador alvo em 50 moedas, pagas em 2 dias.",
        "uso": "Escolha um jogador alvo: esse card ataca esse jogador diretamente, aplicando uma multa em seu saldo livre, em 4 rodadas."
    },{
        "id": 7,
        "freq": 1,
        "card": "Compra time",
        "desc": "Remove patrocinador e compra o time. Pague o time em 3x nos próximos dias.",
        "uso": "Força a compra de um time que já possui um patrocinador. Você passa a patrocinar o time, o antigo dono recebe seu valor no saldo livre, e você pagará em 3 parcelas ao longo das próximas rodadas. O card é processado em uma das próximas rodadas."
    },{
        "id": 8,
        "freq": 3,
        "card": "Remix",
        "desc": "No próximo processamento, devolve mão para o deck, embaralha e compra 2 cartas.",
        "uso": "Esse card reembaralha sua mão no deck e compra 2 cartas, efeito imediato. Esta ação pode ser usada caso não queira utilisar no momento sua mão atual, dando uma chance para buscar novas ações. Seu efeito é adicionado a cards em processamento na próxima rodada. Um remix inicial é programado para o jogo das moedas após a fase de leilões, antes dos jogos."
    },{
        "id": 11,
        "freq": 5,
        "card": "Procurar",
        "desc": "Descarte a mão atual e compre 3 cartas.",
        "uso": "Descarta a mão imediatamente e compra 3 cartas. Use após analisar a mão e ter certeza que não deseja mais as cartas que estão disponíveis, pois essa ação não poderá ser revertida."
    }]
    outdb = mongo.db.moedasdeck.find_one_and_update({"tipo": "cartas"},{'$set': {
        "cartas": cartas
    }})
    if outdb:
        current_app.logger.info(f"Editado deck de cartas.")
    else:
        mongo.db.moedasdeck.insert_one({
            "tipo": "cartas",
            "cartas": cartas
        })
        current_app.logger.info(f"Inserido deck de cartas.")

@timeCommands.cli.command("gera_baralho")
# Gera baralho para jogadores das moedas
@click.argument("user")
def gera_baralho(user):
    geraBaralho(user)

def geraBaralho(user):
    cartas = [{
        "id": 0,
        "freq": 40,
        "card": "Dia de folga",
        "desc": "Nenhuma ação por hoje, use outras cartas ou descanse."
    },{
        "id": 1,
        "freq": 30,
        "card": "Ganhe 10",
        "saldo": 10,
        "desc": "Ganhe imediatamente 10 moedas em seu saldo."
    },{
        "id": 9,
        "freq": 10,
        "card": "Ganhe 15",
        "saldo": 15,
        "desc": "Ganhe imediatamente 15 moedas em seu saldo."
    },{
        "id": 2,
        "freq": 8,
        "card": "Peça 50",
        "desc": "Faça um pedido por 50 moedas que chegará em até dois dias."
    },{
        "id": 10,
        "freq": 2,
        "saldo": 500,
        "card": "Empréstimo longo",
        "desc": 'Peça um empréstimo de 500 moedas, pague 550 entre 30 e 50 dias.'
    },{
        "id": 3,
        "freq": 8,
        "card": "Empréstimo a jato",
        "saldo": 200,
        "desc": "Peça por 200 moedas agora, que serão debitadas em 3 dias."
    },{
        "id": 4,
        "freq": 7,
        "card": "All-in",
        "desc": "Adicione a carta a um dos jogos apoiados ou patrocinados para dobrar ganhos, mas dobrar perdas caso haja derrota."
    },{
        "id": 5,
        "freq": 3,
        "card": "Depreciar time",
        "desc": "Deprecia valor do time em até 50 moedas."
    },{
        "id": 6,
        "freq": 3,
        "card": "Processa jogador",
        "desc": "Multa jogador alvo em 50 moedas, pagas em 2 dias."
    },{
        "id": 7,
        "freq": 1,
        "card": "Compra time",
        "desc": "Remove patrocinador e compra o time. Pague o time em 3x nos próximos dias."
    },{
        "id": 8,
        "freq": 3,
        "card": "Remix",
        "desc": "No próximo processamento, devolve mão para o deck, embaralha e compra 2 cartas."
    },{
        "id": 11,
        "freq": 5,
        "card": "Procurar",
        "desc": "Descarte a mão atual e compre 3 cartas."
    }]
    deck = []
    for card in cartas:
        for f in range(card["freq"]):
            deck.append(card)
            
    # mongo.db.moedasdeck.insert_one({
    #     "tipo": "cartas",
    #     "cartas": cartas
    # })

    #moedas = [u for u in mongo.db.moedas.find()]
    pool_inicial = []
    for i in range(5):
        pool_inicial.append({
        "id": 10,
        "freq": 2,
        "saldo": 500,
        "card": "Empréstimo longo",
        "desc": "Peça um empréstimo de 500 moedas, pague 550 entre 30 e 50 dias."
    })
    processa_inicial = [{
        "card": "Remix inicial do jogo, embaralha a mão no deck",
        "cardid": 8,
        "prazo": 0
    }]
    current_app.logger.info(f"Criado deck com {len(deck)} cartas, atribuindo a {user}.")
    random.shuffle(deck)
    checkdb = mongo.db.moedasdeck.find_one({"tipo": "deck","user": user})
    if checkdb:
        current_app.logger.info(f"Deck já existe para {user}.")
    else:
        outdb = mongo.db.moedasdeck.insert_one({
            "tipo": "deck",
            "user": user,
            "deck": deck,
            "pool": pool_inicial,
            "processa": processa_inicial
        })
        if outdb:
            current_app.logger.info(f"Deck criado com sucesso para {user}.")
        else:
            current_app.logger.error(f"Erro na criação do deck.")

def lock_all_users():
    return mongo.db.moedas.update_many(
        {'lock': False},  # Only lock users who aren't already locked
        {'$set': {'lock': True}}
    )

def unlock_all_users():
    return mongo.db.moedas.update_many(
        {},  # Unlock all users
        {'$set': {'lock': False}}
    )

@timeCommands.cli.command("processaPat")
@click.argument("jogos",required=False)
#@click.argument("leilao",required=False)
def processa_pat(jogos='0'):
    if jogos == '0':
        leilao = True
    else:
        leilao = False
    jogos = int(jogos)
    emojis = mongo.db.emoji
    #{"Time" : "Coréia do Sul", "Valor" : 272, "Patrocinador" : "-", "Apoiadores": [] }
    patrocinios = mongo.db.patrocinio
    #{"nome" : "ze1", "valor" : 140, "time" : "Dinamarca", "timestamp" : ISODate...}
    lista_tentarpat = [u for u in mongo.db.tentarpat.find().sort([('time',pymongo.ASCENDING),("valor",pymongo.DESCENDING)])]
    #{"nome" : "ze8", "saldo" : 1000, "bloqueado" : 0, "investido" : 0 }
    moedas = mongo.db.moedas


    # # Emprestimo extra inicial
    # emprestimo_ini = 400
    # #debito = int((1000 + emprestimo_ini*6) / 18)
    # debito = 200
    # if leilao:
    #     moedas.update_many({},{'$inc': {'saldo': emprestimo_ini}})
    #     moedas_log('all',"+"+str(emprestimo_ini),"",0,"Empréstimo inicial")

    # Processamento dos últimos jogos
    if jogos > 0:
        past_jogos = get_next_jogos()['past_jogos'][:jogos]
        prop_derrota = 0.4
        #verify_jogos = get_next_jogos()['next_jogos'][:12]

        # Equivale aos 19 ultimos processamentos
        # if past_jogos[0]['jid'] > 205:
        #     moedas.update_many({},{'$inc': {'saldo': -debito}})
        #     moedas_log('all',"-"+str(debito),"",0,"Pagamento de empréstimo")
        # Cobra juros se negativo, 5%+1
        users_serasa = [u for u in moedas.find({'saldo': {'$lt': 0}})]
        for user in users_serasa:
            saldo = user['saldo']
            debito = int(saldo*0.05) - 1
            moedas.find_one_and_update({'nome': user['nome']},{'$inc': {'saldo': debito}})
            moedas_log(user['nome'],str(debito),"gkbank",0,"Juros")

        # Devolve apoios de jogos impedidos de apoiar
        #for j in (verify_jogos + past_jogos):
        for j in  past_jogos:
            pat1 = patrocinios.find_one({'Time': j['time1']})
            pat2 = patrocinios.find_one({'Time': j['time2']})
            if pat1 and pat2:
                if pat1['Patrocinador'] != '-' and pat2['Patrocinador'] != '-':
                    lista_apoios_1 = pat1.get('Apoiadores')
                    lista_apoios_2 = pat2.get('Apoiadores')
                    if lista_apoios_1 and lista_apoios_2:
                        # Uma lista para remocao da lista 1 e outra para remocao da lista 2
                        remover_a = []
                        remover_b = []
                        for a1 in lista_apoios_1:
                            apoiador = a1['nome']
                            for a2 in lista_apoios_2:
                                if a2['nome'] == apoiador:
                                    if a2['valor'] > a1['valor']:
                                        remover_a.append(apoiador)
                                    elif a2['valor'] < a1['valor']:
                                        remover_b.append(apoiador)
                                    else:
                                        remover_a.append(apoiador)
                                        remover_b.append(apoiador)

                        if remover_a:
                            print(f"Jogo {j['jid']} possui apoiadores a remover: {remover_a}")
                            current_app.logger.info(f"Jogo {j['jid']} possui apoiadores a remover: {remover_a}")
                            for apoiador in remover_a:
                                for a in lista_apoios_1:
                                    if a['nome'] == apoiador:
                                        moedas.find_one_and_update({'nome': apoiador},{'$inc':{'saldo': a['valor'],'investido': -a['valor']}})
                                        moedas_log(a['nome'],"x "+str(a['valor']),j['time1'],j['jid'],"Apoio duplicado impedido")
                                        lista_apoios_1.remove(a)
                                        break
                            outdb1 = patrocinios.find_one_and_update({'Time': j['time1']},{'$set': {"Apoiadores": lista_apoios_1}})
                            if outdb1:
                                current_app.logger.info(f"Apoios duplicados a {j['time1']} removidos")
                            else:
                                current_app.logger.error(f"Erro na remoção de apoios duplicados em {j['time1']}")
                        if remover_b:
                            print(f"Jogo {j['jid']} possui apoiadores a remover: {remover_b}")
                            current_app.logger.info(f"Jogo {j['jid']} possui apoiadores a remover: {remover_b}")
                            for apoiador in remover_b:
                                for a in lista_apoios_2:
                                    if a['nome'] == apoiador:
                                        moedas.find_one_and_update({'nome': apoiador},{'$inc':{'saldo': a['valor'],'investido': -a['valor']}})
                                        moedas_log(a['nome'],"x "+str(a['valor']),j['time2'],j['jid'],"Apoio duplicado impedido")
                                        lista_apoios_2.remove(a)
                                        break
                            outdb2 = patrocinios.find_one_and_update({'Time': j['time2']},{'$set': {"Apoiadores": lista_apoios_2}})
                            if outdb2:
                                current_app.logger.info(f"Apoios duplicados a {j['time2']} removidos")
                            else:
                                current_app.logger.error(f"Erro na remoção de apoios duplicados em {j['time2']}")

        # Processamento dos jogos
        for jogo in past_jogos:
            jogoDb = mongo.db.jogos.find_one({'Ano': ANO, 'Jogo': jogo['jid']})
            if not jogoDb:
                print("Erro ao buscar jogo")
            elif jogoDb.get('processado'):
                print(f"Jogo {jogo['jid']} já foi processado.")
                break
            else:
                if jogo['vitoria'] == 'empate':
                    lista_m = [int(jogo['moedas_em_jogo']/3),int(jogo['moedas_em_jogo']/3)]
                else:
                    if jogo['vitoria'] == jogo['time1']:
                        lista_m = [jogo['moedas_em_jogo'],-jogo['moedas_em_jogo']]
                    else:
                        lista_m = [-jogo['moedas_em_jogo'],jogo['moedas_em_jogo']]
                lista_t = [(jogo['time1'],lista_m[0],jogo['time2']),(jogo['time2'],lista_m[1],jogo['time1'])]
                for t,moeda_ganha,tadv in lista_t:
                    # Atualização do valor do time
                    inc_invest = int(moeda_ganha*prop_derrota)
                    patDb = patrocinios.find_one_and_update({'Time': t},{'$inc': {'Valor': inc_invest}})
                    # Atualizaçao nos valores de cada jogador
                    if patDb['Patrocinador'] != '-':
                        lista_apoios = patDb.get('Apoiadores')
                        if moeda_ganha > 0:
                            moedas.find_one_and_update({'nome': patDb['Patrocinador']},{'$inc':{'investido': inc_invest,'saldo': moeda_ganha}})
                            moedas_log(patDb['Patrocinador'],"+"+str(moeda_ganha),t,jogo['jid'],"Jogo de time patrocinado")
                            moedas_log(patDb['Patrocinador'],"i+"+str(inc_invest),t,jogo['jid'],"Ganho de valor patrocinado")
                        else:
                            moedas.find_one_and_update({'nome': patDb['Patrocinador']},{'$inc':{'investido': inc_invest}})
                            moedas_log(patDb['Patrocinador'],"i"+str(inc_invest),t,jogo['jid'],"Perda de valor patrocinado")
                        # Se all-in
                        if jogo['allin']:
                            if moeda_ganha > 0:
                                moeda_allin = moeda_ganha
                                moeda_str = "+" + str(moeda_allin)
                            else:
                                moeda_allin = int(prop_derrota*moeda_ganha)
                                moeda_str = str(moeda_allin)
                            nomes_apoios = []
                            max_allin = {patDb['Patrocinador']: 1}
                            if lista_apoios:
                                for ap in lista_apoios:
                                    nomes_apoios.append(ap['nome'])
                                    if ap['valor'] >= jogo['moedas_em_jogo']:
                                        proporc = 1
                                    else:
                                        proporc = ap['valor']/jogo['moedas_em_jogo']
                                    max_allin[ap['nome']] = proporc
                            # Selecao dos que apostaram no patrocinador
                            for apost in jogo['allin']:
                                if apost == patDb['Patrocinador'] or apost in nomes_apoios:
                                    moeda_allin = int(max_allin[apost]*moeda_allin)
                                    moedas.find_one_and_update({'nome': apost},{'$inc':{'saldo': moeda_allin}})
                                    moedas_log(apost,moeda_str,"card4",jogo['jid'],"Card All-in")
                                    mongo.db.moedasdeck.find_one_and_delete({"tipo": "allin","nome": apost})
                        # Processamento da lista de apoios
                        if lista_apoios:
                            apoios_taxa =  0
                            # Calculo da taxa de apoio
                            if moeda_ganha < 100:
                                percent_taxa = 0.1
                            elif moeda_ganha < 1000:
                                percent_taxa = 97/900 - 7*moeda_ganha/90000
                            else:
                                percent_taxa = 0.03
                            # Ganho para cada apoiador
                            for a in lista_apoios:
                                valor_max = moeda_ganha
                                if moeda_ganha > a['valor']:
                                    valor_max = a['valor']
                                # Se perda, perda no valor do patrocinio
                                if moeda_ganha < 0:
                                    moeda_perdida = int(moeda_ganha*prop_derrota - 1)
                                    novo_valor_apoio = a['valor'] + moeda_perdida
                                    if novo_valor_apoio <=0:
                                        moedas.find_one_and_update({'nome': a['nome']},{'$inc':{'investido': -a['valor']}})
                                        moedas_log(a['nome'],"x"+str(-a['valor']),t,jogo['jid'],"Perda de apoio ao time")
                                        lista_apoios.remove(a)
                                    else:
                                        moedas.find_one_and_update({'nome': a['nome']},{'$inc':{'investido': moeda_perdida}})
                                        moedas_log(a['nome'],"i"+str(moeda_perdida),t,jogo['jid'],"Perda parcial do apoio ao time")
                                        a['valor'] = novo_valor_apoio
                                # Se ganho, incrementa saldo e +x% ao patrocinador
                                else:
                                    advDb = patrocinios.find_one({'Time': tadv})
                                    patadversario = advDb['Patrocinador']
                                    if a['nome'] != patadversario:
                                        valor_apoio = valor_max
                                        apoios_taxa += int(valor_max*percent_taxa + 1)
                                        moedas.find_one_and_update({'nome': a['nome']},{'$inc':{'saldo': valor_apoio}})
                                        moedas_log(a['nome'],"+"+str(valor_apoio),t,jogo['jid'],"Jogo de time apoiado")
                                    else:
                                        moedas.find_one_and_update({'nome': a['nome']},{'$inc':{'saldo': a['valor'],'investido': -a['valor']}})
                                        moedas_log(a['nome'],"x "+str(a['valor']),t,jogo['jid'],"Impedido de apoiar jogo")
                                        lista_apoios.remove(a)
                            # Adiciona taxa de apoios ao patrocinador e atualiza apoios
                            if apoios_taxa > 0:
                                moedas.find_one_and_update({'nome': patDb['Patrocinador']},{'$inc':{'saldo': apoios_taxa}})
                                moedas_log(patDb['Patrocinador'],"+"+str(apoios_taxa),t,jogo['jid'],"Taxa de apoios")
                            patrocinios.find_one_and_update({'Time': t},{'$set': {'Apoiadores': lista_apoios}})
                # Escreve jogo como processado
                mongo.db.jogos.find_one_and_update({'Ano': ANO, 'Jogo': jogo['jid']},{'$set': {'moedas_em_jogo': jogo['moedas_em_jogo'],'processado': True}})

    # Processamento da lista de patrocinios no leilao
    # impedidos = []
    # patrocinados = []
    # patok = []
    texto_imp = ""
    texto_pat = ""
    if lista_tentarpat:
        palpites = []
        time_atual = ""
        lista_t_p = []
        next_lista_pat = []
        for p in lista_tentarpat:
            if p['time'] == time_atual:
                lista_t_p.append(p)
            else:
                if time_atual:
                    palpites.append({'time': time_atual, 'palpites': lista_t_p})
                lista_t_p = [p]
                time_atual = p['time']
        if time_atual:
            palpites.append({'time': time_atual, 'palpites': lista_t_p})
        #print(palpites)
        for t in palpites:
            ganhador = ""
            et = emojis.find_one({'País': t['time']})['flag']
            if len(t['palpites']) == 1:
                p = t['palpites'][0]
                if p.get('processar'):
                    ganhador = p
                else:
                    texto_imp+=f"{p['nome']} deu o lance líder do dia em {t['time']} por {p['valor']}🪙.\n"
                    moedas_log(p['nome'],"l "+str(p['valor']),t['time'],0,"Lance líder do dia")
                    next_lista_pat.append({'time': t['time'],'nome': p['nome'],'valor':p['valor'],'processar': True})
            else:
                if t['palpites'][0]['valor'] != t['palpites'][1]['valor']:
                    p = t['palpites'][0]
                    if p.get('processar'):
                        ganhador = p
                        t['palpites'].remove(p)
                    else:
                        t['palpites'].remove(p)
                        texto_imp+=f"{p['nome']} deu o lance líder do dia em {et} {t['time']} por {p['valor']}🪙.\n"
                        moedas_log(p['nome'],"l "+str(p['valor']),t['time'],0,"Lance líder do dia")
                        next_lista_pat.append({'time': t['time'],'nome': p['nome'],'valor':p['valor'],'processar': True})
                for p in t['palpites']:
                    texto_imp+=f"{p['nome']} tentou patrocinar {et} {t['time']} por {p['valor']}🪙.\n"
                    moedas_log(p['nome'],"x "+str(p['valor']),t['time'],0,"Não conseguiu patrocinar")
                    moedas.find_one_and_update({'nome': p['nome']}, {'$inc': {'saldo': p['valor'],'bloqueado': -p['valor']}})
            if ganhador:
                # Checa se time nao estava a venda
                outpat = mongo.db.patrocinio.find_one({'Time': ganhador['time']})
                if outpat:
                    if outpat["Patrocinador"] != "-":
                        if outpat.get('avenda'):
                            vendedor = outpat['Patrocinador']
                            valorat = outpat['Valor']
                            texto_pat+=f"{ganhador['nome']} conseguiu patrocinar {et} {ganhador['time']} vendido por {vendedor} por {ganhador['valor']}🪙\n"
                            moedas_log(ganhador['nome'],"i "+str(ganhador['valor']),ganhador['time'],0,"Comprou patrocinado")
                            moedas.find_one_and_update({'nome': ganhador['nome']}, {'$inc': {'bloqueado': -ganhador['valor'],'investido': ganhador['valor']}})
                            patrocinios.find_one_and_update({'Time': ganhador['time']}, {'$set': {'Patrocinador': ganhador['nome'],'Valor': ganhador['valor'],'avenda': ""}})
                            moedas_log(vendedor,"v "+str(ganhador['valor']),ganhador['time'],0,"Venda de time")
                            moedas.find_one_and_update({'nome': vendedor},{'$inc': {'saldo': ganhador['valor'],'investido': -valorat}})
                        else:
                            moedas_log(ganhador['nome'],"x "+str(ganhador['valor']),ganhador['time'],0,"Venda cancelada")
                            moedas.find_one_and_update({'nome': ganhador['nome']}, {'$inc': {'saldo': ganhador['valor'],'bloqueado': -ganhador['valor']}})
                    else:
                        texto_pat+=f"{ganhador['nome']} conseguiu patrocinar {et} {ganhador['time']} por {ganhador['valor']}🪙\n"
                        moedas_log(ganhador['nome'],"i "+str(ganhador['valor']),ganhador['time'],0,"Conseguiu patrocinar")
                        moedas.find_one_and_update({'nome': ganhador['nome']}, {'$inc': {'bloqueado': -ganhador['valor'],'investido': ganhador['valor']}})
                        patrocinios.find_one_and_update({'Time': ganhador['time']}, {'$set': {'Patrocinador': ganhador['nome'],'Valor': ganhador['valor']}})
                else:
                    moedas_log(ganhador['nome'],"x "+str(ganhador['valor']),ganhador['time'],0,"Time desclassificado")
                    moedas.find_one_and_update({'nome': ganhador['nome']}, {'$inc': {'bloqueado': -ganhador['valor'],'saldo': ganhador['valor']}})



        mongo.db.tentarpat.drop()
        if next_lista_pat:
            mongo.db.tentarpat.insert_many(next_lista_pat)
            
    # Envio de mensagem
    if texto_imp or texto_pat:
        mensagem="🪙 PATROCÍNIOS DO DIA 🪙\n"
        if texto_imp:
            mensagem+= "\n=> Tentativas:\n"
            mensagem+=texto_imp
        if texto_pat:
            mensagem+= "\n=> Finalizadas:\n"
            mensagem+=texto_pat
        print(mensagem)
        if TELEGRAM:
            print("Enviando mensagem via telegram")
            params = {
                'chat_id': TELEGRAM_CHAT_ID,
                'text': mensagem
            }
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            r = requests.get(url, params=params)
            if r.status_code == 200:
                print(json.dumps(r.json(), indent=2))
            else:
                r.raise_for_status()
    else:
        print("Sem patrocinadores novos hoje.")

    # Secao deck e cards
    if jogos > 0:
        lock_all_users()
        try:
            processa_cards()
        except:
            current_app.logger.error("Erro no processamento de cartas.")
            if TELEGRAM:
                params = {
                'chat_id': TELEGRAM_CHAT_ID,
                'text': "🚨⚠️ Erro ao processar moedas, verificar."
                }
                url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                r = requests.get(url, params=params)
                if r.status_code == 200:
                    print(json.dumps(r.json(), indent=2))
                else:
                    r.raise_for_status()
        finally:
            unlock_all_users()
        ranking_moedas()

@timeCommands.cli.command("processaCards")
def processaCards():
    processa_cards()

def processa_cards():
    lista_deck = [u for u in mongo.db.moedasdeck.find({"tipo": "deck"})]
    mensagemc = ""
    last_game = progress_data()['last_game']
    #print(lista_deck)
    # { "tipo": "deck", "user": user['nome'], "deck": deck, "pool": [], "processa": [] }
    for d in lista_deck:
        usuario = d["user"]
        deck = d["deck"]
        new_card = deck.pop()
        pool = d["pool"]
        pool.append(new_card)
        moedas = mongo.db.moedas.find_one({"nome": usuario})
        # pool.append({
        #     "id": 4,
        #     "freq": 7,
        #     "card": "All-in",
        #     "desc": "Adicione a carta a um dos jogos apoiados ou patrocinados para dobrar ganhos, mas perder todo o valor em jogo caso haja derrota."
        # })
        if len(pool) > 5:
            card_descartado = pool.pop(0)
            id_card = card_descartado['id']
            if id_card > 0:
                moedas_log(usuario,"x","card"+str(id_card),0,"Card descartado")
        processar = d["processa"]
        divida_add = 0
        remix =  False
        for c in processar:
            if last_game >= 212:
                c['prazo'] = -1
            else:
                c['prazo'] -= 1
            # Executa acao
            if c['prazo'] < 0:
                if c["cardid"] == 2: # Peça 50
                    mongo.db.moedas.find_one_and_update({'nome': usuario},{'$inc':{'saldo': c['saldo']}})
                    moedas_log(usuario,"+"+str(c['saldo']),"card"+str(c["cardid"]),0,f"Card +{c['saldo']}")
                elif c["cardid"] in [3,10,77]: # Empréstimo a jato # Emprestimo longo # destituir pat
                    mongo.db.moedas.find_one_and_update({'nome': usuario},{'$inc':{'saldo': c['saldo']}})
                    moedas_log(usuario,str(c['saldo']),"card"+str(c["cardid"]),0,"Card empréstimo")
                elif c["cardid"] == 5: # Depreciar time
                    time_alvo = c['alvo']
                    #{"Time" : "Coréia do Sul", "Valor" : 272, "Patrocinador" : "-", "Apoiadores": [] }
                    patrocinio = mongo.db.patrocinio.find_one({"Time": time_alvo})
                    if patrocinio:
                        patrocinador = patrocinio["Patrocinador"]
                        #apoiadores = patrocinio.get("Apoiadores")
                        valor = patrocinio["Valor"]
                        if valor > 100:
                            novo_valor = valor - 50
                        else:
                            novo_valor = int(valor/2)
                        mongo.db.patrocinio.find_one_and_update({"Time": time_alvo},{'$set': {"Valor": novo_valor}})
                        if patrocinador != "-":
                            mongo.db.moedas.find_one_and_update({'nome': patrocinador},{'$inc':{'investido': novo_valor - valor}})
                            moedas_log(patrocinador,"i"+str(novo_valor - valor),time_alvo,0,f"Card de {usuario} deprecia patrocinio")
                            user = mongo.db.users.find_one({"active": True,"gokopa": True, "name": usuario})
                            if user.get("telegram"):
                                user1 = user.get("telegram")
                            else:
                                user1 = usuario
                            userp = mongo.db.users.find_one({"active": True,"gokopa": True, "name": patrocinador})
                            if userp.get("telegram"):
                                user2 = userp.get("telegram")
                            else:
                                user2 = patrocinador
                            mensagemc += f"\n💥💸 O time {time_alvo} perdeu valor, um ataque de {user1} a {user2}"
                elif c["cardid"] == 6: # Processa jogador
                    jogador_alvo = c['alvo']
                    mongo.db.moedas.find_one_and_update({'nome': jogador_alvo},{'$inc':{'saldo': c['saldo']}})
                    moedas_log(jogador_alvo,str(c['saldo']),"card"+str(c["cardid"]),0,f"Jogador {usuario} processou multa")
                    user = mongo.db.users.find_one({"active": True,"gokopa": True, "name": usuario})
                    if user.get("telegram"):
                        user1 = user.get("telegram")
                    else:
                        user1 = usuario
                    usert = mongo.db.users.find_one({"active": True,"gokopa": True, "name": jogador_alvo})
                    if usert.get("telegram"):
                        user2 = usert.get("telegram")
                    else:
                        user2 = jogador_alvo
                    mensagemc += f"\n💥💰 Jogador {user1} aplicou multa a {user2}"
                elif c["cardid"] == 8: # Remix
                    remix = True
                elif c["cardid"] == 7: # Destituir patrocinador
                    time_alvo = c['alvo']
                    #{"Time" : "Coréia do Sul", "Valor" : 272, "Patrocinador" : "-", "Apoiadores": [] }
                    patrocinio = mongo.db.patrocinio.find_one({"Time": time_alvo})
                    if patrocinio:
                        patrocinador = patrocinio["Patrocinador"]
                        valor = patrocinio["Valor"]
                        apoiadores = patrocinio.get("Apoiadores")
                        # Troca patrocinador
                        if patrocinador != "-":
                            if apoiadores:
                                if usuario in apoiadores:
                                    # Devolve apoio do usuario
                                    mongo.db.moedas.find_one_and_update({'nome': usuario},{'$inc':{'saldo': valor, 'investido': -valor}})
                                    moedas_log(usuario,"x "+str(valor),time_alvo,0,"Devolução de apoio")
                                    apoiadores.remove(usuario)
                            mongo.db.patrocinio.find_one_and_update({"Time": time_alvo},{'$set': {"Patrocinador": usuario,"Apoiadores": apoiadores}})
                            mongo.db.moedas.find_one_and_update({'nome': patrocinador},{'$inc':{'investido': -valor, 'saldo': valor}})
                            moedas_log(patrocinador,"x "+str(valor),time_alvo,0,f"Card de {usuario} destitui patrocinio")
                            mongo.db.moedas.find_one_and_update({'nome': usuario},{'$inc':{'investido': valor}})
                            moedas_log(usuario,"i "+str(valor),time_alvo,0,f"Card comprou patrocinio")
                            user = mongo.db.users.find_one({"active": True,"gokopa": True, "name": usuario})
                            divida_add += valor
                            if user.get("telegram"):
                                user1 = user.get("telegram")
                            else:
                                user1 = usuario
                            usert = mongo.db.users.find_one({"active": True,"gokopa": True, "name": patrocinador})
                            if usert.get("telegram"):
                                user2 = usert.get("telegram")
                            else:
                                user2 = patrocinador
                            mensagemc += f"\n💥🚫 Jogador {user1} destituiu patrocinador {user2} de time {time_alvo}!"
        if divida_add > 0:
            # 3 parcelas da divida do time
            processar.append({
                "card": "Destituição de time",
                "cardid": 77,
                "prazo": random.randint(2,8),
                "saldo": int(- divida_add / 3) - (divida_add % 3)
            })
            processar.append({
                "card": "Destituição de time",
                "cardid": 77,
                "prazo": random.randint(9,14),
                "saldo": int(- divida_add / 3)
            })
            processar.append({
                "card": "Destituição de time",
                "cardid": 77,
                "prazo": random.randint(15,20),
                "saldo": int(- divida_add / 3)
            })
        # Limpar cartas gastas
        meu_debito = 0
        for c in processar[:]:
            if c['prazo'] < 0:
                processar.remove(c)
            else:
                saldoc = c.get('saldo')
                if saldoc:
                    meu_debito += saldoc
        if remix:
            deck = deck + pool
            random.shuffle(deck)
            pool = [deck.pop(),deck.pop()]
        # atualiza debito
        if meu_debito != moedas['divida']:
            mongo.db.moedas.find_one_and_update({"nome": usuario},{'$set': {'divida': meu_debito}})
        mongo.db.moedasdeck.find_one_and_update({"tipo": "deck","user": usuario},{'$set': {"deck": deck, "pool": pool, "processa": processar}})

    # Envia mensagem final
    if mensagemc:
        envia_msg = "⚽♠️ Cartas de ação" + mensagemc
        print(envia_msg)
        if TELEGRAM:
            print("Enviando mensagem via telegram")
            params = {
                'chat_id': TELEGRAM_CHAT_ID,
                'text': envia_msg
            }
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            r = requests.get(url, params=params)
            if r.status_code == 200:
                print(json.dumps(r.json(), indent=2))
            else:
                r.raise_for_status()


#@timeCommands.cli.command("rankingMoedas")
def ranking_moedas():
    ranking_moedas = get_moedas_board()['moedas_board']
    mensagem = "== Ranking de moedas ==\n"
    for j in ranking_moedas:
        mensagem+=f"{j['pos']}  {j['total']}🪙 - {j['nome']}\n"
    print(mensagem)
    if TELEGRAM:
        print("Enviando mensagem via telegram")
        params = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': mensagem
        }
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        r = requests.get(url, params=params)
        if r.status_code == 200:
            print(json.dumps(r.json(), indent=2))
        else:
            r.raise_for_status()

