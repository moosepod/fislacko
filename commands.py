""" Contains the commands for the Fiasco/Slack web service
"""
import random

class SlackResponse(object):
    def __init__(self,text,in_channel=False):
        self.text = text
        if in_channel:
            self.response_type='in_channel'
        else:
            self.response_type='ephemeral'

    def to_json(self):
        return {'text': self.text, 'response_type': self.response_type}

def reset_game(game,path,params,user_id,user_name):
    """ Reset the game """
    if len(params) == 1 and params[0].lower() == 'yes':
        game.delete(path,'users')
        game.delete(path,'dice')
        return SlackResponse('%s has reset the game.' % user_name)
    
    return SlackResponse('To reset, pass in confirm as the parameter')   

def register(game,path,params,user_id,user_name):
    """ Register the logged in user as a given character """
    # Take in name
    # Store name
    if not len(params):
        return SlackResponse('Please provide the name you will go by.')
    name = ' '.join(params)
    game.put('%s/users' % path,user_id,{'name':name,'slack_name': user_name})
    return SlackResponse('%s is now registered as %s' % (user_name,name),True)

def status(game,path,params,user_id,user_name):
    """ Send game status to channel """
    player_a = []
    users = game.get(path,'users')
    for v in users.values():
        player_a.append(u'%s (%s)' % (v['name'],v['slack_name']))
    return SlackResponse("""Players: %s

%s""" % (u"\n".join(player_a),
               format_dice_pool(game.get(path,'dice'))),True)

def claim(game,path,params,user_id,user_name):
    """ Claim a specific die """
    # Take color + number
    # Verify die
    # take die
    # Print status
    return SlackResponse("%s claimed die" % (user_name),True)

def give(game,path,params,user_id,user_name):
    """ Give one of your dice to someone else """
    return SlackResponse("%s gave dice" % (user_name),True)

def roll(game,path,params,user_id,user_name):
    """ Roll a user's dice and show the sum """
    return SlackRespones("%s rolled: " % user_name,True)

def roll_pool(game,path,params,user_id,user_name):
    """ Reroll the central dice pool. Should be two black and two white dice for each user """
    dice = {'black': [],'white': []}
    user_count = len(game.get(path,'users'))
    for l in (dice['black'],dice['white']):
        for i in range((user_count*2)):
            l.append(random.randint(1,6))
    game.put(path,'dice',dice)
    return SlackResponse("""Pool recreated.

%s
""" % format_dice_pool(dice),True)

numbers=['zero','one','two','three','four','five','six']

def format_dice_pool(dice):
    return """White:
%s

Black
%s
""" % (''.join([u':%s:' % numbers[x] for x in dice['black']]),
       ','.join([u':%s:' % numbers[x] for x in dice['white']]))

def spend(game,path,params,user_id,user_name):
    """ Let a user spend one of their dice """
    # Take color and number
    # Verify
    return SlackResponse("Spent")
