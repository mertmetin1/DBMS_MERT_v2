import pymysql

def get_db_connection():
    try:
        # Set the database connection information
        db_name = 'mysql'
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

def create_database(conn,dbname):
    try:
        # Create a cursor object to execute SQL queries
        cursor = conn.cursor()
        creadbqueery = "CREATE DATABASE IF NOT EXISTS "+dbname
        # Create the database if not exists
        cursor.execute(creadbqueery)
        usequerry = "USE "+dbname
        # Switch to the newly created database
        cursor.execute(usequerry)

        print("------------------DATABASE CREATED AND SWITCHED TO '"+dbname+"'--------------------------")

        # Commit the changes
        conn.commit()

        # Close the cursor
        cursor.close()

    except pymysql.MySQLError as e:
        print("Error creating database:", e)


# ...

def create_tables(conn):
    try:
        # Create a cursor object to execute SQL queries
        cursor = conn.cursor()

        # Create admin table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin (
                admin_id INT AUTO_INCREMENT PRIMARY KEY,
                admin_username VARCHAR(255),
                admin_password VARCHAR(255)
            )
        """)

        # Create customer table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customer (
                customer_id INT AUTO_INCREMENT PRIMARY KEY,
                customer_name VARCHAR(255),
                customer_surname VARCHAR(255),
                customer_age INT,
                customer_gender VARCHAR(255),
                customer_phone VARCHAR(255)
            )
        """)

        # Create vehicle table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vehicle (
                vehicle_id INT AUTO_INCREMENT PRIMARY KEY,
                plate VARCHAR(255),
                passenger_capacity INT,
                vehicle_km INT,
                maintain_km INT,
                employer VARCHAR(255),
                vehicle_type VARCHAR(255),
                next_maintain_date DATETIME,
                last_maintain_date DATETIME
            )
        """)

        # Create route table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS route (
                route_id INT AUTO_INCREMENT PRIMARY KEY,
                vehicle_id INT,
                time_of_journey TIME,
                start_station VARCHAR(255),
                arrival_station VARCHAR(255),
                price DECIMAL(10, 2),
                date_of_journey DATETIME,
                traveller_count INT,
                FOREIGN KEY (vehicle_id) REFERENCES vehicle(vehicle_id)
            )
        """)

        # Create ticket table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ticket (
                ticket_id INT AUTO_INCREMENT PRIMARY KEY,
                route_id INT,
                customer_id INT,
                seat_no INT,
                FOREIGN KEY (route_id) REFERENCES route(route_id),
                FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
            )
        """)

        # Create user table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user (
                user_id INT AUTO_INCREMENT PRIMARY KEY,
                customer_id INT,
                user_name VARCHAR(255),
                user_password VARCHAR(255),
                FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
            )
        """)

        print("------------------TABLES CREATED SUCCESSFULLY--------------------------")

        # Commit the changes
        conn.commit()

        # Close the cursor
        cursor.close()

    except pymysql.MySQLError as e:
        print("Error creating tables:", e)

# ...



def grant_permissions(conn):
    try:
        # Create a cursor object to execute SQL queries
        cursor = conn.cursor()

        # Grant all privileges to the root user for the created database
        cursor.execute("GRANT ALL PRIVILEGES ON python_travel.* TO 'root'@'localhost' WITH GRANT OPTION")

        # Flush privileges to apply changes
        cursor.execute("FLUSH PRIVILEGES")

        print("------------------PERMISSIONS GRANTED SUCCESSFULLY--------------------------")

        # Commit the changes
        conn.commit()

        # Close the cursor
        cursor.close()

    except pymysql.MySQLError as e:
        print("Error granting permissions:", e)

# Get a database connection
conn = get_db_connection()

if conn:
    # Create the database
    create_database(conn,"python_travel2")

    # Create tables
    create_tables(conn)

    # Grant permissions to the root user
    grant_permissions(conn)

    # Close the database connection
    conn.close()
