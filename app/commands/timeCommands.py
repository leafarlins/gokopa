import json
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

from app.routes.backend import get_moedas_board, get_next_jogos, moedas_log
from ..extentions.database import mongo
from flask import Blueprint

SEPARADOR_CSV=","
ANO=21
RANKING='20-4'
TELEGRAM_TOKEN=os.getenv('TELEGRAM_TKN')
TELEGRAM_CHAT_ID=os.getenv('TELEGRAM_CHAT_ID')

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
    timeCollection.insert(data)
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
            data.append(documento)

        if not data:
            print("Sem dados.")
            return None
        
        #print(data)
    
    
    # question = input(f'Deseja inserir os dados impressos? (S/N) ')
    # if question.upper() == "S":
    timeCollection = mongo.db.timehistory
    timeCollection.insert(data)
    print("Dados inseridos")
    # else:
    #     exit()


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
    timeCollection.insert(data)


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
@click.argument("time")
@click.argument("desc")
def edit_time(time,desc):
    timeValid = mongo.db.ranking.find_one({"ed": RANKING,'time': time})
    if timeValid:
        print(f'Definindo time {time} em {desc}')
    else:
        print(f'Time {time} nao valido.')
        exit()

    ano20_jogos = mongo.db.jogos.find({'Ano': ANO}).sort("Jogo",pymongo.ASCENDING)
    for j in ano20_jogos:
        if j['desc1'] == desc:
            novo_jogo = mongo.db.jogos.find_one_and_update(
                {"_id": ObjectId(j['_id'])},
                {'$set': {'Time1': time}},return_document=ReturnDocument.AFTER)
            print(novo_jogo)
        elif j['desc2'] == desc:
            novo_jogo = mongo.db.jogos.find_one_and_update(
                {"_id": ObjectId(j['_id'])},
                {'$set': {'Time2': time}},return_document=ReturnDocument.AFTER)
            print(novo_jogo)
    print("Finalizado.")

# Para classificação da copa de acordo com confederação
@timeCommands.cli.command("classificaTime")
@click.argument("time")
@click.argument("conf")
def classifica_time(time,conf):
    timeValid = mongo.db.ranking.find_one({"ed": RANKING,'time': time})
    if timeValid:
        print(f'Classificando time {time} em {conf}')
    else:
        print(f'Time {time} nao valido.')
        exit()

    classificado = dict()
    classificado['Ano'] = ANO
    classificado['nome'] = time
    classificado['conf'] = conf

    mongo.db.pot.insert([classificado])
    print("Finalizado.")

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
    mongo.db.historico.insert([ano_hist])

@timeCommands.cli.command("defPot")
@click.argument("time")
@click.argument("pot")
def classifica_time(time,pot):
    timeValid = mongo.db.ranking.find_one({"ed": RANKING,'time': time})
    if timeValid:
        print(f'Definindo para time {time} pot {pot}')
    else:
        print(f'Time {time} nao valido.')
        exit()

    itemdb = mongo.db.pot.find_one_and_update({"Ano": ANO, "nome": time},{'$set': {"pot": int(pot),"sorteado": False}})
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
    jogosCollection.insert(data)
    print("Dados inseridos")

@timeCommands.cli.command("exec")
def exec():
    mongo.db.moedas.find_one_and_update({'nome': 'ze1'},{'$set': {'saldo': 0, 'bloqueado': 0, 'investido': 1000}})
    #mongo.db.patrocinio.find_one_and_update({'Time': 'Holanda'},{'$set': {"Patrocinador" : "-"}})
    #mongo.db.tentarpat.find_one_and_update({'valor':500},{'$set': {'valor':0}})

def processa_jogos():


@timeCommands.cli.command("processaPat")
@click.argument("jogos",required=False)
def processa_pat(jogos=0):
    emojis = mongo.db.emoji
    #{"Time" : "Coréia do Sul", "Valor" : 272, "Patrocinador" : "-", "Apoiadores": [] }
    patrocinios = mongo.db.patrocinio
    #{"nome" : "ze1", "valor" : 140, "time" : "Dinamarca", "timestamp" : ISODate...}
    lista_tentarpat = [u for u in mongo.db.tentarpat.find().sort([('time',pymongo.ASCENDING),("valor",pymongo.DESCENDING)])]
    #{"nome" : "ze8", "saldo" : 1000, "bloqueado" : 0, "investido" : 0 }
    moedas = mongo.db.moedas

    # Processamento dos últimos jogos
    if jogos > 0:
        past_jogos = get_next_jogos()['past_jogos'][:jogos]
        for jogo in past_jogos:
            if jogo['vitoria'] == 'empate':
                moedas_ganhas = int(jogo['moedas_em_jogo']/3)
                lista_t = [jogo['time1'],jogo['time2']]
            else:
                moedas_ganhas = jogo['moedas_em_jogo']
                lista_t = [jogo['vitoria']]
            for t in lista_t:
                patDb = patrocinios.find_one_and_update({'Time': t},{'$inc': {'Valor': moedas_ganhas}})
                if patDb['Patrocinador'] != '-':
                    moedas.find_one_and_update({'nome': patDb['Patrocinador']},{'$inc':{'investido': moedas_ganhas,'saldo': moedas_ganhas}})
                    apoios_taxa =  0
                    for a in patDb['Apoiadores']:
                        moedas.find_one_and_update({'nome': patDb['Patrocinador']},{'$inc':{'investido': moedas_ganhas,'saldo': moedas_ganhas}})






    impedidos = []
    patrocinados = []
    patok = []
    texto_imp = ""
    texto_pat = ""
    for j in range(len(lista_tentarpat)-1):
        time = lista_tentarpat[j]['time']
        print(lista_tentarpat[j]['valor'],time)
        if lista_tentarpat[j]['valor'] == lista_tentarpat[j+1]['valor'] and time == lista_tentarpat[j+1]['time'] and time not in patok:
            print(f'Impedido patrocinio de {time}')
            impedidos.append(time)
        elif time not in patok:
            patok.append(time)
    for t in lista_tentarpat:
        et = emojis.find_one({'País': t['time']})['flag']
        if t['time'] in impedidos or t['time'] in patrocinados:
            texto_imp+=f"{t['nome']} tentou patrocinar {et} {t['time']} por {t['valor']}🪙.\n"
            moedas_log(t['nome'],"x "+str(t['valor']),t['time'],"Não conseguiu patrocinar.")
            moedas.find_one_and_update({'nome': t['nome']}, {'$inc': {'saldo': t['valor'],'bloqueado': -t['valor']}})
        else:
            texto_pat+=f"{t['nome']} conseguiu patrocinar {et} {t['time']} por {t['valor']}🪙!\n"
            moedas_log(t['nome'],"i "+str(t['valor']),t['time'],"Conseguiu patrocinar.")
            patrocinados.append(t['time'])
            moedas.find_one_and_update({'nome': t['nome']}, {'$inc': {'bloqueado': -t['valor'],'investido': t['valor']}})
            patrocinios.find_one_and_update({'Time': t['time']}, {'$set': {'Patrocinador': t['nome'],'Valor': t['valor']}})
    mongo.db.tentarpat.drop()

    if texto_imp or texto_pat:
        mensagem="🪙 PATROCÍNIOS DO DIA 🪙\n"
        if texto_imp:
            mensagem+= "\n=> Sem sucesso :T\n"
            mensagem+=texto_imp
        if texto_pat:
            mensagem+= "\n=> Com sucesso :)\n"
            mensagem+=texto_pat
        print(mensagem)
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
    ranking_moedas()

#@timeCommands.cli.command("rankingMoedas")
def ranking_moedas():
    ranking_moedas = get_moedas_board()['moedas_board']
    mensagem = "== Ranking de moedas ==\n"
    for j in ranking_moedas:
        mensagem+=f"{j['pos']}  {j['total']}🪙 - {j['nome']}\n"
    print(mensagem)
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


    
