#!/bin/bash

edit_changelog() {
    echo "Editando changelog"
    LASTHEAD=$(grep HEAD CHANGELOG.md)
    LASTV=$(echo $LASTHEAD | grep -Po "compare/\K(v[0-9]\.[0-9]*\.[0-9]*)")

    sed -i "s/$LASTV\.\./v$VERSAO\.\./" CHANGELOG.md
    sed -i "/^\[unreleased/a [${VERSAO/v/}]: https://github.com/leafarlins/gokopa/compare/$LASTV..$VERSAO/" CHANGELOG.md
    sed -i "/^## \[unreleased/a ## \[$VERSAO\] - $HOJE" CHANGELOG.md
    #sed -n '/## \[unreleased/,/^## /p' CHANGELOG.md | sed '/^## \[/d' > /tmp/tagnotes

    sed -i "s/Gokopa do Mundo v.*/Gokopa do Mundo v$VERSAO/" app/templates/sobre.html
}

commit_tag() {
    echo "Commitando alteracoes"
    git add CHANGELOG.md
    git add app/templates/sobre.html
    git commit -m "release v$VERSAO"
    git tag v$VERSAO
    git push --tags origin master
    #git push origin master

}

docker_build() {
    echo "Construindo container"
    docker build -t leafarlins/gokopa:v$VERSAO .
    docker build -t leafarlins/gokopa:latest .
    docker push leafarlins/gokopa:v$VERSAO
    docker push leafarlins/gokopa:latest
}

VERSAO=$1
REBUILD="$2"
HOJE=$(date "+%Y-%m-%d")
[ $REBUILD == "rebuild" ] && apenas_build=true || apenas_build=""

echo "Construindo versao $VERSAO"

[ $apenas_build ] || edit_changelog
[ $apenas_build ] || commit_tag
docker_build