from flask import Flask, jsonify, request

from extractor.ExtractorService import ExtractorService


app = Flask(__name__)

@app.route('/')
def homepage():
    date = request.args.get('date')

    liturgy = ExtractorService.getScrapySagradaLiturgia(date)

    response = {
        'objective': 'A API_LITURGIA_DIARIA visa disponibilizar via api as leituras para facilitar a criação de aplicações que almejam a evangelização.',
        'source':'https://sagradaliturgia.com.br/',
        'today': liturgy
    }

    return jsonify(response)

@app.route('/cn')
def cancaoNova():
    liturgy = ExtractorService.getScrapyCancaoNova()

    response = {
        'objective': 'A API_LITURGIA_DIARIA visa disponibilizar via api as leituras para facilitar a criação de aplicações que almejam a evangelização.',
        'source':'Canção Nova',
        'today': liturgy
    }

    return jsonify(response)

