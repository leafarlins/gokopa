from flask import Blueprint, render_template, session, request, url_for, flash
import pymongo
from werkzeug.utils import redirect
from ..extentions.database import mongo
from datetime import date, datetime
from bson.objectid import ObjectId
from operator import itemgetter

bolao = Blueprint('bolao',__name__)

# Rota / associada a função index
@bolao.route('/bolao')
def apostas():
    ano20_jogos = [u for u in mongo.db.jogos.find({'Ano': 20}).sort("Jogo",pymongo.ASCENDING)]
    resultados = []
    total=dict()
    allUsers = [u.get("name") for u in mongo.db.users.find()]
    if "username" in session:
        validUser = mongo.db.users.find_one({"username": session["username"]})
        apostador = validUser["name"]
        apostas = mongo.db.apostas20
        now = datetime.now()
        output = []
        userLogado=True
    else:
        userLogado=False
        
    for jogo in ano20_jogos:
        id_jogo = jogo["Jogo"]
        data_jogo = datetime.strptime(jogo["Data"],"%d/%m/%Y %H:%M")
        aposta = apostas.find_one({"Jogo": id_jogo})
        if data_jogo < now:
            #print(f'Jogo {id_jogo} passou')
            for user in allUsers:
                p1 = aposta.get(str(user + "_p1"))
                p2 = aposta.get(str(user + "_p2"))
                jogo[user]=[str(p1)+"x"+str(p2),p1,p2]
                if total.get(user):
                    total[user]+=p2
                else:
                    total[user]=p2
            resultados.append(jogo)
        elif userLogado:
            ap1 = apostador + "_p1"
            ap2 = apostador + "_p2"
            jogo["bet1"]=aposta.get(ap1)
            jogo["bet2"]=aposta.get(ap2)
            output.append(jogo)
    
    list_total=[]
    for u in allUsers:
        udict=dict()
        udict["nome"]=u
        udict["score"]=int(total[u])
        list_total.append(udict)
    print(list_total)
    #sorted_total = sorted(total.items(), key=itemgetter(1),reverse=True)

    return render_template("bolao.html",menu="Bolao",userlogado=userLogado,lista_jogos=output,resultados=resultados,total=list_total,users=allUsers)
    

@bolao.route('/editaposta',methods=["GET","POST"])
def edit_aposta():
    ANO=20
    edicao_ranking="19-3"
    if "username" in session:
        validUser = mongo.db.users.find_one({"username": session["username"]})
        apostador = validUser["name"]
        idjogo = int(request.values.get("idjogo"))
        aposta = mongo.db.apostas20.find_one_or_404({"Jogo": idjogo})
        ranking = mongo.db.ranking

        if request.method == "GET":
            a1 = aposta.get(str(apostador + "_p1"))
            a2 = aposta.get(str(apostador + "_p2"))
            if not a1:
                a1 = ""
            if not a2:
                a2 = ""
            jogo = mongo.db.jogos.find_one_or_404({"Ano": ANO,"Jogo": idjogo})
            r1 = ranking.find_one({"ed": edicao_ranking,"time": jogo['Time1']})
            r2 = ranking.find_one({"ed": edicao_ranking,"time": jogo['Time2']})
            return render_template('edit_aposta.html',menu='Bolao',jogo=jogo,a1=a1,a2=a2,idjogo=idjogo,r1=r1['pos'],r2=r2['pos'])
        else:
            p1 = request.values.get("p1")
            p2 = request.values.get("p2")
            if not p1.isdigit() or not p2.isdigit():
                flash("Placar deve ser um número!")
            else:
                mongo.db.apostas20.find_one_and_update(
                    {"Jogo": idjogo},
                    {'$set': {
                        str(apostador + "_p1"): int(p1),
                        str(apostador + "_p2"): int(p2)
                        }})
            flash("Placar adicionado com sucesso.")
            return redirect(url_for('bolao.apostas'))
    else:
        return redirect(url_for('usuario.login'))