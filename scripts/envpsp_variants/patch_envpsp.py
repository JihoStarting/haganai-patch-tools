#!/usr/bin/env python3
"""Patch envpsp.dat (UI string table, UTF-16LE, u32 length prefix) ke bahasa Inggris.
Pakai: python3 patch_envpsp.py envpsp.dat envpsp_patched.dat
Hanya mengganti record yang teksnya PERSIS sama dengan kunci di TR, dalam rentang UI."""
import struct, sys

RANGE = (0x1E00, 0xAB00)   # area label UI (flowchart..controls). Cerita/BG/judul ending tidak disentuh.

TR = {
# --- menu pause (System)
'システム':'System','セーブ':'Save','ロード':'Load','クイックセーブ':'Quick Save',
'クイックロード':'Quick Load','終了':'Quit','フローチャート':'Flowchart',
'キーワードリスト':'Keyword List','操作説明':'Controls','オプション':'Options',
# --- tombol / umum
'決定':'Select','戻る':'Back','選択':'Select','項目左へ':'Prev Item','項目右へ':'Next Item',
'クイックセーブしました':'Quick saved.','設定を変更しました。':'Settings changed.',
'ボタンを押してください':'Press a button.',
# --- save/load
' ロック ':' Lock ','アンロック':'Unlock','並び替え':'Sort','表示切替':'Toggle View',
'ロックされています。\u3000セーブはできません。':'Locked. Cannot save.',
'セーブデータがありません':'No save data.',
# --- backlog
'バックログ':'Backlog','バックジャンプ':'Backjump','再生':'Play','停止':'Stop',
# --- flowchart
'通過回数':'Times Passed','シーンタイトル':'Scene Title','ルート名':'Route Name','説明':'Description',
'入手できるキーワード':'Obtainable Keywords','イベントCG':'Event CG','高速':'Fast','縮小':'Zoom Out','拡大':'Zoom In',
# --- extras / viewer / music
'アルバム':'Album','全画面':'Fullscreen','コメント':'Comment','スライドショー':'Slideshow','モーション':'Motion',
'ミュージック':'Music','作曲者コメント':"Composer's Comment",'リピートなし':'No Repeat','全曲リピート':'Repeat All',
'シャッフルなし':'No Shuffle','シャッフルあり':'Shuffle','ズームアウト':'Zoom Out','ズームイン':'Zoom In',
'全画面表示':'Fullscreen','等倍表示':'Actual Size','前ページ':'Prev Page','次ページ':'Next Page',
# --- options
'メッセージスピード':'Message Speed','おそい':'Slow','はやい':'Fast','メッセージ透過':'Message Opacity',
'薄':'Light','濃':'Dark','オートプレイウェイト':'Auto-Play Wait','メッセージスキップ':'Message Skip',
'すべて':'All','既読のみ':'Read Only','選択肢後のオートプレイ':'Auto-Play After Choices',
'継続する':'Continue','解除する':'Cancel','既読メッセージ表示':'Read Text Color','する':'On','しない':'Off',
'音量設定 BGM':'BGM Volume','音量設定 SE':'SE Volume','音量設定 ボイス':'Voice Volume',
'小':'Low','大':'High','BGM音量調整':'BGM Vol. (Voice)','ムービー音量':'Movie Volume',
'オートクイックセーブ':'Auto Quick Save','インストールデータ':'Install Data','使用する':'Use','使用しない':"Don't Use",
'バックライト':'Backlight','常に点灯':'Always On','本体設定に依存':'System Setting',
'高速スキップ':'Fast Skip','あるあるヒント':'Aruaru Hints','あるあるヒントスキップ':'Skip Aruaru Hints',
'システムボイス設定':'System Voice','設定する':'Set','ランダム':'Random',
'小鷹':'Kodaka','夜空':'Yozora','星奈':'Sena','理科':'Rika','幸村':'Yukimura','小鳩':'Kobato','マリア':'Maria','天馬':'Tenma','なし':'None',
# --- deskripsi options
'メッセージスピードを設定します':'Set the message speed.',
'メッセージウィンドウの透明率を設定します':'Set the message window opacity.',
'オートプレイ時のメッセージ終了後の待ち時間を設定します':'Set the wait time after a message ends in auto-play.',
'全てのメッセージをスキップします':'Skip all messages.',
'既読済みのメッセージのみスキップします':'Skip only messages already read.',
'選択肢の後もオートプレイを継続します':'Continue auto-play after choices.',
'選択肢の後はオートプレイを解除します':'Cancel auto-play after choices.',
'既読メッセージの色を変更します':'Change the color of read messages.',
'既読メッセージの色を変更しません':'Do not change the color of read messages.',
'BGMの音量を設定します':'Set the BGM volume.','SEの音量を設定します':'Set the SE volume.',
'ボイスの音量を設定します':'Set the voice volume.','ボイス再生中のBGM音量を設定します':'Set the BGM volume during voice playback.',
'ムービーの音量を設定します':'Set the movie volume.',
'クイックセーブを自動的に行います':'Quick save automatically.','クイックセーブを自動的に行いません':'Do not quick save automatically.',
'インストールデータを使用します':'Use install data.','インストールデータを使用しません':'Do not use install data.',
'バックライトを常に点灯させます':'Keep the backlight always on.','バックライトを本体設定に依存させます':'Follow the system backlight setting.',
'スキップ中にキャラを表示しません':'Hide characters while skipping.','スキップ中にキャラを表示します':'Show characters while skipping.',
'あるあるヒントを表示します':'Show Aruaru hints.','あるあるヒントを表示しません':'Do not show Aruaru hints.',
'あるあるシステムが使用できる箇所をスキップします':'Skip spots where the Aruaru system can be used.',
'あるあるシステムが使用できる箇所をスキップしません':'Do not skip spots where the Aruaru system can be used.',
'システムボイスの設定をします':'Configure the system voices.',
}

def ok(s):
    return len(s) > 0 and all((0x20 <= ord(c) < 0xD800) or c == '\n' for c in s)

def main(src, dst):
    d = open(src, 'rb').read()
    out = bytearray(); last = 0; o = RANGE[0]; n = 0; miss = {}
    while o < min(RANGE[1], len(d) - 4):
        l = struct.unpack_from('<I', d, o)[0]
        if 0 < l < 200 and o + 4 + l * 2 <= len(d):
            s = d[o+4:o+4+l*2].decode('utf-16le', 'replace')
            if ok(s):
                if s in TR:
                    out += d[last:o]
                    e = TR[s]
                    out += struct.pack('<I', len(e)) + e.encode('utf-16le')
                    last = o + 4 + l * 2; n += 1
                elif any(0x3040 <= ord(c) <= 0x9FFF for c in s):
                    miss[s] = miss.get(s, 0) + 1
                o += 4 + l * 2; continue
        o += 1
    out += d[last:]
    open(dst, 'wb').write(out)
    print(f'{n} string diganti. ukuran {len(d)} -> {len(out)}')
    print(f'{len(miss)} string Jepang unik dibiarkan (cerita/BG/judul/pesan installer dll).')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
