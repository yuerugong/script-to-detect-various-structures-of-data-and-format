from flask import Flask, request, render_template, send_file, jsonify, redirect, url_for
import pandas as pd
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, String, Integer, Table, MetaData, DateTime, Boolean
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import hashlib
import cinando
import shutil
from sqlalchemy import create_engine, inspect
import subprocess

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

@app.route('/')
def index():
    cron_tasks = list_crontab_tasks()
    tables_info = session.query(Directory).all()
    return render_template('index.html', cron_tasks=cron_tasks, tables_info=tables_info)

@app.route('/scrape', methods=['POST'])
def scrape():
    url = request.form['url']
    email = request.form['email']
    password = request.form['password']
    auto_collect = 'auto_collect' in request.form
    collection_period = request.form.get('collection_period', 'none') if auto_collect else 'none'

    existing_entry = session.query(Directory).filter_by(url=url).first()
    table_name = existing_entry.table_name if existing_entry else generate_table_name(url)
    csv_path = f'{table_name}.csv'

    # Run the scraping code here (assuming it's implemented)
    try:
        print(f"Scraping URL: {url}")
        cinando.api_login_and_scrape(url, email, password)
        cinando.extract_bio_and_image_from_html('details', f'{table_name}.csv')
        df = pd.read_csv(f'{table_name}.csv')
        df = process_dataframe(df, table_name)
        df.to_csv(csv_path, mode='w', index=False)
        shutil.rmtree('details', ignore_errors=True)

        # If auto collection is enabled, add to crontab
        if auto_collect and collection_period != 'none':
            add_crontab_task(url, email, password, collection_period)

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

    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)})

    return send_file(csv_path, as_attachment=True)


@app.route('/delete_cron', methods=['POST'])
def delete_cron():
    task_id = int(request.form['task_id'])
    remove_crontab_task(task_id)
    return redirect(url_for('index'))


@app.route('/update_cron', methods=['POST'])
def update_cron():
    task_id = int(request.form['task_id'])
    new_period = request.form['new_period']
    update_crontab_task(task_id, new_period)
    return redirect(url_for('index'))


def list_crontab_tasks():
    result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
    tasks = []
    for line in result.stdout.splitlines():
        if not line.startswith('#') and line.strip():
            cron_info = parse_cron_line(line)
            if cron_info:
                tasks.append(cron_info)
    return tasks


def parse_cron_line(line):
    parts = line.split(maxsplit=5)
    if len(parts) < 6:
        return None
    schedule = ' '.join(parts[:5])
    command = parts[5]
    return {'period': schedule, 'command': command}


def add_crontab_task(url, email, password, period):
    cron_command = (f"/Users/gongyueru/anaconda3/python "
                    f"/Users/gongyueru/PycharmProjects/script\ to\ detect\ various\ structures\ of\ data\ and\ format/app.py "
                    f"scrape "
                    f"--url {url} --email {email} --password {password}")
    cron_time = ""
    if period == 'daily':
        cron_time = "0 0 * * *"
    elif period == 'weekly':
        cron_time = "0 0 * * 0"
    elif period == 'monthly':
        cron_time = "0 0 1 * *"

    new_cron_entry = f"{cron_time} {cron_command}\n"
    subprocess.run(['crontab', '-l'], stdout=open('cron_bak', 'w'))
    with open('cron_bak', 'a') as cron_file:
        cron_file.write(new_cron_entry)
    subprocess.run(['crontab', 'cron_bak'])
    os.remove('cron_bak')


def remove_crontab_task(task_id):
    with open('cron_bak', 'w') as cron_file:
        subprocess.run(['crontab', '-l'], stdout=cron_file)
    with open('cron_bak', 'r') as cron_file:
        lines = cron_file.readlines()
    if 0 <= task_id - 1 < len(lines):
        lines.pop(task_id - 1)
    with open('cron_bak', 'w') as cron_file:
        cron_file.writelines(lines)
    subprocess.run(['crontab', 'cron_bak'])
    os.remove('cron_bak')


def update_crontab_task(task_id, new_period):
    with open('cron_bak', 'w') as cron_file:
        subprocess.run(['crontab', '-l'], stdout=cron_file)
    with open('cron_bak', 'r') as cron_file:
        lines = cron_file.readlines()
    if 0 <= task_id - 1 < len(lines):
        command = parse_cron_line(lines[task_id - 1])['command']
        if new_period == 'daily':
            cron_time = "0 0 * * *"
        elif new_period == 'weekly':
            cron_time = "0 0 * * 0"
        elif new_period == 'monthly':
            cron_time = "0 0 1 * *"
        lines[task_id - 1] = f"{cron_time} {command}\n"
    with open('cron_bak', 'w') as cron_file:
        cron_file.writelines(lines)
    subprocess.run(['crontab', 'cron_bak'])
    os.remove('cron_bak')


def generate_table_name(url):
    return f"data_{hashlib.md5(url.encode()).hexdigest()}"


def process_dataframe(df, table_name):
    special_id = f"{table_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    df['special_id'] = special_id
    df['collected_at'] = datetime.now()
    df.to_sql(table_name, con=engine, index=False, if_exists='append')
    return df


if __name__ == '__main__':
    app.run(debug=True)
