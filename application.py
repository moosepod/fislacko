import logging

from flask import Flask,jsonify,request

from firebase import firebase

import commands

app = Flask(__name__)
app.config.from_envvar('FISLACKO_SETTINGS')

COMMAND_MAPPINGS = {'reset_game': commands.reset_game,
                    'register': commands.register,
                    'status': commands.status,
                    'claim': commands.claim,
                    'give': commands.give,
                    'roll_pool': commands.roll_pool,
                    'roll': commands.roll,
                    'spend': commands.spend}
                    

@app.route('/fiasco/',methods=['POST','GET'])
def router():
    data = request.form.get('text','').split(' ')
    userid = request.form.get('user_id')
    username = request.form.get('user_name')
    game_id = request.form.get('channel_id')

    try:   
        return jsonify(route(game_id,data,userid,username,app.config['FIREBASE_URL']))
    except Exception, e:
        logging.error(e)
        return jsonify({'text': 'Whoops! Error.'})

# Broken out to assist in testing
def route(game_id,data,userid,username,firebase_url):
    command = None
    params = []
    if data:
        command = COMMAND_MAPPINGS.get(data[0].lower())
        if len(data) > 1:
            params = data[1:]
    if command:
        # Setup our firebase connection for the request
        fb = firebase.FirebaseApplication(firebase_url,None)
        game = fb.get('/games',game_id)  
        if not game:
            fb.put('/games',game_id,{'active': True})
        return command(commands.Game(fb,'/games/%s' % game_id),
                        params,userid,username).to_json()
    return {'text': u"""Usage: /slack command, where commands are:
reset_game: reset the game
pool: roll the dice for the pool
register [name]: register your player name with the game
status: request that the current game status be output to the channel
claim [color number]: claim a die from the pool
give [color number user]: give a die to another player
roll: roll all your dice and give the aggregate score
spend: spend one your dice (so you no longer have it)"""}


if __name__ == '__main__':
    app.run(debug=True,host='104.236.212.18')
