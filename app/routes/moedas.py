from flask import Blueprint, render_template, session, request, url_for, flash, current_app
from app.routes.backend import get_free_teams, get_moedas_board, get_next_jogos, get_pat_teams, moedas_log, progress_data,get_users,get_games,make_score_board,get_user_name,get_bet_results,get_rank
import pymongo
from werkzeug.utils import redirect
from ..extentions.database import mongo
from datetime import date, datetime
from operator import itemgetter
from ..cache import cache

moedas = Blueprint('moedas',__name__)

ANO=24
MAX_LOG_PAGE=100

@cache.memoize(10)
def get_moedas_info():
    jogos = get_next_jogos()
    board = get_moedas_board()
    logs = [u for u in mongo.db.moedaslog.find().sort('lid',pymongo.DESCENDING)]


    return {'moedas_board': board['moedas_board'], 'jogos': jogos['next_jogos'][:16], 'ultimos_jogos': jogos['past_jogos'][:16],'logs': logs,'logsindex': 0,'logspages': int(len(logs)/MAX_LOG_PAGE)+1}

@moedas.route('/moedas',methods=['GET','POST'])
def gamemoedas():
    user_info = {}
    info = get_moedas_info()
    lista_pat = get_pat_teams()
    if request.values.get("pageind"):
        info['logsindex'] = int(request.values.get("pageind"))
    if session.get('username') == None:
        userLogado=False
    else:
        validUser = mongo.db.users.find_one_or_404({'username': session["username"]})
        if validUser["gokopa"]:
            userLogado = True
            info['username'] = validUser['name']
            user_info['lista_leilao'] = lista_pat.get('lista_leilao')
            user_info["lista_livre"] = lista_pat.get('livres')
            user_info["lista_avenda"] = lista_pat.get('lista_avenda')
            meus_avenda = []
            for item in lista_pat.get('lista_avenda'):
                if item['patrocinador'] == validUser['name']:
                    meus_avenda.append(item)
            user_info['meus_avenda'] = meus_avenda
            user_info["nome"] = validUser['name']
            moedas_user = mongo.db.moedas.find_one({'nome': validUser['name']})
            user_info['saldo'] = moedas_user['saldo']
            user_info['tentarpat'] = [u for u in mongo.db.tentarpat.find({'nome': validUser['name']})]
            meus_pat = []
            for item in lista_pat.get('patrocinados'):
                if item.get('patrocinador') == validUser['name']:
                    meus_pat.append(item)
            user_info['meus_pat'] = meus_pat
            # Escreve nos dados de jogos meu apoio, caso exista, para cada time
            for j in info['jogos']:
                if j['pat1'] != '-':
                    j['meuapo1'] = 0
                    if j.get('apo1'):
                        for item in j.get('apo1'):
                            if item['nome'] == info['username']:
                                j['meuapo1'] = item['valor']
                if j['pat2'] != '-':
                    j['meuapo2'] = 0
                    if j.get('apo2'):
                        for item in j.get('apo2'):
                            if item['nome'] == info['username']:
                                j['meuapo2'] = item['valor']
        else:
            userLogado = False
    
    info['userlogado'] = userLogado
    if not userLogado:
        info['username'] = 'false'
    info['patrocinados'] = lista_pat.get('patrocinados')

    #print(info,user_info)

    return render_template('moedas.html',menu='Moedas',info=info,user_info=user_info)

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
            mongo.db.tentarpat.insert_one(patrocinio)
            novo_saldo = saldo_atual - valor
            bloqueado = valor + moedasDb['bloqueado']
            outdb = mongo.db.moedas.find_one_and_update({'nome': apostador},{'$set':{'saldo': novo_saldo,'bloqueado': bloqueado}})
            if outdb:
                flash(f'Tentativa de patrocínio adicionada para {time} com {valor}!','success')
                current_app.logger.info(f"Tentativa de pat a {time} adicionada pelo {apostador}")
            else:
                flash(f'Erro na atualização da base.','danger')
                current_app.logger.error(f"Erro na atualização da base: {apostador} add pat de {time}")
    else:
        flash(f'Usuário não logado.','danger')
    return redirect(url_for('moedas.gamemoedas'))

@moedas.route('/gk/moedas/venderpat',methods=["POST"])
def venderpat():
    if "username" in session:
        validUser = mongo.db.users.find_one({"username": session["username"]})
        apostador = validUser["name"]
        time = request.values.get("timevenda")
        valor = int(request.values.get("valor_venda"))
        if valor < 0:
            flash(f"Valor de venda inválido","danger")
        else:
            outdb = mongo.db.patrocinio.find_one_and_update({'Time': time},{'$set':{'avenda': valor}})
            if outdb:
                flash(f'Time {time} colocado à venda por {valor}!','success')
                current_app.logger.info(f"Apostador {apostador} colocou {time} à venda por {valor}")
            else:
                flash(f'Erro na atualização da base.','danger')
                current_app.logger.error(f"Erro na atualização da base: {time} colocado à venda por {valor}")
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
                    current_app.logger.info(f"Tentativa de pat a {time} retirado pelo usuário {apostador}")
                else:
                    flash(f'Erro na atualização da base.','danger')
                    current_app.logger.error(f"Erro na atualização da base: {apostador} remove pat de {time}")
    else:
        flash(f'Usuário não logado.','danger')
    return redirect(url_for('moedas.gamemoedas'))


@moedas.route('/gk/moedas/removeavenda',methods=["POST"])
def removeavenda():
    if "username" in session:
        validUser = mongo.db.users.find_one({"username": session["username"]})
        apostador = validUser["name"]
        time = request.values.get("time_av")
        valor = int(request.values.get("valor_av"))
        checktp = mongo.db.tentarpat.find_one({'time': time,'processar': True})
        if checktp:
            flash(f'Venda não pode mais ser cancelada','danger')
        else:
            outdb = mongo.db.patrocinio.find_one_and_update({'Time': time,'Patrocinador': apostador},{'$set':{'avenda': ""}})
            if outdb:
                flash(f'Venda do time {time} cancelada','success')
                current_app.logger.info(f"{apostador} cancelou venda de {time}")
            else:
                flash(f'Patrocínio não encontrado','danger')
                current_app.logger.error(f"{apostador} tentou cancelar venda de {time}")
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
                current_app.logger.info(f"Apoio adicionado ao {time} pelo usuário {apostador}")
            else:
                flash(f'Erro na atualização da base.','danger')
                current_app.logger.error(f"Erro na atualização da base: {apostador} adiciona apoio {valor} ao {time}")
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
                current_app.logger.warn(f"Erro na remoção de apoio de {valor} de {time}, operação não realizada.")
            else:
                outdb = mongo.db.moedas.find_one_and_update({'nome': apostador},{'$inc': {'saldo': valor,'investido': -valor}})
                outdb2 = mongo.db.patrocinio.find_one_and_update({'Time': time},{'$set': {'Apoiadores': apoios}})
                if outdb and outdb2:
                    flash(f'Apoio removido','success')
                    moedas_log(apostador,'x '+str(valor),time,0,"Retirada de apoio")
                    current_app.logger.info(f"Apoio a {time} retirado pelo usuário {apostador}")
                else:
                    flash(f'Erro na atualização da base.','danger')
                    current_app.logger.error(f"Erro na atualização da base: {apostador} remove apoio de {valor} de {time}")
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
                current_app.logger.info(f"Patrocínio a {time} adicionado pelo usuário {apostador}")
            else:
                flash(f'Erro na atualização da base.','danger')
                current_app.logger.error(f"Erro na atualização da base: {apostador} add valor pat de {valor} ao time {time}")
    else:
        flash(f'Usuário não logado.','danger')
    return redirect(url_for('moedas.gamemoedas'))
