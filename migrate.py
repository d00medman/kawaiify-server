import psycopg2

import db

def create_tables():
    """ create tables in the PostgreSQL database"""
    commands = (
        """ 
        DROP TABLE IF EXISTS users CASCADE;
        CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                name VARCHAR(255) NOT NULL
        )
        """,
        """
        DROP TABLE IF EXISTS images CASCADE;
        CREATE TABLE images (
            id SERIAL PRIMARY KEY,
            display_name VARCHAR(255) NOT NULL,
            file_name VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            creator_user_id INTEGER REFERENCES users(id),
            user_email VARCHAR(255),
            is_reported BOOLEAN DEFAULT FALSE
        );
        CREATE UNIQUE INDEX image_name_user ON images(file_name, user_email);
        """
        )
    conn = None
    try:
        # read the connection parameters
        params = db.config()
        # connect to the PostgreSQL server
        conn = psycopg2.connect(**params)
        cur = conn.cursor()
        # create table one by one
        for command in commands:
            cur.execute(command)
        # close communication with the PostgreSQL database server
        cur.close()
        # commit the changes
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)

if __name__ == '__main__':
    create_tables()