import logging

from flask import Flask,jsonify,request

from game import GameState
import commands

app = Flask(__name__)
app.config.from_envvar('FISLACKO_SETTINGS')

COMMAND_MAPPINGS = {'reset': commands.reset_game,
                    'register': commands.register,
                    'unregister': commands.unregister,
                    'status': commands.status,
                    'setup': commands.setup,
                    'take': commands.take,
                    'give': commands.give,
                    'pool': commands.pool,
                    'roll': commands.roll,
                    'spend': commands.spend}
                    

@app.route('/fiasco/',methods=['POST','GET'])
def router():
    data = request.form.get('text','').split(' ')
    userid = request.form.get('user_id')
    username = request.form.get('user_name')
    game_id = request.form.get('channel_id')

    try:   
        return jsonify(route(game_id,data,userid,username))
    except Exception, e:
        logging.error(e)
        return jsonify({'text': 'Whoops! Error.'})

# Broken out to assist in testing
def route(game_id,data,userid,username):
    command = None
    params = []
    if data:
        command = COMMAND_MAPPINGS.get(data[0].lower())
        if len(data) > 1:
            params = data[1:]
    if command:
        game_state = GameState()
        game_state.load(game_id)
        try:
            return command(commands.Game(game_state),
                        params,userid,username).to_json()
        finally:
            game_state.save(game_id)
    return {'text': u"""Usage: /slack command, where commands are:
reset [confirm]:  reset the game if "confirm" is passed as the parameter
setup [add|remove]: display the current setup. If add is the parameter, add rest of text as setup text. If remove, remove the nth item.
pool [reroll|setup]: show the current dice pool. if setup passed as a parameter, setup the initial pool. if reroll passed in, reroll all dice in the pool.
register [name]: register your player name with the game
unregister [name]: unregister yourself or the specified user
status: output current status to channel
take [color number]: take a die from the pool
give [color number] [user]: give a die to another player. use "pool" as player name to return to the pool. 
roll: roll all your dice and give the aggregate score
spend: spend one your dice (so you no longer have it)"""}


if __name__ == '__main__':
    app.run(debug=True,host='104.236.212.18')
