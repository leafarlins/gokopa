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

from app.routes.backend import get_moedas_board, get_next_jogos, get_pat_teams, moedas_log
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
@click.argument("desc")
@click.argument("time")
def edit_time(desc,time):
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
    #mongo.db.moedas.find_one_and_update({'nome': 'ze1'},{'$set': {'saldo': 0, 'bloqueado': 0, 'investido': 1000}})
    #mongo.db.patrocinio.find_one_and_update({'Time': 'Holanda'},{'$set': {"Patrocinador" : "-"}})
    #mongo.db.tentarpat.find_one_and_update({'valor':500},{'$set': {'valor':0}})
    mongo.db.patrocinio.find_and_modify({'Time': 'Holanda'},{'$set': {'Patrocinador': "-"}})

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

@timeCommands.cli.command("processaPat")
@click.argument("jogos",required=False)
@click.argument("leilao",required=False)
def processa_pat(jogos='0',leilao=False):
    telegram = False
    if leilao == 'true':
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

    # Processamento dos últimos jogos
    if jogos > 0:
        past_jogos = get_next_jogos()['past_jogos'][:jogos]

        # Debito de saldo parado
        if past_jogos[0]['jid'] > 16 and past_jogos[0]['jid'] < 61:
            debito_parado = int(past_jogos[0]['jid']*2-30)
        else:
            debito_parado = 0
        if debito_parado > 0:
            lista_moedas = [u for u in moedas.find()]
            for user in lista_moedas:
                if user['saldo'] > 0:
                    deb_saldo = debito_parado
                    if deb_saldo > user['saldo']:
                        deb_saldo = user['saldo']
                    moedas.find_one_and_update({'nome': user['nome']},{'$inc': {'saldo': -deb_saldo}})
                    moedas_log(user['nome'],"-"+str(deb_saldo),"",0,"Débido de saldo parado")

        # Processamento dos jogos
        for jogo in past_jogos:
            jogoDb = mongo.db.jogos.find_one({'Ano': ANO, 'Jogo': jogo['jid']})
            if not jogoDb:
                print("Erro ao buscar jogo")
            elif jogoDb.get('processado'):
                print(f"Jogo {jogo['jid']} já foi processado.")
                quit(0)
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
                    patDb = patrocinios.find_one_and_update({'Time': t},{'$inc': {'Valor': moeda_ganha}})
                    # Atualizaçao nos valores de cada jogador
                    if patDb['Patrocinador'] != '-':
                        if moeda_ganha > 0:
                            moedas.find_one_and_update({'nome': patDb['Patrocinador']},{'$inc':{'investido': moeda_ganha,'saldo': moeda_ganha}})
                            moedas_log(patDb['Patrocinador'],"+"+str(moeda_ganha),t,jogo['jid'],"Jogo de time patrocinado")
                            moedas_log(patDb['Patrocinador'],"i+"+str(moeda_ganha),t,jogo['jid'],"Ganho de valor patrocinado")
                        else:
                            moedas.find_one_and_update({'nome': patDb['Patrocinador']},{'$inc':{'investido': moeda_ganha}})
                            moedas_log(patDb['Patrocinador'],"i"+str(moeda_ganha),t,jogo['jid'],"Perda de valor patrocinado")
                        # Processamento da lista de apoios
                        lista_apoios = patDb.get('Apoiadores')
                        if lista_apoios:
                            apoios_taxa =  0
                            for a in lista_apoios:
                                valor_max = moeda_ganha
                                if moeda_ganha > a['valor']:
                                    valor_max = a['valor']
                                # Se perda, perda no valor do patrocinio
                                if moeda_ganha < 0:
                                    novo_valor_apoio = a['valor'] + moeda_ganha
                                    if novo_valor_apoio <=0:
                                        moedas.find_one_and_update({'nome': a['nome']},{'$inc':{'investido': -a['valor']}})
                                        moedas_log(a['nome'],"x"+str(-a['valor']),t,jogo['jid'],"Perda de apoio ao time")
                                        lista_apoios.remove(a)
                                    else:
                                        moedas.find_one_and_update({'nome': a['nome']},{'$inc':{'investido': moeda_ganha}})
                                        moedas_log(a['nome'],"i"+str(moeda_ganha),t,jogo['jid'],"Perda parcial do apoio ao time")
                                        a['valor'] = novo_valor_apoio
                                # Se ganho, incrementa saldo apos debitar 10%
                                else:
                                    advDb = patrocinios.find_one({'Time': tadv})
                                    patadversario = advDb['Patrocinador']
                                    if a['nome'] != patadversario:
                                        valor_apoio = int(valor_max*90/100)
                                        apoios_taxa += valor_max - valor_apoio
                                        moedas.find_one_and_update({'nome': a['nome']},{'$inc':{'saldo': valor_apoio}})
                                        moedas_log(a['nome'],"+"+str(valor_apoio),t,jogo['jid'],"Jogo de time apoiado")
                                    else:
                                        moedas.find_one_and_update({'nome': a['nome']},{'$inc':{'saldo': a['valor'],'investido': -a['valor']}})
                                        moedas_log(a['nome'],"x "+str(a['valor']),t,jogo['jid'],"Impedido de apoiar jogo")
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
                if leilao:
                    if p.get('processar'):
                        ganhador = p
                    else:
                        texto_imp+=f"{p['nome']} deu o lance líder do dia em {t['time']} por {p['valor']}🪙.\n"
                        moedas_log(p['nome'],"l "+str(p['valor']),t['time'],0,"Lance líder do dia")
                        next_lista_pat.append({'time': t['time'],'nome': p['nome'],'valor':p['valor'],'processar': True})
                else:
                    ganhador = p
            else:
                if t['palpites'][0]['valor'] != t['palpites'][1]['valor']:
                    p = t['palpites'][0]
                    if leilao:
                        if p.get('processar'):
                            ganhador = p
                            t['palpites'].remove(p)
                        else:
                            t['palpites'].remove(p)
                            texto_imp+=f"{p['nome']} deu o lance líder do dia em {et} {t['time']} por {p['valor']}🪙.\n"
                            moedas_log(p['nome'],"l "+str(p['valor']),t['time'],0,"Lance líder do dia")
                            next_lista_pat.append({'time': t['time'],'nome': p['nome'],'valor':p['valor'],'processar': True})
                    else:
                        ganhador = p
                        t['palpites'].remove(p)
                for p in t['palpites']:
                    texto_imp+=f"{p['nome']} tentou patrocinar {et} {t['time']} por {p['valor']}🪙.\n"
                    moedas_log(p['nome'],"x "+str(p['valor']),t['time'],0,"Não conseguiu patrocinar")
                    moedas.find_one_and_update({'nome': p['nome']}, {'$inc': {'saldo': p['valor'],'bloqueado': -p['valor']}})
            if ganhador:
                texto_pat+=f"{ganhador['nome']} conseguiu patrocinar {et} {ganhador['time']} por {ganhador['valor']}🪙!\n"
                moedas_log(ganhador['nome'],"i "+str(ganhador['valor']),ganhador['time'],0,"Conseguiu patrocinar")
                moedas.find_one_and_update({'nome': ganhador['nome']}, {'$inc': {'bloqueado': -ganhador['valor'],'investido': ganhador['valor']}})
                patrocinios.find_one_and_update({'Time': ganhador['time']}, {'$set': {'Patrocinador': ganhador['nome'],'Valor': ganhador['valor']}})


        mongo.db.tentarpat.drop()
        if leilao and next_lista_pat:
            mongo.db.tentarpat.insert_many(next_lista_pat)
            
    # Envio de mensagem
    if texto_imp or texto_pat:
        mensagem="🪙 PATROCÍNIOS DO DIA 🪙\n"
        if texto_imp:
            mensagem+= "\n=> Sem sucesso:\n"
            mensagem+=texto_imp
        if texto_pat:
            mensagem+= "\n=> Com sucesso:\n"
            mensagem+=texto_pat
        print(mensagem)
        if telegram:
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
    telegram=False
    ranking_moedas = get_moedas_board()['moedas_board']
    mensagem = "== Ranking de moedas ==\n"
    for j in ranking_moedas:
        mensagem+=f"{j['pos']}  {j['total']}🪙 - {j['nome']}\n"
    print(mensagem)
    if telegram:
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

# Impedir apoio contra proprio patrocinio
@timeCommands.cli.command("verificaTimes")
def verifica_times():
    pat_teams = get_pat_teams()

    
