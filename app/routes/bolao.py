from flask import Blueprint, render_template, session, request, url_for, flash
from app.routes.backend import progress_data,get_aposta,get_users,get_games,make_score_board,get_user_name,get_bet_results,get_rank
import pymongo
from werkzeug.utils import redirect
from ..extentions.database import mongo
from datetime import date, datetime
from operator import itemgetter
from ..cache import cache

bolao = Blueprint('bolao',__name__)

ANO=21

@cache.memoize(3600*3)
def get_history_data(results,tipo):
    gr_users = get_users(tipo)
    gr_data = []
    dias = [u['Dia'] for u in mongo.db.bolao21his.find({"nome": gr_users[0],"tipo":tipo}).sort("Dia",pymongo.ASCENDING)]
    #print("Dias l",len(dias))
    dias.append('H')
    for usr in gr_users:
        historia = [u['score'] for u in mongo.db.bolao21his.find({"nome": usr, "tipo": tipo}).sort("Dia",pymongo.ASCENDING)]
        #print(f'Historia para {usr} l{len(historia)}: {historia}')
        for item in results:
            if item["nome"] == usr:
                historia.append(item["score"])
        gr_data.append(historia)


    return dias,gr_data



@bolao.route('/<tipo>/bolao<id>')
def old_bolao(id,tipo):
    if id == '20':
        return render_template('static/bolao20.html',menu='Bolao',tipo=tipo)
    else:
        return redirect(url_for('bolao.apostas',tipo=tipo))


@bolao.route('/<tipo>/bolao')
def apostas(tipo):
    list_next_bet = []
    output = []
    now = datetime.now()
    ano_jogos = get_games()
    allUsers = get_users(tipo)
    resultados = []
    if session.get('username') == None:
        userLogado=False
    else:
        apostador = get_user_name(session["username"])
        userLogado=True
    
    for jogo in ano_jogos:
        id_jogo = jogo["Jogo"]

        # Temporario para Catar
        if tipo == 'cp':
            if id_jogo == 1 or id_jogo == 18 or id_jogo == 33:
                jogo["Time1"] = "Qatar"

        data_jogo = datetime.strptime(jogo["Data"],"%d/%m/%Y %H:%M")
        #aposta = apostas.find_one_or_404({"Jogo": id_jogo})
        aposta = get_aposta(id_jogo)
        # If game is old and score not empty -> and jogo['p1'] != ""
        if data_jogo < now:
            jogo_inc = get_bet_results(allUsers,aposta,jogo)
            resultados.append(jogo_inc)
        # If game will happen, is definned and user is logged in
        elif data_jogo > now and userLogado and jogo['Time1'] and jogo['Time2']:
            ap1 = apostador + "_p1"
            ap2 = apostador + "_p2"
            if aposta.get(ap1) != None:
                jogo["bet1"]=str(aposta.get(ap1))
                jogo["bet2"]=str(aposta.get(ap2))
            else:
                list_next_bet.append(jogo['Jogo'])
            output.append(jogo)

    #print(list_next_bet)
    if userLogado:
        cache.set(apostador,list_next_bet,3600)
    #cache_timeout = 3600*24*7
    #cache.set('lista_bolao',ordered_total,cache_timeout)
    #cache.set('lista_date',lista_date,cache_timeout)
    ordered_total = make_score_board(tipo)
    gr_labels,gr_data = get_history_data(ordered_total,tipo)
    #print(gr_labels,gr_data)
    #rendered=render_template("bolao.html",menu="Bolao",userlogado=userLogado,lista_jogos=output,resultados=resultados,total=ordered_total,users=allUsers,gr_labels=gr_labels,gr_data=gr_data)
    #print(rendered)
    return render_template("bolao.html",menu="Bolao",tipo=tipo,userlogado=userLogado,lista_jogos=output,resultados=resultados,total=ordered_total,users=allUsers,gr_labels=gr_labels,gr_data=gr_data,progress_data=progress_data())
    

@bolao.route('/cp/regras')
def regras():
    allUsers = get_users('cp')
    qtd = len(allUsers)
    inscricao = 50
    bolao = qtd*inscricao
    premio = [qtd,"{:.2f}".format(bolao*0.6),"{:.2f}".format(bolao*0.3),"{:.2f}".format(bolao*0.1),"{:.2f}".format(bolao)]
    return render_template("regras.html",menu="Regras",tipo='cp',premio=premio)


@bolao.route('/<tipo>/contato')
def contato(tipo):
    return render_template("contato.html",menu="Contato",tipo=tipo)

@bolao.route('/<tipo>/editaposta',methods=["GET","POST"])
def edit_aposta(tipo):
    if "username" in session:
        validUser = mongo.db.users.find_one({"username": session["username"]})
        apostador = validUser["name"]
        idjogo = int(request.values.get("idjogo"))
        #print("idjogo:",idjogo)
        if idjogo != 0:
            jogo = mongo.db.jogos.find_one_or_404({"Ano": ANO,"Jogo": idjogo})
            aposta = mongo.db.apostas21.find_one_or_404({"Jogo": idjogo})
            a1 = aposta.get(str(apostador + "_p1"))
            a2 = aposta.get(str(apostador + "_p2"))
            if a1 == None:
                a1 = ""
            if a2 == None:
                a2 = ""
            r1 = get_rank(jogo['Time1'])
            r2 = get_rank(jogo['Time2'])
            # Temporario para Catar
            if tipo == 'cp':
                if idjogo == 1 or idjogo == 18 or idjogo == 33:
                    jogo["Time1"] = "Qatar"
        else:
            jogo = ""
            a1=""
            a2=""
            r1=""
            r2=""

        if request.method == "GET":
            #list_next_bet=request.values.get("list_next_bet")
            return render_template('edit_aposta.html',menu='Bolao',tipo=tipo,jogo=jogo,a1=a1,a2=a2,idjogo=idjogo,r1=r1,r2=r2)
        else:
            list_next_bet = cache.get(apostador)
            next_bet = 0
            if list_next_bet and len(list_next_bet)>0:
                if idjogo in list_next_bet:
                    list_next_bet.remove(idjogo)
                if len(list_next_bet)>0:
                    next_bet = list_next_bet.pop(0)
            #print("Next bet",next_bet)
            #print("Next bets",list_next_bet)
            cache.set(apostador,list_next_bet)

            p1 = request.values.get("p1")
            p2 = request.values.get("p2")
            data_jogo = datetime.strptime(request.values.get("data"),"%d/%m/%Y %H:%M")
            now = datetime.now()
            if not p1.isdigit() or not p2.isdigit():
                flash("Placar deve ser um número!",'danger')
            elif now > data_jogo:
                flash("Data do jogo já passou!",'danger')
            else:
                mongo.db.apostas21.find_one_and_update(
                    {"Jogo": idjogo},
                    {'$set': {
                        str(apostador + "_p1"): int(p1),
                        str(apostador + "_p2"): int(p2)
                        }})
                flash(f'Placar adicionado com sucesso no jogo {idjogo}!','success')
            return redirect(url_for('bolao.edit_aposta',tipo=tipo,idjogo=next_bet))
    else:
        return redirect(url_for('usuario.login',tipo=tipo))
