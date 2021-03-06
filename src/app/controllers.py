import os
import time

import flask

import api
from app import sharabelwasl
from app import settings
from api.translate import GoogleTranslator
from transliterate import translit

translator = GoogleTranslator()

# routing for basic pages (pass routing onto the Angular app)
@sharabelwasl.route('/')
def basic_pages(**kwargs):
    now = int(round(time.time() * 1000))
    return flask.render_template('index.html', now=now)

# special file handlers and error handlers
@sharabelwasl.route('/favicon.ico')
def favicon():
    return flask.send_from_directory(os.path.join(sharabelwasl.root_path, 'static'),
                               'img/favicon.ico')


@sharabelwasl.errorhandler(404)
def page_not_found(e):
    return flask.render_template('404.html'), 404

@sharabelwasl.route('/partial/<name>')
def hello(name=None):
    return flask.render_template('{}.html'.format(name))

@sharabelwasl.route('/uib/template/tooltip/tooltip-popup.html')
def popup():
    return flask.render_template('popover.html')

@sharabelwasl.route('/resources/<name>')
def resources(name=None):
    return flask.make_response(open('app/resources/{}'.format(name)).read())

@sharabelwasl.route('/search/<lang>/<term>')
# @api.make_ajax
def search(term=None, lang=None):
    
    terms = {lang:term}
    keys = ['_title', '_first', '_second']

    if lang != 'ar':
        #let's translit the word
        term1 = ""
        term2 = ""
        try:
            detect = translator.detect(term)
            detect = detect[0][0]

            if detect['language'] not in settings.LANGUAGES.keys() \
                or not bool(detect['isReliable']):
                
                term1 = translit(term.lower(), 'ar').encode('utf-8')
                print '>>',term1
                term2 = translator.translate(term1, source="ar", target=lang)[0]['translatedText']

                terms['ar'] = term1.decode('utf-8')
                terms[lang] = term2
        except Exception, e:
            sharabelwasl.logger.exception("exception in translit logic ")
    
    sharabelwasl.logger.info(u'executing search for terms %s .  Original query is %s %s' % (terms, term, lang))
    
    es_results, ordered = api.search(terms)
    ordered.append(['terms', terms])
    sharabelwasl.logger.info(u'returning  %d qasidas' % len(ordered))
    response = dict(next='search',data=ordered)
    return flask.jsonify(response)

@sharabelwasl.route('/read/<number>')
# @api.make_ajax
def read(number=None):
    verses = api.read(number)
    return flask.render_template('verses.html', verses=verses)

@sharabelwasl.route('/dynamo/scan/<lang>/<qasida_number>/<line_number>')
# @api.make_ajax
def scan(lang=None, qasida_number=None, line_number=None):

    response = api.scan(lang, qasida_number, line_number)
    items = sorted(response['Items'], key=lambda i: (int(i['vote_average'])), reverse=True)
    items = [{key:str(val) for key, val in item.items()} for item in items]
    items = items[0] if len(items) > 0 else items

    response = dict(next='show_translation',data=items)
    return flask.jsonify(response)

@sharabelwasl.route('/dynamo/update/<lang>/<uuid>/<is_up>/<vote>')
# @api.make_ajax
def update(lang=None, uuid=None, is_up=1, vote=None):

    response = api.update(lang, uuid, vote, is_up_vote=bool(int(is_up)))
    print ' >>>>>>>>>> ', bool(int(is_up)), is_up
    response = dict(next='show_vote',data=[{key:str(val) for key, val in response['Attributes'].items()}][0])
    print '..............', response
    return flask.jsonify(response)

@sharabelwasl.route('/dynamo/add/<lang>/<qasida_number>/<line_number>/<user_first>/<user_second>')
# @api.make_ajax
def add(lang=None, qasida_number=None, line_number=None, user_first=None, user_second=None):

    data = api.add(lang, qasida_number, line_number, user_first, user_second)
    
    response = dict(next='updated_translation',data=data)
    print '..............', response
    return flask.jsonify(response)
