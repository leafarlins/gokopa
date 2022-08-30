#import re
#from app.routes.bolao import get_rank, make_score_board, read_config_ranking
#from array import array
from datetime import datetime, time
#from typing import Collection
from flask import Blueprint, app, render_template, session, request, url_for, flash, jsonify
import pymongo
from pymongo import collection
from ..extentions.database import mongo
from ..cache import cache

ANO=21

# Para usar curl: WERKZEUG_DEBUG_PIN=off

backend = Blueprint('backend',__name__)

@backend.route('/api/progress_data', methods=['GET'])
@cache.cached(timeout=20*60)
def progress_data():
    ano_jogos = [u for u in mongo.db.jogos.find({'Ano': ANO}).sort("Jogo",pymongo.ASCENDING)]
    progress = dict()
    now = datetime.now()
    progress["last_game"]=0
    progress["total_games"]=64
    progress["game_progress"]=0
    progress["score_progress"]=0
    progress["score_percent"]='0%'
    for jogo in ano_jogos:
        data_jogo = datetime.strptime(jogo["Data"],"%d/%m/%Y %H:%M")
        if data_jogo < now and jogo["p1"] != "":
            progress["last_game"]=jogo['Jogo']
        else:
            break
    if progress["last_game"] > 0:
        last_game = ano_jogos[progress["last_game"] - 1]
        p_acu = int(last_game['p_acu'])
        p_acu_total = int(ano_jogos[-1]['p_acu'])
        progress["game_progress"]=int(progress["last_game"]*100/progress["total_games"])
        progress["score_percent"]=last_game['percent']
        progress["score_progress"]=int(p_acu*100/p_acu_total)
    return progress

