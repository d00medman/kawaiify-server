import os
import psycopg2

def get_db_connection():
    """
    Connect to the PostgreSQL database server
    """
    conn = None
    try:
        # connect to the PostgreSQL server
        print('Connecting to the PostgreSQL database...')
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME', 'steg'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', ''),
            host=os.getenv('DB_HOST', 'localhost')
        )
        cur = conn.cursor()
    except (Exception, psycopg2.DatabaseError) as error:
        print(f'Error in recovering DB connection: {error}')
    return conn, cur

def insert_image(file_name, user_email, display_name, cloud_url):
    """ insert a new image path into the images table """
    sql = """
    INSERT INTO images (
        file_name,
        user_email,
        display_name,
        cloud_url
    ) VALUES (
        %s,
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
        cur.execute(sql, (file_name, user_email, display_name, cloud_url))
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
    def create_user_poco(row):
        return {
            'id': row[0],
            'cloudUrl': row[1],
            'displayName': row[2],
            'creatorEmail': row[3],
            'createdAt': row[4]
        }
    conn = None
    try:
        conn, cur = get_db_connection()
        if user_email is None:
            sql = """
            SELECT
                id,
                cloud_url,
                display_name,
                user_email,
                created_at
            FROM images
            WHERE is_reported IS FALSE;
            """
            cur.execute(sql)
        else:
            sql = """
            SELECT 
                id,
                cloud_url,
                display_name,
                user_email,
                created_at
            FROM images
            WHERE user_email=%s
            AND is_reported IS FALSE;
            """
            cur.execute(sql, (user_email,))
        rows = cur.fetchall()
        image_list = [create_user_poco(row) for row in rows]
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
    def single_image_poco(row):
        return {
            'fileName': row[0],
            'creatorEmail': row[1],
            'cloudUrl': row[2]
        }
    sql = """
    SELECT
        display_name,
        user_email,
        cloud_url
    FROM images
    WHERE id = %s
    AND is_reported IS FALSE;
    """
    conn = None
    try:
        conn, cur = get_db_connection()
        cur.execute(sql, (image_id,))
        row = cur.fetchall()[0]
        return single_image_poco(row)
    except (Exception, psycopg2.DatabaseError) as error:
        print(f'Error in get_image_by_id: {error}')
        return False
    finally:
        if conn is not None:
            conn.close()

def delete_image(image_id):
    """
    Deletes information in the database for a single file, then returns the file's name
    so the file itself can be deleted
    """
    sql = "DELETE FROM images WHERE id = %s RETURNING file_name;"
    conn = None
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
    conn = None
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
