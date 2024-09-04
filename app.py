from flask import Flask, request, render_template, send_file, jsonify, redirect, url_for
import pandas as pd
import main2
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, String, Integer, Table, MetaData, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

app = Flask(__name__)

Base = declarative_base()
engine = create_engine('sqlite:///scraper.db')
Session = sessionmaker(bind=engine)
session = Session()
metadata = MetaData(bind=engine)


class Directory(Base):
    __tablename__ = 'directory'
    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True)
    table_name = Column(String)
    last_collected = Column(DateTime)
    special_id = Column(String)


Base.metadata.create_all(engine)


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

                    special_id = f"{table_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    df['special_id'] = special_id
                    df['collected_at'] = datetime.now()

                    df.to_sql(table_name, con=engine, index=False, if_exists='append')

                    existing_entry.last_collected = datetime.now()
                    existing_entry.special_id = special_id
                    session.commit()

                    # save data to CSV file
                    df.to_csv(csv_path, mode='w', index=False)
                    return send_file(csv_path, as_attachment=True)
                else:
                    return jsonify({"error": "Collected data is not in a proper format for a DataFrame."})
            else:
                return render_template('index.html',
                                       error="Failed to collect data. Please provide a class name if required.")
        except Exception as e:
            session.rollback()
            return jsonify({"error": str(e)})

    # Check that the URL exists and there is no rescrape request
    if existing_entry and not rescrape:
        one_week_ago = datetime.now() - timedelta(weeks=1)
        if existing_entry.last_collected > one_week_ago:
            # The URL already exists and the data has been collected within a week, prompting the user
            return render_template('index.html', prompt_existing_data=True, last_collected=existing_entry.last_collected, table_name=existing_entry.table_name)

    # If the last collected date is more than a week, the request is processed normally
    table_name = existing_entry.table_name if existing_entry else f"data_{hash(url)}"
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

                # Generate special_id for the new data
                special_id = f"{table_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                df['special_id'] = special_id
                df['collected_at'] = datetime.now()

                df.to_sql(table_name, con=engine, index=False, if_exists='append')

                # Update the table of contents or add new entries
                if existing_entry:
                    existing_entry.last_collected = datetime.now()
                    existing_entry.special_id = special_id
                else:
                    new_entry = Directory(url=url, table_name=table_name, last_collected=datetime.now(), special_id=special_id)
                    session.add(new_entry)
                session.commit()

                # save data to CSV
                df.to_csv(csv_path, mode='w', index=False)
                return send_file(csv_path, as_attachment=True)
            else:
                return jsonify({"error": "Collected data is not in a proper format for a DataFrame."})
        else:
            return render_template('index.html',
                                   error="Failed to collect data. Please provide a class name if required.")
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
