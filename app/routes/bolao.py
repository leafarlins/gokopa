from flask import Blueprint, render_template, session, request, url_for, flash
import pymongo
from werkzeug.utils import redirect
from ..extentions.database import mongo
from datetime import date, datetime
from operator import itemgetter
from ..cache import cache

bolao = Blueprint('bolao',__name__)

@cache.memoize(300)
def get_games():
    ano20_jogos = [u for u in mongo.db.jogos.find({'Ano': 20}).sort("Jogo",pymongo.ASCENDING)]
    return ano20_jogos

@cache.memoize(300)
def get_users():
    allUsers = [u.get("name") for u in mongo.db.users.find()]
    return allUsers

@cache.memoize(3600*24)
def get_rank(time):
    edicao_ranking = "19-3"
    ranking = mongo.db.ranking.find_one({"ed": edicao_ranking,"time": time})
    if ranking:
        return ranking['pos']
    else:
        return ""

@cache.memoize(3600)
def get_user_name(username):
    validUser = mongo.db.users.find_one_or_404({"username": username})
    return validUser["name"]

@cache.memoize(3600*24)
def get_score_game(p1,p2,b1,b2):
    score=1
    print(f'Calculando score para aposta {b1}x{b2} e placar {p1}x{p2}: {score}')
    return score

# Insert in jogo bets and results foreach user
@cache.memoize(3600)
def get_bet_results(users,aposta,jogo):
    peso=2
    for user in users:
        b1 = aposta.get(str(user + "_p1"))
        b2 = aposta.get(str(user + "_p2"))
        if b1 == None or b2 == None:
            aposta_str="-"
            score = 0
        else:
            aposta_str=str(b1)+"x"+str(b2)
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
            # sum score*peso foreach result
            for r in resultados:
                scores_user = r.get(u)
                if scores_user:
                    udict["score"]+=int(scores_user[2])
            list_total.append(udict)
        return list_total


@bolao.route('/bolao')
def apostas():
    ano20_jogos = get_games()
    allUsers = get_users()
    resultados = []
    output = []
    list_next_bet = []
    apostas = mongo.db.apostas20
    now = datetime.now()
    if "username" in session:
        apostador = get_user_name(session["username"])
        userLogado=True
    else:
        userLogado=False
        
    for jogo in ano20_jogos:
        id_jogo = jogo["Jogo"]
        data_jogo = datetime.strptime(jogo["Data"],"%d/%m/%Y %H:%M")
        aposta = apostas.find_one_or_404({"Jogo": id_jogo})
        # If game is old and score not empty
        if data_jogo < now and jogo['p1'] != "":
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
    

    if userLogado:
        cache.set(apostador,list_next_bet)

    list_total=get_score_results(allUsers,resultados)

    print(list_total)
    #sorted_total = sorted(total.items(), key=itemgetter(1),reverse=True)

    return render_template("bolao.html",menu="Bolao",userlogado=userLogado,lista_jogos=output,resultados=resultados,total=list_total,users=allUsers)
    

@bolao.route('/editaposta',methods=["GET","POST"])
def edit_aposta():
    ANO=20
    if "username" in session:
        validUser = mongo.db.users.find_one({"username": session["username"]})
        apostador = validUser["name"]
        idjogo = int(request.values.get("idjogo"))
        print("idjogo:",idjogo)
        if idjogo != 0:
            jogo = mongo.db.jogos.find_one_or_404({"Ano": ANO,"Jogo": idjogo})
            aposta = mongo.db.apostas20.find_one_or_404({"Jogo": idjogo})
            a1 = aposta.get(str(apostador + "_p1"))
            a2 = aposta.get(str(apostador + "_p2"))
            if a1 == None:
                a1 = ""
            if a2 == None:
                a2 = ""
            r1 = get_rank(jogo['Time1'])
            r2 = get_rank(jogo['Time2'])
        else:
            jogo = ""
            a1=""
            a2=""
            r1=""
            r2=""

        if request.method == "GET":
            #list_next_bet=request.values.get("list_next_bet")
            return render_template('edit_aposta.html',menu='Bolao',jogo=jogo,a1=a1,a2=a2,idjogo=idjogo,r1=r1,r2=r2)
        else:
            list_next_bet = cache.get(apostador)
            if list_next_bet and len(list_next_bet)>0:
                list_next_bet.remove(idjogo)
                next_bet = list_next_bet.pop(0)
            else:
                next_bet = 0
            print("Next bet",next_bet)
            print("Next bets",list_next_bet)
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
                mongo.db.apostas20.find_one_and_update(
                    {"Jogo": idjogo},
                    {'$set': {
                        str(apostador + "_p1"): int(p1),
                        str(apostador + "_p2"): int(p2)
                        }})
                flash(f'Placar adicionado com sucesso no jogo {idjogo}!','success')
            return redirect(url_for('bolao.edit_aposta',idjogo=next_bet))
    else:
        return redirect(url_for('usuario.login'))

    
@bolao.route('/apostado')
def apostado():

    if "username" in session:
        return render_template('apostado.html',menu='Bolao',idjogo=1,status="success")

    else:
        return redirect(url_for('usuario.login'))