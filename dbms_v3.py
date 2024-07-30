from functools import wraps
import os
import subprocess
from flask import Flask, Response, flash, render_template, request, redirect, send_file, session, url_for
from graphviz import Digraph
import pymysql

app = Flask(__name__)
app.secret_key = 'secretKeys'  # Session security key

defaultDB="mysql"

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash('Admin girişi gereklidir!', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_foreign_rows():
    conn = get_db_connection()
    foreign_rows = {}

    try:
        with conn.cursor() as cursor:
            for table_name in get_tables(defaultDB):
                cursor.execute(f"SHOW COLUMNS FROM {table_name}")
                columns_data = cursor.fetchall()
                for column in columns_data:
                    if column['Field'].endswith('_id'):
                        foreign_table_name = column['Field'][:-3]  # Remove the '_id' suffix to get the foreign table name
                        cursor.execute(f"SELECT * FROM {foreign_table_name}")
                        rows = cursor.fetchall()
                        foreign_rows[column['Field']] = rows
        print(foreign_rows)
    except Exception as e:
        print("Error fetching foreign rows:", e)
    finally:
        conn.close()

    return foreign_rows



def get_foreign_keys(db_name, table_name):
    conn = pymysql.connect(host='localhost', user='mert', password='mert', database=db_name)
    cursor = conn.cursor()
    cursor.execute(f"SHOW CREATE TABLE {table_name}")
    create_table_query = cursor.fetchone()[1]
    foreign_keys = [line.strip() for line in create_table_query.split('\n') if 'FOREIGN KEY' in line]
    cursor.close()
    conn.close()
    return foreign_keys


def create_er_diagram(db_name):
    # ER diyagramı oluşturulur
    diagram = Digraph('ER_Diagram')

    # Veritabanındaki tabloların listesini al
    tables = get_tables(db_name)

    # Tabloları diagrama ekler
    for table in tables:
        # Tablo adını ve sütun bilgilerini birleştir
        table_info = f"{table}\n"
        columns = get_columns_for_table(table)
        for column in columns:
            table_info += f"{column['Field']}: {column['Type']}\n"
        diagram.node(table, label=table_info, shape='box')

    # İlişkiyi sadece bir yönde ekler
    added_relations = set()  # Eklenen ilişkileri tutmak için bir küme
    for table1 in tables:
        columns1 = get_columns_for_table(table1)
        for table2 in tables:
            if table1 != table2:  # Aynı tablo üzerinde işlem yapılmaz
                columns2 = get_columns_for_table(table2)
                for column1 in columns1:
                    for column2 in columns2:
                        if column1['Field'] == column2['Field']:  # Ortak sütunlar bulunur
                            # İlişki daha önce eklenmediyse ekle
                            relation_key = tuple(sorted((table1, table2)))
                            if relation_key not in added_relations:
                                diagram.edge(table1, table2, label=column1['Field'])
                                added_relations.add(relation_key)

    # Diagram dosyası oluşturulur ve belirtilen dizine kaydedilir
    diagram_path = os.path.join('static', f'{db_name}_er_diagram')
    diagram.render(diagram_path, format='png', view=False)

    return f"{diagram_path}.png"



@app.route('/download_diagram/<database_name>')
@admin_required
def download_diagram(database_name):
    # ER diyagramı oluşturulur ve sunucuya kaydedilir
    diagram_path = create_er_diagram(database_name)
    
    # Oluşturulan ER diyagramı dosyası istemciye gönderilir
    return send_file(diagram_path, as_attachment=True)



def get_db_connection():
    global defaultDB
    try:
        # Set the database connection information
        db_name = defaultDB
        db_host = 'localhost'
        db_user = ''
        db_password = ''
        
        conn = pymysql.connect(cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4', host=db_host, user=db_user,
                               password=db_password, db=db_name)
        print("------------------DATABASE CONNECTION SUCCESSFUL--------------------------")
        return conn
    except pymysql.MySQLError as e:
        print("Database connection failed", e)
        return None

@app.route('/export_tables')
@admin_required
def export_tables():
    db_host = 'localhost'
    db_user = ''
    db_password = ''
    db_name = defaultDB
    
    # Generate the backup file name based on the selected database name
    backup_file_name = f"{db_name}_backup.sql"
    backup_file_path = os.path.join(app.root_path, backup_file_name)

    try:
        # Run mysqldump to create a backup
        with open(backup_file_path, 'w') as backup_file:
            subprocess.run(
                ['mysqldump', '-h', db_host, '-u', db_user, f'--password={db_password}', db_name],
                stdout=backup_file,
                check=True
            )

        return send_file(backup_file_path, as_attachment=True, download_name=backup_file_name, mimetype='application/sql')

    except subprocess.CalledProcessError as e:
        print("Error exporting database:", e)
        return Response("Error exporting database", status=500)


def close_db_connection(conn):
    if conn:
        conn.close()
        print("------------------DATABASE CONNECTION CLOSED--------------------------")



def get_tables(db_name):
    """
    Tabloları getirir.

    Args:
    db_name (str): Veritabanı adı.

    Returns:
    list: Tablo adlarını içeren liste
    """
    conn = get_db_connection()

    tables = []

    try:
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables_result = cursor.fetchall()

            for table in tables_result:
                tables.append(table[list(table.keys())[0]])  # İlk sütunu alır

    except Exception as e:
        print("Tabloları alma hatası:", e)
    finally:
        conn.close()
    print(tables)
    return tables

def get_columns_for_table(table_name):
    conn = get_db_connection()  # Get the connection
    cursor = conn.cursor()
    cursor.execute(f"DESCRIBE {table_name}")
    columns = cursor.fetchall()
    close_db_connection(conn)
    return columns




@app.route('/database', methods=['GET', 'POST'])
@admin_required
def database():
    if request.method == 'GET':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES;")
        databases = cursor.fetchall()
        cursor.close()
        close_db_connection(conn)
        return render_template('database.html', databases=databases)
    elif request.method == 'POST':
        global defaultDB
        if 'delete_database' in request.form:
            database_to_delete = request.form['delete_database']
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(f"DROP DATABASE {database_to_delete};")
            conn.commit()
            cursor.close()
            close_db_connection(conn)
            flash(f"Database '{database_to_delete}' successfully deleted.", "success")
            return redirect(url_for('database'))
        else:
            selected_database = request.form['selected_database']
            conn = get_db_connection()
            cursor = conn.cursor()
            query = f"USE {selected_database};"
            cursor.execute(query)
            databases = cursor.fetchall()
            cursor.execute("SHOW DATABASES;")
            databases = cursor.fetchall()
            cursor.close()
            defaultDB = selected_database
            close_db_connection(conn)
            return render_template('database.html', databases=databases)

@app.route('/create_database', methods=['POST'])
@admin_required
def create_database():
    new_database_name = request.form['new_database']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE {new_database_name}")
    conn.commit()
    cursor.execute("SHOW DATABASES;")
    databases=cursor.fetchall()
    cursor.close()
    close_db_connection(conn)
    return render_template('database.html',databases=databases)

@app.route('/add_user', methods=['POST'])
@admin_required
def add_user():
    username = request.form['username']
    password = request.form['password']
    conn = get_db_connection()
    cursor = conn.cursor()
    query = f"CREATE USER '{username}'@'localhost' IDENTIFIED BY '{password}';"
    cursor.execute(query)
    conn.commit()  # 'commit' metodu kullanıldı
    cursor.close()
    conn.close()  # Bağlantıyı kapatmayı unutma
    return redirect(url_for('user'))

@app.route('/delete_user/<string:username>', methods=['POST'])
@admin_required
def delete_user(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = f"DROP USER '{username}'@'localhost';"  # Kullanıcı adını doğru şekilde kullan
    cursor.execute(query)
    conn.commit()  # 'commit' metodu kullanıldı
    cursor.close()
    conn.close()  # Bağlantıyı kapatmayı unutma
    return redirect(url_for('user'))

@app.route('/user')
@admin_required
def user():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT User, Host FROM mysql.user;")
    users = cursor.fetchall()
    cursor.execute("SHOW DATABASES;")
    databases = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('user.html', users=users, databases=databases)

@app.route('/')
@admin_required
def index():

    return render_template('login.html')


@app.route('/grant_permissions', methods=['POST'])
@admin_required
def grant_permissions():
    username = request.form['username']
    database = request.form['database']
    select_permission = 'SELECT' if request.form.get('select') else ''
    insert_permission = 'INSERT' if request.form.get('insert') else ''
    update_permission = 'UPDATE' if request.form.get('update') else ''
    permissions = ', '.join(filter(None, [select_permission, insert_permission, update_permission]))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    query = f"GRANT {permissions} ON {database}.* TO '{username}'@'localhost';"
    cursor.execute(query)
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('user'))

@app.route('/change_password', methods=['POST'])
@admin_required
def change_password():
    username = request.form['username']
    new_password = request.form['new_password']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    query = f"ALTER USER '{username}'@'localhost' IDENTIFIED BY '{new_password}';"
    cursor.execute(query)
    conn.commit()
    cursor.close()
    conn.close()
    
    return redirect(url_for('user'))

@app.route('/show_tables')
@admin_required
def show_tables():

    conn = get_db_connection()  # Get the connection
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    table_info = {}
    database_name = conn.db.decode() if isinstance(conn.db, bytes) else conn.db
    for table in tables:
        table_name = table['Tables_in_' + conn.db] if isinstance(conn.db, str) else table['Tables_in_' + conn.db.decode()]
        columns = get_columns_for_table(table_name)
        table_info[table_name] = columns
    cursor.close()
    close_db_connection(conn)
    return render_template('show_tables.html', table_info=table_info, database_name=database_name )

@app.route('/establish_relationships', methods=['GET', 'POST'])
@admin_required
def establish_relationships():
    if request.method == 'POST':
        primary_table = request.form['primary_table']
        foreign_table = request.form['foreign_table']
        foreign_column = request.form['foreign_column']
        primary_column = request.form['primary_column']

        connection = get_db_connection()
        cursor = connection.cursor()

        query = f"ALTER TABLE {foreign_table} ADD CONSTRAINT fk_{foreign_table}_{primary_table} FOREIGN KEY ({foreign_column}) REFERENCES {primary_table}({primary_column})"
        
        cursor.execute(query)
        connection.commit()

        cursor.close()
        connection.close()

        return f"<script>alert('başarılı');</script>"



    conn = get_db_connection()  # Get the connection
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()

    table_info = {}


    for table in tables:
        table_name = table['Tables_in_' + conn.db] if isinstance(conn.db, str) else table['Tables_in_' + conn.db.decode()]


        columns = get_columns_for_table(table_name)
        table_info[table_name] = columns

    cursor.close()
    close_db_connection(conn)
    return render_template('establish_relationships.html',table_info=table_info)

@app.route('/delete_table/<table_name>')
@admin_required
def delete_table(table_name):
    conn = get_db_connection()  # Get the connection
    cursor = conn.cursor()
    try:
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        conn.commit()
    except Exception as e:
        return f" ERROR OCCURED :  {str(e)}"
    finally:
        cursor.close()
        close_db_connection(conn)
    return redirect(url_for('show_tables'))

@app.route('/add_table', methods=['GET', 'POST'])
@admin_required
def add_table():
    if request.method == 'GET':
        return render_template('add_table.html')
    elif request.method == 'POST':
        table_name = request.form['table_name']
        conn = get_db_connection()  # Get the connection
        cursor = conn.cursor()
        try:
            create_table_query=f"CREATE TABLE {table_name} ({table_name}_id INT AUTO_INCREMENT PRIMARY KEY);"
            cursor.execute(create_table_query)
            conn.commit()
        except Exception as e:
            print("Error creating table:", e)
            conn.rollback()
        finally:
            cursor.close()
            close_db_connection(conn)

        return redirect(url_for('show_tables'))

@app.route('/edit_table_name/<old_table_name>', methods=['GET', 'POST'])
@admin_required
def edit_table_name(old_table_name):
    if request.method == 'GET':
        return render_template('edit_table_name.html', old_table_name=old_table_name)
    elif request.method == 'POST':
        edited_table_name = request.form['edited_table_name']
        
        conn = get_db_connection()  # Get the connection
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"ALTER TABLE {old_table_name} RENAME TO {edited_table_name}")
            conn.commit()
            flash('Table name updated successfully!', 'success')
        except Exception as e:
            print("Error updating table name:", e)
            conn.rollback()
            flash('Error updating table name!', 'error')
        finally:
            cursor.close()
            close_db_connection(conn)

        return redirect(url_for('show_tables'))

@app.route('/delete_column/<table_name>/<column_name>', methods=['POST'])
@admin_required
def delete_column(table_name, column_name):
    if request.method == 'POST':
        conn = get_db_connection()  # Get the connection
        cursor = conn.cursor()

        try:
            cursor.execute(f"ALTER TABLE {table_name} DROP COLUMN {column_name}")
            conn.commit()
            flash('Column deleted successfully!', 'success')
        except Exception as e:
            print("Error deleting column:", e)
            conn.rollback()
            flash('Error deleting column!', 'error')
        finally:
            cursor.close()
            close_db_connection(conn)

        return redirect(url_for('show_tables'))

@app.route('/edit_column/<table_name>/<column_name>', methods=['GET', 'POST'])
@admin_required
def edit_column(table_name, column_name):
    if request.method == 'GET':
        data_types = ['INT', 'VARCHAR(255)', 'DATE', 'BOOLEAN', 'TEXT', 'DATETIME', 'FLOAT', 'DOUBLE', 'DECIMAL', 'ENUM', 'SET']

        return render_template('edit_column.html', table_name=table_name, column_name=column_name,data_types=data_types)
    elif request.method == 'POST':
        new_column_name = request.form['new_column_name']
        data_type = request.form['data_type']
        
        # Sütun güncelleme işlemleri
        conn = get_db_connection()  # Veritabanı bağlantısını al
        cursor = conn.cursor()

        try:
            cursor.execute(f"ALTER TABLE {table_name} CHANGE {column_name} {new_column_name} {data_type}")
            conn.commit()
            flash('Column updated successfully!', 'success')  # Başarılı mesajı göstermek için flash kullanımı
        except Exception as e:
            print("Error updating column:", e)
            conn.rollback()
            flash('Error updating column!', 'error')  # Hata durumunda hata mesajı göstermek için flash kullanımı
        finally:
            cursor.close()
            close_db_connection(conn)

        return redirect(url_for('show_tables'))

@app.route('/add_column/<table_name>', methods=['GET', 'POST'])
@admin_required
def add_column(table_name):
    if request.method == 'POST':
        new_column_name = request.form['column_name']
        data_type = request.form['data_type']

        conn = get_db_connection()  # Get the connection
        cursor = conn.cursor()
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {new_column_name} {data_type}")
        conn.commit()
        cursor.close()
        close_db_connection(conn)

        return redirect(url_for('show_tables'))  # Buradaki endpoint adı doğru olmalı

    # Get column types dynamically here (for example purposes, use predefined types)
    data_types = ['INT', 'VARCHAR(255)', 'DATE', 'BOOLEAN', 'TEXT', 'DATETIME', 'FLOAT', 'DOUBLE', 'DECIMAL', 'ENUM', 'SET']


    return render_template('add_column.html', table_name=table_name, data_types=data_types)

@app.route('/view_table/<table_name>')
@admin_required
def view_table(table_name):
    conn = get_db_connection()  # Get the connection
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    columns = [desc[0] for desc in cursor.description]  # Column names
    rows = cursor.fetchall()  # Rows
    conn.commit()
    cursor.close()
    close_db_connection(conn)

    return render_template('view_table.html', table_name=table_name, columns=columns, rows=rows)

@app.route('/add_row/<table_name>', methods=['GET', 'POST'])
@admin_required
def add_row(table_name):
    conn = get_db_connection()
    columns = []  # Sütunları tutacak bir liste
    if request.method == 'POST':
        form_data = request.form.to_dict()

        conn = get_db_connection()
        cursor = conn.cursor()

        # Replace empty strings with None
        for key, value in form_data.items():
            if value == '':
                form_data[key] = None

        # Create the INSERT query dynamically
        columns = ', '.join(form_data.keys())
        values_template = ', '.join(['%s'] * len(form_data))
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({values_template})"

        try:
            cursor.execute(query, tuple(form_data.values()))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            close_db_connection(conn)
        
        flash('Row added successfully!', 'success')
        return redirect(url_for('view_table', table_name=table_name))

    if request.method == 'GET':
        cursor=conn.cursor() 
        cursor.execute(f"SHOW COLUMNS FROM {table_name}")
        columns_data = cursor.fetchall()
        columns = [column['Field'] for column in columns_data]

        foreign_rows = get_foreign_rows()  # Get foreign rows for foreign key columns

        conn.close()
        return render_template('add_row.html', table_name=table_name, columns=columns, foreign_rows=foreign_rows)

@app.route('/edit_row/<table_name>/<row_id>', methods=['GET', 'POST'])
@admin_required
def edit_row(table_name, row_id):
    conn = get_db_connection()

    if request.method == 'POST':
        form_data = request.form.to_dict()

        conn = get_db_connection()

        try:
            with conn.cursor() as cursor:
                update_values = ', '.join([f"{key} = %s" for key in form_data.keys()])
                sql = f"UPDATE {table_name} SET {update_values} WHERE {table_name}_id = %s"
                cursor.execute(sql, list(form_data.values()) + [row_id])
                conn.commit()
                print("Row updated successfully.")

        except Exception as e:
            print(f"Error updating row in {table_name}: {e}")
        finally:
            conn.close()
        
        flash('Satır başarıyla güncellendi!', 'success')
        return redirect(url_for('view_table', table_name=table_name))

    columns = []  # Sütunları tutacak bir liste
    row_data = {}  # Satır verilerini tutacak bir sözlük
    if conn:
        try:
            with conn.cursor() as cursor:
                # Seçilen tablonun sütunlarını al
                cursor.execute(f"SHOW COLUMNS FROM {table_name}")
                columns_data = cursor.fetchall()
                columns = [column['Field'] for column in columns_data]

                # Seçilen satırın mevcut verilerini al
                cursor.execute(f"SELECT * FROM {table_name} WHERE {table_name}_id = %s", (row_id,))
                row_data = cursor.fetchone()

        except Exception as e:
            print("Veri alınamadı:", e)
        finally:
            conn.close()

    return render_template('edit_row.html', table_name=table_name, columns=columns, row_data=row_data)

@app.route('/delete_row/<table_name>/<row_id>', methods=['POST'])
@admin_required
def delete_row(table_name, row_id):
    conn = get_db_connection()

    try:
        with conn.cursor() as cursor:
            # Belirtilen satırı sil
            cursor.execute(f"DELETE FROM {table_name} WHERE {table_name}_id = %s", (row_id,))
            conn.commit()
    except Exception as e:
        print(f"Error while deleting row: {e}")
    finally:
        conn.close()

    flash('Row deleted successfully!', 'success')
    return redirect(url_for('view_table', table_name=table_name))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == 'admin' and password == 'admin':
            session['admin_logged_in'] = True
            flash('Başarıyla giriş yaptınız!', 'success')
            return redirect(url_for('database'))
        else:
            flash('Geçersiz kullanıcı adı veya şifre!', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)  # Oturumu sonlandır
    flash('Başarıyla çıkış yaptınız.', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
