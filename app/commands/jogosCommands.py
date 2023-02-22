import json
import os
from xmlrpc.client import boolean
import requests
import click
import pymongo

from app.commands.configCommands import add_news
from ..extentions.database import mongo
from flask import Blueprint
from ..routes.backend import get_next_jogos, get_users, make_score_board
from ..cache import cache
from random import randrange
#from twilio.rest import Client

SEPARADOR_CSV=","
ANO=22
APOSTADB='apostas22'
TELEGRAM_TOKEN=os.getenv('TELEGRAM_TKN')
TELEGRAM_CHAT_ID=os.getenv('TELEGRAM_CHAT_ID')
TELEGRAM=os.getenv('TELEGRAM')

if TELEGRAM:
    if TELEGRAM.lower() in ['yes','true','True']:
        TELEGRAM=True
    else:
        TELEGRAM=False

jogosCommands = Blueprint('jogos',__name__)

@jogosCommands.cli.command("loadCsv")
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
            documento["Jogo"]=int(documento["Jogo"])
            documento["Ano"]=int(documento["Ano"])
            data.append(documento)

        if not data:
            return None
        
        #print(data)
    
    
    jogosCollection = mongo.db.jogos
    jogosCollection.insert(data)
    print("Dados inseridos")
    

@jogosCommands.cli.command("getJogo")
@click.argument("ano")
@click.argument("jogo")
def get_jogos(ano,jogo):
    jogosCollection = mongo.db.jogos
    print(f'Buscando ano {ano} e jogo {jogo}')
    busca = [u for u in jogosCollection.find({"Ano": int(ano),"Jogo": int(jogo)})]
    if busca:
        print("Jogo encontrado: ",busca)
    else:
        print("Nada encontrado.")

@jogosCommands.cli.command("getAposta")
@click.argument("jogo")
def get_aposta(jogo):
    apostas = mongo.db[APOSTADB].find_one({'Jogo': int(jogo)})
    if apostas:
        print(apostas)
    else:
        print("Nada encontrado.")

@jogosCommands.cli.command("editJogo")
@click.argument("ano")
@click.argument("jogo")
@click.argument("campo")
@click.argument("valor1")
@click.argument("valor2")
def edit_jogo(ano,jogo,campo,valor1,valor2):
    jogo = mongo.db.jogos.find_one({"Ano": int(ano),"Jogo": int(jogo)})
    #jogo = [u for u in jogosCollection.find({"Ano": ano,"Jogo": jogo})]
    if jogo:
        print("Jogo encontrado: ",jogo)
        idJogo = jogo["_id"]
        if campo == "placar":
            campo1 = "p1"
            campo2 = "p2"
        elif campo == "tr":
            campo1 = "tr1"
            campo2 = "tr2"
        elif campo == "pe":
            campo1 = "pe1"
            campo2 = "pe2"
        else:
            print("Forneca os valores de campo: placar, tr, pe.")
            exit()
        print(f'Editando campo {campo1}: {valor1} e {campo2}: {valor2}')
        mongo.db.jogos.find_one_and_update({'_id': idJogo},{'$set': {campo1: int(valor1), campo2: int(valor2)}})
        print("Finalizado.")

    else:
        print("Nada encontrado.")

def gera_random_score():
    # 0:0-4 1:5-10 2:11-16 3:17-20 4:21-22 r(2):23-24 5:25
    aleatorio = randrange(25)
    if aleatorio < 5:
        rp = 0
    elif aleatorio < 11:
        rp = 1
    elif aleatorio < 18:
        rp = 2
    elif aleatorio < 23:
        rp = 3
    elif aleatorio < 25:
        rp = 4
    else:
        rp = 5
    return int(rp)

def gera_random_penalti():
    aleatorio = randrange(3)
    pe1 = 1 + aleatorio
    pe2 = 1 + aleatorio
    aleatorio = randrange(4)
    if aleatorio < 2:
        pe1 += aleatorio + 1
    else:
        pe2 += aleatorio - 1
    return (pe1,pe2)

@jogosCommands.cli.command("betRandom")
@click.argument("user")
@click.argument("jogo")
def teste2(user,jogo):
    p1 = gera_random_score()
    p2 = gera_random_score()
    list_pe = list(range(172,204))+[9,10,25,34,35,50,59,60,75]+list(range(76,100))
    if p1 == p2 and int(jogo) in list_pe:
        r = randrange(2)
        outp = mongo.db.apostas22.find_one_and_update(
            {"Jogo": int(jogo)},
            {'$set': {
                str(user + "_p1"): int(p1),
                str(user + "_p2"): int(p2),
                str(user + "_vit"): str(r)
                }})
        print(f'jid {jogo} Aposta de {user}: {p1}x{p2} v{r}')
    else:
        outp = mongo.db.apostas22.find_one_and_update(
            {"Jogo": int(jogo)},
            {'$set': {
                str(user + "_p1"): int(p1),
                str(user + "_p2"): int(p2)
                }})
        print(f'jid {jogo} Aposta de {user}: {p1}x{p2}')
    #print(outp)

# Print random commando to edit game
@jogosCommands.cli.command("printRandom")
@click.argument("jogoi")
@click.argument("jogof")
@click.argument("tr")
def print_random_editgame(jogoi,jogof,tr):
    for jogo in range(int(jogoi),int(jogof)+1):
        p1 = gera_random_score()
        p2 = gera_random_score()
        if p1 == p2 and int(tr) == 1:
            print(f'flask jogos editJogo {ANO} {jogo} tr {p1} {p2}')
            aleatorio = randrange(10)
            if aleatorio < 1:
                print(f'flask jogos editJogo {ANO} {jogo} placar {p1+2} {p2}')
            elif aleatorio < 3:
                print(f'flask jogos editJogo {ANO} {jogo} placar {p1+1} {p2}')
            elif aleatorio < 7:
                print(f'flask jogos editJogo {ANO} {jogo} placar {p1} {p2}')
                pe1,pe2 = gera_random_penalti()
                print(f'flask jogos editJogo {ANO} {jogo} pe {pe1} {pe2}')
            elif aleatorio < 9:
                print(f'flask jogos editJogo {ANO} {jogo} placar {p1} {p2+1}')
            elif aleatorio < 10:
                print(f'flask jogos editJogo {ANO} {jogo} placar {p1} {p2+2}')
        else:
            print(f'flask jogos editJogo {ANO} {jogo} placar {p1} {p2}')

@jogosCommands.cli.command("initApostas22")
def init_apostas22():
    JOGOS=203
    apostas = mongo.db.apostas22
    if apostas.count_documents({}) > 0:
        print("Base já existente.")
    else:
        for i in range(1,JOGOS+1):
            apostas.insert_one({"Jogo": i})
        print("Finalizado.")

@jogosCommands.cli.command("deleteAno")
@click.argument("ano")
def delete_ano(ano):
    lista = [u for u in mongo.db.jogos.find({'Ano': int(ano)})]
    for j in lista:
        jogo = j['Jogo']
        print("Excluindo jogo ",jogo)
        mongo.db.jogos.find_one_and_delete({'Ano': int(ano),'Jogo':jogo})
    print("Finalizado.")


@jogosCommands.cli.command("report")
@click.argument("jogos")
@click.argument("proximos")
@click.argument("texto",required=False)
def report(jogos,proximos,texto=""):
    emojis = mongo.db.emoji
    apostas = mongo.db.apostas22
    lista_jogos = get_next_jogos()
    jogos_list = lista_jogos['past_jogos'][:int(jogos)]
    next_list = lista_jogos['next_jogos'][:int(proximos)]
    mensagem="⚽ Gokopa 22"
    newsm = ""
    #jogos_list[0] = int(jogos_list[0]) - 1
    #jogos_list[1] = int(jogos_list[1]) + 1
    #next_list[0] = int(next_list[0]) - 1
    #next_list[1] = int(next_list[1]) + 1
    #recentes = [u for u in jogosdb.find({'Ano': ANO, "Jogo": {'$gt': jogos_list[0], '$lt': jogos_list[1] }}).sort("Jogo",pymongo.ASCENDING)]
    #next_games = [u for u in jogosdb.find({'Ano': 20, "Jogo": {'$gt': next_list[0], '$lt': next_list[1] }}).sort("Jogo",pymongo.ASCENDING)]
    if jogos_list:
        mensagem="⚽ Gokopa 22 - Jogos recentes\n"
        for j in jogos_list:
            #mensagem+=" ".join([j['Competição'],"-",j['Fase']])+"\n"
            placar = str(j['p1']) + "x" + str(j['p2'])
            e1 = emojis.find_one({'País': j['time1']})
            e2 = emojis.find_one({'País': j['time2']})
            if j['jid'] > 48 and j['p1'] == j['p2']:
                tr = "vitória: " + j['vitoria']
            else:
                tr = ""
            mensagem+=" ".join([j['time1'],e1['flag'],placar,e2['flag'],j['time2'],tr])+"\n"
            newsm += " ".join([j['time1'],e1['flag'],placar,e2['flag'],j['time2'],tr])+"\\n"

    if texto:
        mensagem+="\n"+texto+"\n"
        newsm+="\\n"+texto+"\\n"

    print("Publicando mensagem como notícia")
    add_news("Jogos recentes",newsm)

    if next_list:
        allUsers = [u for u in mongo.db.users.find({"active": True,"gokopa": True}).sort("name",pymongo.ASCENDING)]
        #print(allUsers)
        missing_users = set()
        for j in next_list:
            bets = apostas.find_one({'Jogo': j['jid']})
            for user in allUsers:
                betu = user.get('name') + '_p1'
                if (not bets.get(betu)) and bets.get(betu) != 0:
                    if user.get('telegram'):
                        missing_users.add(user.get('telegram'))
                    else:
                        missing_users.add(user.get('name'))
            #print(bets)
        #print(missing_users)
        lista_users = ', '.join(missing_users)
        if len(missing_users) > 0:
            mensagem+="\n❗ Lista de apostadores pendentes com os próximos jogos ❗\n"
            mensagem+=lista_users
            mensagem+="\n"

    ordered_total = make_score_board(ANO)
    range_print = 5
    if len(ordered_total) < 5:
        range_print = len(ordered_total)
    mensagem+="\n🔝 Bolão Hoje \n"
    string_placar = ""
    for i in range(range_print):
        string_placar += " ▪️ " + str(ordered_total[i]['score']) + " - " + str(ordered_total[i]['nome'])
    mensagem+=string_placar
        
    mensagem+="\n\n➡️ Visite e acompanhe: https://gokopa.leafarlins.com"
    #print("Preparando mensagem para envio")
    #print(mensagem)
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
    # client = Client(TWILIO_SID,TWILIO_TKN)
    # message = client.messages.create(
    #     to="+5561992728778",
    #     from_="+5561992728778",
    #     body=mensagem)
    # print(message.sid)

