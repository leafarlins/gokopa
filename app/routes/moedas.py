from flask import Blueprint, render_template, session, request, url_for, flash
from app.routes.backend import get_free_teams, get_moedas_board, get_next_jogos, get_pat_teams, moedas_log, progress_data,get_aposta,get_users,get_games,make_score_board,get_user_name,get_bet_results,get_rank
import pymongo
from werkzeug.utils import redirect
from ..extentions.database import mongo
from datetime import date, datetime
from operator import itemgetter
from ..cache import cache

moedas = Blueprint('moedas',__name__)

ANO=21

@cache.memoize(60)
def get_moedas_info():
    jogos = get_next_jogos()
    board = get_moedas_board()
    logs = [u for u in mongo.db.moedaslog.find().sort('lid',pymongo.DESCENDING)]


    return {'moedas_board': board['moedas_board'], 'jogos': jogos['next_jogos'][:16], 'ultimos_jogos': jogos['past_jogos'][:16],'logs': logs,'logsindex': 0,'logspages': int(len(logs)/80)+1}

@moedas.route('/gk/moedas',methods=['GET','POST'])
def gamemoedas():
    user_info = {}
    info = get_moedas_info()
    lista_pat = get_pat_teams()
    print(request.values.get("pageind"))
    if request.values.get("pageind"):
        info['logsindex'] = int(request.values.get("pageind"))
    if session.get('username') == None:
        userLogado=False
    else:
        validUser = mongo.db.users.find_one_or_404({'username': session["username"]})
        if validUser["gokopa"]:
            userLogado = True
            info['username'] = validUser['name']
            user_info['lista_leilao'] = lista_pat['lista_leilao']
            user_info["lista_livre"] = lista_pat['livres']
            user_info["nome"] = validUser['name']
            moedas_user = mongo.db.moedas.find_one({'nome': validUser['name']})
            user_info['saldo'] = moedas_user['saldo']
            user_info['tentarpat'] = [u for u in mongo.db.tentarpat.find({'nome': validUser['name']})]
        else:
            userLogado = False
    
    info['userlogado'] = userLogado
    if not userLogado:
        info['username'] = 'false'
    info['patrocinados'] = lista_pat['patrocinados']

    return render_template('moedas.html',menu='Moedas',tipo='gk',info=info,user_info=user_info)

@cache.memoize(60)
def get_apoio_liberado(time):
    pat_teams = get_pat_teams()
    apoio_liberado = False
    for t in pat_teams['livres']:
        if t['time'] == time:
            return True
    for t in pat_teams['patrocinados']:
        if t['time'] == time:
            if t['apoio_liberado']:
                return True
    return apoio_liberado

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


@moedas.route('/gk/moedas/removepat',methods=["POST"])
def removepat():
    if "username" in session:
        validUser = mongo.db.users.find_one({"username": session["username"]})
        apostador = validUser["name"]
        time = request.values.get("time_pat")
        valor = int(request.values.get("valor_pat"))
        apoio_liberado = get_apoio_liberado(time)
        if not apoio_liberado:
            flash(f'Apoio não liberado no momento.','danger')
        else:
            patDb = mongo.db.tentarpat.find_one_and_delete({'nome': apostador, 'time': time})
            if not patDb:
                flash(f'Tentativa de apoio não encontrada.','danger')
            else:
                outdb = mongo.db.moedas.find_one_and_update({'nome': apostador},{'$inc':{'saldo': valor,'bloqueado': -valor}})
                if outdb:
                    flash(f'Tentativa de patrocínio removida para {time}!','success')
                else:
                    flash(f'Erro na atualização da base.','danger')
    else:
        flash(f'Usuário não logado.','danger')
    return redirect(url_for('moedas.gamemoedas'))

@moedas.route('/gk/moedas/addapoio',methods=["POST"])
def addapoio():
    if "username" in session:
        validUser = mongo.db.users.find_one({"username": session["username"]})
        apostador = validUser["name"]
        time = request.values.get("time_apoio")
        valor = int(request.values.get("valor_apoio"))
        #print(f'time {time} valor {valor}')
        moedasDb = mongo.db.moedas.find_one({'nome': apostador})
        saldo_atual = moedasDb['saldo']
        timeDb = mongo.db.patrocinio.find_one({'Time': time})
        apoio_liberado = get_apoio_liberado(time)
        if valor > saldo_atual:
            flash(f'Usuário não possui saldo suficiente.','danger')
        elif not apoio_liberado:
            flash(f'Apoio não liberado no momento.','danger')
        elif valor <=0:
            flash(f'Valor inválido!','danger')
        else:
            apoios = timeDb.get('Apoiadores')
            atualizado = False
            if apoios:
                for a in apoios:
                    if a['nome'] == apostador:
                        a['valor'] += valor
                        atualizado = True
            else:
                apoios = []
            if not atualizado:
                apoios.append({'nome': apostador, 'valor': valor})
            outdb = mongo.db.moedas.find_one_and_update({'nome': apostador},{'$inc': {'saldo': -valor,'investido': valor}})
            outdb2 = mongo.db.patrocinio.find_one_and_update({'Time': time},{'$set': {'Apoiadores': apoios}})
            if outdb and outdb2:
                flash(f'Apoio adicionado','success')
                moedas_log(apostador,'i '+str(valor),time,0,"Apoio adicionado")
            else:
                flash(f'Erro na atualização da base.','danger')
    else:
        flash(f'Usuário não logado.','danger')
    return redirect(url_for('moedas.gamemoedas'))

@moedas.route('/gk/moedas/removeapoio',methods=["POST"])
def removeapoio():
    if "username" in session:
        validUser = mongo.db.users.find_one({"username": session["username"]})
        apostador = validUser["name"]
        time = request.values.get("time_apoio")
        valor = int(request.values.get("valor_apoio"))
        timeDb = mongo.db.patrocinio.find_one({'Time': time})
        apoios = timeDb['Apoiadores']
        apoio_liberado = get_apoio_liberado(time)
        if not apoio_liberado:
            flash(f'Apoio não liberado no momento.','danger')
        else:
            try:
                apoios.remove({'nome': apostador,'valor': valor})
            except:
                flash(f'Erro na remoção de apoio de {apostador}.','danger')
            
            outdb = mongo.db.moedas.find_one_and_update({'nome': apostador},{'$inc': {'saldo': valor,'investido': -valor}})
            outdb2 = mongo.db.patrocinio.find_one_and_update({'Time': time},{'$set': {'Apoiadores': apoios}})
            if outdb and outdb2:
                flash(f'Apoio removido','success')
                moedas_log(apostador,'x '+str(valor),time,0,"Retirada de apoio")
            else:
                flash(f'Erro na atualização da base.','danger')
    else:
        flash(f'Usuário não logado.','danger')
    return redirect(url_for('moedas.gamemoedas'))


@moedas.route('/gk/moedas/addvalorpat',methods=["POST"])
def addvalorpat():
    if "username" in session:
        validUser = mongo.db.users.find_one({"username": session["username"]})
        apostador = validUser["name"]
        time = request.values.get("time_apoio")
        valor = int(request.values.get("valor_apoio"))
        moedasDb = mongo.db.moedas.find_one({'nome': apostador})
        saldo_atual = moedasDb['saldo']
        apoio_liberado = get_apoio_liberado(time)
        if not apoio_liberado:
            flash(f'Apoio não liberado no momento.','danger')
        elif valor > saldo_atual:
            flash(f'Usuário não possui saldo suficiente.','danger')
        else:
            outdb = mongo.db.moedas.find_one_and_update({'nome': apostador},{'$inc': {'saldo': -valor,'investido': valor}})
            outdb2 = mongo.db.patrocinio.find_one_and_update({'Time': time},{'$inc': {'Valor': valor}})
            if outdb and outdb2:
                flash(f'Patrocínio atualizado','success')
                moedas_log(apostador,'i '+str(valor),time,0,"Patrocínio adicionado")
            else:
                flash(f'Erro na atualização da base.','danger')
    else:
        flash(f'Usuário não logado.','danger')
    return redirect(url_for('moedas.gamemoedas'))
