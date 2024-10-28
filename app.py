from flask import Flask, request, render_template, send_file, jsonify, redirect, url_for
import pandas as pd
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, String, Integer, Table, MetaData, DateTime, Boolean
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import hashlib
import cinando  # Import cinando.py for scraping functions
import shutil
from sqlalchemy import create_engine, inspect
from datetime import datetime
import pandas as pd

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
    auto_collect = Column(Boolean, default=False)
    email = Column(String)
    password = Column(String)


Base.metadata.create_all(engine)


def create_dynamic_table(table_name, df_columns):
    """
    Dynamically create or update a database table to include all columns from the DataFrame,
    including special_id and collected_at.
    """
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        if table_name not in existing_tables:
            columns = [Column('id', Integer, primary_key=True)]
            for col in df_columns:
                columns.append(Column(col, String))
            columns.append(Column('special_id', String))
            columns.append(Column('collected_at', DateTime))
            new_table = Table(table_name, metadata, *columns)
            metadata.create_all(engine)
            print(f"Table '{table_name}' created successfully.")
        else:
            existing_columns = [col['name'] for col in inspector.get_columns(table_name)]
            for col in df_columns:
                if col not in existing_columns:
                    with engine.connect() as conn:
                        conn.execute(f'ALTER TABLE {table_name} ADD COLUMN "{col}" TEXT')
                    print(f"Column '{col}' added to table '{table_name}'.")
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
    email = request.form['email']  # Add email input
    password = request.form['password']  # Add password input
    rescrape = request.form.get('rescrape', 'false').lower() == 'true'
    auto_collect = request.form.get('auto_collect', 'false') == 'on'
    existing_entry = session.query(Directory).filter_by(url=url).first()

    if existing_entry and rescrape:
        table_name = existing_entry.table_name
        csv_path = f'{table_name}.csv'
        try:
            print(f"Rescraping URL: {url}")
            # Step 1: Use api_login_and_scrape to fetch company details
            cinando.api_login_and_scrape(url, email, password)  # Fetch data and save to 'details'

            # Step 2: Extract bio and image from fetched HTML files
            cinando.extract_bio_and_image_from_html('details', f'{table_name}.csv')
            df = pd.read_csv(f'{table_name}.csv')
            df = process_dataframe(df, table_name)

            # Save the data to a CSV file
            df.to_csv(csv_path, mode='w', index=False)

            # Delete the 'details' directory after generating CSV
            shutil.rmtree('details', ignore_errors=True)

            return send_file(csv_path, as_attachment=True)
        except Exception as e:
            session.rollback()
            return jsonify({"error": str(e)})

    if existing_entry and not rescrape:
        one_week_ago = datetime.now() - timedelta(weeks=1)
        if existing_entry.last_collected > one_week_ago:
            return render_template('index.html', prompt_existing_data=True,
                                   last_collected=existing_entry.last_collected, table_name=existing_entry.table_name)

    table_name = existing_entry.table_name if existing_entry else generate_table_name(url)
    csv_path = f'{table_name}.csv'

    try:
        print(f"Scraping URL: {url}")
        # Step 1: Use api_login_and_scrape to fetch company details
        cinando.api_login_and_scrape(url, email, password)  # Fetch data and save to 'details'

        # Step 2: Extract bio and image from fetched HTML files
        cinando.extract_bio_and_image_from_html('details', f'{table_name}.csv')
        df = pd.read_csv(f'{table_name}.csv')
        df = process_dataframe(df, table_name)

        # Save the data to a CSV file
        df.to_csv(csv_path, mode='w', index=False)

        # **Insert or update the URL information in the database**
        if existing_entry:
            existing_entry.last_collected = datetime.now()
            existing_entry.auto_collect = auto_collect
            session.commit()
        else:
            new_entry = Directory(
                url=url,
                table_name=table_name,
                last_collected=datetime.now(),
                special_id=f"{table_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                email=email,
                password=password,
                auto_collect=auto_collect
            )
            session.add(new_entry)
            session.commit()

        # Delete the 'details' directory after generating CSV
        shutil.rmtree('details', ignore_errors=True)

        return send_file(csv_path, as_attachment=True)
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)})


def process_dataframe(df, table_name):
    """
    Process the DataFrame by adding a special_id and collected_at columns, storing in the database.
    It checks for new and modified rows.
    """
    # Convert list-type columns to string (for uniform storage in the database)
    for col in df.columns:
        df[col] = df[col].apply(lambda x: str(x) if isinstance(x, list) else x)

    # Generate a unique identifier for this collection
    special_id = f"{table_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    df['special_id'] = special_id
    df['collected_at'] = datetime.now()

    # Fetch existing data to identify new or modified rows
    existing_data = pd.read_sql_table(table_name, con=engine) if inspect(engine).has_table(
        table_name) else pd.DataFrame()

    # Find new rows
    if not existing_data.empty:
        merged_data = df.merge(existing_data, on='id', how='left', suffixes=('', '_existing'), indicator=True)
        new_rows = merged_data[merged_data['_merge'] == 'left_only'].drop(columns=existing_data.columns)
        modified_rows = merged_data[(merged_data['_merge'] == 'both') &
                                    (merged_data.apply(lambda row: any(row[col] != row[col + '_existing']
                                                                       for col in df.columns if col != 'id'), axis=1))]
    else:
        # If no existing data, all rows are new
        new_rows = df.copy()
        modified_rows = pd.DataFrame()

    # Mark status of rows
    if not new_rows.empty:
        new_rows['status'] = 'new'
        new_rows.to_sql(table_name, con=engine, index=False, if_exists='append')

    if not modified_rows.empty:
        modified_rows['status'] = 'modified'
        modified_rows.to_sql(table_name, con=engine, index=False, if_exists='append')

    # Save the latest collected data
    df.to_sql(table_name, con=engine, index=False, if_exists='append')

    return df


@app.route('/download_latest/<table_name>', methods=['GET'])
def download_latest(table_name):
    try:
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


def auto_collect_data():
    links_to_collect = session.query(Directory).filter_by(auto_collect=True).all()
    for entry in links_to_collect:
        try:
            print(f"Automatically scraping URL: {entry.url}")
            cinando.api_login_and_scrape(entry.url, entry.email, entry.password)
            cinando.extract_bio_and_image_from_html('details', f'{entry.table_name}.csv')
            df = pd.read_csv(f'{entry.table_name}.csv')
            process_dataframe(df, entry.table_name)
            entry.last_collected = datetime.now()
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error in auto_collect_data for {entry.url}: {e}")


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'auto_collect_data':
        auto_collect_data()
    else:
        print("Starting Flask app...")
        app.run(debug=True)
