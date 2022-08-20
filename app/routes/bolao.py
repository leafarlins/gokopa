from flask import Blueprint, render_template, session, request, url_for, flash
import pymongo
from werkzeug.utils import redirect
from ..extentions.database import mongo
from datetime import date, datetime
from operator import itemgetter
from ..cache import cache

bolao = Blueprint('bolao',__name__)

ANO=21

@cache.memoize(300)
def get_games():
    ano_jogos = [u for u in mongo.db.jogos.find({'Ano': ANO}).sort("Jogo",pymongo.ASCENDING)]
    return ano_jogos

@cache.memoize(600)
def get_users(tipo):
    if tipo == 'gk':
        allUsers = [u.get("name") for u in mongo.db.users.find({"active": True,"gokopa": True}).sort("name",pymongo.ASCENDING)]
    else:
        allUsers = [u.get("name") for u in mongo.db.users.find({"active": True}).sort("name",pymongo.ASCENDING)]
    return allUsers

@cache.memoize(3600*2)
def read_config_ranking():
    dbitem = mongo.db.settings.find_one({"config": "ranking"})
    return dbitem.get('edition')

@cache.memoize(3600*24)
def get_rank(time):
    rank_ed = read_config_ranking()
    ranking = mongo.db.ranking.find_one({"ed": rank_ed,"time": time})
    if ranking:
        return ranking['pos']
    else:
        return ""

@cache.memoize(3600)
def get_user_name(username):
    validUser = mongo.db.users.find_one_or_404({"username": username})
    return validUser["name"]

@cache.memoize(3600*24*7)
def get_score_game(p1,p2,b1,b2):
    score=0
    if p1 == b1 and p2 == b2:
        # Placar cheio
        score = 5
    elif (p1 > p2 and b1 > b2) or (p1 == p2 and b1 == b2) or (p1 < p2 and b1 < b2):
        # Acertou vitoria/empate
        score = 2
        # Ponto extra se saldo igual
        if (p1-p2) == (b1-b2) and (abs(p1-b1) == 1):
            score += 1 
    #print(f'Calculando score para aposta {b1}x{b2} e placar {p1}x{p2}: {score}')

    return score

@cache.memoize(3600)
def get_last_pos(user):
    user_last = [u for u in mongo.db.bolao21his.find({"nome": user}).sort("Dia",pymongo.DESCENDING)]
    if user_last:
        last_day = user_last[0].get("posicao")
        if len(user_last) >= 7:
            last_week = user_last[6].get("posicao")
        else:
            last_week = user_last[-1].get("posicao")
        return last_day,last_week
    else:
        return 0,0

# Insert in jogo bets and results foreach user
@cache.memoize(600)
def get_bet_results(users,aposta,jogo):
    peso=int(jogo['peso'])
    for user in users:
        b1 = aposta.get(str(user + "_p1"))
        b2 = aposta.get(str(user + "_p2"))
        if b1 == None or b2 == None:
            aposta_str="-"
            score = 0
        else:
            aposta_str=str(b1)+"x"+str(b2)
            # Caso jogo esta sem resultado ainda
            if jogo['p1'] == "" or jogo['p1'] == None:
                score = 0
            else:
                score = get_score_game(jogo['p1'],jogo['p2'],b1,b2)
        # Score com valor de pontos e valor de pontos*peso
        jogo[user]=[aposta_str,score,score*peso]
    return jogo

@cache.memoize(300)
def get_score_results(users,resultados):
        list_total=[]
        for u in users:
            udict=dict()
            udict["nome"]=u
            udict["score"]=0
            udict["pc"]=0
            last_position_day,last_position_week = get_last_pos(u)
            udict["last_day"] = last_position_day
            udict["last_week"] = last_position_week
            # sum score*peso foreach result
            for r in resultados:
                scores_user = r.get(u)
                if scores_user:
                    udict["score"]+=int(scores_user[2])
                    if scores_user[1] == 5:
                        udict["pc"] += 1 
            list_total.append(udict)
        return list_total

@cache.memoize(10)
def get_aposta(id_jogo):
    apostas = mongo.db.apostas21
    return apostas.find_one_or_404({"Jogo": id_jogo})

@cache.memoize(600)
def make_score_board(tipo):
    now = datetime.now()
    ano_jogos = get_games()
    allUsers = get_users(tipo)
    resultados = []
        
    for jogo in ano_jogos:
        id_jogo = jogo["Jogo"]
        data_jogo = datetime.strptime(jogo["Data"],"%d/%m/%Y %H:%M")
        aposta = get_aposta(id_jogo)
        # If game is old and score not empty
        if data_jogo < now and jogo['p1'] != "":
            jogo_inc = get_bet_results(allUsers,aposta,jogo)
            resultados.append(jogo_inc)
    
    list_total=get_score_results(allUsers,resultados)

    ordered_total = sorted(sorted(list_total, key=lambda k: k['pc'],reverse=True), key=lambda k: k['score'],reverse=True)
    last_score = 0
    last_pc = 0
    last_pos = 1
    for i in range(len(ordered_total)):
        if ordered_total[i]["score"] == last_score and ordered_total[i]["pc"] == last_pc:
            ordered_total[i]["posicao"] = last_pos
        else:
            ordered_total[i]["posicao"] = i+1
            last_score = ordered_total[i]["score"]
            last_pc = ordered_total[i]["pc"]
            last_pos = i+1

    return ordered_total

@cache.memoize(3600*3)
def get_history_data(results,tipo):
    gr_users = get_users(tipo)
    gr_data = []
    dias = [u['Dia'] for u in mongo.db.bolao21his.find({"nome": gr_users[0],"tipo":tipo}).sort("Dia",pymongo.ASCENDING)]
    print("Dias l",len(dias))
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
    return render_template("bolao.html",menu="Bolao",tipo=tipo,userlogado=userLogado,lista_jogos=output,resultados=resultados,total=ordered_total,users=allUsers,gr_labels=gr_labels,gr_data=gr_data)
    

@bolao.route('/cp/regras')
def regras():
    allUsers = get_users('cp')
    qtd = len(allUsers)
    inscricao = 50
    bolao = qtd*inscricao
    premio = [qtd,"{:.2f}".format(bolao*0.6),"{:.2f}".format(bolao*0.3),"{:.2f}".format(bolao*0.1),"{:.2f}".format(bolao)]
    return render_template("regras.html",menu="Regras",tipo='cp',premio=premio)

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
