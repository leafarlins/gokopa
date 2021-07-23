import sys
from bson.objectid import ObjectId
import click
import getpass

from flask_pymongo import BSONObjectIdConverter
import pymongo
from ..extentions.database import mongo
from flask import Blueprint


SEPARADOR_CSV=","

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
        elif campo == "penalti":
            campo1 = "pe1"
            campo2 = "pe2"
        else:
            print("Forneca os valores de campo: placar, tr, penalti ou times.")
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

@jogosCommands.cli.command("deleteAno")
@click.argument("ano")
def delete_ano(ano):
    lista = [u for u in mongo.db.jogos.find({'Ano': int(ano)})]
    for j in lista:
        jogo = j['Jogo']
        print("Excluindo jogo ",jogo)
        mongo.db.jogos.find_one_and_delete({'Ano': int(ano),'Jogo':jogo})
    print("Finalizado.")

