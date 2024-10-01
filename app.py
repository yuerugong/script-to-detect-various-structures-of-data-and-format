from flask import Flask, request, render_template, send_file, jsonify, redirect, url_for
import pandas as pd
import main2
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, String, Integer, Table, MetaData, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import hashlib
from sqlalchemy import inspect


app = Flask(__name__)

Base = declarative_base()
engine = create_engine('sqlite:///scraper.db')
Session = sessionmaker(bind=engine)
session = Session()
metadata = MetaData(bind=engine)
metadata.bind = engine

class Directory(Base):
    __tablename__ = 'directory'
    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True)
    table_name = Column(String)
    last_collected = Column(DateTime)
    special_id = Column(String)


Base.metadata.create_all(engine)


def create_dynamic_table(table_name, df_columns):
    """
    Dynamically create or update a database table to include all columns from the DataFrame,
    including special_id and collected_at.
    """
    try:
        # Reflect the current state of the database
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        if table_name not in existing_tables:
            # If the table does not exist, create it with all columns and additional fields
            columns = [Column('id', Integer, primary_key=True)]
            for col in df_columns:
                columns.append(Column(col, String))
            # Add fixed columns special_id and collected_at
            columns.append(Column('special_id', String))
            columns.append(Column('collected_at', DateTime))
            new_table = Table(table_name, metadata, *columns)
            metadata.create_all(engine)
            print(f"Table '{table_name}' created successfully.")
        else:
            # If the table exists, check if each column needs to be added
            existing_columns = [col['name'] for col in inspector.get_columns(table_name)]

            # Add missing columns to the existing table
            for col in df_columns:
                if col not in existing_columns:
                    with engine.connect() as conn:
                        conn.execute(f'ALTER TABLE {table_name} ADD COLUMN "{col}" TEXT')
                    print(f"Column '{col}' added to table '{table_name}'.")

            # Ensure 'special_id' and 'collected_at' columns exist
            if 'special_id' not in existing_columns:
                with engine.connect() as conn:
                    conn.execute(f'ALTER TABLE {table_name} ADD COLUMN "special_id" TEXT')
                print(f"Column 'special_id' added to table '{table_name}'.")

            if 'collected_at' not in existing_columns:
                with engine.connect() as conn:
                    conn.execute(f'ALTER TABLE {table_name} ADD COLUMN "collected_at" DATETIME')
                print(f"Column 'collected_at' added to table '{table_name}'.")

    except Exception as e:
        print(f"Error in create_dynamic_table: {e}")



def generate_table_name(url):
    return f"data_{hashlib.md5(url.encode()).hexdigest()}"


@app.route('/')
def index():
    tables_info = session.query(Directory).all()
    return render_template('index.html', tables_info=tables_info)


@app.route('/scrape', methods=['GET', 'POST'])
def scrape():
    if request.method == 'GET':
        return redirect(url_for('index'))

    url = request.form['url']
    class_name = request.form.get('class_name')
    rescrape = request.form.get('rescrape', 'false').lower() == 'true'
    existing_entry = session.query(Directory).filter_by(url=url).first()

    if existing_entry and rescrape:
        table_name = existing_entry.table_name
        csv_path = f'{table_name}.csv'
        try:
            print(f"Rescraping URL: {url}")
            data = main2.scrape_with_fallback(url, class_name)

            if data:
                print("Data collected successfully")
                if isinstance(data, (list, dict)):
                    df = pd.DataFrame(data)
                    for col in df.columns:
                        df[col] = df[col].apply(lambda x: str(x) if isinstance(x, list) else x)

                    create_dynamic_table(table_name, df.columns)

                    special_id = f"{table_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    df['special_id'] = special_id
                    df['collected_at'] = datetime.now()

                    df.to_sql(table_name, con=engine, index=False, if_exists='append')

                    existing_entry.last_collected = datetime.now()
                    existing_entry.special_id = special_id
                    session.commit()

                    # save data to CSV file
                    df.drop(['special_id', 'collected_at'], axis=1, inplace=True)
                    df.to_csv(csv_path, mode='w', index=False)
                    return send_file(csv_path, as_attachment=True)
                else:
                    return jsonify({"error": "Collected data is not in a proper format for a DataFrame."})
            else:
                return render_template('index.html', error="Failed to collect data. Please provide a class name if required.")
        except Exception as e:
            session.rollback()
            return jsonify({"error": str(e)})

    if existing_entry and not rescrape:
        one_week_ago = datetime.now() - timedelta(weeks=1)
        if existing_entry.last_collected > one_week_ago:
            return render_template('index.html', prompt_existing_data=True, last_collected=existing_entry.last_collected, table_name=existing_entry.table_name)

    table_name = existing_entry.table_name if existing_entry else generate_table_name(url)
    csv_path = f'{table_name}.csv'

    try:
        print(f"Scraping URL: {url}")
        data = main2.scrape_with_fallback(url, class_name)

        if data:
            print("Data collected successfully")
            if isinstance(data, (list, dict)):
                df = pd.DataFrame(data)
                for col in df.columns:
                    df[col] = df[col].apply(lambda x: str(x) if isinstance(x, list) else x)

                create_dynamic_table(table_name, df.columns)

                special_id = f"{table_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                df['special_id'] = special_id
                df['collected_at'] = datetime.now()

                df.to_sql(table_name, con=engine, index=False, if_exists='append')

                if existing_entry:
                    existing_entry.last_collected = datetime.now()
                    existing_entry.special_id = special_id
                else:
                    new_entry = Directory(url=url, table_name=table_name, last_collected=datetime.now(), special_id=special_id)
                    session.add(new_entry)
                session.commit()

                df.drop(['special_id', 'collected_at'], axis=1, inplace=True)
                df.to_csv(csv_path, mode='w', index=False)
                return send_file(csv_path, as_attachment=True)
            else:
                return jsonify({"error": "Collected data is not in a proper format for a DataFrame."})
        else:
            return render_template('index.html', error="Failed to collect data. Please provide a class name if required.")
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)})


@app.route('/download_latest/<table_name>', methods=['GET'])
def download_latest(table_name):
    try:
        # Read the latest data in the database
        df = pd.read_sql_table(table_name, con=engine)
        latest_csv_path = f'{table_name}_latest.csv'
        df.to_csv(latest_csv_path, mode='w', index=False)
        return send_file(latest_csv_path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/view_table/<table_name>', methods=['GET'])
def view_table(table_name):
    try:
        df = pd.read_sql_table(table_name, con=engine)
        table_html = df.to_html(classes='data')
        return render_template('view_table.html', table_html=table_html)
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/delete_table/<table_name>', methods=['GET'])
def delete_table(table_name):
    try:
        metadata.reflect()
        if table_name in metadata.tables:
            table_to_delete = metadata.tables[table_name]
            table_to_delete.drop(engine)
            print(f"Table {table_name} deleted successfully.")

        session.query(Directory).filter(Directory.table_name == table_name).delete()
        session.commit()

        return redirect(url_for('index'))
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)})


if __name__ == '__main__':
    print("Starting Flask app...")
    app.run(debug=True)