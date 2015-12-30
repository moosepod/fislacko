from flask import Flask,jsonify,request
from flask_restful import Resource, Api
import json
import commands

app = Flask(__name__)
api = Api(app)

COMMAND_MAPPINGS = {'reset_game': commands.reset_game,
                    'register': commands.register}
                    

@app.route('/game/<game_id>/',methods=['POST','GET'])
def router(game_id):
    data = request.form.get('text','').split(' ')
    userid = request.form.get('user_id')
    username = request.form.get('user_name')
    command = None
    params = None
    if data:
        command = COMMAND_MAPPINGS.get(data[0].lower())
        if len(data) > 1:
            params = data[1:]
    if command:
        return jsonify(command(params,userid,username).to_json())
    return u'Error! Unknown command'

if __name__ == '__main__':
    app.run(debug=True,host='104.236.212.18')
