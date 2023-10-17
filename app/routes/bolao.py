import json
from flask import Blueprint, current_app, render_template, session, request, url_for, flash
from app.routes.backend import getBolaoUsers,progress_data,get_aposta,get_users,get_games,make_score_board,get_user_name,get_bet_results,get_bet_results2,get_rank
import pymongo
from werkzeug.utils import redirect
from ..extentions.database import mongo
from datetime import date, datetime
from operator import itemgetter
from ..cache import cache

bolao = Blueprint('bolao',__name__)

ANO=23
APOSTADB='apostas23'

@cache.memoize(3600)
def get_history_data(results,ano):
    basehis = 'bolao' + str(ano) + 'his'
    gr_users = getBolaoUsers(int(ano))
    gr_data = []
    dias = [u['Dia'] for u in mongo.db[basehis].find({"nome": gr_users[0]}).sort("Dia",pymongo.ASCENDING)]
    #print("Dias l",len(dias))
    dias.append('H')
    for usr in gr_users:
        historia = [u['score'] for u in mongo.db[basehis].find({"nome": usr}).sort("Dia",pymongo.ASCENDING)]
        #print(f'Historia para {usr} l{len(historia)}: {historia}')
        for item in results:
            if item["nome"] == usr:
                historia.append(item["score"])
        gr_data.append(historia)

    return dias,gr_data

@bolao.route('/api/get_bolao<ano>')
def get_bolao_data(ano,apostador=""):
    ano_bolao = int(ano)
    base_bolao = 'apostas' + ano

    list_next_bet = []
    output = []
    now = datetime.now()
    ano_jogos = get_games(ano_bolao)
    allUsers = getBolaoUsers(ano)
    resultados = []

    if int(ano) == ANO:
        progresso = progress_data()
    else:
        progresso = ""
    
    for jogo in ano_jogos:
        id_jogo = jogo["Jogo"]

        # Temporario para Catar
        if ano == '2022':
            if id_jogo == 1 or id_jogo == 18 or id_jogo == 33:
                jogo["Time1"] = "Qatar"

        data_jogo = datetime.strptime(jogo["Data"],"%d/%m/%Y %H:%M")
        #aposta = apostas.find_one_or_404({"Jogo": id_jogo})
        aposta = get_aposta(id_jogo,base_bolao)
        # If game is old and score not empty -> and jogo['p1'] != ""
        if data_jogo < now:
            if ano_bolao >= 22 and ano_bolao < 2000:
                jogo_inc = get_bet_results2(allUsers,aposta,jogo)
            else:
                jogo_inc = get_bet_results(allUsers,aposta,jogo)
            jogo_inc.pop('_id', None)
            resultados.append(jogo_inc)
        # If game will happen, is definned and user is logged in
        elif data_jogo > now and apostador and jogo['Time1'] and jogo['Time2']:
            ap1 = apostador + "_p1"
            ap2 = apostador + "_p2"
            if aposta.get(ap1) != None:
                jogo["bet1"]=str(aposta.get(ap1))
                jogo["bet2"]=str(aposta.get(ap2))
            else:
                list_next_bet.append(jogo['Jogo'])
            output.append(jogo)

    # print(list_next_bet)
    # print(json.dumps(list_next_bet))
    # if apostador:
    #     cache.set(apostador,,3600)
    #     print(f'Set cache: "lista": {list_next_bet}')
    ordered_total = make_score_board(ano_bolao)
    gr_labels,gr_data = get_history_data(ordered_total,ano)

    return {"Ano": ano, "apostador": apostador, "next_bet": json.dumps(list_next_bet), "lista_jogos": output, 'users': allUsers, "grafico": {"labels": gr_labels, "data": gr_data}, 'ranking': ordered_total, 'progress_data':  progresso,'resultados': resultados}

@bolao.route('/bolao<ano>')
def apostas(ano):
    #ano = '2022'
    if ano not in ['23','22','2022','21','20']:
        flash(f'Página do bolao {ano} não encontrada.','danger')
        ano = '23'

    if session.get('username') == None:
        dados = get_bolao_data(ano)
    else:
        apostador = get_user_name(session["username"])
        dados = get_bolao_data(ano,apostador)
    return render_template("bolao.html",menu="Bolao",dados=dados)

@bolao.route('/regras')
def regras():
    allUsers = get_users('cp')
    qtd = len(allUsers)
    inscricao = 50
    bolao = qtd*inscricao
    premio = [qtd,"{:.2f}".format(bolao*0.6),"{:.2f}".format(bolao*0.3),"{:.2f}".format(bolao*0.1),"{:.2f}".format(bolao)]
    return render_template("regras.html",menu="Regras",premio=premio)

@bolao.route('/sobre')
def sobre():
    return render_template("sobre.html",menu="Sobre")

@bolao.route('/aposta',methods=["GET","POST"])
def edit_aposta():
    if "username" in session:
        validUser = mongo.db.users.find_one({"username": session["username"]})
        apostador = validUser["name"]
        jogoid = int(request.values.get("jogoid"))
        # Faixa no ano22 de jogos que precisa indicar vencedor
        faixa_j = [9,10,34,35,59,60,25,50]
        faixa_j = faixa_j + [u for u in range(75,100)]
        faixa_j = faixa_j + [u for u in range(172,204)]
        if jogoid in faixa_j:
            faixavit = True
        else:
            faixavit = False
        jogo = mongo.db.jogos.find_one_or_404({"Ano": ANO,"Jogo": jogoid})
        aposta = mongo.db[APOSTADB].find_one_or_404({"Jogo": jogoid})
        a1 = aposta.get(str(apostador + "_p1"))
        a2 = aposta.get(str(apostador + "_p2"))
        if a1 == None:
            a1 = ""
        if a2 == None:
            a2 = ""
        r1 = get_rank(jogo['Time1'])['posicao']
        r2 = get_rank(jogo['Time2'])['posicao']
        nextbetarr = request.values.get('nextbet')
        if nextbetarr:
            list_next_bet = json.loads(nextbetarr)
        else:
            list_next_bet = []
        if list_next_bet and jogoid in list_next_bet:
            list_next_bet.remove(jogoid)

        p1 = request.values.get("p1")
        p2 = request.values.get("p2")
        vit = request.values.get("vitradio")
        if p1 and request.method == "POST":
            data_jogo = datetime.strptime(request.values.get("data"),"%d/%m/%Y %H:%M")
            now = datetime.now()
            if not p1.isdigit() or not p2.isdigit():
                flash("Placar deve ser um número",'danger')
            elif now > data_jogo:
                flash("Data do jogo já passou",'danger')
                current_app.logger.info(f"Apostador {apostador} tentou apostar no jogo {jogoid} com data passada")
            elif jogoid in faixa_j and not vit and p1 == p2:
                flash("Deve-se indicar vitorioso em caso de empate",'danger')
            else:
                if jogoid in faixa_j and p1 == p2:
                    outdb = mongo.db[APOSTADB].find_one_and_update(
                        {"Jogo": jogoid},
                        {'$set': {
                            str(apostador + "_p1"): int(p1),
                            str(apostador + "_p2"): int(p2),
                            str(apostador + "_vit"): vit
                            }})
                else:
                    outdb = mongo.db[APOSTADB].find_one_and_update(
                        {"Jogo": jogoid},
                        {'$set': {
                            str(apostador + "_p1"): int(p1),
                            str(apostador + "_p2"): int(p2)
                            }})
                if outdb:
                    flash(f'Placar adicionado com sucesso no jogo {jogoid}!','success')
                    current_app.logger.info(f"Usuário {apostador} apostou no jogo {jogoid}")
                    # next jogoid
                    #print(f'nextid: {list_next_bet},nextbet={json.dumps(list_next_bet)}')
                    if list_next_bet:
                        nextjogo = list_next_bet[0]
                        return redirect(url_for('bolao.edit_aposta',jogoid=nextjogo,nextbet=json.dumps(list_next_bet)))
                    else:
                        flash(f'Apostas finalizadas','success')
                        return redirect(url_for('bolao.apostas',ano='22'))
                else:
                    flash(f'Erro ao escrever na base placar do jogo {jogoid}','danger')
                    current_app.logger.error(f"Erro ao escrever na base: aposta de {apostador} do jogo {jogoid}")
        return render_template('edit_aposta.html',menu='Bolao',jogo=jogo,a1=a1,a2=a2,idjogo=jogoid,r1=r1,r2=r2,faixavit=faixavit,nextbet=json.dumps(list_next_bet))
    else:
        return redirect(url_for('usuario.login'))


# Funcao criada para cadastro na copa
@bolao.route('/placar',methods=["GET","POST"])
def edit_placar():
    if 'username' in session and session['username'] == 'leafarlins@gmail.com':
        lista_jogos = get_games(ANO)
        if request.method == "GET":
            progresso = progress_data()
            current_game = progresso['last_game']
        else:
            p1 = int(request.values.get("p1"))
            p2 = int(request.values.get("p2"))
            current_game = int(request.values.get("jids"))
            tr1 = request.values.get("tr1")
            tr2 = request.values.get("tr2")
            pe1 = request.values.get("pe1")
            pe2 = request.values.get("pe2")
            if tr1:
                tr1 = int(tr1)
                tr2 = int(tr2)
                if pe1:
                    pe1 = int(pe1)
                    pe2 = int(pe2)
            outdb = mongo.db['jogos'].find_one_and_update(
                    {"Jogo": current_game, "Ano": ANO},
                    {'$set': {
                        'p1': p1, 'p2': p2, 'tr1': tr1, 'tr2': tr2, 'pe1': pe1, 'pe2': pe2
                    }})
            if outdb:
                flash(f'Placar adicionado no jogo {current_game}: {p1}x{p2}','success')
                current_app.logger.info(f"Placar do jogo {current_game} cadastrado")
            else:
                flash(f'Erro no cadastro do jogo {current_game}','danger')
                current_app.logger.error(f"Erro ao cadastrar placar do jogo {current_game}")

        data = {
            'jogos': lista_jogos,
            'last_game': current_game
        }

        return render_template('placar.html',data=data)
    else:
        return redirect(url_for('gokopa.home'))

