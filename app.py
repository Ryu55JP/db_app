#/db_app/app.py
"""
ディスコグラフィのデータベースを使った Web アプリケーション

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
    'id-has-invalid-charactor':
    '指定された情報には使えない文字があります - '
    'IDは数字のみで指定してください',
    'include-invalid-charactor':
    '指定された情報には使えない文字があります - ',
    'id-already-exists':
    '指定されたIDのデータは既に存在します - '
    '存在しないIDを指定してください',
    'include-control-charactor':
    '制御文字は指定しないでください',
    'database-error':
    'データベースエラー',
    'deleted':
    '削除しました',
    'updated':
    '更新しました',
    'unchanged':
    '変更はありません',
    'debug':
    'debug',
    # cd
    'series-number-has-invalid-charactor':
    '指定された情報には使えない文字があります - '
    'シリーズ通し番号は数字のみで指定してください',
    'track-number-has-invalid-charactor':
    '指定された情報には使えない文字があります - '
    'トラック番号は数字のみで指定してください',
    'track-added':
    'トラックが追加されました',
    'cd-added':
    'CDを追加しました',
    # song
    'song-id-has-invalid-charactor':
    '指定された情報には使えない文字があります - '
    '楽曲IDは数字のみで指定してください',
    'song-does-not-exist':
    '指定された楽曲は存在しません',
    'song-added':
    '楽曲を追加しました',
    # artist
    'artist-id-has-invalid-charactor':
    '指定された情報には使えない文字があります - '
    'アーティストIDは数字のみで指定してください',
    'artist-does-not-exist':
    '指定されたアーティストは存在しません',
    'artist-added':
    'アーティストを追加しました',
    # concert
    'number-of-order-has-invalid-charactor':
    '指定された情報には使えない文字があります - '
    'セットリスト番号は数字のみで指定してください',
    'concert-added':
    'コンサートを追加しました',
    'setlist-added':
    'セットリストに追加されました',
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
      SELECT t.track_number, s.title, GROUP_CONCAT(a.name, ', ') AS artists, s.id AS song_id
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
        cd = cur.execute('SELECT * FROM cds WHERE id = ?',
                         (id,)).fetchone()
    except cd is None:
        # 指定されたCD番号の行が無い
        return render_template('cd-del-results.html',
                               results='指定されたCD番号は存在しません')

    return render_template('cd-del.html', id=id, cd=cd)

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

    # tracks, tracks_artistsからcd_idに指定したCD番号を持つものを削除し、
    # cdsから指定したCD品番を持つものを削除
    try:
        cur.execute('DELETE FROM tracks_artists WHERE cd_id = ?', (id,))
        cur.execute('DELETE FROM tracks WHERE cd_id = ?', (id,))
        cur.execute('DELETE FROM cds WHERE id = ?', (id,))
    except sqlite3.Error as e:
        # エラーが発生した場合はロールバック
        con.rollback()
        # エラーログを出力（デバッグ用）
        print(f"Database error: {e}")
        # データベースエラーが発生
        return redirect(url_for('cd_del_results',
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

    if has_control_character(title):
            # タイトルに制御文字が含まれる
            return redirect(url_for('song_edit_results',
                                    code='include-control-charactor'))

    if has_control_character(series_name):
            # タイトルに制御文字が含まれる
            return redirect(url_for('song_edit_results',
                                    code='include-control-charactor'))

    if has_control_character(issued_date):
            # タイトルに制御文字が含まれる
            return redirect(url_for('song_edit_results',
                                    code='include-control-charactor'))

    if order_in_series_str:
      try:
        # 文字列型で渡された CD ID を整数型へ変換する
        order_in_series = int(order_in_series_str)
      except ValueError:
        # シリーズ通し番号が整数型へ変換できない
        return render_template('cd-edit-results.html',
                    results='シリーズ通し番号は数値で指定してください')

    if order_in_series_str:
        # データベースを更新
        try:
        # cds テーブルの指定された行のパラメータを更新
            cur.execute('UPDATE cds '
                        'SET title = ?, '
                        'series_name = ?, '
                        'order_in_series = ?, '
                        'issued_date = ? '
                        'WHERE id = ?',
                        (title, series_name, order_in_series, issued_date, id))
        except sqlite3.Error:
            # データベースエラーが発生
            return redirect(url_for('cd_edit_results',
                                    code='database-error'))

    else:
        # データベースを更新
        try:
        # cds テーブルの指定された行のパラメータを更新
            cur.execute('UPDATE cds '
                        'SET title = ?, '
                        'series_name = ?, '
                        'order_in_series = NULL, '
                        'issued_date = ? '
                        'WHERE id = ?',
                        (title, series_name, issued_date, id))
        except sqlite3.Error:
            # データベースエラーが発生
            return redirect(url_for('cd_edit_results',
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

# 楽曲関連
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
        'SELECT DISTINCT c.title, c.id AS cd_id '
        'FROM cds c '
        'JOIN tracks t ON c.id = t.cd_id '
        'WHERE t.song_id = ? '
        , (id,)).fetchall()

    concerts = cur.execute(
        'SELECT DISTINCT c.title, c.id AS concert_id '
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
                    '(id, title) '
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
def song_del(id: str) -> str:
    # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()

    id = int(id)

    try:
        # 楽曲IDの存在チェックをする：
        # songs テーブルで同じ楽曲IDの行を 1 行だけ取り出す
        song = cur.execute('SELECT * FROM songs WHERE id = ?',
                         (id,)).fetchone()
    except song is None:
        # 指定されたCD番号の行が無い
        return render_template('song-del-results.html',
                               results='指定された楽曲は存在しません')

    return render_template('song-del.html', id=id, song=song)

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

    try:
        # cds テーブルの指定された行を削除
        cur.execute('DELETE FROM songs WHERE id = ?', (id,))
    except sqlite3.Error:
        # データベースエラーが発生
        return redirect(url_for('song_del_results',
                                code='database-error'))


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

@app.route('/song-edit-results/<code>')
def song_edit_results(code: str) -> str:
    return render_template('song-edit-results.html',
                           results=RESULT_MESSAGES.get(code, 'code error'))

# 未完成です
# トラック
@app.route('/track-add/<id>')
def track_add(id: str) -> str:
    con = get_db()
    cur = con.cursor()

    # CD タイトルを取得
    cd = cur.execute('SELECT * FROM cds WHERE id = ?', (id,)).fetchone()

    return render_template('track-add.html', cd=cd)

@app.route('/track-add/<id>', methods=['POST'])
def track_add_execute(id: str) -> Response:
     # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()

    # リクエストされた POST パラメータの内容を取り出す
    cd_id = id
    track_number_str = request.form['track_number']
    song_id_str = request.form['song_id']
    artist_id_str = request.form['artist_id']

    try:
        # 文字列型で渡されたシリーズ通し番号を整数型へ変換する
        track_number = int(track_number_str)
    except ValueError:
    # シリーズ通し番号が整数型へ変換できない
        return redirect(url_for('track_add_results',
                    code='track-number-has-invalid-charactor'))
    try:
        # 文字列型で渡されたシリーズ通し番号を整数型へ変換する
        song_id = int(song_id_str)
    except ValueError:
    # シリーズ通し番号が整数型へ変換できない
        return redirect(url_for('track_add_results',
                    code='song-id-has-invalid-charactor'))
    try:
        # 文字列型で渡されたシリーズ通し番号を整数型へ変換する
        artist_id = int(artist_id_str)
    except ValueError:
    # シリーズ通し番号が整数型へ変換できない
        return redirect(url_for('track_add_results',
                    code='artist-id-has-invalid-charactor'))

    # 楽曲IDの存在チェックをする：
    # songs テーブルで同じ楽曲IDの行を 1 行だけ取り出す
    song = cur.execute('SELECT id FROM songs WHERE id = ?',
                         (song_id,)).fetchone()
    if song is None:
        # 指定された楽曲IDの行が無い
        return redirect(url_for('track_add_results',
                                code='song-does-not-exist'))

    # アーティストIDの存在チェックをする：
    # artists テーブルで同じ楽曲IDの行を 1 行だけ取り出す
    artist = cur.execute('SELECT id FROM artists WHERE id = ?',
                         (artist_id,)).fetchone()
    if artist is None:
        # 指定された楽曲IDの行が無い
        return redirect(url_for('track_add_results',
                                code='artist-does-not-exist'))

    try:
        # tracks テーブルの指定された行のパラメータを更新
        cur.execute(
                    'INSERT INTO tracks '
                    '(cd_id, track_number, song_id) '
                    'VALUES (?, ?, ?) ',
                    (cd_id, track_number, song_id))
    except sqlite3.Error:
            return redirect(url_for('track_add_results',
                                    code='database-error'))

    try:
            # tracks テーブルの指定された行のパラメータを更新
        cur.execute(
                    'INSERT INTO tracks_artists '
                    '(cd_id, track_number, artist_id) '
                    'VALUES (?, ?, ?) ',
                    (cd_id, track_number, artist_id))
    except sqlite3.Error:
        return redirect(url_for('track_add_results',
                        code='database-error'))

    # コミット（データベース更新処理を確定）
    con.commit()

    return redirect(url_for('track_add_results',
                            code='track-added'))

@app.route('/track-add-results/<code>')
def track_add_results(code: str) -> str:
    return render_template('track-add-results.html',
                           results=RESULT_MESSAGES.get(code, 'code error'))

@app.route('/tracks-del/<id>')
def tracks_del(id: str) -> str:
    """
    tracks削除確認ページ.

    `http://localhost:5000/cd-del/<id>` への GET メソッドによる
    リクエストがあった時に Flask が呼ぶ関数。

    Returns:
      str: ページのコンテンツ
    """
    # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()


    # CD番号の存在チェックをする：
    # cds テーブルで同じCD番号の行を 1 行だけ取り出す
    cd = cur.execute('SELECT * FROM cds WHERE id = ?',
                        (id,)).fetchone()
    if cd is None:
        # 指定されたCD番号の行が無い
        return render_template('tracks-del-results.html',
                               results='指定されたCDは存在しません')

    return render_template('tracks-del.html', id=id, cd=cd)

@app.route('/tracks-del/<id>', methods=['POST'])
def tracks_del_execute(id: str) -> Response:
    """
    tracks削除実行.

    Returns:
      Response: リダイレクト情報
    """
    # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()

    # tracksからtracks_cd_idに指定したCD番号を持つものを削除
    try:
        cur.execute('DELETE FROM tracks_artists WHERE cd_id = ?', (id,))
        cur.execute('DELETE FROM tracks WHERE cd_id = ?', (id,))
    except sqlite3.Error:
        # データベースエラーが発生
        return redirect(url_for('tracks_del_results',
                                code='database-error'))




    con.commit()

    # tracks削除完了
    return redirect(url_for('tracks_del_results',
                            code='deleted'))

@app.route('/tracks-del-results/<code>')
def tracks_del_results(code: str) -> str:
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
    return render_template('tracks-del-results.html',
                           results=RESULT_MESSAGES.get(code, 'code error'))




# アーティスト
@app.route('/artists')
def artists() -> str:


    cur = get_db().cursor()

    artists = cur.execute('SELECT * FROM artists').fetchall()

    return render_template('artists.html', artists=artists)

@app.route('/artists', methods=['POST'])
def artists_filtered() -> str:
    cur = get_db().cursor()

    artists = cur.execute('SELECT * FROM artists WHERE name LIKE ?', (request.form['name_filter'],)).fetchall()

    return render_template('artists.html', artists=artists)


@app.route('/artist/<id>')
def artist(id: str) -> str:
    con = get_db()
    cur = con.cursor()

    # cds テーブルから指定された CD ID の行を 1 行だけ取り出す
    artist = cur.execute('''
      SELECT * FROM artists WHERE id = ?
      ''',(id,)).fetchone()
    if artist is None:
        # 指定された アーティストID の行が無かった
        return render_template('index.html')

    cds = cur.execute(
                    'SELECT DISTINCT c.title AS cd_title, c.id AS cd_id '
                    'FROM cds c '
                    'JOIN tracks t ON t.cd_id = c.id '
                    'JOIN tracks_artists ta ON ta.cd_id = t.cd_id AND ta.track_number = t.track_number '
                    'JOIN artists a ON a.id = ta.artist_id '
                    'WHERE a.id = ? '
    , (id, )).fetchall()

    concerts = cur.execute(
                    'SELECT DISTINCT c.title AS concert_title, c.id AS concert_id '
                    'FROM concerts c '
                    'JOIN performances p ON p.concert_id = c.id '
                    'JOIN artists_performances ap ON ap.concert_id = p.concert_id AND ap.order_in_concert = p.number_of_order '
                    'JOIN artists a ON a.id = ap.artist_id '
                    'WHERE a.id = ? '
    , (id, )).fetchall()


    return render_template('artist.html', artist=artist, cds=cds, concerts=concerts)

@app.route('/artist-add')
def artist_add() -> str:
    return render_template('artist-add.html')

@app.route('/artist-add', methods=['POST'])
def artist_add_execute() -> Response:
    # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()

    # id取得、チェック
    id = request.form['id']
    if id:
      try:
        # 文字列型で渡されたシリーズ通し番号を整数型へ変換する
        id = int(id)
      except ValueError:
        # シリーズ通し番号が整数型へ変換できない
        return redirect(url_for('artist_add_results',
                    code='id-has-invalid-charactor'))

    # アーティスト名取得、チェック
    name = request.form['name']
    if has_control_character(name):
        # アーティスト名に制御文字が含まれる
        return redirect(url_for('artist_add_results',
                                code='include-control-charactor'))

    # issued_date取得、チェック
    group_name = request.form['group_name']
    if has_control_character(group_name):
        # タイトルに制御文字が含まれる
        return redirect(url_for('cd_add_results',
                                code='include-control-charactor'))

    # データベースへアーティストを追加
    try:
        # cds テーブルに指定されたパラメータの行を挿入
        cur.execute('INSERT INTO artists '
                    '(id, name, group_name) '
                    'VALUES (?, ?, ?)',
                    (id, name, group_name))
    except sqlite3.Error:
        # データベースエラーが発生
        return redirect(url_for('artist_add_results',
                                code='database-error'))
    # コミット（データベース更新処理を確定）
    con.commit()

    # CD追加完了
    return redirect(url_for('artist_add_results',
                            code='artist-added'))

@app.route('/artist-add-results/<code>')
def artist_add_results(code: str) -> str:
    return render_template('artist-add-results.html',
                           results=RESULT_MESSAGES.get(code, 'code error'))

@app.route('/artist-del/<id>')
def artist_del(id: str) -> str:
    # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()

    try:
        # CD番号の存在チェックをする：
        # cds テーブルで同じCD番号の行を 1 行だけ取り出す
        artist = cur.execute('SELECT * FROM artists WHERE id = ?',
                         (id,)).fetchone()
    except artist is None:
        # 指定されたCD番号の行が無い
        return render_template('artist-del-results.html',
                               results='指定されたアーティストは存在しません')

    return render_template('artist-del.html', id=id, artist=artist)

@app.route('/artist-del/<id>', methods=['POST'])
def artist_del_execute(id: str) -> Response:
    # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()


    try:
        # CD番号の存在チェックをする：
        # cds テーブルで同じCD番号の行を 1 行だけ取り出す
        artist = cur.execute('SELECT id FROM artists WHERE id = ?',
                         (id,)).fetchone()
    except artist is None:
        # 指定されたCD番号の行が無い
        return redirect(url_for('artist_del_results',
                                code='id-does-not-exist'))


    try:
        # cds テーブルの指定された行を削除
        cur.execute('DELETE FROM artists WHERE id = ?', (id,))
    except sqlite3.Error:
        # データベースエラーが発生
        return redirect(url_for('artist_add_results',
                                code='database-error'))
    con.commit()

    # CD削除完了
    return redirect(url_for('artist_del_results',
                            code='deleted'))

@app.route('/artist-del-results/<code>')
def artist_del_results(code: str) -> str:
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
    return render_template('artist-del-results.html',
                           results=RESULT_MESSAGES.get(code, 'code error'))

@app.route('/artist-edit/<id>')
def artist_edit(id: str) -> str:
    # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()

    artist = cur.execute('SELECT * FROM artists WHERE id = ?',
                        (id,)).fetchone()

    # 編集対象の CD 情報をテンプレートへ渡してレンダリングしたものを返す
    return render_template('artist-edit.html', artist=artist)

@app.route('/artist-edit/<id>', methods=['POST'])
def artist_edit_update(id: str) -> Response:
    # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()


    # CD ID の存在チェックをする：
    # cds テーブルで同じ CD ID の行を 1 行だけ取り出す
    artist = cur.execute('SELECT id FROM artists WHERE id = ?',
                           (id,)).fetchone()
    if artist is None:
        # 指定された CD ID の行が無い
        return redirect(url_for('artist_edit_results',
                                code='id-does-not-exist'))

    # リクエストされた POST パラメータの内容を取り出す
    name = request.form['name']
    group_name = request.form['group_name']

    if has_control_character(name):
            # タイトルに制御文字が含まれる
            return redirect(url_for('song_edit_results',
                                    code='include-control-charactor'))

    if has_control_character(group_name):
            # タイトルに制御文字が含まれる
            return redirect(url_for('song_edit_results',
                                    code='include-control-charactor'))

    # データベースを更新
    try:
        cur.execute('UPDATE artists '
                    'SET name = ?, '
                    'group_name = ? '
                    'WHERE id = ?',
                    (name, group_name, id))
    except sqlite3.Error:
        # データベースエラーが発生
        return redirect(url_for('artist_edit_results',
                                code='database-error'))
    # コミット（データベース更新処理を確定）
    con.commit()

    # アーティスト編集完了
    return redirect(url_for('artist_edit_results',
                            code='updated'))

@app.route('/artist-edit-results/<code>')
def artist_edit_results(code: str) -> str:
    return render_template('artist-edit-results.html',
                           results=RESULT_MESSAGES.get(code, 'code error'))




# コンサート
@app.route('/concerts')
def concerts() -> str:
    # データベース接続してカーソルを得る
    cur = get_db().cursor()

    # cds テーブルの全行から CD の情報を取り出した一覧を取得
    concerts = cur.execute('SELECT * FROM concerts ORDER BY held_date').fetchall()

    # 一覧をテンプレートへ渡してレンダリングしたものを返す
    return render_template('concerts.html', concerts=concerts)

@app.route('/concerts', methods=['POST'])
def concerts_filtered() -> str:
    # データベース接続してカーソルを得る
    cur = get_db().cursor()

    # cds テーブルからタイトルで絞り込み、
    # 得られた全行から CD の情報を取り出した一覧を取得
    concerts = cur.execute('SELECT * FROM concerts WHERE title LIKE ? ORDER BY held_date', (request.form['title_filter'],)).fetchall()

    # 一覧をテンプレートへ渡してレンダリングしたものを返す
    return render_template('concerts.html', concerts=concerts)

@app.route('/concert/<id>')
def concert(id: str) -> str:
    # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()

    # songs テーブルから指定された song_id の行を 1 行だけ取り出す
    concert = cur.execute('SELECT * FROM concerts WHERE id = ?', (id,)).fetchone()

    if concert is None:
        # 指定された song_id の行が無かった
        return render_template('concert-not-found.html')

    performances = cur.execute(
                        'SELECT p.number_of_order AS number_of_order, s.title AS song_title, s.id AS song_id, GROUP_CONCAT(a.name, ", ") AS artists '
                        'FROM performances p '
                        'JOIN songs s ON s.id = p.song_id '
                        'JOIN artists_performances ap ON ap.concert_id = p.concert_id AND ap.order_in_concert = p.number_of_order '
                        'JOIN artists a ON a.id = ap.artist_id '
                        'WHERE p.concert_id = ? '
                        'GROUP BY p.number_of_order, s.title '
                        'ORDER BY p.number_of_order'
                        , (id,)).fetchall()

    # 楽曲の情報をテンプレートへ渡してレンダリングしたものを返す
    return render_template('concert.html', concert=concert, performances=performances)

@app.route('/concert-add')
def concert_add() -> str:
    # テンプレートへ何も渡さずにレンダリングしたものを返す
    return render_template('concert-add.html')

@app.route('/concert-add', methods=['POST'])
def concert_add_execute() -> Response:
    # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()

    # リクエストされた POST パラメータの内容を取り出す
    id_str = request.form['id']
    title = request.form['title']
    held_date = request.form['held-date']

    try:
    # 文字列型で渡されたIDを整数型へ変換する
        id = int(id_str)
    except ValueError:
    # シリーズ通し番号が整数型へ変換できない
        return redirect(url_for('concert_add_results',
                code='id-has-invalid-charactor'))

    concert = cur.execute('SELECT id FROM concerts WHERE id = ?',\
                           (id,)).fetchone()

    if concert is not None:
        # 指定されたIDの行が既に存在
        return redirect(url_for('concert_add_results',
                                code='id-already-exists'))
    # タイトルチェック
    if has_control_character(title):
        # タイトルに制御文字が含まれる
        return redirect(url_for('concert_add_results',
                                code='include-control-charactor'))

    # 開催日チェック
    if has_control_character(held_date):
        # タイトルに制御文字が含まれる
        return redirect(url_for('concert_add_results',
                                code='include-control-charactor'))

    # データベースへ楽曲を追加
    try:
        # cds テーブルに指定されたパラメータの行を挿入
        cur.execute('INSERT INTO concerts '
                    '(id, title, held_date) '
                    'VALUES (?, ?, ?)',
                    (id, title, held_date))
    except sqlite3.Error:
        # データベースエラーが発生
        return redirect(url_for('concert_add_results',
                                code='database-error'))
    # コミット（データベース更新処理を確定）
    con.commit()

    # 楽曲追加完了
    return redirect(url_for('concert_add_results',
                            code='concert-added'))

@app.route('/concert-add-results/<code>')
def concert_add_results(code: str) -> str:

    return render_template('concert-add-results.html',
                           results=RESULT_MESSAGES.get(code, 'code error'))

@app.route('/concert-del/<id>')
def concert_del(id: str) -> str:
    # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()

    id = int(id)

    try:
        # 楽曲IDの存在チェックをする：
        # songs テーブルで同じ楽曲IDの行を 1 行だけ取り出す
        concert = cur.execute('SELECT id FROM concerts WHERE id = ?',
                         (id,)).fetchone()
    except concert is None:
        # 指定されたCD番号の行が無い
        return render_template('concert-del-results.html',
                               results='指定されたコンサートは存在しません')

    return render_template('concert-del.html', id=id, concert=concert)


@app.route('/concert-del/<id>', methods=['POST'])
def concert_del_execute(id: str) -> Response:
    # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()

    id = int(id)

    try:
        # 楽曲IDの存在チェックをする：
        # songs テーブルで同じ楽曲IDの行を 1 行だけ取り出す
        concert = cur.execute('SELECT id FROM concerts WHERE id = ?',
                         (id,)).fetchone()
    except concert is None:
        # 指定された楽曲IDの行が無い
        return redirect(url_for('concert_del_results',
                                code='id-does-not-exist'))

    try:
        # cds テーブルの指定された行を削除
        cur.execute('DELETE FROM artists_performances WHERE concert_id = ?', (id,))
        cur.execute('DELETE FROM performances WHERE concert_id = ?', (id,))
        cur.execute('DELETE FROM concerts WHERE id = ?', (id,))
    except sqlite3.Error:
        # データベースエラーが発生
        return redirect(url_for('concert_del_results',
                                code='database-error'))

    con.commit()

    # 楽曲削除完了
    return redirect(url_for('concert_del_results',
                            code='deleted'))


@app.route('/concert-del-results/<code>')
def concert_del_results(code: str) -> str:
    return render_template('concert-del-results.html',
                           results=RESULT_MESSAGES.get(code, 'code error'))


@app.route('/concert-edit/<id>')
def concert_edit(id: str) -> str:
    # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()

    concert = cur.execute('SELECT * FROM concerts WHERE id = ?',
                        (id,)).fetchone()

    # 編集対象の コンサート 情報をテンプレートへ渡してレンダリングしたものを返す
    return render_template('concert-edit.html', concert=concert)

@app.route('/concert-edit/<id>', methods=['POST'])
def concert_edit_update(id: str) -> Response:
    # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()

    concert = cur.execute('SELECT id FROM concerts WHERE id = ?',
                           (id,)).fetchone()
    if concert is None:
        # 指定された CD ID の行が無い
        return redirect(url_for('concert_edit_results',
                                code='id-does-not-exist'))

    # リクエストされた POST パラメータの内容を取り出す
    title = request.form['title']
    held_date = request.form['held_date']

    if has_control_character(title):
            # タイトルに制御文字が含まれる
            return redirect(url_for('concert_edit_results',
                                    code='include-control-charactor'))

    if has_control_character(held_date):
            # タイトルに制御文字が含まれる
            return redirect(url_for('concert_edit_results',
                                    code='include-control-charactor'))

    # データベースを更新
    try:
        cur.execute('UPDATE concerts '
                    'SET title = ?, '
                    'held_date = ? '
                    'WHERE id = ?',
                    (title, held_date, id))

    except sqlite3.Error:
        # データベースエラーが発生
        return redirect(url_for('concert_edit_results',
                                code='database-error'))
    # コミット（データベース更新処理を確定）
    con.commit()

    # CD編集完了
    return redirect(url_for('concert_edit_results',
                            code='updated'))


@app.route('/concert-edit-results/<code>')
def concert_edit_results(code: str) -> str:

    return render_template('concert-edit-results.html',
                           results=RESULT_MESSAGES.get(code, 'code error'))


# セットリスト
@app.route('/setlist-add/<id>')
def setlist_add(id: str) -> str:
    con = get_db()
    cur = con.cursor()

    concert = cur.execute('SELECT * FROM concerts WHERE id = ?', (id,)).fetchone()
    return render_template('setlist-add.html', concert=concert)


@app.route('/setlist-add/<id>', methods=['POST'])
def setlist_add_execute(id: str) -> Response:
     # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()

    concert_id_str = id
    number_of_order_str = request.form['number_of_order']
    song_id = request.form['song_id']
    artist_id = request.form['artist_id']

    try:
        # 文字列型で渡されたシリーズ通し番号を整数型へ変換する
        concert_id = int(concert_id_str)
    except ValueError:
    # シリーズ通し番号が整数型へ変換できない
        return redirect(url_for('setlist_add_results',
                    code='id-has-invalid-charactor'))

    try:
        # 文字列型で渡されたシリーズ通し番号を整数型へ変換する
        number_of_order = int(number_of_order_str)
    except ValueError:
    # シリーズ通し番号が整数型へ変換できない
        return redirect(url_for('setlist_add_results',
                    code='number-of-order-has-invalid-charactor'))

# 楽曲IDの存在チェックをする：
    # songs テーブルで同じ楽曲IDの行を 1 行だけ取り出す
    song = cur.execute('SELECT id FROM songs WHERE id = ?',
                         (song_id,)).fetchone()
    if song is None:
        # 指定された楽曲IDの行が無い
        return redirect(url_for('setlist_add_results',
                                code='song-does-not-exist'))

    # アーティストIDの存在チェックをする：
    # artists テーブルで同じ楽曲IDの行を 1 行だけ取り出す
    artist = cur.execute('SELECT id FROM artists WHERE id = ?',
                         (artist_id,)).fetchone()
    if artist is None:
        # 指定された楽曲IDの行が無い
        return redirect(url_for('setlist_add_results',
                                code='artist-does-not-exist'))


    try:
        # tracks テーブルの指定された行のパラメータを更新
        cur.execute(
                    'INSERT INTO performances '
                    '(concert_id, number_of_order, song_id) '
                    'VALUES (?, ?, ?) ',
                    (concert_id, number_of_order, song_id))
        cur.execute(
                    'INSERT INTO artists_performances '
                    '(concert_id, order_in_concert, artist_id) '
                    'VALUES (?, ?, ?) ',
                    (concert_id, number_of_order, artist_id))
    except sqlite3.Error as e:
        print(e)
        return redirect(url_for('setlist_add_results',
                                    code='database-error'))

    con.commit()

    return redirect(url_for('setlist_add_results',
                                    code='setlist-added'))

@app.route('/setlist-add-results/<code>')
def setlist_add_results(code: str) -> str:
    return render_template('setlist-add-results.html',
                           results=RESULT_MESSAGES.get(code, 'code error'))


@app.route('/setlist-del/<id>')
def setlist_del(id: str) -> str:
    """
    setlist削除確認ページ.

    `http://localhost:5000/cd-del/<id>` への GET メソッドによる
    リクエストがあった時に Flask が呼ぶ関数。

    Returns:
      str: ページのコンテンツ
    """
    # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()

    concert = cur.execute('SELECT * FROM concerts WHERE id = ?',
                         (id,)).fetchone()
    if concert is None:
        # 指定されたCD番号の行が無い
        return render_template('setlist-del-results.html',
                               results='指定されたコンサートは存在しません')

    return render_template('setlist-del.html', id=id, concert=concert)

@app.route('/setlist-del/<id>', methods=['POST'])
def setlist_del_execute(id: str) -> Response:
    """
    setlist削除実行.

    Returns:
      Response: リダイレクト情報
    """
    # データベース接続してカーソルを得る
    con = get_db()
    cur = con.cursor()

    # tracksからtracks_cd_idに指定したCD番号を持つものを削除
    try:
        cur.execute('DELETE FROM artists_performances WHERE concert_id = ?', (id,))
        cur.execute('DELETE FROM performances WHERE concert_id = ?', (id,))
    except sqlite3.Error as e:
        # データベースエラーが発生
        print(e)
        return redirect(url_for('setlist_del_results',
                                code='database-error'))


    con.commit()

    # tracks削除完了
    return redirect(url_for('setlist_del_results',
                            code='deleted'))


@app.route('/setlist-del-results/<code>')
def setlist_del_results(code: str) -> str:
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
    return render_template('setlist-del-results.html',
                           results=RESULT_MESSAGES.get(code, 'code error'))



if __name__ == '__main__':
    # このスクリプトを直接実行したらデバッグ用 Web サーバで起動する
    app.run(debug=True)