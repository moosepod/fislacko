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
    if len(params):
        return SlackResponse('Please provide the name you will go by.')
    name = ' '.join(params)
    return SlackResponse('%s is now registered as %s' % (user_name,name),True)
