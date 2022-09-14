from flask import Blueprint, render_template, session, request, url_for, flash
from app.routes.backend import progress_data,get_aposta,get_users,get_games,make_score_board,get_user_name,get_bet_results,get_rank
import pymongo
from werkzeug.utils import redirect
from ..extentions.database import mongo
from datetime import date, datetime
from operator import itemgetter
from ..cache import cache

moedas = Blueprint('moedas',__name__)

ANO=21

@moedas.route('/gk/moedas')
def gamemoedas():
    if session.get('username') == None:
        userLogado=False
    else:
        apostador = get_user_name(session["username"])
        userLogado=True
    return render_template('moedas.html',menu='Moedas',tipo='gk',userlogado=userLogado)
