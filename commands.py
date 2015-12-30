""" Contains the commands for the Fiasco/Slack web service
"""

class SlackResponse(object):
    def __init__(self,text,in_channel=False):
        self.text = text
        if in_channel:
            self.response_type='in_channel'
        else:
            self.response_type='ephemeral'

    def to_json(self):
        return {'text': self.text, 'response_type': self.response_type}

def reset_game(params,user_id,user_name):
    """ Reset the game """
    if len(params) == 1 and params[0].lower() == 'yes':
        return SlackResponse('%s has reset the game.' % user_name)
    return SlackResponse('To reset, pass in confirm as the parameter')   

def register(params,user_id,user_name):
    """ Register the logged in user as a given character """
    # Take in name
    # Store name
    if not len(params):
        return SlackResponse('Please provide the name you will go by.')
    name = ' '.join(params)
    return SlackResponse('%s is now registered as %s' % (user_name,name),True)

def status(params,user_id,user_name):
    """ Send game status to channel """
    # NO parameters
    return SlackResponse("Status: test",True)

def claim(params,user_id,user_name):
    """ Claim a specific die """
    # Take color + number
    # Verify die
    # take die
    # Print status
    return SlackResponse("%s claimed die" % (user_name),True)

def give(params,user_id,user_name):
    """ Give one of your dice to someone else """
    return SlackResponse("%s gave dice" % (user_name),True)

def roll(params,user_id,user_name):
    """ Roll a user's dice and show the sum """
    return SlackRespones("%s rolled: " % user_name,True)

def roll_pool(params,user_id,user_name):
    """ Reroll the central dice pool """
    return SlackResponse("Pool recreated.",True)

def spend(params,user_id,user_name):
    """ Let a user spend one of their dice """
    # Take color and number
    # Verify
    return SlackResponse("Spent")
