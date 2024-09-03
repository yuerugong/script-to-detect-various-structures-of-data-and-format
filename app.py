from flask import Flask, request, render_template, send_file, jsonify, redirect, url_for
import pandas as pd
import main2
import os
from sqlalchemy import create_engine, Column, String, Integer, Table, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

app = Flask(__name__)

# 初始化SQLAlchemy
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


Base.metadata.create_all(engine)


@app.route('/')
def index():
    tables_info = session.query(Directory).all()
    return render_template('index.html', tables_info=tables_info)


@app.route('/scrape', methods=['POST'])
def scrape():
    url = request.form['url']
    class_name = request.form.get('class_name')
    table_name = f"data_{hash(url)}"  # Generate a unique table name
    csv_path = f'{table_name}.csv'  # Use table names to generate CSV file names

    try:
        print(f"Scraping URL: {url}")
        data = main2.scrape_with_fallback(url, class_name)

        if data:
            print("Data collected successfully")
            if isinstance(data, (list, dict)):
                df = pd.DataFrame(data)
                for col in df.columns:
                    df[col] = df[col].apply(lambda x: str(x) if isinstance(x, list) else x)

                df.to_sql(table_name, con=engine, index=False, if_exists='replace')  # 将数据保存到数据库

                # Insert the URL and table name into the catalog table
                new_entry = Directory(url=url, table_name=table_name)
                session.add(new_entry)
                session.commit()

                # Save data to CSV
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



@app.route('/view_table/<table_name>', methods=['GET'])
def view_table(table_name):
    try:
        # Reads the data table from the database
        df = pd.read_sql_table(table_name, con=engine)
        # covert data to HTML
        table_html = df.to_html(classes='data')
        return render_template('view_table.html', table_html=table_html)
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/delete_table/<table_name>', methods=['GET'])
def delete_table(table_name):
    try:
        # Delete database table
        metadata.reflect()
        if table_name in metadata.tables:
            table_to_delete = metadata.tables[table_name]
            table_to_delete.drop(engine)
            print(f"Table {table_name} deleted successfully.")

        # Delete a record from the catalog table
        session.query(Directory).filter(Directory.table_name == table_name).delete()
        session.commit()

        return redirect(url_for('index'))
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)})


if __name__ == '__main__':
    print("Starting Flask app...")
    app.run(debug=True)
