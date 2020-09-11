import psycopg2
from configparser import ConfigParser

def config(filename='database.ini', section='postgresql'):
    # create a parser
    parser = ConfigParser()
    # read config file
    parser.read(filename)

    # get section, default to postgresql
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))

    return db

def get_db_connection():
    """ Connect to the PostgreSQL database server """
    conn = None
    try:
        # read connection parameters
        params = config()

        # connect to the PostgreSQL server
        # print('Connecting to the PostgreSQL database...')
        conn = psycopg2.connect(**params)
        cur = conn.cursor()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    
    return conn, cur

def insert_image(file_name, user_email):
    """ insert a new image path into the images table """
    sql = """
    INSERT INTO images (
        file_name,
        user_email
    ) VALUES (
        %s,
        %s
    );
    """
    conn = None
    try:
        conn, cur = get_db_connection()
        # execute the INSERT statement
        cur.execute(sql, (file_name, user_email,))
        
        conn.commit()
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(f'Error in insert_image: {error}')
    finally:
        if conn is not None:
            conn.close()

def get_all_images_initial_data():
    conn = None
    image_id = None
    file_name = None
    max_image_id = None
    try:
        conn, cur = get_db_connection()
        cur.execute("SELECT id, file_name FROM images;")
        rows = cur.fetchall()
        # print("The number of images: ", cur.rowcount)
        for row in rows:
            if image_id is None:
                image_id = row[0]
            if file_name is None:
                file_name = row[1]
            max_image_id = row[0]
            # print(row)
        cur.close()
        return image_id, file_name, max_image_id
    except (Exception, psycopg2.DatabaseError) as error:
        print(f'Error in get_all_images_initial_data: {error}')
    finally:
        # print('hits finally')
        if conn is not None:
            conn.close()
    # print(f'max image id: {max_image_id}')
    

def get_image_by_id(image_id):
    file_name = None
    sql = """
    SELECT file_name
    FROM images
    WHERE id = %s
    """
    try:
        conn, cur = get_db_connection()
        cur.execute(sql, (image_id,))
        rows = cur.fetchall()
        # print("The number of images: ", cur.rowcount)
        for row in rows:
            if file_name is None:
                file_name = row[0]
            # print(row)
        cur.close()
        return file_name
    except (Exception, psycopg2.DatabaseError) as error:
        print(f'Error in get_image_by_id: {error}')
    finally:
        if conn is not None:
            conn.close()
    

def get_user_initialization_data(username):
    file_name = None
    image_id = None
    user_image_ids = []
    sql = """
    SELECT file_name, id
    FROM images
    WHERE user_email = %s
    """
    try:
        conn, cur = get_db_connection()
        cur.execute(sql, (username,))
        rows = cur.fetchall()
        # print("The number of images in intialize user data: ", cur.rowcount)
        for row in rows:
            if file_name is None:
                file_name = row[0]
            if image_id is None:
                image_id = row[1]
            user_image_ids.append(row[1])
            print(row)
        cur.close()
        print(user_image_ids)
        return image_id, file_name, user_image_ids
    except (Exception, psycopg2.DatabaseError) as error:
        print(f'Error in get_user_initialization_data: {error}')
    finally:
        if conn is not None:
            conn.close()
    

