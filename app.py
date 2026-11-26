from datetime import datetime

import requests
from flask import Flask, jsonify, request

from extractor.ExtractorService import ExtractorService


app = Flask(__name__)


@app.before_request
def validate_date_parameter():
    date = request.args.get('date')
    if date is None:
        return None

    try:
        parsed_date = datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'A data deve estar no formato YYYY-MM-DD.'}), 400

    if parsed_date.strftime('%Y-%m-%d') != date:
        return jsonify({'error': 'A data deve estar no formato YYYY-MM-DD.'}), 400

    return None


@app.after_request
def allow_browser_clients(response):
    response.headers.setdefault('Access-Control-Allow-Origin', '*')
    return response


@app.errorhandler(requests.exceptions.RequestException)
def handle_upstream_failure(error):
    app.logger.warning('Falha ao consultar uma fonte externa: %s', error)
    return jsonify({'error': 'Não foi possível consultar a fonte litúrgica no momento.'}), 502


@app.route('/healthz')
def health_check():
    return jsonify({'status': 'ok'})


@app.route('/')
def homepage():
    date = request.args.get('date')

    try:
        liturgy = ExtractorService.getLiturgiaCNBB(date)
        source = 'CNBB'
    except (requests.exceptions.RequestException, AttributeError, IndexError, KeyError, ValueError):
        try:
            liturgy = ExtractorService.getScrapySagradaLiturgia(date)
            source = 'https://sagradaliturgia.com.br/'
        except (requests.exceptions.RequestException, AttributeError, IndexError, KeyError, ValueError):
            liturgy = ExtractorService.getScrapyCancaoNova()
            source = 'Canção Nova'

    response = {
        'objective': 'A API_LITURGIA_DIARIA visa disponibilizar via api as leituras para facilitar a criação de aplicações que almejam a evangelização.',
        'source': source,
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

@app.route('/cnbb')
def cnbb():
    liturgy = ExtractorService.getLiturgiaCNBB(request.args.get('date'))

    response = {
        'objective': 'A API_LITURGIA_DIARIA visa disponibilizar via api as leituras para facilitar a criação de aplicações que almejam a evangelização.',
        'source': 'CNBB',
        'today': liturgy
    }

    return jsonify(response)

@app.route('/santo-do-dia')
def santo():
    santo = ExtractorService.getScrapySantoCancaoNova()

    response = {
        'objective': 'A API_LITURGIA_DIARIA visa disponibilizar via api as leituras para facilitar a criação de aplicações que almejam a evangelização.',
        'source':'Canção Nova',
        'today': santo
    }

    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=False)