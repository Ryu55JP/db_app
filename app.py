#!/application/app.py
"""
データベースを使った Web アプリケーションのサンプル.

細田 真道
"""

import sqlite3
from typing import Final, Optional, Union
import unicodedata

from flask import Flask, g, redirect, render_template, request, url_for
from werkzeug import Response

# データベースのファイル名
DATABASE: Final[str] = 'discography.db'

# Flask クラスのインスタンス
app = Flask(__name__)

# 処理結果コードとメッセージ
RESULT_MESSAGES: Final[dict[str, str]] = {
    'include-invalid-charactor':
    '指定された情報には使えない文字があります - ',
    'series-number-has-invalid-charactor':
    '指定された情報には使えない文字があります - '
    'シリーズ通し番号は数字のみで指定してください',
    'id-has-invalid-charactor':
    '指定された情報には使えない文字があります - '
    'IDは数字のみで指定してください',
    'id-already-exists':
    '指定されたIDのデータは既に存在します - '
    '存在しないIDを指定してください',
    'id-does-not-exist':
    '指定された社員番号は存在しません',
    'id-is-manager':
    '指定された社員番号の社員には部下がいます - '
    '部下に登録された上司を変更してから削除してください',
    'manager-id-has-invalid-charactor':
    '指定された上司の社員番号には使えない文字があります - '
    '数字のみで指定してください',
    'manager-id-does-not-exist':
    '指定された上司の社員番号が存在しません - '
    '既に存在する社員番号か追加する社員の社員番号と同じものを指定してください',
    'salary-has-invalid-charactor':
    '指定された給与には使えない文字があります - '
    '数字のみで指定してください',
    'birth-year-has-invalid-charactor':
    '指定された生年には使えない文字があります - '
    '数字のみで指定してください',
    'start-year-has-invalid-charactor':
    '指定された入社年には使えない文字があります - '
    '数字のみで指定してください',
    'include-control-charactor':
    '制御文字は指定しないでください',
    'database-error':
    'データベースエラー',
    'cd-added':
    'CDを追加しました',
    'song-added':
    '楽曲を追加しました',
    'deleted':
    '削除しました',
    'updated':
    '更新しました'
}


def get_db() -> sqlite3.Connection:
    """
    データベース接続を得る.

    リクエスト処理中にデータベース接続が必要になったら呼ぶ関数。

    Flask の g にデータベース接続が保存されていたらその接続を返す。
    そうでなければデータベース接続して g に保存しつつ接続を返す。
    その際に、カラム名でフィールドにアクセスできるように設定変更する。

    https://flask.palletsprojects.com/en/3.0.x/patterns/sqlite3/
    のサンプルにある関数を流用し設定変更を追加。

    Returns:
      sqlite3.connect: データベース接続
    """
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.execute('PRAGMA foreign_keys = ON')  # 外部キー制約を有効化
        db.row_factory = sqlite3.Row  # カラム名でアクセスできるよう設定変更
    return db


@app.teardown_appcontext
def close_connection(exception: Optional[BaseException]) -> None:
    """
    データベース接続を閉じる.

    リクエスト処理の終了時に Flask が自動的に呼ぶ関数。

    Flask の g にデータベース接続が保存されていたら閉じる。

    https://flask.palletsprojects.com/en/3.0.x/patterns/sqlite3/
    のサンプルにある関数をそのまま流用。

    Args:
      exception (Optional[BaseException]): 未処理の例外
    """
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def has_control_character(s: str) -> bool:
    """
    文字列に制御文字が含まれているか否か判定する.

    Args:
      s (str): 判定対象文字列
    Returns:
      bool: 含まれていれば True 含まれていなければ False
    """
    return any(map(lambda c: unicodedata.category(c) == 'Cc', s))

# TOPページ
@app.route('/')
def index() -> str:
    """
    入口のページ.

    `http://localhost:5000/` へのリクエストがあった時に Flask が呼ぶ関数。

    テンプレート index.html
    （本アプリケーションの説明や他ページへのリンクがある）
    をレンダリングして返す。

    Returns:
      str: ページのコンテンツ
    """
    # テンプレートへ何も渡さずにレンダリングしたものを返す
    return render_template('index.html')

# CD関連ページ
@app.route('/cds')
def cds() -> str:
    """
    CD 一覧のページ（全件）.

    `http://localhost:5000/cds` への GET メソッドによる
    リクエストがあった時に Flask が呼ぶ関数。

    データベース接続を得て、SELECT 文で全 CD 一覧を取得し、
    テンプレート cds.html へ一覧を渡して埋め込んでレンダリングして返す。

    Returns:
      str: ページのコンテンツ
    """
    # データベース接続してカーソルを得る
    cur = get_db().cursor()

    # cds テーブルの全行から CD の情報を取り出した一覧を取得
    cds = cur.execute('SELECT * FROM cds').fetchall()

    # 一覧をテンプレートへ渡してレンダリングしたものを返す
    return render_template('cds.html', cds=cds)

@app.route('/cds', methods=['POST'])
def cds_filtered() -> str:
    """
    CD 一覧のページ（絞り込み）.

    `http://localhost:5000/cds` への POST メソッドによる
    リクエストがあった時に Flask が呼ぶ関数。
    絞り込み用のタイトルが POST のパラメータ `title_filter` に入っている。

    データベース接続を得て、
    SELECT 文でリクエストされたタイトルで絞り込んだ CD 一覧を取得、
    テンプレート cds.html へ一覧を渡して埋め込んでレンダリングして返す。
    （これは PRG パターンではない）

    Returns:
      str: ページのコンテンツ
    """
    # データベース接続してカーソルを得る
    cur = get_db().cursor()

    # cds テーブルからタイトルで絞り込み、
    # 得られた全行から CD の情報を取り出した一覧を取得
    cds = cur.execute('SELECT * FROM cds WHERE title LIKE ?',
                          (request.form['title_filter'],)).fetchall()

    # 一覧をテンプレートへ渡してレンダリングしたものを返す
    return render_template('cds.html', cds=cds)

@app.route('/cd/<id>')
def cd(id: str) -> str:
    """
    CD 詳細ページ.

    `http://localhost:5000/cd/<id>` への GET メソッドによる
    リクエストがあった時に Flask が呼ぶ関数。

    データベース接続を得て、
    URL 中の `<id>` で指定された CD の全情報を取得し、
    テンプレート cd.html へ情報を渡して埋め込んでレンダリングして返す。
    指定された CD が見つからない場合は
    テンプレート cd-not-found.html
    （CD が見つからない旨が記載されている）
    をレンダリングして返す。

    Returns:
      str: ページのコンテンツ
    """
    # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()

    # cds テーブルから指定された CD ID の行を 1 行だけ取り出す
    cd = cur.execute('''
      SELECT * FROM cds WHERE id = ?
      ''',(id,)).fetchone()
    songs = cur.execute('''
      SELECT t.track_number, s.title, GROUP_CONCAT(a.name, ', ') AS artists
        FROM tracks t
          JOIN songs s ON s.id = t.song_id
          JOIN tracks_artists ta ON ta.cd_id = t.cd_id AND ta.track_number = t.track_number
          JOIN artists a ON a.id = ta.artist_id
        WHERE t.cd_id = ?
        GROUP BY t.track_number, s.title
        ORDER BY t.track_number
      ''', (id, )).fetchall()

    if cd is None:
        # 指定された CD ID の行が無かった
        return render_template('cd-not-found.html')

    # CD の情報をテンプレートへ渡してレンダリングしたものを返す
    return render_template('cd.html', cd=cd, songs=songs)

@app.route('/cd-add')
def cd_add() -> str:
    """
    CD 追加ページ.

    `http://localhost:5000/cd-add` への GET メソッドによる
    リクエストがあった時に Flask が呼ぶ関数。

    テンプレート cd-add.html
    （CD 追加フォームがあり、追加ボタンで CD 追加実行の POST ができる）
    をレンダリングして返す。

    Returns:
      str: ページのコンテンツ
    """
    # テンプレートへ何も渡さずにレンダリングしたものを返す
    return render_template('cd-add.html')

@app.route('/cd-add', methods=['POST'])
def cd_add_execute() -> Response:
    """
    CD 追加実行.

    `http://localhost:5000/cd-add` への POST メソッドによる
    リクエストがあった時に Flask が呼ぶ関数。
    追加する CD の情報が POST パラメータの `title`, `artist`, `price`
    に入っている。

    データベース接続を得て、POST パラメータの各内容をチェック、
    問題なければ新しい CD として追加し、
    cd_add_results へ処理結果コードを入れてリダイレクトする。
    （PRG パターンの P を受けて R を返す）

    Returns:
      Response: リダイレクト情報
    """
    # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()

    # タイトル取得、チェック
    title = request.form['title']
    if has_control_character(title):
        # タイトルに制御文字が含まれる
        return redirect(url_for('cd_add_results',
                                code='include-control-charactor'))

    # id取得、チェック
    id = request.form['id']
    if has_control_character(id):
        # タイトルに制御文字が含まれる
        return redirect(url_for('cd_add_results',
                                code='include-control-charactor'))

    # series_name取得、チェック
    series_name = request.form['series_name']
    if series_name and has_control_character(series_name):
      # タイトルに制御文字が含まれる
      return redirect(url_for('cd_add_results',
                  code='include-control-charactor'))

    # order_in_series取得、チェック
    order_in_series = request.form['order_in_series']
    if order_in_series:
      try:
        # 文字列型で渡されたシリーズ通し番号を整数型へ変換する
        order_in_series = int(order_in_series)
      except ValueError:
        # シリーズ通し番号が整数型へ変換できない
        return redirect(url_for('cd_add_results',
                    code='series-number-has-invalid-charactor'))

      if has_control_character(order_in_series):
        # シリーズ通し番号に制御文字が含まれる
        return redirect(url_for('cd_add_results',
                    code='include-control-charactor'))

    # issued_date取得、チェック
    issued_date = request.form['issued_date']
    if has_control_character(issued_date):
        # タイトルに制御文字が含まれる
        return redirect(url_for('cd_add_results',
                                code='include-control-charactor'))

    # データベースへCDを追加
    try:
        # cds テーブルに指定されたパラメータの行を挿入
        cur.execute('INSERT INTO cds '
                    '(id, title, series_name, order_in_series, issued_date) '
                    'VALUES (?, ?, ?, ?, ?)',
                    (id, title, series_name, order_in_series, issued_date))
    except sqlite3.Error:
        # データベースエラーが発生
        return redirect(url_for('cd_add_results',
                                code='database-error'))
    # コミット（データベース更新処理を確定）
    con.commit()

    # CD追加完了
    return redirect(url_for('cd_add_results',
                            code='cd-added'))

@app.route('/cd-add-results/<code>')
def cd_add_results(code: str) -> str:
    """
    CD 追加結果ページ.

    `http://localhost:5000/cd-add-result/<code>`
    への GET メソッドによるリクエストがあった時に Flask が呼ぶ関数。

    PRG パターンで CD 追加実行の POST 後にリダイレクトされてくる。
    テンプレート cd-add-results.html
    へ処理結果コード code に基づいたメッセージを渡してレンダリングして返す。

    Returns:
      str: ページのコンテンツ
    """
    return render_template('cd-add-results.html',
                           results=RESULT_MESSAGES.get(code, 'code error'))

@app.route('/cd-del/<id>')
def cd_del(id: str) -> str:
    """
    CD削除確認ページ.

    `http://localhost:5000/cd-del/<id>` への GET メソッドによる
    リクエストがあった時に Flask が呼ぶ関数。

    データベース接続を得て URL 中の `<id>` で指定された CD 情報を取得し、
    削除できるなら
    テンプレート cd-del.html
    （CD削除してよいかの確認ページ）
    へCD番号を渡してレンダリングして返す。
    削除できないなら
    テンプレート cd-del-results.html
    へ理由を渡してレンダリングして返す。

    Returns:
      str: ページのコンテンツ
    """
    # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()

    try:
        # CD番号の存在チェックをする：
        # cds テーブルで同じCD番号の行を 1 行だけ取り出す
        cd = cur.execute('SELECT id FROM cds WHERE id = ?',
                         (id,)).fetchone()
    except cd is None:
        # 指定されたCD番号の行が無い
        return render_template('cd-del-results.html',
                               results='指定されたCD番号は存在しません')

    return render_template('cd-del.html', id=id)

@app.route('/cd-del/<id>', methods=['POST'])
def cd_del_execute(id: str) -> Response:
    """
    CD削除実行.

    `http://localhost:5000/cd-del/<id>` への POST メソッドによる
    リクエストがあった時に Flask が呼ぶ関数。
    POST パラメータは無し。

    データベース接続を得て URL 中の `<id>` で指定された CD 情報を取得し、
    削除できるならして、
    cd_del_results へ処理結果コードを入れてリダイレクトする。
    （PRG パターンの P を受けて R を返す）

    Returns:
      Response: リダイレクト情報
    """
    # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()

    try:
        # CD番号の存在チェックをする：
        # cds テーブルで同じCD番号の行を 1 行だけ取り出す
        cd = cur.execute('SELECT id FROM cds WHERE id = ?',
                         (id,)).fetchone()
    except cd is None:
        # 指定されたCD番号の行が無い
        return redirect(url_for('cd_del_results',
                                code='id-does-not-exist'))

    # tracksからtracks_cd_idに指定したCD番号を持つものを削除
    try:
        # cds テーブルの指定された行を削除
        cur.execute('DELETE FROM tracks WHERE cd_id = ?', (id,))
    except sqlite3.Error:
        # データベースエラーが発生
        return redirect(url_for('cd_add_results',
                                code='database-error'))
    con.commit()

    # cdsから指定したCD番号を持つものを削除
    try:
        # cds テーブルの指定された行を削除
        cur.execute('DELETE FROM cds WHERE id = ?', (id,))
    except sqlite3.Error:
        # データベースエラーが発生
        return redirect(url_for('cd_add_results',
                                code='database-error'))
    # コミット（データベース更新処理を確定）
    con.commit()

    # CD削除完了
    return redirect(url_for('cd_del_results',
                            code='deleted'))

@app.route('/cd-del-results/<code>')
def cd_del_results(code: str) -> str:
    """
    CD削除結果ページ.

    `http://localhost:5000/cd-del-result/<code>`
    への GET メソッドによるリクエストがあった時に Flask が呼ぶ関数。

    PRG パターンでCD削除実行の POST 後にリダイレクトされてくる。
    テンプレート cd-del-results.html
    へ処理結果コード code に基づいたメッセージを渡してレンダリングして返す。

    Returns:
      str: ページのコンテンツ
    """
    return render_template('cd-del-results.html',
                           results=RESULT_MESSAGES.get(code, 'code error'))

@app.route('/cd-edit/<id>')
def cd_edit(id: str) -> str:
    """
    CD 編集ページ.

    `http://localhost:5000/cd-edit/<id>` への GET メソッドによる
    リクエストがあった時に Flask が呼ぶ関数。

    データベース接続を得て URL 中の `<id>` で指定された CD 情報を取得し、
    編集できるなら
    テンプレート cd-edit.html
    （CD 編集フォームがあり、決定ボタンで CD 編集更新の POST ができる）
    へ情報を渡してレンダリングして返す。
    編集できないなら
    テンプレート cd-edit-results.html
    へ理由を渡してレンダリングして返す。

    Returns:
        str: ページのコンテンツ
    """
    # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()

    cd = cur.execute('SELECT * FROM cds WHERE id = ?',
                        (id,)).fetchone()

    # 編集対象の CD 情報をテンプレートへ渡してレンダリングしたものを返す
    return render_template('cd-edit.html', cd=cd)

@app.route('/cd-edit/<id>', methods=['POST'])
def cd_edit_update(id: str) -> Response:
    """
    CD編集更新.

    `http://localhost:5000/cd-edit/<id>` への POST メソッドによる
    リクエストがあった時に Flask が呼ぶ関数。
    編集後の CD の情報が POST パラメータの
    `id`, `title`, `series_name`, `order_in_series`, `issued_date`
    に入っている（CD番号は編集できない）。

    データベース接続を得て URL 中の `<id>` で指定された CD 情報を取得し、
    編集できるなら、POST パラメータの CD 情報をチェック、
    問題なければ CD 情報を更新し、
    テンプレート cd-edit-results.html
    cd_edit_results へ処理結果コードを入れてリダイレクトする。
    （PRG パターンの P を受けて R を返す）

    Returns:
      Response: リダイレクト情報
    """
    # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()


    # CD ID の存在チェックをする：
    # cds テーブルで同じ CD ID の行を 1 行だけ取り出す
    cd = cur.execute('SELECT id FROM cds WHERE id = ?',
                           (id,)).fetchone()
    if cd is None:
        # 指定された CD ID の行が無い
        return redirect(url_for('cd_edit_results',
                                code='id-does-not-exist'))

    # リクエストされた POST パラメータの内容を取り出す
    title = request.form['title']
    series_name = request.form['series_name']
    order_in_series_str = request.form['order_in_series']
    issued_date = request.form['issued_date']

    if order_in_series_str:
      try:
        # 文字列型で渡された CD ID を整数型へ変換する
        order_in_series = int(order_in_series_str)
      except ValueError:
        # CD ID が整数型へ変換できない
        return render_template('cd-edit-results.html',
                    results='シリーズ通し番号は数値で指定してください')


    # データベースを更新
    try:
      # cds テーブルの指定された行のパラメータを更新
      if order_in_series_str:
        cur.execute('UPDATE cds '
                    'SET id = ?, '
                    'title = ?, '
                    'series_name = ?, '
                    'order_in_series = ?, '
                    'issued_date = ? '
                    'WHERE id = ?',
                    (id, title, series_name, order_in_series, issued_date, id))
    except sqlite3.Error:
        # データベースエラーが発生
        return redirect(url_for('employee_edit_results',
                                code='database-error'))
    # コミット（データベース更新処理を確定）
    con.commit()

    # CD編集完了
    return redirect(url_for('cd_edit_results',
                            code='updated'))

@app.route('/cd-edit-results/<code>')
def cd_edit_results(code: str) -> str:
    """
    CD編集結果ページ.

    `http://localhost:5000/cd-edit-result/<code>`
    への GET メソッドによるリクエストがあった時に Flask が呼ぶ関数。

    PRG パターンでCD編集更新の POST 後にリダイレクトされてくる。
    テンプレート cd-edit-results.html
    へ処理結果コード code に基づいたメッセージを渡してレンダリングして返す。

    Returns:
      str: ページのコンテンツ
    """
    return render_template('cd-edit-results.html',
                           results=RESULT_MESSAGES.get(code, 'code error'))

# 楽曲関連ページ
@app.route('/songs')
def songs() -> str:
    """
    CD 一覧のページ（全件）.

    `http://localhost:5000/cds` への GET メソッドによる
    リクエストがあった時に Flask が呼ぶ関数。

    データベース接続を得て、SELECT 文で全 CD 一覧を取得し、
    テンプレート cds.html へ一覧を渡して埋め込んでレンダリングして返す。

    Returns:
      str: ページのコンテンツ
    """
    # データベース接続してカーソルを得る
    cur = get_db().cursor()

    # cds テーブルの全行から CD の情報を取り出した一覧を取得
    songs = cur.execute('SELECT * FROM songs').fetchall()

    # 一覧をテンプレートへ渡してレンダリングしたものを返す
    return render_template('songs.html', songs=songs)

@app.route('/songs', methods=['POST'])
def songs_filtered() -> str:
    """
    CD 一覧のページ（絞り込み）.

    `http://localhost:5000/cds` への POST メソッドによる
    リクエストがあった時に Flask が呼ぶ関数。
    絞り込み用のタイトルが POST のパラメータ `title_filter` に入っている。

    データベース接続を得て、
    SELECT 文でリクエストされたタイトルで絞り込んだ CD 一覧を取得、
    テンプレート cds.html へ一覧を渡して埋め込んでレンダリングして返す。
    （これは PRG パターンではない）

    Returns:
      str: ページのコンテンツ
    """
    # データベース接続してカーソルを得る
    cur = get_db().cursor()

    # cds テーブルからタイトルで絞り込み、
    # 得られた全行から CD の情報を取り出した一覧を取得
    songs = cur.execute('SELECT * FROM songs WHERE title LIKE ?', (request.form['title_filter'],)).fetchall()

    # 一覧をテンプレートへ渡してレンダリングしたものを返す
    return render_template('songs.html', songs=songs)

@app.route('/song/<id>')
def song(id: str) -> str:
    """
    CD 詳細ページ.

    `http://localhost:5000/cd/<id>` への GET メソッドによる
    リクエストがあった時に Flask が呼ぶ関数。

    データベース接続を得て、
    URL 中の `<id>` で指定された CD の全情報を取得し、
    テンプレート cd.html へ情報を渡して埋め込んでレンダリングして返す。
    指定された CD が見つからない場合は
    テンプレート cd-not-found.html
    （CD が見つからない旨が記載されている）
    をレンダリングして返す。

    Returns:
      str: ページのコンテンツ
    """
    # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()

    # songs テーブルから指定された song_id の行を 1 行だけ取り出す
    song = cur.execute('SELECT * FROM songs WHERE id = ?', (id,)).fetchone()

    cds = cur.execute(
        'SELECT c.title '
        'FROM cds c '
        'JOIN tracks t ON c.id = t.cd_id '
        'WHERE t.song_id = ? '
        , (id,)).fetchall()

    concerts = cur.execute(
        'SELECT c.title '
        'FROM concerts c '
        'JOIN performances p ON p.concert_id = c.id '
        'JOIN songs s ON s.id = p.song_id '
        'WHERE s.id = ? '
        , (id,)).fetchall()

    if song is None:
        # 指定された song_id の行が無かった
        return render_template('song-not-found.html')

    # 楽曲の情報をテンプレートへ渡してレンダリングしたものを返す
    return render_template('song.html', song=song, cds=cds, concerts=concerts)

@app.route('/song-add')
def song_add() -> str:
    """
    CD 追加ページ.

    `http://localhost:5000/cd-add` への GET メソッドによる
    リクエストがあった時に Flask が呼ぶ関数。

    テンプレート cd-add.html
    （CD 追加フォームがあり、追加ボタンで CD 追加実行の POST ができる）
    をレンダリングして返す。

    Returns:
      str: ページのコンテンツ
    """
    # テンプレートへ何も渡さずにレンダリングしたものを返す
    return render_template('song-add.html')

@app.route('/song-add', methods=['POST'])
def song_add_execute() -> Response:
    # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()

    # リクエストされた POST パラメータの内容を取り出す
    id_str = request.form['id']
    title = request.form['title']

    try:
    # 文字列型で渡されたIDを整数型へ変換する
        id = int(id_str)
    except ValueError:
    # シリーズ通し番号が整数型へ変換できない
        return redirect(url_for('song_add_results',
                code='id-has-invalid-charactor'))

    song = cur.execute('SELECT id FROM songs WHERE id = ?',\
                           (id,)).fetchone()
    if song is not None:
        # 指定されたIDの行が既に存在
        return redirect(url_for('song_add_results',
                                code='id-already-exists'))
    # タイトルチェック
    if has_control_character(title):
        # タイトルに制御文字が含まれる
        return redirect(url_for('song_add_results',
                                code='include-control-charactor'))

    # データベースへ楽曲を追加
    try:
        # cds テーブルに指定されたパラメータの行を挿入
        cur.execute('INSERT INTO songs '
                    '(id, title'
                    'VALUES (?, ?)',
                    (id, title))
    except sqlite3.Error:
        # データベースエラーが発生
        return redirect(url_for('song_add_results',
                                code='database-error'))
    # コミット（データベース更新処理を確定）
    con.commit()

    # 楽曲追加完了
    return redirect(url_for('song_add_results',
                            code='song-added'))

@app.route('/song-add-results/<code>')
def song_add_results(code: str) -> str:
    """
    CD 追加結果ページ.

    `http://localhost:5000/cd-add-result/<code>`
    への GET メソッドによるリクエストがあった時に Flask が呼ぶ関数。

    PRG パターンで CD 追加実行の POST 後にリダイレクトされてくる。
    テンプレート cd-add-results.html
    へ処理結果コード code に基づいたメッセージを渡してレンダリングして返す。

    Returns:
      str: ページのコンテンツ
    """
    return render_template('song-add-results.html',
                           results=RESULT_MESSAGES.get(code, 'code error'))

@app.route('/song-del/<id>')
def song_del() -> str:
    # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()

    try:
        # 楽曲IDの存在チェックをする：
        # songs テーブルで同じ楽曲IDの行を 1 行だけ取り出す
        song = cur.execute('SELECT id FROM songs WHERE id = ?',
                         (id,)).fetchone()
    except song is None:
        # 指定されたCD番号の行が無い
        return render_template('song-del-results.html',
                               results='指定された楽曲は存在しません')

    return render_template('song-del.html', id=id)

@app.route('/song-del/<id>', methods=['POST'])
def song_del_execute(id: str) -> Response:
    # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()

    try:
        # 楽曲IDの存在チェックをする：
        # songs テーブルで同じ楽曲IDの行を 1 行だけ取り出す
        song = cur.execute('SELECT id FROM songs WHERE id = ?',
                         (id,)).fetchone()
    except song is None:
        # 指定された楽曲IDの行が無い
        return redirect(url_for('song_del_results',
                                code='id-does-not-exist'))
    con.commit()

    # 楽曲削除完了
    return redirect(url_for('song_del_results',
                            code='deleted'))

@app.route('/song-del-results/<code>')
def song_del_results(code: str) -> str:
    return render_template('song-del-results.html',
                           results=RESULT_MESSAGES.get(code, 'code error'))

@app.route('/song-edit/<id>')
def song_edit(id: str) -> str:
    # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()

    song = cur.execute('SELECT * FROM songs WHERE id = ?',
                        (id,)).fetchone()

    return render_template('song-edit.html', song=song)

@app.route('/song-edit/<id>', methods=['POST'])
def song_edit_update(id: str) -> Response:
    # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()

    # 楽曲IDの存在チェックをする：
    # songs テーブルで同じ楽曲IDの行を 1 行だけ取り出す
    song = cur.execute('SELECT id FROM songs WHERE id = ?',
                         (id,)).fetchone()
    if song is None:
        # 指定された楽曲IDの行が無い
        return redirect(url_for('song_edit_results',
                                code='id-does-not-exist'))

    # リクエストされた POST パラメータの内容を取り出す
    title = request.form['title']

    # タイトルチェック
    if has_control_character(title):
        # タイトルに制御文字が含まれる
        return redirect(url_for('song_edit_results',
                                code='include-control-charactor'))

    # データベースを更新
    try:
        # cds テーブルの指定された行のパラメータを更新
        cur.execute('UPDATE songs '
                    'SET title = ? '
                    'WHERE id = ?',
                    (title, id))
    except sqlite3.Error:
        # データベースエラーが発生
        return redirect(url_for('song_edit_results',
                                code='database-error'))
    # コミット（データベース更新処理を確定）
    con.commit()

    # 楽曲編集完了
    return redirect(url_for('song_edit_results',
                            code='updated'))

# トラック関連
@app.route('/tracks-edit/<id>')
def tracks_edit(id: str) -> str:
    con = get_db()
    cur = con.cursor()

    # CD タイトルを取得
    cd = cur.execute('SELECT title FROM cds WHERE id = ?', (id,)).fetchone()

    # トラック情報を取得
    tracks = cur.execute(
        'SELECT t.track_number, s.title AS song_title, a.name AS artist_name '
        'FROM tracks t '
        'JOIN songs s ON s.id = t.song_id '
        'JOIN tracks_artists ta ON ta.cd_id = t.cd_id AND ta.track_number = t.track_number '
        'JOIN artists a ON a.id = ta.artist_id '
        'WHERE t.cd_id = ? '
        'ORDER BY t.track_number '
    , (id,)).fetchall()

    # 編集対象の CD 情報をテンプレートへ渡してレンダリングしたものを返す
    return render_template('tracks-edit.html', cd=cd, tracks=tracks)

@app.route('/tracks-edit', methods=['POST'])
def tracks_edit_update(id: str) -> Response:
    # # データベース接続してカーソルを得る
    # con = get_db()
    # cur = con.cursor()

    # track = cur.execute('SELECT * FROM tracks WHERE cd_id = ? AND track_number = ? AND artist_name = ?',
    #                     (cd_id, track_number, artist_name)).fetchone()

    # if track is None:
    #     return render_template('tracks-edit-results.html',
    #                            results='指定されたトラック存在しません')

    # song_title = request.form['song_title']
    # artist_name = request.form['artist_name']

    # try:
    #     # tracks テーブルの指定された行のパラメータを更新
    #     cur.execute(
    #         'UPDATE tracks '
    #         'SET t.song_id = ? '
    #         'FROM tracks t '
    #         'INNER JOIN songs ON songs.title = ? '
    #         'WHERE cd_id = ? AND track_number = ?'
    #         , (song_id, cd_id, track_number,))
    #     cur.execute(
    #         'UPDATE artists_tracks '
    #         'SET track_number = ?, '
    #         'SET '
    #         'song_id = ? '
    #         'WHERE cd_id = ?'
    #         , (track_number, song_id, id))
    # except sqlite3.Error:
    #     return redirect(url_for('tracks_edit_results',
    #                             code='database-error'))

    # con.commit()

    return render_template('tracks_edit_results.html', code='updated')


if __name__ == '__main__':
    # このスクリプトを直接実行したらデバッグ用 Web サーバで起動する
    app.run(debug=True)