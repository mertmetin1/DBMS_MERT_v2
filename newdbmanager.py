from flask import Flask, flash, render_template, request, redirect, session, url_for
import pymysql

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Session security key

defaulDB="python_travel"

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        
        return render_template('index.html')
    elif request.method == 'POST':
        return render_template('index.html')



def get_db_connection():
    try:
        # Set the database connection information
        db_name = defaulDB
        db_host = 'localhost'
        db_user = 'root'
        db_password = '1324'
        
        conn = pymysql.connect(cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4', host=db_host, user=db_user,
                               password=db_password, db=db_name)
        print("------------------DATABASE CONNECTION SUCCESSFUL--------------------------")
        return conn
    except pymysql.MySQLError as e:
        print("Database connection failed", e)
        return None

def close_db_connection(conn):
    if conn:
        conn.close()
        print("------------------DATABASE CONNECTION CLOSED--------------------------")

def execute_query(query):
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute(query)
                conn.commit()
                print("Query executed successfully")
        except pymysql.MySQLError as e:
            print("Query execution failed", e)
        finally:
            close_db_connection(conn)

def get_columns_for_table(table_name):
    conn = get_db_connection()  # Get the connection
    cursor = conn.cursor()
    cursor.execute(f"DESCRIBE {table_name}")
    columns = cursor.fetchall()
    close_db_connection(conn)
    return columns

def create_table(table_name, columns):
    conn = get_db_connection()  # Get the connection
    cursor = conn.cursor()
    
    try:
        create_table_query = f"CREATE TABLE {table_name} (id INT AUTO_INCREMENT PRIMARY KEY"

        for column in columns:
            create_table_query += f", {column} VARCHAR(255)"  # Example uses VARCHAR, you can change the data type.

        create_table_query += ")"
        cursor.execute(create_table_query)
        conn.commit()
    except Exception as e:
        print("Error creating table:", e)
        conn.rollback()
    finally:
        cursor.close()
        close_db_connection(conn)

def add_column(table_name, new_column_name, data_type):
    conn = get_db_connection()  # Get the connection
    cursor = conn.cursor()
    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {new_column_name} {data_type}")
    conn.commit()
    cursor.close()
    close_db_connection(conn)
    
def delete_table(table_name):
    conn = get_db_connection()  # Get the connection
    cursor = conn.cursor()
    try:
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        conn.commit()
    except Exception as e:
        return f"Error occurred: {str(e)}"
    finally:
        cursor.close()
        close_db_connection(conn)

@app.route('/add_table', methods=['GET', 'POST'])
def add_table():
    if request.method == 'GET':
        return render_template('add_table.html')
    elif request.method == 'POST':
        table_name = request.form['table_name']
        columns = request.form.getlist('column_name')

        create_table(table_name, columns)

        return redirect(url_for('show_tables'))

@app.route('/add_column/<table_name>', methods=['GET', 'POST'])
def add_column_route(table_name):
    if request.method == 'POST':
        new_column_name = request.form['column_name']
        data_type = request.form['data_type']

        add_column(table_name, new_column_name, data_type)

        return redirect(url_for('show_tables'))  # Buradaki endpoint adı doğru olmalı

    # Get column types dynamically here (for example purposes, use predefined types)
    data_types = ['INT', 'VARCHAR(255)', 'DATE', 'BOOLEAN']

    return render_template('add_column.html', table_name=table_name, data_types=data_types)

@app.route('/view_table/<table_name>')
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

# Satır silme işlemi için route
@app.route('/delete_row/<table_name>', methods=['POST'])
def delete_row(table_name):
    try:
        conn = get_db_connection()  # Veritabanı bağlantısını al
        cursor = conn.cursor()
        
        primary_key_column = request.form['primary_key_column']
        primary_key_value = request.form['primary_key_value']
        
        sql = f"DELETE FROM {table_name} WHERE {primary_key_column} = %s"
        cursor.execute(sql, (primary_key_value,))
        conn.commit()
        cursor.close()
        close_db_connection(conn)
        
        return redirect(url_for('view_table', table_name=table_name))
    
    except Exception as e:
        error_message = f"Error occurred: {str(e)}"
        return render_template('error.html', error_message=error_message)

@app.route('/edit_row/<table_name>', methods=['POST'])
def edit_row(table_name):
    try:
        conn = get_db_connection()  # Veritabanı bağlantısını al
        cursor = conn.cursor()
        
        id = request.form['id']
        primary_key_column = request.form['primary_key_column']
        primary_key_value = request.form['primary_key_value']
        
        # Diğer düzenleme için gerekli olan sütunlar buraya eklenecek
        
        # Tablonun sütunlarını al
        cursor.execute(f"DESCRIBE {table_name}")
        columns = cursor.fetchall()
        
        # Güncellenecek sütunları al
        update_columns = []
        for column in columns:
            # İlk sütun ID olduğu için ve onu güncellemek istemiyoruz, onu dışarıda bırakıyoruz
            if column['Field'] != 'id':
                update_columns.append(column['Field'])
        
        # Sütunlara göre güncelleme sorgusu oluştur
        set_columns = ', '.join([f"{col} = %s" for col in update_columns])
        sql = f"UPDATE {table_name} SET {set_columns} WHERE id = %s"
        
        # Formdan gelen verileri al
        update_values = [request.form[col] for col in update_columns]
        update_values.append(id)  # ID değerini de ekle
        
        cursor.execute(sql, tuple(update_values))
        conn.commit()
        cursor.close()
        close_db_connection(conn)
        
        return redirect(url_for('view_table', table_name=table_name))
    
    except Exception as e:
        error_message = f"Error occurred: {str(e)}"
        return render_template('error.html', error_message=error_message)

@app.route('/add_row/<table_name>', methods=['GET', 'POST'])
def add_row(table_name):
    if request.method == 'GET':
        columns_info = get_columns_for_table(table_name)
        return render_template('add_row.html', table_name=table_name, columns=columns_info)
    elif request.method == 'POST':
        try:
            column_values = {}
            columns_info = get_columns_for_table(table_name)

            for column in columns_info:
                column_name = column['Field']
                # Veri tabanında auto increment özelliği olan sütunları ekleme sırasında dışarıda bırak
                if column_name != 'id' and 'auto_increment' not in column['Extra']:
                    value = request.form.get(column_name)
                    column_values[column_name] = value

            add_row_to_table(table_name, column_values)
            return redirect(url_for('view_table', table_name=table_name))
        except Exception as e:
            print("Error adding row:", e)
            # Hata durumunda geriye yönlendirme yapılabilir veya hata mesajı gösterilebilir.
            return "Error adding row to the table."

def add_row_to_table(table_name, column_values):
    conn = get_db_connection()  
    cursor = conn.cursor()
    columns_info = get_columns_for_table(table_name)

    try:
        column_values_filtered = {column['Field']: column_values[column['Field']] for column in columns_info if 'auto_increment' not in column['Extra']}
        columns_str = ', '.join(column_values_filtered.keys())
        values_str = ', '.join(['%s'] * len(column_values_filtered))
        query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str})"
        
        cursor.execute(query, tuple(column_values_filtered.values()))
        conn.commit()
    except Exception as e:
        print("Error adding data:", e)
        conn.rollback()
    finally:
        cursor.close()
        close_db_connection(conn)
        


@app.route('/delete_table/<table_name>', methods=['GET', 'POST'])
def delete_table_route(table_name):
    if request.method == 'GET':
        # Render the confirmation page
        return render_template('delete_table.html', table_name=table_name)
    elif request.method == 'POST':
        # Handle the form submission
        delete_table(table_name)
        return redirect(url_for('show_tables'))
    else:
        return "Invalid request method!"










# Add this route to your Flask app
@app.route('/set_database', methods=['POST'])
def set_database():
    selected_database = request.form.get('selected_database')

    if selected_database:
        # Update the database connection based on the selected database
        app.config['DB_NAME'] = selected_database

        # Redirect to the show_tables route
        return redirect(url_for('show_tables'))

    return "Invalid database selection"

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Basic check for admin credentials
        if username == 'admin' and password == 'admin':
            session['username'] = username  # Set session for admin
            return redirect(url_for('show_tables'))  # Redirect to show_tables route after login
        else:
            return render_template('login.html', error='Invalid credentials')

    return render_template('login.html', error=None)

# Logout route
@app.route('/logout')
def logout():
    session.pop('username', None)  # Remove username from session
    return redirect(url_for('login')) 

@app.route('/show_tables')
def show_tables():
    if 'username' not in session or session['username'] != 'admin':
        return redirect(url_for('login'))  # Redirect to login if not logged in as admin

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

    return render_template('show_tables.html', table_info=table_info, database_name=database_name)

@app.route('/edit_column/<table_name>/<column_name>', methods=['GET', 'POST'])
def edit_column(table_name, column_name):
    if request.method == 'GET':
        # Sütun düzenleme formunu göster
        return render_template('edit_column.html', table_name=table_name, column_name=column_name)
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

def get_foreign_keys_for_table(table_name):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    cursor.execute(f"SELECT COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE WHERE TABLE_NAME = %s AND CONSTRAINT_SCHEMA = %s AND REFERENCED_TABLE_NAME IS NOT NULL", (table_name, conn.db))
    
    foreign_keys = cursor.fetchall()
    cursor.close()
    close_db_connection(conn)
    
    return foreign_keys
def get_columns_for_table(table_name):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    cursor.execute(f"DESCRIBE {table_name}")
    columns = cursor.fetchall()
    
    foreign_keys = get_foreign_keys_for_table(table_name)  # Fetch foreign key info for the table

    # Include foreign key information in the columns dictionary
    for column in columns:
        column['Foreign Key Table'] = ''
        column['Foreign Key Column'] = ''
        for foreign_key in foreign_keys:
            if foreign_key['COLUMN_NAME'] == column['Field']:
                column['Foreign Key Table'] = foreign_key['REFERENCED_TABLE_NAME']
                column['Foreign Key Column'] = foreign_key['REFERENCED_COLUMN_NAME']

    cursor.close()
    close_db_connection(conn)

    return columns

@app.route('/delete_column/<table_name>/<column_name>', methods=['POST'])
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



















if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')