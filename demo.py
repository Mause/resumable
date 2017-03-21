#!/usr/bin/env python3

from flask import Flask, redirect, request

from resumable import rebuild, value

app = Flask(__name__)

def form(action, contents):
    return '''
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
    <form action="{}" method=post>
        {}
        <button type=submit>Submit</button>
    </form>
    '''.format(action, contents)

# for the purposes of this demo, we will explicitly pass request
# and response (this is not needed in flask)
@rebuild
def controller(_):
    page = form('/c/welcomed', '<input name="name"/>')

    response = value(page, 'welcomed')

    page = form(
        '/c/my_name', 
        '''
        <label>
            Hi, {}, my name is
            <input name="my_name"/>
        </label>
        '''.format(response.form['name'])
    )

    response = value(page, 'my_name')

    return value('Sweet, my name is {}!'.format(response.form['my_name']))


@app.route('/c/<name>', methods=['POST', 'GET'])
def router(name):
    return controller[name](request)


@app.route('/')
def index():
    return redirect('/c/controller')



if __name__ == '__main__':
    app.run(debug=True)


