from datetime import datetime
import json
import os
import click
import getpass

import pymongo
import requests
from ..extentions.database import mongo
from flask import Blueprint,current_app
from app.routes.backend import get_aposta,get_users,get_games,make_score_board,get_bet_results2,get_score_results,getBolaoUsers

configCommands = Blueprint('config',__name__)
ANO=24
TELEGRAM_TOKEN=os.getenv('TELEGRAM_TKN')
TELEGRAM_CHAT_ID=os.getenv('TELEGRAM_CHAT_ID')
TELEGRAM=os.getenv('TELEGRAM')

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
    mongo.db[basehis].insert_many(ordered_total_gk)

@configCommands.cli.command("setRank")
@click.argument("edition")
def set_history(edition):
    mongoconfig = mongo.db.settings.find_one_and_update({"config": "ranking"},{'$set': {'edition': edition }})
    if mongoconfig:
        print("Valor atualizado.")
    else:
        print("Config não existe na base, definindo...")
        mongo.db.settings.insert_one({"config": "ranking", "edition": edition})

@configCommands.cli.command("setHl")
@click.argument("team")
def set_hl(team):
    mongoconfig = mongo.db.settings.find_one_and_update({"config": "highlight"},{'$set': {'time': team }})
    if mongoconfig:
        print("Valor atualizado.")
    else:
        print("Config não existe na base, definindo...")
        mongo.db.settings.insert_one({"config": "highlight", "time": team})

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
        mongo.db.settings.insert_one({"config": "bolao_u","ano": int(ano),"users": u_arr })

# def getBolaoUsers(ano):
#     b_users = mongo.db.settings.find_one({"config": "bolao_u","ano": int(ano)})
#     return b_users["users"]

@configCommands.cli.command("get_bolao_users")
@click.argument("ano")
def get_bolao_users(ano):
    print(getBolaoUsers(ano))

@configCommands.cli.command("migrate141")
def migrate141():
    enquete = [{
        'ano': 22,
        'game': 90,
        'nome': 'Votação para sede da Taça Ásia-Oceania 23',
        'votos': {},
        'opcoes': [
            {
                'nome': 'Coréia do Sul',
                'paises': ['Coréia do Sul'],
                'id': 0,
                'desc': 'Coréia do Sul, atualmente na liderança do ranking asiático, deseja sediar com excelente estrutura.'
            },
            {
                'nome': 'Coréia do Norte',
                'paises': ['Coréia do Norte'],
                'id': 1,
                'desc': 'Os vizinhos do norte não querem ficar de fora, e querem ganhar a sede do vizinho do sul.'
            },
            {
                'nome': 'Nova Zelândia',
                'paises': ['Nova Zelândia'],
                'id': 2,
                'desc': 'Candidata oceânica, belo país e bela estrutura para sediar o evento.'
            },
            {
                'nome': 'Vietnã',
                'paises': ['Vietnã'],
                'id': 3,
                'desc': 'O Vietnã já fez boas participações e tomou gosto, quer voltar a ser protagonista nos jogos.'
            }
        ]
    },{
        'ano': 22,
        'game': 95,
        'nome': 'Votação para sede da Taça África 23',
        'votos': {},
        'opcoes': [
            {
                'nome': 'Camarões',
                'paises': ['Camarões'],
                'id': 0,
                'desc': 'Uma das grandes seleções africanas e mais presentes nas copas.'
            },
            {
                'nome': 'Argélia',
                'paises': ['Argélia'],
                'id': 1,
                'desc': 'Árgélia sediou a Copa mas não a Taça África. Quer aproveitar sua experiência para este evento.'
            },
            {
                'nome': 'Egito',
                'paises': ['Egito'],
                'id': 2,
                'desc': 'País muito visitado e com um time que deseja muito voltar a competir.'
            },
            {
                'nome': 'Costa do Marfim',
                'paises': ['Costa do Marfim'],
                'id': 3,
                'desc': 'Uma das forças africanas, querendo ser mais protagonista como sede.'
            }
        ]
    },{
        'ano': 22,
        'game': 99,
        'nome': 'Votação para sede da Taça Europa 23',
        'votos': {},
        'opcoes': [
            {
                'nome': 'Ucrânia',
                'paises': ['Ucrânia'],
                'id': 0,
                'desc': 'Sede e campeã da Gokopa 5, quer retomar os velhos tempos e sediar o evento.'
            },
            {
                'nome': 'Áustria',
                'paises': ['Áustria'],
                'id': 1,
                'desc': 'Sede da Gokopa 6 e 3x vice-campeã. O passado de glória é nostálgico aos austríacos.'
            },
            {
                'nome': 'Inglaterra',
                'paises': ['Inglaterra'],
                'id': 2,
                'desc': 'Sede e campeã da Gokopa 8, muita experiência no campo e em organização.'
            },
            {
                'nome': 'Noruega',
                'paises': ['Noruega'],
                'id': 3,
                'desc': 'Sede da Gokopa 10, quer sediar a Taça Regional.'
            }
        ]
    },{
        'ano': 22,
        'game': 188,
        'nome': 'Votação para sede da Gokopa 23',
        'votos': {},
        'opcoes': [
            {
                'nome': 'Hermanos da Plata',
                'paises': ['Argentina','Uruguai'],
                'id': 0,
                'desc': 'Aliança entre Argentinos e Uruguaios para sediar a Gokopa. Chamada de Hermanos da Plata para tentar causar mais simpatia e atrair os jurados. Temos uma campeã do mundo, Argentina, e o Uruguai, candidatura com melhor tradição nos jogos da Gokopa e boa estrutura física.'
            },
            {
                'nome': 'Caribe',
                'paises': ['Trinidad e Tobago','St Vicente','São Cristóvão'],
                'id': 1,
                'desc': 'Caribe abre suas portas para a Gokopa! Trinidad e Tobago é o time com mais tradição e bem posicionado. St Vicente já foi sensação de Gokopas passadas. Muita alegria, mar e prais, e prometem também uma bela festa para sediar a Gokopa.'
            },
            {
                'nome': 'Peru e Bolívia',
                'paises': ['Peru','Bolívia'],
                'id': 2,
                'desc': 'A Gokopa das Cordilheiras e Amazônia. Peru e Bolívia não tem muita tradição na Gokopa, mas querem sediar com muita disposição, mostrar a cultura local e progredir em seu futebol.'
            },
            {
                'nome': 'Equatombia',
                'paises': ['Equador','Colômbia'],
                'id': 3,
                'desc': 'Duas boas seleções americanas, dispostas a fazer uma grande festa no centro da América do Sul. Equador e Colômbia já conquistaram medalhas, falta um campeonato. Os países dispõem de muitas atrações e estrutura.'
            }
        ]
    }]
    outdb = mongo.db.enquete.find_one({'ano': 22,'nome': 'Votação para sede da Gokopa 23'})
    if outdb:
        print("Enquete já cadastrada.")
    else:
        mongo.db.enquete.insert_many(enquete)

    print("Finalizado.")

@configCommands.cli.command("migrate142")
def migrate142():
    print("-Correção no id de jogos 51-54")
    mongo.db.jogos.find_one_and_update({'Ano': 22,'Time1': 'Bélgica','Time2':'Ucrânia'},{'$set': {'Jogo': 53}})
    mongo.db.jogos.find_one_and_update({'Ano': 22,'Time1': 'Alemanha','Time2':'Italia'},{'$set': {'Jogo': 54}})
    mongo.db.jogos.find_one_and_update({'Ano': 22,'Time1': 'Rússia','Time2':'Holanda'},{'$set': {'Jogo': 51}})
    mongo.db.jogos.find_one_and_update({'Ano': 22,'Time1': 'Espanha','Time2':'Suiça'},{'$set': {'Jogo': 52}})
    print("-Seta status de c22")
    times_ano22 = ['Dinamarca']
    for j in mongo.db.jogos.find({'Ano': 22, 'Jogo': {'$lt': 51}}):
        times_ano22.append(j.get('Time1'))
        times_ano22.append(j.get('Time2'))
    timehis = [u for u in mongo.db.timehistory.find()]
    for t in timehis:
        if t['Time'] in times_ano22:
            mongo.db.timehistory.find_one_and_update({"_id": t['_id']},{'$set':{'c22': 't'}})
        else:
            mongo.db.timehistory.find_one_and_update({"_id": t['_id']},{'$set':{'c22': '-'}})
    mongo.db.timehistory.find_one_and_update({"Time": 'Dinamarca'},{'$set':{'c22': '?'}})

    print("-Ajuste de nomes de competição")
    compn = {
        'copa':'Copa do Mundo',
        'tacaaso':'Taça Ásia-Oceania',
        'tacaame':'Taça América',
        'tacaeur':'Taça Europa',
        'tacaafr':'Taça África',
        'taca':'Taça Mundial'
    }
    historico = [u for u in mongo.db.historico.find()]
    for h in historico:
        if h['comp'] in ['copa','tacaaso','tacaame','tacaeur','tacaafr','taca']:
            mongo.db.historico.find_one_and_update({'_id': h['_id']},{'$set': {'comp': compn[h['comp']] }})

    print("Finalizado.")

@configCommands.cli.command("migrate164")
def migrate164():
    mongo.db.moedas.update_many({},{'$set': {'lock': False}})

@configCommands.cli.command("migrate147")
def migrate147():
    estadiolist = [{
        'ano': 22,
        'games': [100,203],
        'nome': 'Estádios da Copa do Mundo',
        'cidades': ['Estocolmo','Copenhague','Malmo','Brøndbyvester','Gotemburgo','Aarhus','Norrköping','Esbjerg']
    },{
        'ano': 22,
        'games': [1,99],
        'nome': 'Estádios das Taças Regionais e Mundial',
        'cidades': ['Estocolmo','Malmo','New Jersey','Orlando','Abuja','Lagos','Melbourne','Sydney']
    }]
    with open('executar/estadios22','r') as file:
        estadios = json.load(file)
    outdb = mongo.db.estadios.find_one({'cidade': 'Estocolmo'})
    if outdb:
        print("Estádios já cadastrados.")
    else:
        mongo.db.estadios.insert_many(estadios)
        mongo.db.estadiolist.insert_many(estadiolist)
    print("Finalizado.")


def reset_base_moedas():
    mongo.db.moedas.drop()
    mongo.db.moedaslog.drop()
    mongo.db.patrocinio.drop()
    mongo.db.moedasdeck.drop()
    for i in range(1,5):
        novo_user = {
                "nome": "ze"+str(i),
                "saldo": 0,
                "bloqueado": 0,
                "investido": 0
        }
        mongo.db.moedas.insert_one(novo_user)
    print(f"Reiniciando base de moedas")

@configCommands.cli.command("cadastra_estadio")
def cadastra_estadio():
    estadiolist = [{
        'ano': ANO,
        'games': [109,212],
        'nome': 'Estádios da Copa do Mundo',
        'cidades': ['Alexandria','Ondurman','Cairo','Cartum','New Administrative Capital','Wad Madani','Suez','Atbara']
    },{
        'ano': ANO,
        'games': [1,108],
        'nome': 'Estádios das Taças Regionais e Mundial',
        'cidades': ['Ondurman','Cartum','Amsterdam','Rotterdam','Kingston','Trelawny','Ba','Suva']
    }]
    with open('executar/estadios24','r') as file:
        estadios = json.load(file)
    outdb = mongo.db.estadios.find_one({'cidade': 'Ondurman'})
    if outdb:
        print("Estádios já cadastrados.")
    else:
        mongo.db.estadios.insert_many(estadios)
        mongo.db.estadiolist.insert_many(estadiolist)
    print("Finalizado.")


@configCommands.cli.command("migrate170")
def migrate170():
    reset_base_moedas()
    for i in range(1,40):
        mongo.db.jogos.find_one_and_update({'Ano': 24, 'Jogo': i},{'$set': {"processado": False}})


@configCommands.cli.command("migrate160")
def migrate160():
    reset_base_moedas()
    print("Setando posições no ranking atual")
    cname = "c" + str(ANO)
    mongo.db.timehistory.update_many({},{'$set':{cname: '-'}})
    listat_gokopa = ["Egito","Sudão","Nigéria","Marrocos","Tunísia","Camarões","Argélia","Costa do Marfim","Zâmbia","Congo","Níger","Guiné","Angola","África do Sul","Ruanda","Botsuana","Holanda","França","Alemanha","Tcheca","Portugal","Espanha","Sérvia","Italia","Rússia","Bélgica","Croácia","Suécia","Ucrânia","Bulgária","Inglaterra","Suiça","Dinamarca","Finlândia","Escócia","Polônia","Gales","Áustria","Islândia","Bósnia","Belarus","Hungria","Albania","Romênia","Geórgia","Irlanda do Norte","Moldávia","Letônia","San Marino","Chipre","Andorra","Liechenstein","Jamaica","Brasil","Argentina","Trinidad e Tobago","Equador","Panamá","Estados Unidos","Colômbia","Uruguai","Chile","México","Costa Rica","Honduras","Venezuela","Bolívia","Guatemala","Nicarágua","Paraguai","Fiji","Coréia do Sul","Austrália","Japão","Irã","Hong Kong","Arábia Saudita","Vietnã","Taiti","Vanuatu","Iraque","Bahrein"]
    listac_gokopa = ["Egito","Sudão"]
    for time in listat_gokopa:
        mongo.db.timehistory.find_one_and_update({'Time': time},{'$set': {cname: 't'}})
    for time in listac_gokopa:
        mongo.db.timehistory.find_one_and_update({'Time': time},{'$set': {cname: 'c'}})

@configCommands.cli.command("fixbase")
def fixbase():
    times = [u for u in mongo.db.timehistory.find()]
    for t in times:
        print("db.timehistory.findOneAndUpdate({'Time': '",t["Time"],"'},{'$set': {'r23': ",t["r23"],"}})",sep="")

@configCommands.cli.command("migrate150")
def migrate150():
    mongo.db.moedas.drop()
    mongo.db.moedaslog.drop()
    mongo.db.patrocinio.drop()
    novo_user = {
            "nome": "ernani",
            "saldo": 1000,
            "bloqueado": 0,
            "investido": 0
    }
    mongo.db.moedas.insert_one(novo_user)
    print(f"Reiniciando base de moedas")
    # Mudança de nome da Rep Tcheca para Tcheca
    print("Mudança de nome da Tcheca e Belarus")
    oldname  = "Rep Tcheca"
    newname = "Tcheca"
    mongo.db.timehistory.find_one_and_update({'Time': oldname},{'$set': {"Time": newname}})
    mongo.db.emoji.find_one_and_update({'País': oldname},{'$set': {"País": newname}})
    mongo.db.historico.update_many({'ouro': oldname},{'$set': {"ouro": newname}})
    mongo.db.historico.update_many({'prata': oldname},{'$set': {"prata": newname}})
    mongo.db.jogos.update_many({'Time1': oldname},{'$set': {"Time1": newname}})
    mongo.db.jogos.update_many({'Time2': oldname},{'$set': {"Time2": newname}})
    oldname = "Bielorússia"
    newname = "Belarus"
    mongo.db.timehistory.find_one_and_update({'Time': oldname},{'$set': {"Time": newname}})
    mongo.db.emoji.find_one_and_update({'País': oldname},{'$set': {"País": newname}})
    mongo.db.jogos.update_many({'Time1': oldname},{'$set': {"Time1": newname}})
    mongo.db.jogos.update_many({'Time2': oldname},{'$set': {"Time2": newname}})

    print("Setando posições no ranking atual")
    mongo.db.timehistory.update_many({},{'$set':{'c23': '-'}})
    listat_gokopa23 = ["França","Alemanha","Sérvia","Bélgica","Italia","Espanha","Rússia","Croácia","Portugal","Tcheca","Bulgária","Suécia","Inglaterra","Escócia","Suiça","Dinamarca","Finlândia","Ucrânia","Polônia","Holanda","Gales","Bósnia","Lituânia","Israel","Irlanda","Áustria","Grécia","Cazaquistão","Eslováquia","Turquia","Noruega","Malta","Azerbaijão","Macedônia","Ilhas Faroe","Luxemburgo","Brasil","Argentina","Equador","Jamaica","Panamá","Estados Unidos","Colômbia","México","Chile","Honduras","Costa Rica","Uruguai","Venezuela","Bolívia","Canadá","Peru","El Salvador","Nigéria","Camarões","Marrocos","Argélia","Tunísia","Gana","Senegal","RD do Congo","Egito","Benin","Uganda","Libéria","Cabo Verde","Togo","Gabão","Coréia do Sul","Austrália","Japão","Irã","Hong Kong","Arábia Saudita","Ilhas Salomão","Paquistão","China","Coréia do Norte","Índia","Kwait"]
    listac_gokopa23 = ["Trinidad e Tobago","St Vicente","São Cristóvão"]
    for time in listat_gokopa23:
        mongo.db.timehistory.find_one_and_update({'Time': time},{'$set': {'c23': 't'}})
    for time in listac_gokopa23:
        mongo.db.timehistory.find_one_and_update({'Time': time},{'$set': {'c23': 'c'}})
    
@configCommands.cli.command("updateEstadio")
def updateEstadio():
    estadiolist = [{
        'ano': 23,
        'games': [109,212],
        'nome': 'Estádios da Copa do Mundo',
        'cidades': ['Port of Spain','Arnos Vale','Basseterre','Couva','Arima','Marabella','Charlestown','Kingstown']
    },{
        'ano': 23,
        'games': [1,108],
        'nome': 'Estádios das Taças Regionais e Mundial',
        'cidades': ['Port of Spain','Couva','Kiev','Carcóvia','Alexandria','Cairo','Rungra Island','Pyongyang']
    }]
    with open('executar/estadios23','r') as file:
        estadios = json.load(file)
    outdb = mongo.db.estadios.find_one({'cidade': 'Couva'})
    if outdb:
        print("Estádios já cadastrados.")
    else:
        mongo.db.estadios.insert_many(estadios)
        mongo.db.estadiolist.insert_many(estadiolist)

@configCommands.cli.command("addEnquete")
@click.argument("filerec")
def addEnquete(filerec):
    with open(filerec) as file:
        enquete = json.load(file)
    outdb =  mongo.db.enquete.insert_one(enquete)
    if outdb:
        print("Enquete cadastrada")
    else:
        print("Erro ao cadastrar")

@configCommands.cli.command("setEnqueteEnd")
@click.argument("enquete")
def setEnqueteEnd(enquete):
    outdb = mongo.db.enquete.find_one_and_update({'nome': enquete},{"$set": {'andamento': False }})
    if outdb:
        print("Enquete alterada com sucesso.")
    else:
        print("Erro ao alterar enquete.")

def add_news(titulo,noticia,img="",link="",linkname=""):
    new = {
        'titulo': titulo,
        'texto': noticia,
        'ano': ANO
    }
    if img:
        new['img'] = img
    if link:
        new['link'] = link
        new['linkname'] = linkname
    data = datetime.strftime(datetime.now(),"%d/%m/%Y")
    new['data'] = data
    new_id = mongo.db.settings.find_one_and_update({'config':'newsid'},{'$inc': {'nid': 1}})
    if new_id:
        nid = new_id['nid']+1
    else:
        print("Sem noticias na base, iniciando")
        nid = 1
        mongo.db.settings.insert_one({'config':'newsid','nid': 1})
    new['nid'] = nid
    mongo.db.news.insert_one(new)
    current_app.logger.info(f"Adicionando noticia: {new}")

    mensagem = "⚽ Gokopa News: " + new['titulo'] + "\n\n" + new['texto'].replace('\\n','\n')
    if img == 'youtube':
        mensagem+="\n\nhttps://www.youtube.com/watch?v=" + link
    else:
        mensagem+="\n\n➡️ Todas as notícias em: https://gokopa.leafarlins.com/noticias" + str(ANO)
    print("Preparando mensagem para envio")
    print(mensagem)
    if TELEGRAM and titulo != 'Jogos recentes':
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

@configCommands.cli.command("news")
@click.argument("titulo")
@click.argument("noticia")
@click.argument("img",required=False)
@click.argument("link",required=False)
@click.argument("linkname",required=False)
def addNews(titulo,noticia,img="",link="",linkname=""):
    add_news(titulo,noticia,img,link,linkname)