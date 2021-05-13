from urllib.request import Request, urlopen
from bs4 import BeautifulSoup as soup
from PIL import Image, ImageTk
import json
import os
import photoshop.api as ps
from photoshop import Session
import requests
import pandas as pd


def saveConfig(path, dic):
    with open(path, "w+") as f:
        json.dump(dic, f)


def loadConfig(path):
    with open(path, "r") as f:
        return json.load(f)


def removeChars(string):
    copy = [char for char in string]
    i = 0
    for char in string:
        if not (
            (ord(char) >= 48 and ord(char) <= 57)
            or (ord(char) >= 65 and ord(char) <= 90)
            or (ord(char) >= 97 and ord(char) <= 122)
        ):
            copy = copy[:i] + copy[i + 1 :]
        else:
            i += 1
    out = ""
    for char in copy:
        out += char

    return out


def validatePlayers(players):
    players = [sorted(elem) for elem in players]
    for j in range(len(players) - 1):
        for i in range(len(players[j])):
            if players[j][i] != players[j + 1][i]:
                print("player names inconsistent")
                break

    return players[0]


def getMatchDictionary(match_id):
    req = Request(
        "https://api.opendota.com/api/matches/" + str(match_id),
        headers={"User-Agent": "Mozilla/5.0"},
    )
    page_html = urlopen(req).read()
    page_soup = soup(page_html, "html.parser")
    dic = json.loads(str(page_soup))
    players = getPlayerNames(dic)
    dic["players"] = [x for _, x in sorted(zip(players, dic["players"]))]

    return dic


def getPlayerNames(matchDictionary):
    return [
        removeChars(matchDictionary["players"][i]["name"])
        for i in range(len(matchDictionary["players"]))
    ]


def changeImage(doc, layer_name, image_path):
    doc.activeLayer = doc.ArtLayers[layer_name]
    with Session() as pss:
        replace_contents = pss.app.stringIDToTypeID("placedLayerReplaceContents")
        desc = pss.ActionDescriptor
        idnull = pss.app.charIDToTypeID("null")
        desc.putPath(idnull, image_path)
        pss.app.executeAction(replace_contents, desc)


def getPlayerInfo(matchDictionary, id):
    player = matchDictionary["players"][id]

    return {
        "nickname": removeChars(player["name"]),
        "heroId": player["hero_id"],
        "level": player["level"],
        "kills": player["kills"],
        "assists": player["assists"],
        "deaths": player["deaths"],
        "gpm": player["gold_per_min"],
        "xpm": player["xp_per_min"],
        "networth": player["net_worth"],
        "buildingDamage": player["tower_damage"],
        "heroDamage": player["hero_damage"],
        "heroHealing": player["hero_healing"],
        "item0": player["item_0"],
        "item1": player["item_1"],
        "item2": player["item_2"],
        "item3": player["item_3"],
        "item4": player["item_4"],
        "item5": player["item_5"],
        "purchase_time": player["purchase_time"],
    }


def getTeamLogos(matchDictionary):
    url_radiant = matchDictionary["radiant_team"]["logo_url"]
    url_dire = matchDictionary["dire_team"]["logo_url"]

    for i, elem in enumerate([url_radiant, url_dire]):
        if elem is None:
            img = Image.open("data/team_logos/empty_logo.png")
            img.save("data/team_logos/{}.png".format(i))
        else:
            response = requests.get(elem)
            file = open("data/team_logos/{}.png".format(i), "wb")
            file.write(response.content)
            file.close()

            desired_height = 180

            img = Image.open("data/team_logos/{}.png".format(i))
            img = img.resize(
                (int(desired_height / img.size[1] * img.size[0]), desired_height),
                Image.ANTIALIAS,
            )
            img.save("data/team_logos/{}.png".format(i))


def convertSecToMin(seconds):
    return "{:02d}".format(seconds // 60) + ":" + "{:02d}".format(seconds % 60)


def getItemTimings(player_dic):
    mapping = loadConfig("data/item_img/item_mapping.json")

    out = []
    for i in range(6):
        item_id = player_dic["item{}".format(i)]
        if item_id != 0:
            item_name = mapping[str(float(item_id))]
        if not item_name in ["aegis", "cheese", "refresher_shard"]:
            time = player_dic["purchase_time"][item_name]
        out.append((item_id, convertSecToMin(time)))

    
        

def createImages(match_dictionaries, games, players, player_names):
    if games == "All":
        dics_to_iterate_over = match_dictionaries
    else:
        dics_to_iterate_over = [match_dictionaries[int(games) - 1]]
    if players == 10:
        players_to_iterate_over = [i for i in range(10)]
    else:
        players_to_iterate_over = [int(players)]

    app = ps.Application()
    doc = app.open(os.getcwd() + "/player_performance_base.psd")

    elements = [
        "nickname",
        "level",
        "kills",
        "deaths",
        "assists",
        "gpm",
        "xpm",
        "buildingDamage",
        "heroDamage",
        "heroHealing",
        "networth",
    ]

    getTeamLogos(dics_to_iterate_over[0])
    changeImage(doc, "team_logo_radiant", os.getcwd() + "/data/team_logos/0.png")
    changeImage(doc, "team_logo_dire", os.getcwd() + "/data/team_logos/1.png")

    for i, game in enumerate(dics_to_iterate_over):
        doc.ArtLayers["matchID"].TextItem.contents = str(game["match_id"])
        for player in players_to_iterate_over:
            player_game_dic = getPlayerInfo(game, player)

            for elem in elements:
                doc.ArtLayers[elem].TextItem.contents = str(player_game_dic[elem])

            # change hero image
            changeImage(
                doc,
                "Hero",
                os.getcwd() + "/data/hero_img/{}.png".format(player_game_dic["heroId"]),
            )

            # # #change item images
            # for j in range(6):
            #     changeImage(
            #         doc,
            #         "item_{}".format(j + 1),
            #         os.getcwd()
            #         + "/data/item_img/{}.png".format(
            #             player_game_dic["item{}".format(j)]
            #         ),
            #     )

            getItemTimings(player_game_dic)

            doc.saveAs(
                os.getcwd()
                + "/results/game_"
                + str(i)
                + "_player_"
                + player_names[player]
                + ".png",
                ps.PNGSaveOptions(),
                True,
            )
