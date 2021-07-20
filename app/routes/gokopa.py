from datetime import datetime
from typing import Collection
from flask import Blueprint, render_template, session, request, url_for, flash
import pymongo
from werkzeug.utils import redirect
from werkzeug.security import check_password_hash
from ..extentions.database import mongo

#current_app para carregar app.py

gokopa = Blueprint('gokopa',__name__)

# Rota / associada a função index
@gokopa.route('/')
def index():
    LIMITE_JOGOS=20
    past_jogos = [u for u in mongo.db.jogos.find({'Ano': 19})]
    ano20_jogos = mongo.db.jogos.find({'Ano': 20}).sort([("Jogo",pymongo.ASCENDING),("Ano",pymongo.DESCENDING)])
    next_jogos = []
    now = datetime.now()
    for n in ano20_jogos:
        if n["Time1"] and n["Time2"]:
            data_jogo = datetime.strptime(n["Data"],"%d/%m/%Y %H:%M")
            if data_jogo < now:
                past_jogos.insert(0,n)
            else:
                next_jogos.append(n)

    return render_template("inicio.html",menu="Home",past_jogos=past_jogos[:20],next_jogos=next_jogos[:20])

@gokopa.route('/tabela20')
def tabela():
    return render_template("tabela.html",menu="Tabela")

@gokopa.route('/ranking')
def ranking():
    ranking = [u for u in mongo.db.ranking.find({"ed": "19-3"})]
    return render_template("ranking.html",menu="Ranking",ranking=ranking)

    