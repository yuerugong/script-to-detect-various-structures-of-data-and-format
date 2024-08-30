from flask import Flask, request, render_template, send_file, jsonify, redirect, url_for
import pandas as pd
import main2
import os

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/scrape', methods=['POST'])
def scrape():
    url = request.form['url']
    class_name = request.form.get('class_name')
    csv_path = 'data.csv'

    try:
        print(f"Scraping URL: {url}")
        data = main2.scrape_with_fallback(url, class_name)

        if data:
            print("Data collected successfully")
            if isinstance(data, (list, dict)):
                df = pd.DataFrame(data)

                if not os.path.exists(csv_path):
                    df.to_csv(csv_path, mode='w', index=False)
                else:
                    df.to_csv(csv_path, mode='a', index=False, header=not pd.read_csv(csv_path).empty)

                return send_file(csv_path, as_attachment=True)
            else:
                return jsonify({"error": "Collected data is not in a proper format for a DataFrame."})
        else:
            return render_template('index.html',
                                   error="Failed to collect data. Please provide a class name if required.")
    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == '__main__':
    print("Starting Flask app...")
    app.run(debug=True)
