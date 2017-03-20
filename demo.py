#!/usr/bin/env python3

from flask import Flask, redirect, request

from resumable import rebuild, split

app = Flask(__name__)


# for the purposes of this demo, we will explicitly pass request
# and response (this is not needed in flask)
@rebuild
def controller(request):
    page = '''
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
    <form action="/c/welcomed" method=post>
        <input name="name"/>
        <button type=submit>Submit</button>
    </form>
    '''

    response = split(lambda: page, 'welcomed')()

    page = '''
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
    <form action="/c/my_name" method=post>
        <label>
            Hi, {}, my name is
            <input name="my_name"/>
        </label>
        <button type=submit>Submit</button>
    </form>
    '''.format(response.form['name'])

    response = split(lambda: page, 'my_name')()

    return split(lambda: 'Sweet, my name is {}!'.format(response.form['my_name']))()


@app.route('/c/<name>', methods=['POST', 'GET'])
def router(name):
    return controller[name](request)


@app.route('/')
def index():
    return redirect('/c/controller')



if __name__ == '__main__':
    app.run(debug=True)


