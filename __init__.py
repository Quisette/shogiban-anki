# -*- mode: Python ; coding: utf-8 -*-
#
# Copyright © 2022 Quisette C.
# Copyright © 2018 tokoharu
# The style is from the AnkiDroid code and tokoharu's repository https://github.com/tokoharu/shogi_addon_for_Anki, presumably
# Copyright (c) 2012 Kostas Spyropoulos <inigo.aldana@gmail.com>
#
# License: GNU AGPL, version 3 or later;
# http://www.gnu.org/copyleft/agpl.html

"""
Add-on for Anki 2.1 to show a shogi board.
"""
import re
import sys
from collections import namedtuple

from anki import hooks
from anki.cards import Card
from aqt.utils import showInfo

BOARD_SIZE = 150
__version__ = '1.0.1-alpha'

FenData = namedtuple(
    'FenData',
    ['placement', 'active', 'mochi', 'count'])

piece = dict(zip("kgsnlbrp", u"玉金銀桂香角飛歩"))
promote = dict(zip(u"銀桂香角飛歩", u"全圭杏馬龍と"))
"""
promote = dict([(u"銀", u"成銀"), (u"桂", u"成桂"), (u"香", u"成香"),\
                (u"角", u"馬"), (u"飛", u"龍"), (u"歩", u"と")] )
"""

fen_template = u"""

<figure class="shogi_diagram">
<table class="shogi_mochi_gote">{gotemochi}</table>
<table class="shogi_board">{rows}</table>
<table class="shogi_mochi_sente">{sentemochi}</table>
<figcaption>

<span class="fen_extra count">{count}手目、{act}</span>
<!-- <span class="fen_extra active"></span>-->
<br/>
<span class="fen_extra comment"> {other}</span>
</figcaption>
</figure>
"""



def counted_spaces(match):
    u"""Replace numbers with spaces"""
    return ' ' * int(match.group(0))


def get_mochi(origin):
    sente_res = list()
    gote_res = list()
    if origin == "-":
        return sente_res, gote_res
    tmp = ""
    for c in origin:
        if c.isdigit():
            tmp += c
        else:
            if tmp == "":
                tmp = "1"
            tmp = tuple([c.lower(), int(tmp)])
            if c.islower():
                gote_res.append(tmp)
            else:
                sente_res.append(tmp)
            tmp = ""
    return sente_res, gote_res


def format_mochi(p, val):
    return u"<tr><td>" + p + u"<span class=\"num\">" + str(val) + u"</span>" + u"</td></tr>"


def insert_table(fen_match):
    u"""
    Replace well formed FEN data with a shogi board diagram.

    This is the worker function that replaces the actual data.
    """
    revflag = [False] * 200
    promoteflag = [False] * 200
    itr = 0
    fen_str = fen_match.group(1)
    spacesplit = fen_str.split(" ")
    for c in fen_str:
        if c.isdigit():
            itr += int(c)
            continue
        if c.islower():
            revflag[itr] = True
        if c == "+":
            promoteflag[itr] = True
            continue
        if c == "/":
            continue
        itr += 1

    fen_text = u''

    for c in fen_str:
        if c.isalpha():
            c = c.lower()
            try:
                fen_text += piece[c]
            except KeyError:
                fen_text += c
        else:
            fen_text += c
    try:
        fen = FenData(*(fen_text.split()))
    except TypeError:
        return fen_match.group(0)
    rows = fen.placement.split('/')
    active = u'.'
    if fen.active == "b":
        active = u"先手番です"
    else:
        active = u"後手番です"
    trows = []
    itr = 0
    for r in rows:
        assert(itr % 9 == 0)
        r = re.sub('[1-9][0-9]?', counted_spaces, r)
        tr = u'<tr>'
        remain = ""
        for p in r:
            if p == "+":
                remain = "+"
                continue
            if remain == "+":
                p = promote[p]
            remain = ""

            head = u'<td class=\"def\"'
            if len(p) == 2:
                head += u" class=\"press\" "
            head += u">"
            p = head + u"{0}</td>".format(p)
            if promoteflag[itr] is True:
                p = p.replace(u"def", u"def promote")
            if revflag[itr] is True:
                p = p.replace(u"def", u"rev")
            tr += p
            itr += 1
            
        trows.append(tr + u'</tr>\n')

    sente_mochi, gote_mochi = get_mochi(spacesplit[2])
    sente_str = ""
    gote_str = ""

    for p, val in gote_mochi:
        gote_str += format_mochi(piece[p], val)
    for p, val in sente_mochi:
        sente_str += format_mochi(piece[p], val)

    return fen_template.format(
        gotemochi=gote_str, sentemochi=sente_str,
        rows=''.join(trows), act=active, count=fen.count, other="")


def kanji_num(c):
    patterns = dict(zip(u"一二三四五六七八九十", range(1, 11)))
    try:
        return patterns[c]
    except:
        return 0


def insert_kif_table(txt):
    origin = txt.group(1)
    line_re = re.compile(r"<div>[^<]*</div>")
    stripdiv_re = re.compile(r"<div>(.*)</div>")
    origin = "<div>" + origin + "</div>"
    if origin.count("div") < origin.count("br"):
        line_re = re.compile(r"<br>[^<]*")
        stripdiv_re = re.compile(r"<br>(.*)")

    line_data = line_re.findall(origin)
    boardflag = 0
    boardstr = []
    sente_str = ""
    gote_str = ""

    revBoard = False
    for line in line_data:
        if line.find(u"手数＝") >= 0 and line.find(u"▲") >= 0:
            revBoard = True

    def get_mochi_kif(line):
        line += "end"
        ret = ""
        posa = line.find(u"：")
        posb = line.find(u"end")
        mochi_data = line[(posa+1):(posb)].split(u"　")
        for pdata in mochi_data:
            if len(pdata) == 0:
                continue
            val = 0
            for c in pdata:
                val += kanji_num(c)
            if val == 0:
                val = 1
            ret += format_mochi(pdata[0], val)
        return ret
    for line in line_data:
        try:
            line = stripdiv_re.match(line).group(1)
        except:
            continue
        if line.find(u"後手の持駒") >= 0:
            if line.find(u"なし") >= 0:
                continue
            gote_str += get_mochi_kif(line)

        if line.find(u"先手の持駒") >= 0:
            if line.find(u"なし") >= 0:
                continue
            sente_str += get_mochi_kif(line)

        if line.find(u"+-----") >= 0:
            boardflag += 1
            continue
        if boardflag == 1:
            line_str = ""
            inner = 0
            revflag = False
            for c in line:
                if c == "|":
                    inner += 1
                    continue
                if inner != 1:
                    continue
                if c == "v":
                    revflag = True
                elif not c == u" ":
                    if c == u"・":
                        c = " "
                    tmp = u"<td class=\"def\">" + c + u"</td>"
                    if revflag + revBoard == 1:
                        tmp = tmp.replace(u"def", u"rev")
                    revflag = False
                    line_str += tmp
            if revBoard is True:
                tmp_re = re.compile(r"<td[^<]*</td>")
                tmp = tmp_re.findall(line_str)
                tmp = tmp[::-1]
                line_str = "".join(tmp)
            boardstr.append("<tr>" + line_str + "</tr>")

    comment = ""
    if revBoard is True:
        comment += u"(先後反転)"
        sente_str, gote_str = gote_str, sente_str
        boardstr = boardstr[::-1]

    rows = ''.join(boardstr)

    return fen_template.format(
        gotemochi=gote_str, sentemochi=sente_str,
        rows=rows, act="", count="", other=comment)


def show_error_message(output):
    comment = "<h2>Error occured when rendering (shogiban-anki by Quisette).</h2>"
    comment += "<pre>Please submit your error message to the github page to get more information.</pre>"

    message1 = comment

    comment += "<pre>message : </pre>"
    comment += output.question_text.replace("<", "_").replace(">", "_")
    comment += output.answer_text.replace("<", "_").replace(">", "_")

    sys.stderr.write(comment)
    showInfo(message1)


def make_kif_table(output, context):
    kif_re = re.compile(r"\[kif\](.+?)\[/kif\]", re.DOTALL | re.IGNORECASE)
    try:
        output.question_text = kif_re.sub(
            insert_kif_table, output.question_text)
        output.answer_text = kif_re.sub(insert_kif_table, output.answer_text)
    except:
        show_error_message(output)


def make_fen_table(output, context):
    fen_re = re.compile(r"\[sfen\](.+?)\[/sfen\]", re.DOTALL | re.IGNORECASE)
    try:
        output.question_text = fen_re.sub(insert_table, output.question_text)
        output.answer_text = fen_re.sub(insert_table, output.answer_text)
    except:
        show_error_message(output)

hooks.card_did_render.append(make_fen_table)
hooks.card_did_render.append(make_kif_table)
