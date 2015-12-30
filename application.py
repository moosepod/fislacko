from flask import Flask,jsonify,request
from flask_restful import Resource, Api
import json
import commands

app = Flask(__name__)
api = Api(app)

COMMAND_MAPPINGS = {'reset_game': commands.reset_game,
                    'register': commands.register,
                    'status': commands.status,
                    'claim': commands.claim,
                    'give': commands.give,
                    'roll_pool': commands.roll_pool,
                    'roll': commands.roll,
                    'spend': commands.spend}
                    

@app.route('/game/<game_id>/',methods=['POST','GET'])
def router(game_id):
    data = request.form.get('text','').split(' ')
    userid = request.form.get('user_id')
    username = request.form.get('user_name')
    command = None
    params = []
    if data:
        command = COMMAND_MAPPINGS.get(data[0].lower())
        if len(data) > 1:
            params = data[1:]
    if command:
        return jsonify(command(params,userid,username).to_json())
    return u"""Usage: /slack command, where commands are:
reset_game: reset the game
pool: roll the dice for the pool
register [name]: register your player name with the game
status: request that the current game status be output to the channel
claim [color number]: claim a die from the pool
give [color number user]: give a die to another player
roll: roll all your dice and give the aggregate score
spend: spend one your dice (so you no longer have it)"""


if __name__ == '__main__':
    app.run(debug=True,host='104.236.212.18')
