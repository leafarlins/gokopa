from app.commands.configCommands import get_ordered
import click
import pymongo
from ..extentions.database import mongo
from flask import Blueprint
from ..routes.bolao import get_users, make_score_board
from ..cache import cache


SEPARADOR_CSV=","
ANO=20

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
        
        print(data)
    
    
    question = input(f'Deseja inserir os dados impressos? (S/N) ')
    if question.upper() == "S":
        jogosCollection = mongo.db.jogos
        jogosCollection.insert(data)
        print("Dados inseridos")
    else:
        exit()
    

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
    apostas = mongo.db.apostas21.find_one({'Jogo': int(jogo)})
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


@jogosCommands.cli.command("teste2")
def teste2():
    idjogo=1
    aposta = mongo.db.apostas20.find_one_or_404({"Jogo": idjogo})
    print(aposta)

@jogosCommands.cli.command("teste")
def teste():
    LIMITE_JOGOS=20
    past_jogos = [u for u in mongo.db.jogos.find({'Ano': 19})]
    ano20_jogos = mongo.db.jogos.find({'Ano': 20}).sort([("Jogo",pymongo.ASCENDING),("Ano",pymongo.DESCENDING)])
    next_jogos = []
    for n in ano20_jogos:
        if n["Time1"]=="China":
            past_jogos.insert(0,n)
        else:
            next_jogos.append(n)
        #print("Past jogos:",past_jogos)
        print("Next:",next_jogos)

@jogosCommands.cli.command("initApostas20")
def init_apostas20():
    JOGOS=184
    BASE='apostas20'
    apostas = mongo.db.apostas20
    if apostas.count_documents({}) > 0:
        print("Base já existente.")
    else:
        for i in range(1,JOGOS+1):
            apostas.insert_one({"Jogo": i})
        print("Finalizado.")

@jogosCommands.cli.command("initApostas21")
def init_apostas21():
    JOGOS=64
    BASE='apostas21'
    apostas = mongo.db.apostas21
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
def report(jogos,proximos):
    jogosdb = mongo.db.jogos
    emojis = mongo.db.emoji
    apostas = mongo.db.apostas21
    jogos_list = jogos.split(',')
    next_list = proximos.split(',')
    jogos_list[0] = int(jogos_list[0]) - 1
    jogos_list[1] = int(jogos_list[1]) + 1
    #next_list[0] = int(next_list[0]) - 1
    #next_list[1] = int(next_list[1]) + 1
    recentes = [u for u in jogosdb.find({'Ano': 21, "Jogo": {'$gt': jogos_list[0], '$lt': jogos_list[1] }}).sort("Jogo",pymongo.ASCENDING)]
    #next_games = [u for u in jogosdb.find({'Ano': 20, "Jogo": {'$gt': next_list[0], '$lt': next_list[1] }}).sort("Jogo",pymongo.ASCENDING)]
    print("⚽ Gokopa 21 - Jogos recentes")
    for j in recentes:
        print(j['Competição'],"-",j['Fase'])
        placar = str(j['p1']) + "x" + str(j['p2'])
        e1 = emojis.find_one({'País': j['Time1']})
        e2 = emojis.find_one({'País': j['Time2']})
        if j['tr1'] or j['tr1'] == 0 :
            tr = "(tr " + str(j['tr1']) + "x" + str(j['tr2'])
            if j['pe1'] or j['pe1'] == 0:
                tr = tr + " pe " + str(j['pe1']) + "x" + str(j['pe2']) + ")"
            else:
                tr = tr + ")"
        else:
            tr = ""
        print(j['Time1'],e1['flag'],placar,e2['flag'],j['Time2'],tr)


    allUsers = get_users()
    #print(allUsers)
    missing_users = set()
    for j in range(int(next_list[0]),int(next_list[1])+1):
        bets = apostas.find_one({'Jogo': j})
        for user in allUsers:
            betu = user + '_p1'
            if (not bets.get(betu)) and bets.get(betu) != 0:
                missing_users.add(user)
        #print(bets)
    #print(missing_users)
    lista_users = ', '.join(missing_users)
    #if len(missing_users) > 0:
    print("\n❗ Lista de apostadores pendentes com os próximos jogos ❗")
    print(lista_users)

    #ordered_total = get_ordered()
    ordered_total = make_score_board()
    range_print = 5
    if len(ordered_total) < 5:
        range_print = len(ordered_total)
    print("\n🔝 Bolão Hoje ")
    string_placar = ""
    for i in range(range_print):
        string_placar += " ▪️ " + str(ordered_total[i]['score']) + " - " + str(ordered_total[i]['nome'])
    print(string_placar)
        
    print("\n➡️ Visite e acompanhe: http://gokopa.herokuapp.com")
