from flask import Blueprint, render_template, session, request, url_for, flash
from app.routes.backend import get_free_teams, get_moedas_board, get_next_jogos, progress_data,get_aposta,get_users,get_games,make_score_board,get_user_name,get_bet_results,get_rank
import pymongo
from werkzeug.utils import redirect
from ..extentions.database import mongo
from datetime import date, datetime
from operator import itemgetter
from ..cache import cache

moedas = Blueprint('moedas',__name__)

ANO=21

@cache.memoize(600)
def get_moedas_info():
    jogos = get_next_jogos()
    board = get_moedas_board()
    return {'moedas_board': board['moedas_board'], 'jogos': jogos['next_jogos'][:16]}

@moedas.route('/gk/moedas')
def gamemoedas():
    user_info = {}
    if session.get('username') == None:
        userLogado=False
    else:
        validUser = mongo.db.users.find_one_or_404({'username': session["username"]})
        if validUser["gokopa"]:
            userLogado = True
            lista = get_free_teams()
            user_info["lista_livre"] = lista['Livres']
            user_info["nome"] = validUser['name']
            moedas_user = mongo.db.moedas.find_one({'nome': validUser['name']})
            user_info['saldo'] = moedas_user['saldo']
            user_info['tentarpat'] = [u for u in mongo.db.tentarpat.find({'nome': validUser['name']})]
        else:
            userLogado = False
    
    info = get_moedas_info()
    info['userlogado': userLogado]
    return render_template('moedas.html',menu='Moedas',tipo='gk',info=info,user_info=user_info)

@moedas.route('/gk/moedas/addpat',methods=["POST"])
def addpat():
    if "username" in session:
        validUser = mongo.db.users.find_one({"username": session["username"]})
        apostador = validUser["name"]
        time = request.values.get("timename")
        valor = int(request.values.get("valor_pat"))
        now = datetime.now()
        moedasDb = mongo.db.moedas.find_one({'nome': apostador})
        saldo_atual = moedasDb['saldo']
        if valor > saldo_atual:
            flash(f'Usuário não possui saldo suficiente.','danger')
        else:
            patrocinio = {
                'nome': apostador,
                'valor': valor,
                'time': time,
                'timestamp': now
            }
            mongo.db.tentarpat.insert(patrocinio)
            novo_saldo = saldo_atual - valor
            bloqueado = valor + moedasDb['bloqueado']
            outdb = mongo.db.moedas.find_one_and_update({'nome': apostador},{'$set':{'saldo': novo_saldo,'bloqueado': bloqueado}})
            if outdb:
                flash(f'Tentativa de patrocínio adicionada para {time} com {valor}!','success')
            else:
                flash(f'Erro na atualização da base.','danger')
    else:
        flash(f'Usuário não logado.','danger')
    return redirect(url_for('moedas.gamemoedas'))


