import sys
from bson.objectid import ObjectId
import click
import getpass

from flask_pymongo import BSONObjectIdConverter
import pymongo
from ..extentions.database import mongo
from flask import Blueprint


SEPARADOR_CSV=","

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
    
    
    question = input(f'Deseja inserir os dados impressos? (S/N) ')
    if question.upper() == "S":
        timeCollection = mongo.db.ranking
        timeCollection.insert(data)
        print("Dados inseridos")
    else:
        exit()
    

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

