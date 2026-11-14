#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_envpsp.py (GABUNGAN) - ganti string Jepang di envpsp.dat dengan Inggris.

Menggantikan 3 skrip lama (cukup simpan file ini saja):
  [UI]     label menu/opsi/flowchart/musik dst. -> HANYA dalam rentang RANGE
           (dari "patch_envpsp lama"; rentang dibatasi supaya cerita/BG/judul ending tidak tersentuh)
  [DIALOG] kotak konfirmasi/simpan/muat dst.    -> seluruh file, hanya record UTUH yang cocok persis
           (dari "patch_envpsp" baru)

Format string di envpsp.dat: u32 jumlah_karakter + UTF-16LE (dibaca berurutan oleh loader).
Penanda khusus di teks dialog: '_' (ASCII) = pindah baris, '\uFF3F' = pemisah pilihan.

Urutan kerja (penting): [UI] dulu (memakai offset file asli), baru [DIALOG].
Selalu mulai dari envpsp.dat ASLI (45.711 byte). Berkas asli tidak diubah.

Pakai (dari folder scripts tools):
  python patch_envpsp.py envpsp.dat --check
  python patch_envpsp.py envpsp.dat envpsp_en.dat
  python patch_envpsp.py envpsp.dat envpsp_en.dat --miss sisa_jepang.txt
--miss menulis daftar string Jepang di rentang UI yang MASIH belum diterjemahkan (offset + jumlah).

Kelompok tambahan (GROUPS, belum dites di game): extras, endings, bg, bgm, install, savemsg,
comments, endtitles (aktif) dan title (MATI, hanya bila diminta).
  --skip bg,bgm        matikan kelompok tertentu (bila layout di layar rusak)
  --with title         hidupkan kelompok yang default-nya mati
"""
import argparse
import struct
import sys

RANGE = (0x1E00, 0xAB00)   # area label UI (flowchart..controls). Cerita/BG/judul ending tidak disentuh.

# ---------------------------------------------------------------- [UI] label, hanya dalam RANGE
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


# ---------------------------------------------------------------- [UI-2] tambahan per kelompok (dari sisa_jepang.txt)
GROUPS = {
    # daftar Extras: "<karakter> Extra"
    'extras': {
        '夜空おまけ': 'Yozora Extra',  # 0x25c6
        '理科おまけ': 'Rika Extra',  # 0x25fc
        '星奈おまけ': 'Sena Extra',  # 0x2632
        '幸村おまけ': 'Yukimura Extra',  # 0x2668
        '小鳩おまけ': 'Kobato Extra',  # 0x269e
        'マリアおまけ': 'Maria Extra',  # 0x26d4
    },
    # daftar Opening/Ending (movie/replay)
    'endings': {
        'オープニング': 'Opening',  # 0x2810
        'ノーマルエンディング': 'Normal Ending',  # 0x2840
        '夜空エンディング': 'Yozora Ending',  # 0x2878
        '星奈エンディング': 'Sena Ending',  # 0x28ac
        '幸村エンディング': 'Yukimura Ending',  # 0x28e0
        '理科エンディング': 'Rika Ending',  # 0x2914
        '小鳩エンディング': 'Kobato Ending',  # 0x2948
        'マリアエンディング': 'Maria Ending',  # 0x297c
    },
    # nama latar (album/BG viewer)
    'bg': {
        '空': 'Sky',  # 0x39a2
        'ビーチ': 'Beach',  # 0x3a04
        '海': 'Sea',  # 0x3ab8
        'テラス': 'Terrace',  # 0x3aec
        '森': 'Forest',  # 0x3c18
        '川': 'River',  # 0x3c4c
        '別荘外観': 'Villa Exterior',  # 0x3cb4
        'リビング': 'Living Room',  # 0x3db2
        'ダイニング': 'Dining Room',  # 0x3e2a
        '別荘客室': 'Villa Guest Room',  # 0x3eca
        '別荘納屋': 'Villa Barn',  # 0x3f24
        '別荘廊下': 'Villa Hallway',  # 0x3f42
        '礼拝堂': 'Chapel',  # 0x406a
        '礼拝堂外観': 'Chapel Exterior',  # 0x40c0
        '会議室': 'Meeting Room',  # 0x4146
        '柏崎家応接間': 'Kashiwazaki Parlor',  # 0x4162
        '柏崎家廊下': 'Kashiwazaki Hallway',  # 0x4184
        '柏崎家ダイニング': 'Kashiwazaki Dining',  # 0x41a4
        '星奈の部屋': "Sena's Room",  # 0x41ca
        '羽瀬川家外観': 'Hasegawa Exterior',  # 0x41ea
        '羽瀬川リビング': 'Hasegawa Living',  # 0x4272
        '羽瀬川ダイニング': 'Hasegawa Dining',  # 0x434a
        '小鷹の部屋': "Kodaka's Room",  # 0x43e2
        '小鳩の部屋前': "Kobato's Doorway",  # 0x4482
        '小鳩の部屋': "Kobato's Room",  # 0x44e8
        '風呂場': 'Bathroom',  # 0x4548
        '街中': 'Downtown',  # 0x4580
        '公園': 'Park',  # 0x45ce
        '伊勢神宮': 'Ise Shrine',  # 0x46b6
        'おかげ横丁': 'Okage Yokocho',  # 0x46f2
        '部室前': 'Club Room Front',  # 0x4714
    },
    # judul BGM (pemutar Music) - tebakan dari konteks
    'bgm': {
        '残念に登場': 'Disappointing Debut',  # 0x474e
        'なんか違うような……': "Something's Off...",  # 0x4772
        '嫌な予感': 'A Bad Feeling',  # 0x478a
        '決意': 'Resolve',  # 0x4796
        '隣人部の活動を始める': 'Club Activities Begin',  # 0x479e
        '大切なともだち': 'Precious Friend',  # 0x47cc
        'ひとり優雅に': 'Elegantly Alone',  # 0x47de
        '理解されない天才少女': 'Misunderstood Genius',  # 0x47ee
        'ずっと、そばに': 'Always By Your Side',  # 0x4806
        'ちいさな天使': 'Little Angel',  # 0x4818
        'わんぱくシスター': 'Mischievous Sister',  # 0x4828
        'ゆるやかな昼': 'Leisurely Afternoon',  # 0x483c
        '穏やかなじかん': 'Peaceful Time',  # 0x484c
        '気付いた想い': 'Feelings Realized',  # 0x485e
        '僕のものがたり': 'My Story',  # 0x486e
        'わかってたさ………': 'I Knew It...',  # 0x4880
        'スペシャルミッション': 'Special Mission',  # 0x4896
        'ヒトノココロ': 'The Human Heart',  # 0x48ae
        'おくりもの': 'A Gift',  # 0x48be
    },
    # judul savedata/instalasi PSP (muncul di XMB) - DEFAULT MATI
    'title': {
        '僕は友達が少ない\u3000ぽーたぶる': 'Boku wa Tomodachi ga Sukunai Portable',  # 0x5f84
        '僕は友達が少ない\u3000ぽーたぶるの\nインストールデータです。': 'Install data for_Boku wa Tomodachi ga Sukunai Portable.',  # 0x5fba
    },
    # dialog dan menu Install
    'install': {
        'インストールデータの使用がONになっているため_インストールを行うことはできません。_インストールデータの使用をOFFにしてください。': "Cannot install while_'Use Install Data' is ON._Please set it to OFF.",  # 0x6020
        '上書き準備中です。_記録メディアを絶対に抜かないでください。': 'Preparing to overwrite._Never remove the Memory Stick.',  # 0x6352
        '記録メディアをチェック中です。': 'Checking the Memory Stick.',  # 0x6392
        '記録メディアの総容量は_インストールデータ量を下回っています。_処理を中断します。': 'The total capacity is less than_the size of the install data._Aborting.',  # 0x63b4
        'B 以上の空き容量を確保するために_既存のセーブデータを削除してください。': 'B or more free space needed._Delete save data to make room.',  # 0x643c
        '記録メディアが入っていません。_処理を中断します。': 'No Memory Stick inserted._Aborting.',  # 0x648a
        'キャンセルしました。': 'Cancelled.',  # 0x6674
        'インストール情報を保存しています。_記録メディアを絶対に抜かないでください。': 'Saving install information._Never remove the Memory Stick.',  # 0x668c
        'インストールが完了しました。_インストールデータの使用をONに変更しました。': 'Installation complete._Use Install Data is now ON.',  # 0x66dc
        '記録メディア読み込みに切り替え中です。_記録メディアを抜かないでください。': 'Switching to Memory Stick loading._Do not remove the Memory Stick.',  # 0x672c
        'UMD®読み込みに切り替え中です。': 'Switching to UMD® loading.',  # 0x677a
        '切り替えが完了しました。': 'Switch complete.',  # 0x67a0
        '正常なインストールデータが存在しません。_インストールデータをセーブし直してください。_インストールデータがロードできなかったため_UMD®読み込みに切り替えます。': 'No valid install data exists._Please save the install data again._Install data could not be loaded,_so switching to UMD® loading.',  # 0x67bc
        'インストール': 'Install',  # 0x6864
        'インストールを行う': 'Install Now',  # 0x688c
        'インストールデータの使用': 'Use Install Data',  # 0x68a2
        'インストール中です': 'Installing...',  # 0x6950
        '記録メディアを抜かないでください。': 'Do not remove the Memory Stick.',  # 0x6966
        '中断': 'Abort',  # 0x6b36
    },
    # pesan pembuatan/penghapusan/pemuatan savedata
    'savemsg': {
        '記録メディアが入っていません。_セーブデータを作成するには_': 'No Memory Stick inserted._To create save data,_',  # 0x6be8
        '記録メディア内に_セーブデータが見当たりません。_セーブデータを作成するには_': 'No save data found on the_Memory Stick._To create save data,_',  # 0x6d16
        'KB 以上の空き容量を確保するために_既存のセーブデータを削除してください。': 'KB or more free space needed._Delete save data to make room.',  # 0x6e70
        'セーブデータを作成しました。': 'Save data created.',  # 0x6f14
        '処理に失敗しました。_セーブデータが破損しているため削除します。': 'Operation failed._The save data is corrupted_and will be deleted.',  # 0x6f34
        'セーブデータを削除中': 'Deleting save data...',  # 0x6f78
        'セーブデータを削除しました。': 'Save data deleted.',  # 0x6f90
        '読み込みが完了しました。': 'Load complete.',  # 0x6ffa
        '記録メディアが入っていません。': 'No Memory Stick inserted.',  # 0x717e
        '起動中のシステムデータが見つからないため_読み込みを行うことができません。': 'No active system data found._Cannot load.',  # 0x722c
        '記録メディア内に_セーブデータが見当たりません。': 'No save data found_on the Memory Stick.',  # 0x7308
    },
    # komentar komposer (Music)
    'comments': {
        'ちょっと右側のシンセがざわつき始めました・・・': 'The right-side synth gets a bit restless...',  # 0x8fb8
        '一転、リズムが落ち着いて女性コーラスが入ってきます。': 'The rhythm settles down as a female chorus joins in.',  # 0x903c
    },
    # judul ending - tebakan dari konteks
    'endtitles': {
        '本物の妹は真似できない': "Real Sisters Can't Be Faked",  # 0xa452
        '自分探し――失われた友を求めて': 'Finding Myself, Lost Friends',  # 0xa48e
        'ハッピー・インターバル': 'Happy Interval',  # 0xa4d2
        'もう一度、初めから': 'Back to the Beginning',  # 0xa50e
        'お姫さまの事後': 'Princess Aftermath',  # 0xa546
        'ほんのりグッドエンド': 'Faintly Good End',  # 0xa57a
        '夜空×星奈': 'Yozora x Sena',  # 0xa5b4
        'しゅどうへようこそ': 'Welcome to Shudou',  # 0xa5e4
        'それでもわたくしは――': 'Even So, I--',  # 0xa61c
        'あしたもきっと――': 'Surely, Tomorrow--',  # 0xa658
        '俗世に還れば': 'Back to Reality',  # 0xa690
        'マリアの涙': "Maria's Tears",  # 0xa706
    },
}
DEFAULT_OFF = {'title'}   # hanya dipakai bila diminta: --with title

# ---------------------------------------------------------------- [DIALOG] seluruh file
TABLE = [
    ("タイトルに戻ります。_よろしいですか？", "Return to the title screen._Are you sure?"),
    ("シーン再生に戻ります。_よろしいですか？", "Return to Scene Replay._Are you sure?"),
    ("おまけシナリオに戻ります。_よろしいですか？", "Return to Extra Scenarios._Are you sure?"),
    ("システムデータを保存しますがよろしいですか？", "Save system data. Is this OK?"),
    ("システムデータを保存しました。", "System data saved."),
    ("データを保存しますがよろしいですか？", "Save data. Is this OK?"),
    ("データを上書きしますがよろしいですか？", "Overwrite data. Is this OK?"),
    ("データを保存しました。", "Data saved."),
    ("ロードを行いますがよろしいですか？", "Load data. Is this OK?"),
    ("クイックロードを行いますがよろしいですか？＿※これ以降に保存したクイックセーブは_全て削除されます。",
     "Quick Load. Is this OK?＿*All Quick Saves made after this_point will be deleted."),
    ("セーブしますか？", "Save?"),
    ("ロードしますか？", "Load?"),
    ("設定を初期化しますが_よろしいですか？", "Reset settings to default._Are you sure?"),
    ("変更した設定が保存されませんが_よろしいですか？", "Changes will not be saved._Are you sure?"),
    ("変更を保存しますか？", "Save changes?"),
    ("バックジャンプしますか？", "Backjump?"),
    ("セーブしました。", "Saved."),
    ("はい＿いいえ", "Yes＿No"),
    ("はい＿いいえ＿戻る", "Yes＿No＿Back"),
    ("はい＿いいえ＿キャンセル", "Yes＿No＿Cancel"),
    ("戻る", "Back"),
]


def ok(s):
    return len(s) > 0 and all((0x20 <= ord(c) < 0xD800) or c == '\n' for c in s)


def enc(s):
    return struct.pack("<I", len(s)) + s.encode("utf-16-le")


def pass_ui(d, tr):
    """Sama persis dengan skrip lama: baca berurutan di dalam RANGE, ganti record yang cocok persis."""
    out = bytearray()
    last = 0
    o = RANGE[0]
    n = 0
    miss = {}
    used = {}
    while o < min(RANGE[1], len(d) - 4):
        l = struct.unpack_from('<I', d, o)[0]
        if 0 < l < 200 and o + 4 + l * 2 <= len(d):
            s = d[o + 4:o + 4 + l * 2].decode('utf-16le', 'replace')
            if ok(s):
                if s in tr:
                    out += d[last:o]
                    out += enc(tr[s])
                    last = o + 4 + l * 2
                    n += 1
                    used[s] = used.get(s, 0) + 1
                elif any(0x3040 <= ord(c) <= 0x9FFF for c in s):
                    m = miss.setdefault(s, [0, o])
                    m[0] += 1
                o += 4 + l * 2
                continue
        o += 1
    out += d[last:]
    return bytes(out), n, miss, used


def read_str(d, p):
    if p + 4 > len(d):
        return None
    n = struct.unpack_from("<I", d, p)[0]
    if not (1 <= n <= 400) or p + 4 + 2 * n > len(d):
        return None
    try:
        return n, d[p + 4:p + 4 + 2 * n].decode("utf-16-le")
    except UnicodeDecodeError:
        return None


def pass_dialog(d):
    """Sama persis dengan skrip baru: cek tiap posisi, ganti hanya record utuh yang cocok."""
    out = bytearray()
    pos = 0
    stats = {}
    jp2en = dict(TABLE)
    en_set = set(jp2en.values())
    while pos < len(d):
        r = read_str(d, pos)
        if r and r[1] in jp2en:
            n, s = r
            stats.setdefault(s, [0, 0])[0] += 1
            out += enc(jp2en[s])
            pos += 4 + 2 * n
        elif r and r[1] in en_set:
            stats.setdefault(r[1], [0, 0])[1] += 1
            out.append(d[pos])
            pos += 1
        else:
            out.append(d[pos])
            pos += 1
    return bytes(out), stats


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Patch envpsp.dat (UI + dialog) ke Inggris")
    ap.add_argument("src")
    ap.add_argument("dst", nargs="?")
    ap.add_argument("--check", action="store_true", help="hanya hitung, tidak menulis file")
    ap.add_argument("--miss", help="tulis daftar string Jepang UI yang belum diterjemahkan ke file ini")
    ap.add_argument("--skip", default="", help="kelompok yang dimatikan, pisah koma (mis. bg,bgm)")
    ap.add_argument("--with", dest="with_", default="", help="kelompok default-mati yang dihidupkan (mis. title)")
    a = ap.parse_args()
    if a.dst == "--check":          # kompatibel dengan cara pakai lama: patch_envpsp.py envpsp.dat --check
        a.check, a.dst = True, None
    if not a.check and not a.dst:
        ap.error("butuh nama file keluaran, atau pakai --check")
    if a.dst and a.dst == a.src:
        ap.error("file keluaran tidak boleh sama dengan file asli")
    skip = {x.strip() for x in a.skip.split(",") if x.strip()}
    with_ = {x.strip() for x in a.with_.split(",") if x.strip()}
    unknown = (skip | with_) - set(GROUPS)
    if unknown:
        ap.error("kelompok tidak dikenal: %s (ada: %s)" % (",".join(sorted(unknown)), ",".join(GROUPS)))

    tr = dict(TR)
    active, key2group = [], {}
    for name, table in GROUPS.items():
        on = (name not in DEFAULT_OFF or name in with_) and name not in skip
        if on:
            active.append(name)
            for k, v in table.items():
                if k in tr:
                    raise SystemExit("Kunci ganda di GROUPS dan TR: %r" % k)
                tr[k] = v
                key2group[k] = name

    d = open(a.src, "rb").read()
    d1, n_ui, miss, used = pass_ui(d, tr)
    d2, stats = pass_dialog(d1)
    jp_total = sum(v[0] for v in stats.values())
    en_total = sum(v[1] for v in stats.values())

    print("[UI]     %d string diganti (rentang 0x%X-0x%X). Ukuran %d -> %d" % (n_ui, RANGE[0], RANGE[1], len(d), len(d1)))
    per = {}
    for k, c in used.items():
        if k in key2group:
            per[key2group[k]] = per.get(key2group[k], 0) + c
    print("         kelompok tambahan aktif: %s" % (", ".join("%s=%d" % (g, per.get(g, 0)) for g in active) or "(tidak ada)"))
    off = [g for g in GROUPS if g not in active]
    if off:
        print("         kelompok mati: %s" % ", ".join(off))
    print("         %d string Jepang unik di rentang itu masih dibiarkan (cerita/BG/judul/dll)." % len(miss))
    print("[DIALOG] ditemukan JEPANG: %d   sudah INGGRIS: %d. Ukuran %d -> %d" % (jp_total, en_total, len(d1), len(d2)))
    for jp, (x, y) in stats.items():
        if x:
            print("           x%d  %s" % (x, jp[:40]))
    if a.miss:
        with open(a.miss, "w", encoding="utf-8") as f:
            for s, (cnt, off_) in sorted(miss.items(), key=lambda kv: kv[1][1]):
                f.write("0x%06x\tx%d\t%s\n" % (off_, cnt, s))
        print("Daftar sisa Jepang ditulis ke %s" % a.miss)
    if a.check:
        print("Mode --check: tidak ada file ditulis.")
        return
    open(a.dst, "wb").write(d2)
    print("Ditulis %s  %d -> %d byte" % (a.dst, len(d), len(d2)))


if __name__ == "__main__":
    main()
