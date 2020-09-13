from configparser import ConfigParser
import psycopg2

def config(filename='database.ini', section='postgresql'):
    """
    recovers configuration data for the DB
    """
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
    """
    Connect to the PostgreSQL database server
    """
    conn = None
    try:
        # read connection parameters
        params = config()

        # connect to the PostgreSQL server
        print('Connecting to the PostgreSQL database...')
        conn = psycopg2.connect(**params)
        cur = conn.cursor()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    return conn, cur

def insert_image(file_name, user_email, display_name):
    """ insert a new image path into the images table """
    sql = """
    INSERT INTO images (
        file_name,
        user_email,
        display_name
    ) VALUES (
        %s,
        %s,
        %s
    )
    RETURNING id;
    """
    conn = None
    try:
        conn, cur = get_db_connection()
        # execute the INSERT statement
        cur.execute(sql, (file_name, user_email, display_name,))
        image_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return image_id
    except (Exception, psycopg2.DatabaseError) as error:
        print(f'Error in insert_image: {error}')
        return False
    finally:
        if conn is not None:
            conn.close()

def get_images_for_list(user_email=None):
    """
    Recovers the image data needed to hydrate the list view. If the user_email param is passed, 
    will only get the ones for the passed user
    """
    try:
        conn, cur = get_db_connection()
        if user_email is None:
            sql = """
            SELECT
                id,
                display_name
            FROM images
            WHERE is_reported IS FALSE;
            """
            cur.execute(sql)
        else:
            sql = """
            SELECT 
                id,
                display_name 
            FROM images
            WHERE user_email=%s
            AND is_reported IS FALSE;
            """
            cur.execute(sql, (user_email,))
        rows = cur.fetchall()
        image_list = [{'id': row[0], 'fileName': row[1]} for row in rows]
        cur.close()
        return image_list
    except (Exception, psycopg2.DatabaseError) as error:
        print(f'Error in get_all_images_initial_data: {error}')
        return False
    finally:
        if conn is not None:
            conn.close()


def get_image_by_id(image_id):
    """
    Gets data needed for the proper display of a single file
    """
    file_name = None
    file_creator = None
    sql = """
    SELECT
        display_name,
        user_email
    FROM images
    WHERE id = %s
    AND is_reported IS FALSE;
    """
    try:
        conn, cur = get_db_connection()
        cur.execute(sql, (image_id,))
        rows = cur.fetchall()
        # print("The number of images: ", cur.rowcount)
        for row in rows:
            if file_name is None:
                file_name = row[0]
            if file_creator is None:
                file_creator = row[1]
            # print(row)
        cur.close()
        return file_name, file_creator
    except (Exception, psycopg2.DatabaseError) as error:
        print(f'Error in get_image_by_id: {error}')
        return False
    finally:
        if conn is not None:
            conn.close()

def delete_image(image_id):
    """
    Deletes information in the database for a single file, then returns the file's name so the file itself can be deleted
    """
    sql = "DELETE FROM images WHERE id = %s RETURNING file_name;"
    try:
        conn, cur = get_db_connection()
        cur.execute(sql, (image_id,))
        conn.commit()
        file_name = cur.fetchone()[0]
        cur.close()
        return file_name
    except (Exception, psycopg2.DatabaseError) as error:
        print(f'Error in get_user_initialization_data: {error}')
        return False
    finally:
        if conn is not None:
            conn.close()

def report_image(image_id):
    """
    Marks an images as reported, which will prevent it from appearing in get queries
    """
    sql = """
    UPDATE images
    SET is_reported = TRUE
    WHERE id = %s
    """
    try:
        conn, cur = get_db_connection()
        cur.execute(sql, (image_id,))
        conn.commit()
        cur.close()
        return True
    except (Exception, psycopg2.DatabaseError) as error:
        print(f'Error in get_user_initialization_data: {error}')
        return False
    finally:
        if conn is not None:
            conn.close()
