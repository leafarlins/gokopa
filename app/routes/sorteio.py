from app.routes.bolao import get_rank, make_score_board, read_config_ranking
from array import array
from datetime import datetime, time
from typing import Collection
from flask import Blueprint, app, render_template, session, request, url_for, flash
import pymongo
from pymongo import collection
from werkzeug.utils import redirect
from werkzeug.security import check_password_hash
from ..extentions.database import mongo
from ..cache import cache
import threading
from turbo_flask import Turbo
from .gokopa import get_team_table

#current_app para carregar app.py

sorteio = Blueprint('sorteio',__name__)

ANO=20
turbo = Turbo(app)

@sorteio.context_processor
def inject_load():
    now = datetime.strftime(datetime.now,"%H:%M:%S")
    return {'time_now': now }

def update_load():
    with app.app_context():
        while True:
            time.sleep(5)
            turbo.push(turbo.replace(render_template('loadavg.html'), 'load'))

@sorteio.before_first_request
def before_first_request():
    threading.Thread(target=update_load().start())

@sorteio.route('/sorteio')
def sorteio_page():
    tabelas_label = ['A','B','C','D','E','F','G','H']
    tabelas = []
    tabela_pot = []
    # Tabelas para campeonatos regionais
    for i in range(8):
        desc1 = "p" + str(1) + tabelas_label[i]
        desc2 = "p" + str(2) + tabelas_label[i]
        desc3 = "p" + str(3) + tabelas_label[i]
        time1 = get_team_table('desc1',desc1,'Time1')
        time2 = get_team_table('desc1',desc2,'Time1')
        time3 = get_team_table('desc2',desc3,'Time2')
        desc4 = "p" + str(4) + tabelas_label[i]
        time4 = get_team_table('desc2',desc4,'Time2')
        times = [time1,time2,time3,time4]
        descs = [desc1,desc2,desc3,desc4]
        for j in range(len(times)):
            linha = dict()
            if times[j]:
                linha['nome'] = times[j]
                linha['rank'] = get_rank(times[j])
            else:
                linha['nome'] = descs[j]
                #tab.update({'nome': desc})
            tabelas.append(linha)
    
    # Tabela de pots
    for i in range(4):
        times = []
        times_pot = [u for u in mongo.db.pot.find({"Ano": ANO,"pot": int(i+1)}).sort('nome',pymongo.ASCENDING)]
        tabela_pot.append(times_pot)
    print(tabela_pot)


    return render_template('sorteio.html',menu='Home',labels=tabelas_label,tabelas=tabelas,tabela_pot=tabela_pot)